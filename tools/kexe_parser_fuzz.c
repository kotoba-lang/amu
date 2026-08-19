#define _GNU_SOURCE
#include <setjmp.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

/* Reuse the production parser implementation in the same translation unit. */
#define main kexe_loader_main_not_used_by_fuzzer
#define KEXE_SANITIZER_TEST 1
#include "kexe_loader.c"
#undef main

#if defined(__has_feature)
#if __has_feature(address_sanitizer)
#define KEXE_FUZZ_ASAN 1
#endif
#elif defined(__SANITIZE_ADDRESS__)
#define KEXE_FUZZ_ASAN 1
#endif

#if defined(KEXE_FUZZ_ASAN)
#include <sanitizer/asan_interface.h>
#define KEXE_POISON(pointer, size) __asan_poison_memory_region((pointer), (size))
#define KEXE_UNPOISON(pointer, size) __asan_unpoison_memory_region((pointer), (size))
#else
#define KEXE_POISON(pointer, size) ((void)(pointer), (void)(size))
#define KEXE_UNPOISON(pointer, size) ((void)(pointer), (void)(size))
#endif

/* ---------------------------------------------------------------------------
 * Input cursor. Running off the end yields zeroes rather than wrapping, so a
 * short input is a short op sequence instead of a repeating one.
 * ------------------------------------------------------------------------ */

struct fuzz_cursor {
  const uint8_t *data;
  size_t size;
  size_t at;
};

static uint8_t take_u8(struct fuzz_cursor *cursor) {
  if (cursor->at >= cursor->size) return 0;
  return cursor->data[cursor->at++];
}

static uint64_t take_u64(struct fuzz_cursor *cursor) {
  uint64_t value = 0;
  for (int i = 0; i < 8; i++) value = (value << 8) | (uint64_t)take_u8(cursor);
  return value;
}

static int exhausted(const struct fuzz_cursor *cursor) {
  return cursor->at >= cursor->size;
}

/* ---------------------------------------------------------------------------
 * Reach counters.
 *
 * A fuzz target that never reaches the function it names answers "no defect"
 * for the same reason a check with no input does, and looks identical from the
 * outside. The first draft of this file had exactly that shape: the result
 * handle was drawn as a raw 64-bit word, so it landed inside the 32-entry pair
 * table roughly never, and a deliberately broken `inspect_string_result`
 * survived 20,000 cases. These counters are printed at exit and the runner
 * refuses a run in which any of them is zero.
 * ------------------------------------------------------------------------ */

struct fuzz_reach {
  uint64_t inputs;
  uint64_t operations_completed;
  uint64_t operations_trapped;
  uint64_t string_bytes_read;
  uint64_t dataspace_calls;
  uint64_t string_result_read;
  uint64_t record_result_read;
  uint64_t tagged_result_read;
  uint64_t variant_result_read;
  uint64_t string_handle_accepted;
};

static struct fuzz_reach fuzz_reach;

static void fuzz_report_reach(void) {
  fprintf(stderr,
          "{:format :kotoba.fuzz-reach/v1"
          " :inputs %llu :ops-completed %llu :ops-trapped %llu"
          " :string-bytes-read %llu :dataspace-calls %llu"
          " :string-result %llu :record-result %llu :tagged-result %llu"
          " :variant-result %llu :string-handle %llu}\n",
          (unsigned long long)fuzz_reach.inputs,
          (unsigned long long)fuzz_reach.operations_completed,
          (unsigned long long)fuzz_reach.operations_trapped,
          (unsigned long long)fuzz_reach.string_bytes_read,
          (unsigned long long)fuzz_reach.dataspace_calls,
          (unsigned long long)fuzz_reach.string_result_read,
          (unsigned long long)fuzz_reach.record_result_read,
          (unsigned long long)fuzz_reach.tagged_result_read,
          (unsigned long long)fuzz_reach.variant_result_read,
          (unsigned long long)fuzz_reach.string_handle_accepted);
}

static void fuzz_arm_reach_report(void) {
  static int armed = 0;
  if (armed) return;
  armed = 1;
  (void)atexit(fuzz_report_reach);
}

/* A word that is plausible where the loader expects one. Uniformly random
 * 64-bit values are rejected by the first bound they meet, so drawing them
 * exclusively keeps the input outside every body worth testing; a raw word is
 * still drawn one time in eight, because that is what a miscompiled or hostile
 * guest actually leaves in a register. */
static int64_t fuzz_word(struct fuzz_cursor *cursor, uint64_t code_length,
                         uint64_t pool_used) {
  switch (take_u8(cursor) % 8u) {
    case 0:
    case 1:
      return (int64_t)((uint64_t)take_u8(cursor) % 64u);
    case 2:
      return (int64_t)((uint64_t)take_u8(cursor) % (code_length + 1u));
    case 3:
      return -(int64_t)((uint64_t)take_u8(cursor) % (pool_used + 1u)) - 1;
    case 4:
    case 5:
      return (int64_t)((uint64_t)take_u8(cursor) % 40u);
    case 6:
      return (int64_t)(int8_t)take_u8(cursor);
    default:
      return (int64_t)take_u64(cursor);
  }
}

/* ---------------------------------------------------------------------------
 * Trap unwinding.
 *
 * Every `checked_*` helper answers an invalid handle with `raise(SIGILL)`, and
 * in the real loader `trap_handler` ends the process with `_exit(120)` -- the
 * raise NEVER returns. That matters for fidelity: `checked_string_equal`, for
 * one, calls `resolve_string_bytes` twice and memcmp's the results without a
 * NULL test, which is sound ONLY because a NULL is unreachable. A handler that
 * returned would manufacture a crash production cannot have.
 *
 * So the handler here does not return either: it siglongjmp's past the rest of
 * the trapping helper, which models `_exit(120)`'s "the operation does not
 * complete" without ending the fuzzer. The caller then rewinds the arena
 * watermarks to their pre-op values, so the state the next op sees is one some
 * shorter op sequence could have produced -- never a torn intermediate.
 * ------------------------------------------------------------------------ */

static sigjmp_buf fuzz_trap_return;
static volatile sig_atomic_t fuzz_inside_guest_call;

static void fuzz_trap_handler(int signal_number) {
  (void)signal_number;
  if (!fuzz_inside_guest_call) _exit(120);
  fuzz_inside_guest_call = 0;
  siglongjmp(fuzz_trap_return, 1);
}

static void install_fuzz_trap_handler(void) {
  static int installed = 0;
  if (installed) return;
  installed = 1;
  struct sigaction action;
  memset(&action, 0, sizeof(action));
  action.sa_handler = fuzz_trap_handler;
  sigemptyset(&action.sa_mask);
  action.sa_flags = SA_NODEFER;
  (void)sigaction(SIGILL, &action, NULL);
}

/* ---------------------------------------------------------------------------
 * Shared-state lifecycle.
 *
 * The arena is heap allocated per input rather than static, so a walk off the
 * end of `vector_items` (the last member) is an ASan heap overflow instead of
 * a silent read into whatever the previous input left behind.
 * ------------------------------------------------------------------------ */

struct ds_snapshot {
  int64_t next_facet;
  uint8_t live_facets[sizeof(ds_live_facets)];
  struct ds_item asserts[DS_MAX_ITEMS];
  struct ds_item observers[DS_MAX_ITEMS];
  uint8_t mail_bytes[DS_MAX_MAIL][DS_MAX_BYTES];
  uint64_t mail_len[DS_MAX_MAIL];
  int mail_kind[DS_MAX_MAIL];
  int mail_count;
};

static void ds_save(struct ds_snapshot *out) {
  out->next_facet = ds_next_facet;
  memcpy(out->live_facets, ds_live_facets, sizeof(ds_live_facets));
  memcpy(out->asserts, ds_asserts, sizeof(ds_asserts));
  memcpy(out->observers, ds_observers, sizeof(ds_observers));
  memcpy(out->mail_bytes, ds_mail_bytes, sizeof(ds_mail_bytes));
  memcpy(out->mail_len, ds_mail_len, sizeof(ds_mail_len));
  memcpy(out->mail_kind, ds_mail_kind, sizeof(ds_mail_kind));
  out->mail_count = ds_mail_count;
}

static void ds_restore(const struct ds_snapshot *in) {
  ds_next_facet = in->next_facet;
  memcpy(ds_live_facets, in->live_facets, sizeof(ds_live_facets));
  memcpy(ds_asserts, in->asserts, sizeof(ds_asserts));
  memcpy(ds_observers, in->observers, sizeof(ds_observers));
  memcpy(ds_mail_bytes, in->mail_bytes, sizeof(ds_mail_bytes));
  memcpy(ds_mail_len, in->mail_len, sizeof(ds_mail_len));
  memcpy(ds_mail_kind, in->mail_kind, sizeof(ds_mail_kind));
  ds_mail_count = in->mail_count;
}

static void ds_clear(void) {
  ds_next_facet = 1;
  memset(ds_live_facets, 0, sizeof(ds_live_facets));
  memset(ds_asserts, 0, sizeof(ds_asserts));
  memset(ds_observers, 0, sizeof(ds_observers));
  memset(ds_mail_bytes, 0, sizeof(ds_mail_bytes));
  memset(ds_mail_len, 0, sizeof(ds_mail_len));
  memset(ds_mail_kind, 0, sizeof(ds_mail_kind));
  ds_mail_count = 0;
}

/* The code+literal region is allocated at its EXACT length, unlike the real
 * loader's page-rounded mapping. A read one byte past `code_length` faults
 * here and merely reads padding there -- but it is a defect either way, since
 * `code_length` is the whole bound `resolve_string_bytes` and
 * `inspect_string_result` are given to work with. */
static struct kexe_shared_v3 *fuzz_open(struct fuzz_cursor *cursor,
                                        uint8_t **code_out,
                                        uint64_t *code_length_out) {
  struct kexe_shared_v3 *shared = (struct kexe_shared_v3 *)malloc(sizeof *shared);
  if (shared == NULL) return NULL;
  memset(shared, 0, sizeof *shared);
  /* At least one byte, never zero -- `main` refuses `length <= 0` before it
   * maps anything, so a live context always has a non-NULL `code_base` over at
   * least one byte. An empty region is a state the loader cannot be in, and
   * constructing one here made the harness report a defect that production
   * cannot reach: with `code_base` NULL and a zero-length string handle,
   * `resolve_string_bytes` evaluates `code_base + 0`, and UBSan called it
   * `applying zero offset to null pointer`.
   *
   * That report is version-dependent, which is the more useful half of the
   * lesson. C23 made `NULL + 0` well defined; Apple clang 21 on the authoring
   * workstation says nothing, Apple clang 17 on fleet node simeon fails the
   * run. The gate was green locally and red on the fleet for a difference that
   * is neither in the loader nor in the input. `scripts/fuzz-native.cljs` now
   * records the compiler in the summary so a verdict carries the toolchain
   * that produced it.
   *
   * The repair is fidelity, not suppression: remove the unreachable state
   * rather than teach the loader about a NULL it never receives. */
  uint64_t code_length = 1u + (uint64_t)(take_u8(cursor) % 128u);
  /* Half the artifacts carry ASCII literal data. Uniformly random bytes fail
   * `valid_utf8` almost always, and every string operation checks it before
   * touching a byte, so an all-random region would leave those bodies
   * unreached -- the same blindness the reach counters exist to catch. */
  int ascii = (take_u8(cursor) & 1u) != 0;
  uint8_t *code = (uint8_t *)malloc((size_t)code_length);
  if (code == NULL) { free(shared); return NULL; }
  for (uint64_t i = 0; i < code_length; i++) {
    uint8_t byte = take_u8(cursor);
    code[i] = ascii ? (uint8_t)(0x20u + (byte % 0x5fu)) : byte;
  }
  shared->context.version = 3;
  shared->context.fuel = 512;
  shared->context.code_base = code;
  shared->context.code_length = code_length;
  /* Capability admission is argv-driven and already covered by parse_allow.
   * Granting everything here puts the OPERATIONS behind the mask in reach. */
  for (int i = 0; i < 4; i++) shared->context.allow[i] = ~UINT64_C(0);
  ds_clear();
  *code_out = code;
  *code_length_out = code_length;
  return shared;
}

static void fuzz_close(struct kexe_shared_v3 *shared, uint8_t *code) {
  free(code);
  free(shared);
}

/* ---------------------------------------------------------------------------
 * Sub-target 1: the live handle graph.
 *
 * Drives the `checked_*` context callbacks -- every operation a guest can
 * reach through the KEXE ABI -- against an arena the input builds up. Operands
 * come from a register file written by earlier results, so plausible handles
 * are cheap to produce and the sequence reaches depth; a minority mode injects
 * a raw 64-bit word instead, which is what a miscompiled or hostile guest
 * would put in a register.
 * ------------------------------------------------------------------------ */

#define FUZZ_REGISTERS 16
#define FUZZ_MAX_OPERATIONS 48

enum fuzz_arena { FUZZ_ARENA_PAIR, FUZZ_ARENA_VECTOR };

struct fuzz_marks {
  uint64_t pair_used;
  uint64_t kgraph_used;
  uint64_t string_pool_used;
  uint64_t vector_used;
  uint64_t vector_item_used;
};

static void marks_save(const struct kexe_shared_v3 *shared,
                       struct fuzz_marks *marks) {
  marks->pair_used = shared->pair_used;
  marks->kgraph_used = shared->kgraph_used;
  marks->string_pool_used = shared->string_pool_used;
  marks->vector_used = shared->vector_used;
  marks->vector_item_used = shared->vector_item_used;
}

static void marks_restore(struct kexe_shared_v3 *shared,
                          const struct fuzz_marks *marks) {
  shared->pair_used = marks->pair_used;
  shared->kgraph_used = marks->kgraph_used;
  shared->string_pool_used = marks->string_pool_used;
  shared->vector_used = marks->vector_used;
  shared->vector_item_used = marks->vector_item_used;
}

static int64_t fuzz_value(struct fuzz_cursor *cursor, const int64_t *registers) {
  uint8_t selector = take_u8(cursor);
  if (selector >= 0xf0) return (int64_t)take_u64(cursor);
  return registers[selector % FUZZ_REGISTERS];
}

static int64_t fuzz_handle(struct fuzz_cursor *cursor, const int64_t *registers,
                           const struct kexe_shared_v3 *shared,
                           enum fuzz_arena arena) {
  uint8_t selector = take_u8(cursor);
  if (selector >= 0xf0) return (int64_t)take_u64(cursor);
  if (selector >= 0x60) {
    uint64_t live = arena == FUZZ_ARENA_PAIR ? shared->pair_used
                                             : shared->vector_used;
    if (live == 0) return 0;
    return (int64_t)(1u + (uint64_t)take_u8(cursor) % live);
  }
  return registers[selector % FUZZ_REGISTERS];
}

static int64_t fuzz_dispatch(struct fuzz_cursor *cursor, int64_t *registers,
                             struct kexe_shared_v3 *shared, uint8_t operation) {
  struct kexe_context_v3 *context = &shared->context;
  switch (operation % 20u) {
    case 0:
      return checked_pair_new(context, fuzz_value(cursor, registers),
                              fuzz_value(cursor, registers));
    case 1:
      return checked_pair_first(
          context, fuzz_handle(cursor, registers, shared, FUZZ_ARENA_PAIR));
    case 2:
      return checked_pair_second(
          context, fuzz_handle(cursor, registers, shared, FUZZ_ARENA_PAIR));
    case 3:
      return checked_vector_new_empty(context);
    case 4:
      return checked_vector_conj(
          context, fuzz_handle(cursor, registers, shared, FUZZ_ARENA_VECTOR),
          fuzz_value(cursor, registers));
    case 5:
      return checked_vector_count(
          context, fuzz_handle(cursor, registers, shared, FUZZ_ARENA_VECTOR));
    case 6:
      return checked_vector_at(
          context, fuzz_handle(cursor, registers, shared, FUZZ_ARENA_VECTOR),
          fuzz_value(cursor, registers));
    case 7:
      return checked_vector_assoc(
          context, fuzz_handle(cursor, registers, shared, FUZZ_ARENA_VECTOR),
          fuzz_value(cursor, registers), fuzz_value(cursor, registers));
    case 8:
      return checked_vector_drop(
          context, fuzz_handle(cursor, registers, shared, FUZZ_ARENA_VECTOR),
          fuzz_value(cursor, registers));
    case 9:
      return checked_kgraph_assert(context, fuzz_value(cursor, registers),
                                   fuzz_value(cursor, registers),
                                   fuzz_value(cursor, registers));
    case 10:
      return checked_kgraph_get(context, fuzz_value(cursor, registers),
                                fuzz_value(cursor, registers));
    case 11:
      return checked_kgraph_count(context, fuzz_value(cursor, registers));
    case 12:
      return checked_kgraph_entity_at(context, fuzz_value(cursor, registers),
                                      fuzz_value(cursor, registers));
    case 13:
      return checked_string_equal(
          context, fuzz_handle(cursor, registers, shared, FUZZ_ARENA_PAIR),
          fuzz_handle(cursor, registers, shared, FUZZ_ARENA_PAIR));
    case 14:
      return checked_string_concat(
          context, fuzz_handle(cursor, registers, shared, FUZZ_ARENA_PAIR),
          fuzz_handle(cursor, registers, shared, FUZZ_ARENA_PAIR));
    case 15:
      return checked_string_substring(
          context, fuzz_handle(cursor, registers, shared, FUZZ_ARENA_PAIR),
          fuzz_value(cursor, registers), fuzz_value(cursor, registers));
    case 16:
      return checked_string_code_point_at(
          context, fuzz_handle(cursor, registers, shared, FUZZ_ARENA_PAIR),
          fuzz_value(cursor, registers));
    case 17:
      return checked_cap_call(context, (uint64_t)take_u8(cursor),
                              fuzz_value(cursor, registers));
    case 18: {
      uint64_t request_kind = 1u + (uint64_t)(take_u8(cursor) % 5u);
      /* Mostly well-formed (the helper rejects a mismatch outright), but a
       * minority carry a different result kind so the rejection path itself
       * is exercised. */
      uint64_t result_kind =
          (take_u8(cursor) & 0x0fu) == 0 ? 1u + (uint64_t)(take_u8(cursor) % 5u)
                                         : request_kind;
      return checked_typed_cap_call(
          context, (uint64_t)take_u8(cursor), request_kind, result_kind,
          fuzz_handle(cursor, registers, shared, FUZZ_ARENA_PAIR));
    }
    default: {
      /* A literal string handle as `emit-string-literal` builds one: a pair
       * over the artifact's own code+literal region. Sometimes in range,
       * sometimes not. */
      uint64_t span = shared->context.code_length + 1u;
      int64_t offset = (int64_t)((uint64_t)take_u8(cursor) % span);
      int64_t length = (int64_t)((uint64_t)take_u8(cursor) % 40u);
      return checked_pair_new(context, offset, length);
    }
  }
}

static void fuzz_handle_graph(const uint8_t *data, size_t size) {
  struct fuzz_cursor cursor = {data, size, 0};
  uint8_t *code = NULL;
  uint64_t code_length = 0;
  struct kexe_shared_v3 *shared = fuzz_open(&cursor, &code, &code_length);
  if (shared == NULL) return;

  int64_t registers[FUZZ_REGISTERS];
  for (int i = 0; i < FUZZ_REGISTERS; i++) registers[i] = 0;

  install_fuzz_trap_handler();
  fuzz_arm_reach_report();

  for (int step = 0; step < FUZZ_MAX_OPERATIONS && !exhausted(&cursor); step++) {
    uint8_t operation = take_u8(&cursor);
    uint8_t destination = (uint8_t)(take_u8(&cursor) % FUZZ_REGISTERS);
    struct fuzz_marks marks;
    struct ds_snapshot dataspace;
    int dataspace_op = (operation % 20u) == 18u;
    marks_save(shared, &marks);
    if (dataspace_op) ds_save(&dataspace);

    if (sigsetjmp(fuzz_trap_return, 1) == 0) {
      fuzz_inside_guest_call = 1;
      int64_t result = fuzz_dispatch(&cursor, registers, shared, operation);
      fuzz_inside_guest_call = 0;
      registers[destination] = result;
      fuzz_reach.operations_completed++;
      /* A concat that completed copied both operands' bytes through
       * `resolve_string_bytes`, which is the read this sub-target exists for;
       * a completed dataspace call walked the request graph and interned its
       * reply. Counted apart from bare completions so a run that only ever
       * minted pairs cannot look like a run that exercised the string and
       * capability paths. */
      if ((operation % 20u) == 14u) fuzz_reach.string_bytes_read++;
      if ((operation % 20u) == 18u) fuzz_reach.dataspace_calls++;
    } else {
      /* Trapped. Rewind to the pre-operation state, which is exactly the
       * state an input that had omitted this operation would have reached. */
      marks_restore(shared, &marks);
      if (dataspace_op) ds_restore(&dataspace);
      fuzz_reach.operations_trapped++;
    }
  }

  fuzz_close(shared, code);
}

/* ---------------------------------------------------------------------------
 * Sub-target 2: result marshalling in the supervisor.
 *
 * `inspect_string_result` and its siblings run AFTER the sandboxed child has
 * exited, in the supervisor -- outside seccomp, outside the macOS sandbox
 * profile -- and every byte they walk (the pair table, the string pool, the
 * chosen result handle) is whatever the guest left behind. That makes this the
 * one place where guest-controlled data is read by an unsandboxed process, so
 * the arena is populated straight from the input rather than through the
 * allocators.
 *
 * The unallocated tail of each arena is ASan-poisoned. Those slots hold stale
 * words in production, so reading one is a defect that no bounds check on the
 * capacity would catch; poisoning turns it into a report.
 * ------------------------------------------------------------------------ */

static void fuzz_result_inspection(const uint8_t *data, size_t size) {
  struct fuzz_cursor cursor = {data, size, 0};
  uint8_t *code = NULL;
  uint64_t code_length = 0;
  struct kexe_shared_v3 *shared = fuzz_open(&cursor, &code, &code_length);
  if (shared == NULL) return;
  fuzz_arm_reach_report();

  uint64_t pool = (uint64_t)take_u8(&cursor) % 65u;
  int ascii_pool = (take_u8(&cursor) & 1u) != 0;
  for (uint64_t i = 0; i < pool; i++) {
    uint8_t byte = take_u8(&cursor);
    shared->string_pool[i] = ascii_pool ? (uint8_t)(0x20u + (byte % 0x5fu)) : byte;
  }
  shared->string_pool_used = pool;

  /* Pair cells are drawn as plausible words rather than uniform noise, for
   * the reason `fuzz_word` documents: a string handle is pair(offset,length)
   * and both halves are bounded, so noise never survives to a byte read. */
  uint64_t pairs = (uint64_t)take_u8(&cursor) % 33u;
  /* Two shapes, because `inspect_record_result` walks a NULL-terminated cons
   * chain and free-form cells almost never form one: measured over 20,000
   * deterministic cases, free-form alone decoded a record exactly once. The
   * chain shape lays the table out the way `record-new` lowers a record, so
   * the walk, its terminator and the field-count boundary are all reachable. */
  int chain = (take_u8(&cursor) & 1u) != 0;
  for (uint64_t i = 0; i < pairs; i++) {
    shared->pairs[i].first = fuzz_word(&cursor, code_length, pool);
    if (chain) {
      /* Mostly the next cell, sometimes the terminator early, so a chain
       * shorter than the requested field count is reached too. */
      uint8_t link = take_u8(&cursor);
      shared->pairs[i].second =
          (link % 8u) == 0u ? 0 : (int64_t)(i + 2u <= pairs ? i + 2u : 0u);
    } else {
      shared->pairs[i].second = fuzz_word(&cursor, code_length, pool);
    }
  }
  shared->pair_used = pairs;

  /* Every pair accessor in the loader -- `checked_pair_get`, `peek_pair` and
   * all four `inspect_*` -- bounds the handle by `pair_used`, so a read of an
   * unallocated pair slot is a defect no capacity check would catch. Poison
   * makes it a report.
   *
   * The string pool is deliberately NOT poisoned above its watermark, and the
   * first draft of this file was wrong to do so. `peek_string_bytes` and
   * `resolve_string_bytes` bound against the pool CAPACITY, while
   * `inspect_string_result` bounds against the watermark and says in its own
   * comment that it is the stricter of the two on purpose. Reading above the
   * watermark is therefore intended, and it is safe: `main` memsets the whole
   * shared region to zero before the guest runs, and the pool is only ever
   * appended to (`intern_utf8`, `checked_string_concat`, `parse_guest_arg`),
   * so those bytes are zeros or bytes this same guest wrote. Poisoning them
   * reported `valid_string_handle` as a use-after-poison on the very first
   * run -- a property of this harness, not of the loader. */
  KEXE_POISON(&shared->pairs[pairs],
              (KEXE_PAIR_CAPACITY - pairs) * sizeof(struct kexe_pair_v1));

  /* The handle the supervisor is told to decode. Mostly one the guest could
   * have minted; one time in eight, a raw word. */
  int64_t handle;
  if ((take_u8(&cursor) % 8u) == 0u) {
    handle = (int64_t)take_u64(&cursor);
  } else {
    handle = (int64_t)(1u + (uint64_t)take_u8(&cursor) % (pairs == 0 ? 1u : pairs));
  }

  uint64_t checksum = 0;

  uint64_t length = 0;
  const uint8_t *bytes = inspect_string_result(shared, handle, &length);
  if (bytes != NULL) {
    fuzz_reach.string_result_read++;
    /* Touch every byte: a pointer computed out of bounds is only a report
     * once it is dereferenced. */
    for (uint64_t i = 0; i < length; i++) checksum += bytes[i];
  }

  int64_t fields[KEXE_RECORD_FIELD_LIMIT];
  /* Straddle the two boundaries that matter: the chain's real length (so the
   * terminator check is tested from both sides) and KEXE_RECORD_FIELD_LIMIT
   * (so the rejection above the limit is tested rather than assumed). */
  uint64_t field_count;
  switch (take_u8(&cursor) % 4u) {
    case 0: field_count = pairs; break;
    case 1: field_count = pairs + 1u; break;
    case 2: field_count = pairs == 0 ? 0u : pairs - 1u; break;
    default: field_count = (uint64_t)take_u8(&cursor) % (KEXE_RECORD_FIELD_LIMIT + 2u);
  }
  if (inspect_record_result(shared, handle, field_count, fields)) {
    fuzz_reach.record_result_read++;
    for (uint64_t i = 0; i < field_count; i++) checksum += (uint64_t)fields[i];
  }

  int64_t tag = 0, payload = 0;
  if (inspect_tagged_i64_result(shared, handle, 1, &tag, &payload) ||
      inspect_tagged_i64_result(shared, handle, 0, &tag, &payload)) {
    fuzz_reach.tagged_result_read++;
  }
  checksum += (uint64_t)tag + (uint64_t)payload;

  uint64_t case_count = 1u + (uint64_t)take_u8(&cursor) % 32u;
  uint64_t bool_mask = take_u64(&cursor);
  bool_mask &= (UINT64_C(1) << case_count) - 1u;
  int64_t ordinal = 0;
  if (inspect_variant_result(shared, handle, case_count, bool_mask, &ordinal,
                             &payload)) {
    fuzz_reach.variant_result_read++;
    checksum += (uint64_t)ordinal;
  }

  /* The non-trapping predicates the typed capability boundary uses before it
   * commits to a value. Unlike the `checked_*` family these answer 0 rather
   * than raising, so they belong on the frozen arena. */
  if (valid_string_handle(&shared->context, handle)) {
    fuzz_reach.string_handle_accepted++;
  }
  int64_t peeked = 0;
  checksum += (uint64_t)peek_pair(&shared->context, handle, 0, &peeked);
  checksum += (uint64_t)peek_pair(&shared->context, handle, 1, &peeked);
  if (pool > 0) {
    checksum += (uint64_t)valid_utf8(shared->string_pool,
                                     (uint64_t)take_u8(&cursor) % (pool + 1u));
  }

  /* Keep the results observable so nothing above is optimized away. */
  shared->result = (int64_t)checksum;
  fuzz_reach.inputs++;

  KEXE_UNPOISON(shared->pairs, KEXE_PAIR_CAPACITY * sizeof(struct kexe_pair_v1));
  fuzz_close(shared, code);
}

/* ---------------------------------------------------------------------------
 * Sub-target 0: the argv parsers.
 *
 * The original four, unchanged so the committed corpus keeps its meaning, plus
 * the two that decode structured guest arguments -- `parse_guest_arg` mints
 * pairs and writes the string pool from hex text, and `parse_variant_profile`
 * feeds the result decoder above.
 * ------------------------------------------------------------------------ */

static void fuzz_parsers(const uint8_t *data, size_t size) {
  char *text = (char *)malloc(size + 1);
  if (text == NULL) return;
  memcpy(text, data, size);
  text[size] = '\0';

  uint64_t u64 = 0;
  unsigned long ulong_value = 0;
  int64_t i64 = 0;
  uint64_t allow[4] = {0, 0, 0, 0};
  (void)parse_u64(text, &u64);
  (void)parse_ulong_decimal(text, &ulong_value);
  (void)parse_i64(text, &i64);
  (void)parse_allow(text, allow);

  uint64_t case_count = 0, bool_mask = 0;
  (void)parse_variant_profile(text, &case_count, &bool_mask);

  struct kexe_shared_v3 *shared = (struct kexe_shared_v3 *)malloc(sizeof *shared);
  if (shared != NULL) {
    memset(shared, 0, sizeof *shared);
    shared->context.version = 3;
    int64_t value = 0;
    (void)parse_guest_arg(shared, text, &value);
    free(shared);
  }

  free(text);
}

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
  if (size > 1024) return 0;

  /* Runs on every input: the committed corpus was selected for this target,
   * and routing inputs away from it would silently drop that coverage. */
  fuzz_parsers(data, size);

  if (size == 0) return 0;
  if ((data[0] & 1u) == 0) {
    fuzz_handle_graph(data + 1, size - 1);
  } else {
    fuzz_result_inspection(data + 1, size - 1);
  }
  return 0;
}

#if defined(KEXE_STANDALONE_FUZZ)
int main(int argc, char **argv) {
  unsigned long runs = argc >= 2 ? strtoul(argv[1], NULL, 10) : 20000;
  uint64_t state = UINT64_C(0x4b4f544f4241465a);
  uint8_t input[1024];
  for (int arg = 2; arg < argc; arg++) {
    FILE *seed = fopen(argv[arg], "rb");
    if (seed == NULL) return 2;
    size_t size = fread(input, 1, sizeof(input), seed);
    if (ferror(seed) || !feof(seed) || fclose(seed) != 0) return 2;
    (void)LLVMFuzzerTestOneInput(input, size);
  }
  for (unsigned long run = 0; run < runs; run++) {
    state ^= state << 13;
    state ^= state >> 7;
    state ^= state << 17;
    size_t size = (size_t)(state % sizeof(input));
    for (size_t i = 0; i < size; i++) {
      state ^= state << 13;
      state ^= state >> 7;
      state ^= state << 17;
      input[i] = (uint8_t)state;
    }
    (void)LLVMFuzzerTestOneInput(input, size);
  }
  return 0;
}
#endif
