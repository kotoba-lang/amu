#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <signal.h>
#include <stddef.h>
#include <time.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#if defined(__aarch64__)
#include <arm_neon.h>
#elif defined(__SSE2__)
#include <emmintrin.h>
#endif

#if defined(__APPLE__)
#include <sandbox.h>
#endif

#if defined(__linux__)
#include <linux/audit.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#endif

typedef int64_t (*kexe_fn6)(int64_t, int64_t, int64_t, int64_t, int64_t, int64_t);
typedef int64_t (*kexe_fn8)(int64_t, int64_t, int64_t, int64_t,
                            int64_t, int64_t, int64_t, int64_t);

/* The pair heap: every string handle, every option, every result and every
 * record boundary is a pair, and nothing is ever reclaimed.
 *
 * KEXE_PAIR_CAPACITY is the DEFAULT budget and stays what it has always
 * been; KEXE_PAIRS names another positive decimal for one run, and a
 * packaged command bakes it. Same shape as KEXE_FUEL and KEXE_STRING_POOL,
 * and the same argument: raising a bound at build time moves every
 * program's ceiling at once, raising it per run moves one caller's.
 *
 * Measured 2026-09-10, which is why this is here: a `uniq` walking 600 lines
 * trapped with `:heap {:capacity 4096 :used 4096}` and 49,994,368 fuel
 * REMAINING -- about eight pairs per line, from the substrings a line walk
 * takes. The report naming the arena is what turned that into one
 * measurement instead of a bisection.
 *
 * KEXE_PAIR_MAX is address space, not memory: the mapping is MAP_ANONYMOUS
 * and nothing memsets it, so pages fault in as the bump allocator reaches
 * them. */
#define KEXE_PAIR_CAPACITY 4096u
#define KEXE_PAIR_MAX (4u * 1024u * 1024u)
#define KEXE_KGRAPH_CAPACITY 4096u
/* The string arena.
 *
 * KEXE_STRING_POOL_BYTES is the DEFAULT budget and stays exactly what it has
 * always been, so a guest that ran before runs identically. KEXE_STRING_POOL
 * names another positive decimal for one run, the way KEXE_FUEL already does
 * for fuel -- and that shape is the decision, not the number. Raising a bound
 * at build time moves every program's ceiling at once; raising it per run
 * moves one caller's, and a guest that outgrows the default still refuses
 * unless its caller asks. (kotoba-lang lang/surface-status.edn :arena-bounds
 * records this shape for the vector arenas; the string arena had been left
 * behind.)
 *
 * KEXE_STRING_POOL_MAX is the address space the arena is mapped over, not
 * memory it uses: the mapping is MAP_ANONYMOUS, so pages are zero-filled by
 * the kernel and faulted in only as the bump allocator reaches them. That is
 * why the explicit memset of the shared struct had to go -- it touched every
 * page and would have turned a large ceiling into a large cost. */
#define KEXE_STRING_POOL_BYTES 65536u
#define KEXE_STRING_POOL_MAX (256u * 1024u * 1024u)
/* granted regions: a bounded arena of HOST bytes an entry may be handed as a
 * (base, length) pair. Same 64 KiB bound as the string pool, and for the same
 * reason -- both arrive as hex in argv, and argv is what actually limits them
 * long before the arena does. A region that does not fit through argv needs a
 * different transport, and that is a gap rather than a bound. */
/* (The string pool's 64 KiB is now a DEFAULT rather than a fixed size --
 * KEXE_STRING_POOL / --string-pool move it per run. The region arena is
 * still fixed, and the sentence above is about argv either way.) */
#define KEXE_REGION_CAPACITY 8u
#define KEXE_REGION_POOL_BYTES 65536u
#define KEXE_RECORD_FIELD_LIMIT 128u
/* Fuel the guest starts with. 512 unless KEXE_FUEL names another positive
 * decimal budget; the loader enforces the number it is handed and decides
 * nothing about it (the kbb shim passes `--fuel` through here). The CPU and
 * wall-clock limits in install_limits()/supervise() are NOT raised by a
 * larger budget: fuel bounds the guest's own steps, the rlimits bound the
 * child, and both stay in force. */
static uint64_t kexe_initial_fuel = 512;
/* The string arena budget in force for this run: the default above unless
 * KEXE_STRING_POOL (or, in a packaged command, the baked constant) names
 * another positive decimal. Every allocation site checks THIS, never the
 * array's size, so the ceiling a guest meets is the budget and not the
 * mapping. */
static uint64_t kexe_string_pool_budget = KEXE_STRING_POOL_BYTES;
/* The pair-heap budget in force for this run. Every allocation site checks
 * THIS, never the array's size, so the ceiling a guest meets is the budget
 * and not the mapping. */
static uint64_t kexe_pair_budget = KEXE_PAIR_CAPACITY;

static void write_stderr_checked(const char *bytes, size_t length) {
  ssize_t written = write(STDERR_FILENO, bytes, length);
  (void)written;
}
/* Vector handles, and the element words they slice. The element arena is
 * deliberately four times `kotoba.kir.value/vector-item-limit` (16384), the
 * longest single vector KIR admits: an allocating update could build such a
 * vector and then never touch it again. This bounds total LIVE allocation,
 * not any one vector's length -- the same distinction the string pool above
 * already makes, in bytes rather than words.
 *
 * ABI v4 adds `vector_assoc_in_place`, which allocates NOTHING, so the
 * sentence this comment used to open with -- every operation that changes an
 * element allocates rather than mutates -- is no longer true of the whole
 * table. It is still true of `checked_vector_assoc`, and that is what keeps
 * an unproven handle safe. The two numbers below are UNCHANGED by v4:
 * removing the copy removes the reason the arena had to be four vectors wide,
 * but raising a bound is a separate decision with its own fail-closed
 * argument, and it has not been made (superproject `surface-status.edn`,
 * `:arena-bounds`). */
#define KEXE_VECTOR_CAPACITY 4096u
#define KEXE_VECTOR_ITEM_CAPACITY 65536u

struct kexe_context_v4 {
  uint64_t version;
  uint64_t fuel;
  uint64_t allow[4];
  int64_t (*cap_call)(struct kexe_context_v4 *, uint64_t, int64_t);
  int64_t (*pair_new)(struct kexe_context_v4 *, int64_t, int64_t);
  int64_t (*pair_first)(struct kexe_context_v4 *, int64_t);
  int64_t (*pair_second)(struct kexe_context_v4 *, int64_t);
  /* kgraph-* (ADR-2607198300): an all-integer EAVT datom store, the native
   * analog of kotoba-lang/kotoba's string/EDN-based kgraph-assert!/
   * kgraph-query -- this loader has no addressable guest buffer for EDN
   * text, so entity/attribute/value are caller-assigned integer ids. */
  int64_t (*kgraph_assert)(struct kexe_context_v4 *, int64_t, int64_t, int64_t);
  int64_t (*kgraph_get)(struct kexe_context_v4 *, int64_t, int64_t);
  int64_t (*kgraph_count)(struct kexe_context_v4 *, int64_t);
  int64_t (*kgraph_entity_at)(struct kexe_context_v4 *, int64_t, int64_t);
  /* string-* (ADR-2607198300 follow-up): a string VALUE is a pair(offset,
   * length) handle (built by backend/{aarch64,x86_64}.clj's
   * emit-string-literal via the existing pair_new above). `offset` addresses
   * one contiguous byte space uniformly: non-negative resolves into the
   * artifact's own code+literal-data region (`code_base`, read-only, string
   * literals appended once per distinct content past the last function's
   * code -- see emit-program); negative resolves into `string_pool` below
   * (dynamic string-concat results), via `-offset - 1`. string-byte-length
   * is exactly pair_second (no new host function); string=?/string-concat
   * need one each, since only they read/copy the addressed bytes. */
  int64_t (*string_equal)(struct kexe_context_v4 *, int64_t, int64_t);
  int64_t (*string_concat)(struct kexe_context_v4 *, int64_t, int64_t);
  int64_t (*typed_cap_call)(struct kexe_context_v4 *, uint64_t, uint64_t,
                            uint64_t, int64_t);
  /* string-substring over an arbitrary string value. Unlike string_concat
   * this allocates no pool bytes: a substring is a contiguous byte range of
   * its source, so the result is a VIEW -- a new pair(offset', length')
   * addressing the same bytes. Only the boundary CHECK needs the host (the
   * guest cannot load a byte), which is why this is a whole-operation
   * callback like string_equal/string_concat rather than a byte accessor. */
  int64_t (*string_substring)(struct kexe_context_v4 *, int64_t, int64_t,
                              int64_t);
  /* string-code-point-at. Like string_substring this exists only because the
   * guest cannot load a byte; unlike it the result is a scalar, not a handle,
   * so nothing is allocated at all. */
  int64_t (*string_code_point_at)(struct kexe_context_v4 *, int64_t, int64_t);
  /* vector-i64 / vector-f64 (ADR-2608030300). A vector VALUE is a one-word
   * handle into `vectors` below, exactly as a pair value is a handle into
   * `pairs` -- so the backends need no new value representation and every
   * operation is an ordinary context call. Each entry is an (offset, length)
   * slice of the shared `vector_items` arena, which makes `vector_drop` a
   * VIEW for the same reason `string_substring` is one: a suffix is
   * contiguous within its source.
   *
   * The element type is not recorded, and does not need to be: a native f64
   * is already an i64 word carrying an IEEE-754 bit pattern, so an f64 vector
   * is a vector of those words. Both KIR families reach these six slots; the
   * two ABI v4 slots below are reached by the i64 family only, because KIR
   * declares no `vector-f64-alloc` and no `vector-f64-assoc!`.
   *
   * `vector_new_empty` has no KIR operation of its own -- KIR's `vector-new`
   * is variadic and this ABI is not, so the backends expand a literal into
   * an empty vector plus one `vector_conj` per element. */
  int64_t (*vector_new_empty)(struct kexe_context_v4 *);
  int64_t (*vector_conj)(struct kexe_context_v4 *, int64_t, int64_t);
  int64_t (*vector_count)(struct kexe_context_v4 *, int64_t);
  int64_t (*vector_at)(struct kexe_context_v4 *, int64_t, int64_t);
  int64_t (*vector_assoc)(struct kexe_context_v4 *, int64_t, int64_t, int64_t);
  int64_t (*vector_drop)(struct kexe_context_v4 *, int64_t, int64_t);
  /* ABI v4 (superproject ADR-2609010200). Two slots the copying table above
   * cannot express, and the reason this struct is v4 rather than v3 with an
   * appended tail: a guest bakes these offsets in, so a v3 host reached by
   * v4-compiled code would jump through uninitialised memory. Every
   * `checked_*` above refuses a context whose version is not exactly 4, which
   * is the same one-directional guard the v2 -> v3 bump installed.
   *
   * `vector_alloc` exists because `vector-new` is variadic -- its arity IS the
   * literal's element count -- so a struct of arrays with a million slots
   * would need a million arguments in source, and the literal limit refuses
   * that long before the item limit does. Correct (nobody writes a book as a
   * literal) and it left no way to allocate one at all.
   *
   * `vector_assoc_in_place` is `vector_assoc` lowered to a STORE. It writes
   * inside the slice the handle already covers and returns THE SAME handle,
   * where `checked_vector_assoc` memmoves the whole vector and bump-allocates
   * a new one. The saving is not constant-factor: the arena is bump-only and
   * never reclaimed, so copying caps a vector's whole-program write count at
   * `arena / length` -- FOUR writes for a 16384-item vector.
   *
   * The host cannot check the claim that makes the store legal, and does not
   * pretend to. It checks MEMORY safety (handle resolves, index inside the
   * slice), which is unconditional; the ALIASING claim -- that no other live
   * handle spans the word being written -- is the compiler's, discharged by
   * `kotoba.compiler.affine/linear?` behind `check-affine-writes!` in
   * kotoba-sema, which refuses `vector-assoc!` on a handle it cannot prove
   * dead. That split is deliberate: a host-side alias check would have to
   * walk the handle table on every write, which is the O(length) cost this
   * slot exists to remove. */
  int64_t (*vector_alloc)(struct kexe_context_v4 *, int64_t);
  int64_t (*vector_assoc_in_place)(struct kexe_context_v4 *, int64_t, int64_t,
                                   int64_t);
  /* Data-only (not part of the compiler-checked context-abi): the mmap'd
   * code+literal-data region's base address and real (unpadded) byte
   * length, set once in main() before the guest runs. Never read by guest
   * code directly -- only string_equal/string_concat's C implementations
   * resolve a non-negative string offset through these. */
  const uint8_t *code_base;
  uint64_t code_length;
};

struct kexe_pair_v1 { int64_t first; int64_t second; };
struct kexe_datom_v1 { int64_t e; int64_t a; int64_t v; };
struct kexe_vector_v1 { uint64_t offset; uint64_t length; };

/* granted regions: where one lives in the pool. The LENGTH is recorded here
 * rather than taken from the caller a second time, which is the whole point --
 * a base and a length that do not belong together is how a granted region
 * becomes an ungranted one. */
struct kexe_granted_region_v1 {
  uint64_t offset;
  uint64_t length;
};

struct kexe_shared_v4 {
  struct kexe_context_v4 context;
  int64_t result;
  uint64_t completed;
  uint64_t pair_used;
  struct kexe_pair_v1 pairs[KEXE_PAIR_MAX];
  /* One flag per pair handle: the (offset, length) bytes this handle
   * addresses are known-valid canonical UTF-8. Sound because the bytes a
   * handle covers never change after it is minted -- code+literal data is
   * read-only and the string pool is append-only -- so validity, once
   * established, holds for the handle's lifetime. This turns the
   * per-access whole-string valid_utf8 in substring/code-point-at (an
   * O(n^2) cost for a scan) into one validation per handle. */
  uint8_t pair_validated[KEXE_PAIR_MAX];
  uint64_t kgraph_used;
  struct kexe_datom_v1 datoms[KEXE_KGRAPH_CAPACITY];
  uint64_t string_pool_used;
  uint8_t string_pool[KEXE_STRING_POOL_MAX];
  /* Two arenas, because a vector table entry and the elements it spans are
   * separately exhaustible: many small vectors run out of entries first, one
   * growing vector runs out of elements first, and neither bound implies the
   * other. */
  uint64_t vector_used;
  struct kexe_vector_v1 vectors[KEXE_VECTOR_CAPACITY];
  uint64_t vector_item_used;
  int64_t vector_items[KEXE_VECTOR_ITEM_CAPACITY];
  /* granted regions: appended LAST on purpose, for TWO reasons.
   *
   * The first is that every offset this file asserts (`fuel` at 8, `allow` at
   * 16, `cap_call` at 48) is inside `context`, which is first, so growing the
   * tail cannot move one.
   *
   * The second is the one that matters if something goes wrong. The pool is
   * the only guest-WRITABLE arena a caller hands an address to, and it is the
   * last thing in the mapping -- so a write past its end leaves the mapping
   * and the supervisor reports a trap. Put it between `pairs` and `vectors`
   * instead and the same write silently corrupts a handle table, which is a
   * wrong answer rather than a stopped one. The emitted bounds check should
   * make that unreachable; this is where it lands if it ever is not, and the
   * `_Static_assert` below is what keeps a later field from being appended
   * after it. */
  uint64_t region_used;
  uint64_t region_count;
  struct kexe_granted_region_v1 regions[KEXE_REGION_CAPACITY];
  uint8_t region_pool[KEXE_REGION_POOL_BYTES];
};

/* granted regions: the pool ends the mapping. A guest overrun must leave the
 * mapping and trap, not reach a handle table -- so nothing may be appended
 * after it, and this is the check rather than a comment saying so. */
_Static_assert(offsetof(struct kexe_shared_v4, region_pool) +
                   KEXE_REGION_POOL_BYTES == sizeof(struct kexe_shared_v4),
               "region pool must be the last field of the shared mapping");
_Static_assert(offsetof(struct kexe_context_v4, fuel) == 8, "fuel ABI drift");
_Static_assert(offsetof(struct kexe_context_v4, allow) == 16, "allow ABI drift");
_Static_assert(offsetof(struct kexe_context_v4, cap_call) == 48, "cap ABI drift");
_Static_assert(offsetof(struct kexe_context_v4, pair_new) == 56, "pair ABI drift");
_Static_assert(offsetof(struct kexe_context_v4, pair_first) == 64, "pair ABI drift");
_Static_assert(offsetof(struct kexe_context_v4, pair_second) == 72, "pair ABI drift");
_Static_assert(offsetof(struct kexe_context_v4, kgraph_assert) == 80, "kgraph ABI drift");
_Static_assert(offsetof(struct kexe_context_v4, kgraph_get) == 88, "kgraph ABI drift");
_Static_assert(offsetof(struct kexe_context_v4, kgraph_count) == 96, "kgraph ABI drift");
_Static_assert(offsetof(struct kexe_context_v4, kgraph_entity_at) == 104, "kgraph ABI drift");
_Static_assert(offsetof(struct kexe_context_v4, typed_cap_call) == 128, "typed cap ABI drift");
_Static_assert(offsetof(struct kexe_context_v4, string_equal) == 112, "string ABI drift");
_Static_assert(offsetof(struct kexe_context_v4, string_concat) == 120, "string ABI drift");
_Static_assert(offsetof(struct kexe_context_v4, string_substring) == 136, "string ABI drift");
_Static_assert(offsetof(struct kexe_context_v4, string_code_point_at) == 144, "string ABI drift");
/* The arena is now mapped over KEXE_PAIR_MAX and BOUNDED by
 * kexe_pair_budget, so the tripwire moves from a literal to the max it is
 * sized by -- it still catches a change to the array, which is what it is
 * for, and no longer asserts a number that stopped being the ceiling. */
_Static_assert(sizeof(((struct kexe_shared_v4 *)0)->pairs)
                   == KEXE_PAIR_MAX * sizeof(struct kexe_pair_v1),
               "pair arena size drift");
_Static_assert(sizeof(((struct kexe_shared_v4 *)0)->datoms) == 98304,
               "kgraph arena size drift");
_Static_assert(offsetof(struct kexe_context_v4, vector_new_empty) == 152, "vector ABI drift");
_Static_assert(offsetof(struct kexe_context_v4, vector_conj) == 160, "vector ABI drift");
_Static_assert(offsetof(struct kexe_context_v4, vector_count) == 168, "vector ABI drift");
_Static_assert(offsetof(struct kexe_context_v4, vector_at) == 176, "vector ABI drift");
_Static_assert(offsetof(struct kexe_context_v4, vector_assoc) == 184, "vector ABI drift");
_Static_assert(offsetof(struct kexe_context_v4, vector_drop) == 192, "vector ABI drift");
_Static_assert(offsetof(struct kexe_context_v4, vector_alloc) == 200, "vector ABI drift");
_Static_assert(offsetof(struct kexe_context_v4, vector_assoc_in_place) == 208, "vector ABI drift");
_Static_assert(sizeof(((struct kexe_shared_v4 *)0)->string_pool) == KEXE_STRING_POOL_MAX,
               "string pool size drift");
_Static_assert(sizeof(((struct kexe_shared_v4 *)0)->vectors) == 65536,
               "vector table size drift");
_Static_assert(sizeof(((struct kexe_shared_v4 *)0)->vector_items) == 524288,
               "vector item arena size drift");

static int parse_u64(const char *text, uint64_t *value) {
  if (text == NULL || *text < '0' || *text > '9') return -1;
  char *end = NULL;
  errno = 0;
  unsigned long long parsed = strtoull(text, &end, 10);
  if (errno == ERANGE || end == text || *end != '\0') return -1;
  *value = (uint64_t)parsed;
  return 0;
}

static int parse_ulong_decimal(const char *text, unsigned long *value) {
  if (text == NULL || *text < '0' || *text > '9') return -1;
  char *end = NULL;
  errno = 0;
  unsigned long parsed = strtoul(text, &end, 10);
  if (errno == ERANGE || end == text || *end != '\0') return -1;
  *value = parsed;
  return 0;
}

static int parse_i64(const char *text, int64_t *value) {
  if (text == NULL || (*text != '-' && (*text < '0' || *text > '9')) ||
      (*text == '-' && (text[1] < '0' || text[1] > '9'))) return -1;
  char *end = NULL;
  errno = 0;
  long long parsed = strtoll(text, &end, 10);
  if (errno == ERANGE || end == text || *end != '\0') return -1;
  *value = (int64_t)parsed;
  return 0;
}

static volatile sig_atomic_t supervisor_timed_out = 0;
static volatile sig_atomic_t supervised_pid = -1;

static int64_t checked_cap_call(struct kexe_context_v4 *context,
                                uint64_t cap_id, int64_t value) {
  if (context == NULL || context->version != 4 || cap_id > 255 ||
      (context->allow[cap_id / 64] & (UINT64_C(1) << (cap_id % 64))) == 0) {
    raise(SIGILL);
    return 0;
  }
  return value + 1;
}

static int64_t checked_pair_new(struct kexe_context_v4 *context,
                                int64_t first, int64_t second) {
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
/* Every allocation site bounds the index against the ARRAY as well as the
 * budget, and the second half is not redundant belt-and-braces -- it is what
 * makes the invariant LOCAL.
 *
 * While the bound was a compile-time constant the compiler could prove
 * `index < KEXE_PAIR_CAPACITY` from the guard and the write was obviously in
 * range. A runtime budget it cannot prove anything about, so gcc on the CI
 * runners refused the file:
 *
 *   kexe_loader.c:401: error: writing 1 byte into a region of size 0
 *   [-Werror=stringop-overflow=]
 *
 * The budget is validated against KEXE_PAIR_MAX once at startup, so this
 * adds no behaviour -- it moves that fact to where the write is, which is
 * where the compiler is looking. Clang (macOS, and every local build here)
 * did not warn, so this was invisible until CI compiled it with
 * -Wall -Wextra -Werror. */
  if (context == NULL || context->version != 4 ||
      shared->pair_used >= kexe_pair_budget ||
      shared->pair_used >= KEXE_PAIR_MAX) {
    raise(SIGILL);
    return 0;
  }
  uint64_t index = shared->pair_used++;
  shared->pairs[index].first = first;
  shared->pairs[index].second = second;
  shared->pair_validated[index] = 0;
  return (int64_t)(index + 1);
}

static int64_t checked_pair_get(struct kexe_context_v4 *context,
                                int64_t handle, int second) {
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
  if (context == NULL || context->version != 4 || handle <= 0 ||
      (uint64_t)handle > shared->pair_used) {
    raise(SIGILL);
    return 0;
  }
  struct kexe_pair_v1 *pair = &shared->pairs[(uint64_t)handle - 1];
  return second ? pair->second : pair->first;
}

static int64_t checked_pair_first(struct kexe_context_v4 *context, int64_t handle) {
  return checked_pair_get(context, handle, 0);
}

static int64_t checked_pair_second(struct kexe_context_v4 *context, int64_t handle) {
  return checked_pair_get(context, handle, 1);
}

/* vector-i64 / vector-f64 host table.
 *
 * Through ABI v3 every operation that changed an element allocated a new
 * slice and a new handle; nothing ever wrote inside a slice an existing
 * handle covers. That is what makes a handle an immutable VALUE despite the
 * shared arena, and it is the whole safety argument for
 * `checked_vector_conj`'s in-place append below -- so the two must be read
 * together.
 *
 * ABI v4's `checked_vector_assoc_in_place` is the ONE exception, and it does
 * not weaken that argument, it relocates it: the write is legal exactly when
 * no other live handle spans the word, and the compiler proves that before
 * choosing the slot (see the struct field's comment). Reached through
 * `vector-assoc!`, which `kotoba-sema` refuses on a handle it cannot prove
 * dead. Everything else in this table still allocates. */

static struct kexe_vector_v1 *resolve_vector(struct kexe_shared_v4 *shared,
                                             int64_t handle) {
  if (handle <= 0 || (uint64_t)handle > shared->vector_used) return NULL;
  return &shared->vectors[(uint64_t)handle - 1];
}

/* Mints a handle for an already-populated slice. Returns 0 when the handle
 * table is full; every caller turns that into SIGILL, so exhaustion is a trap
 * rather than a silently wrong vector. */
static int64_t intern_vector(struct kexe_shared_v4 *shared,
                             uint64_t offset, uint64_t length) {
  if (shared->vector_used >= KEXE_VECTOR_CAPACITY) return 0;
  uint64_t index = shared->vector_used++;
  shared->vectors[index].offset = offset;
  shared->vectors[index].length = length;
  return (int64_t)(index + 1);
}

/* An empty vector starts at the current arena top, which is what lets the
 * conj chain a `vector-new` literal expands into take the copy-free path from
 * its very first element. */
static int64_t checked_vector_new_empty(struct kexe_context_v4 *context) {
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
  if (context == NULL || context->version != 4) { raise(SIGILL); return 0; }
  int64_t handle = intern_vector(shared, shared->vector_item_used, 0);
  if (handle == 0) { raise(SIGILL); return 0; }
  return handle;
}

static int64_t checked_vector_count(struct kexe_context_v4 *context,
                                    int64_t handle) {
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
  if (context == NULL || context->version != 4) { raise(SIGILL); return 0; }
  struct kexe_vector_v1 *vector = resolve_vector(shared, handle);
  if (vector == NULL) { raise(SIGILL); return 0; }
  return (int64_t)vector->length;
}

/* Traps out of range, matching `kotoba.kir`'s own vector-at. The total
 * variant is vector-get, which the backends lower to a bounds test around
 * this call rather than to a host function of its own. */
static int64_t checked_vector_at(struct kexe_context_v4 *context,
                                 int64_t handle, int64_t index) {
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
  if (context == NULL || context->version != 4) { raise(SIGILL); return 0; }
  struct kexe_vector_v1 *vector = resolve_vector(shared, handle);
  if (vector == NULL || index < 0 || (uint64_t)index >= vector->length) {
    raise(SIGILL);
    return 0;
  }
  return shared->vector_items[vector->offset + (uint64_t)index];
}

static int64_t checked_vector_conj(struct kexe_context_v4 *context,
                                   int64_t handle, int64_t item) {
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
  if (context == NULL || context->version != 4) { raise(SIGILL); return 0; }
  struct kexe_vector_v1 *vector = resolve_vector(shared, handle);
  if (vector == NULL) { raise(SIGILL); return 0; }
  uint64_t offset = vector->offset;
  uint64_t length = vector->length;
  /* The single vector length bound, re-derived from
   * `kotoba.kir.value/vector-item-limit`. Checked separately from arena
   * capacity because the arena is deliberately wider: exhausting the arena
   * and exceeding what KIR admits are different failures. */
  if (length >= 16384u) { raise(SIGILL); return 0; }
  if (offset + length != shared->vector_item_used) {
    /* Interior slice: appending would write a word some other handle may
     * already span, so copy first. */
    if (shared->vector_item_used + length + 1u > KEXE_VECTOR_ITEM_CAPACITY) {
      raise(SIGILL);
      return 0;
    }
    uint64_t destination = shared->vector_item_used;
    memmove(&shared->vector_items[destination], &shared->vector_items[offset],
            (size_t)length * sizeof(int64_t));
    shared->vector_item_used += length;
    offset = destination;
  }
  /* The slice now ends at the arena top, so the next word belongs to no
   * handle: writing it cannot change what any existing handle reads, because
   * every handle carries its own length. This is why repeated conj is linear
   * rather than quadratic. */
  if (shared->vector_item_used >= KEXE_VECTOR_ITEM_CAPACITY) {
    raise(SIGILL);
    return 0;
  }
  shared->vector_items[shared->vector_item_used++] = item;
  int64_t result = intern_vector(shared, offset, length + 1u);
  if (result == 0) { raise(SIGILL); return 0; }
  return result;
}

/* Always copies: the changed element sits inside the slice, and other handles
 * may span it. There is no in-place case to detect. */
static int64_t checked_vector_assoc(struct kexe_context_v4 *context,
                                    int64_t handle, int64_t index,
                                    int64_t item) {
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
  if (context == NULL || context->version != 4) { raise(SIGILL); return 0; }
  struct kexe_vector_v1 *vector = resolve_vector(shared, handle);
  if (vector == NULL || index < 0 || (uint64_t)index >= vector->length) {
    raise(SIGILL);
    return 0;
  }
  uint64_t offset = vector->offset;
  uint64_t length = vector->length;
  if (shared->vector_item_used + length > KEXE_VECTOR_ITEM_CAPACITY) {
    raise(SIGILL);
    return 0;
  }
  uint64_t destination = shared->vector_item_used;
  memmove(&shared->vector_items[destination], &shared->vector_items[offset],
          (size_t)length * sizeof(int64_t));
  shared->vector_items[destination + (uint64_t)index] = item;
  shared->vector_item_used += length;
  int64_t result = intern_vector(shared, destination, length);
  if (result == 0) { raise(SIGILL); return 0; }
  return result;
}

/* ABI v4: `n` zero words, in one call.
 *
 * The item bound is re-derived from `kotoba.kir.value/vector-item-limit`, the
 * same 16384 `checked_vector_conj` above re-derives, and is checked SEPARATELY
 * from arena capacity because exhausting the arena and exceeding what KIR
 * admits are different failures. `n == 0` is admitted and yields a real handle
 * over an empty slice, exactly as `checked_vector_new_empty` does. */
static int64_t checked_vector_alloc(struct kexe_context_v4 *context,
                                    int64_t count) {
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
  if (context == NULL || context->version != 4) { raise(SIGILL); return 0; }
  if (count < 0 || count > 16384) { raise(SIGILL); return 0; }
  if (shared->vector_item_used + (uint64_t)count > KEXE_VECTOR_ITEM_CAPACITY) {
    raise(SIGILL);
    return 0;
  }
  uint64_t offset = shared->vector_item_used;
  for (uint64_t i = 0; i < (uint64_t)count; i++) shared->vector_items[offset + i] = 0;
  shared->vector_item_used += (uint64_t)count;
  int64_t result = intern_vector(shared, offset, (uint64_t)count);
  if (result == 0) { raise(SIGILL); return 0; }
  return result;
}

/* ABI v4: the same update as `checked_vector_assoc`, lowered to a store.
 *
 * Returns THE SAME handle, allocates nothing, and touches exactly one word.
 * Read this beside `checked_vector_assoc` above: that one always copies
 * because the changed element sits inside the slice and other handles may
 * span it. Here the compiler has already proved no other live handle does --
 * see the ABI v4 comment on the struct field for where that proof lives and
 * why the host does not repeat it.
 *
 * What the host still owns is memory safety, and it is checked exactly as
 * `checked_vector_assoc` checks it: the handle must resolve inside the table
 * and the index must be inside the slice's own length. A forged handle or an
 * out-of-range index traps here, before any word is written, whatever the
 * compiler believed. */
static int64_t checked_vector_assoc_in_place(struct kexe_context_v4 *context,
                                             int64_t handle, int64_t index,
                                             int64_t item) {
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
  if (context == NULL || context->version != 4) { raise(SIGILL); return 0; }
  struct kexe_vector_v1 *vector = resolve_vector(shared, handle);
  if (vector == NULL || index < 0 || (uint64_t)index >= vector->length) {
    raise(SIGILL);
    return 0;
  }
  shared->vector_items[vector->offset + (uint64_t)index] = item;
  return handle;
}

/* A VIEW, for the same reason string_substring is one: a suffix is contiguous
 * within its source, so it needs a handle but no elements. Dropping zero
 * elements is admitted and yields a distinct handle over the same slice. */
static int64_t checked_vector_drop(struct kexe_context_v4 *context,
                                   int64_t handle, int64_t count) {
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
  if (context == NULL || context->version != 4) { raise(SIGILL); return 0; }
  struct kexe_vector_v1 *vector = resolve_vector(shared, handle);
  if (vector == NULL || count < 0 || (uint64_t)count > vector->length) {
    raise(SIGILL);
    return 0;
  }
  int64_t result = intern_vector(shared, vector->offset + (uint64_t)count,
                                 vector->length - (uint64_t)count);
  if (result == 0) { raise(SIGILL); return 0; }
  return result;
}

static int64_t checked_kgraph_assert(struct kexe_context_v4 *context,
                                     int64_t e, int64_t a, int64_t v) {
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
  if (context == NULL || context->version != 4 ||
      shared->kgraph_used >= KEXE_KGRAPH_CAPACITY) {
    raise(SIGILL);
    return 0;
  }
  uint64_t index = shared->kgraph_used++;
  shared->datoms[index].e = e;
  shared->datoms[index].a = a;
  shared->datoms[index].v = v;
  return 1;
}

/* Last-write-wins point lookup, matching kgraph-lang/kotoba's own
 * kgraph-query semantics for a single (entity, attribute) pair. */
static int64_t checked_kgraph_get(struct kexe_context_v4 *context,
                                  int64_t e, int64_t a) {
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
  if (context == NULL || context->version != 4) {
    raise(SIGILL);
    return 0;
  }
  int64_t result = INT64_MIN;
  for (uint64_t i = 0; i < shared->kgraph_used; i++) {
    if (shared->datoms[i].e == e && shared->datoms[i].a == a) {
      result = shared->datoms[i].v;
    }
  }
  return result;
}

/* True (non-zero) exactly when entity `e` has ever been asserted with
 * attribute `a`, used by checked_kgraph_count/checked_kgraph_entity_at to
 * de-duplicate to the first occurrence without a separate seen-set. */
static int kgraph_entity_seen_before(const struct kexe_shared_v4 *shared,
                                     uint64_t upto, int64_t a, int64_t e) {
  for (uint64_t j = 0; j < upto; j++) {
    if (shared->datoms[j].a == a && shared->datoms[j].e == e) return 1;
  }
  return 0;
}

static int64_t checked_kgraph_count(struct kexe_context_v4 *context, int64_t a) {
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
  if (context == NULL || context->version != 4) {
    raise(SIGILL);
    return 0;
  }
  int64_t count = 0;
  for (uint64_t i = 0; i < shared->kgraph_used; i++) {
    if (shared->datoms[i].a != a) continue;
    if (!kgraph_entity_seen_before(shared, i, a, shared->datoms[i].e)) count++;
  }
  return count;
}

static int64_t checked_kgraph_entity_at(struct kexe_context_v4 *context,
                                        int64_t a, int64_t index) {
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
  if (context == NULL || context->version != 4 || index < 0) {
    raise(SIGILL);
    return 0;
  }
  int64_t seen = -1;
  for (uint64_t i = 0; i < shared->kgraph_used; i++) {
    if (shared->datoms[i].a != a) continue;
    if (kgraph_entity_seen_before(shared, i, a, shared->datoms[i].e)) continue;
    seen++;
    if (seen == index) return shared->datoms[i].e;
  }
  raise(SIGILL);
  return 0;
}

/* Resolves a string handle's (offset, length) pair, bounds-checks the
 * addressed byte range against whichever region `offset`'s sign selects,
 * and returns a pointer directly into that region -- never copies. */
static const uint8_t *resolve_string_bytes(struct kexe_context_v4 *context,
                                           int64_t offset, int64_t length) {
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
  if (length < 0) { raise(SIGILL); return NULL; }
  if (offset >= 0) {
    if ((uint64_t)offset + (uint64_t)length > context->code_length) {
      raise(SIGILL);
      return NULL;
    }
    return context->code_base + offset;
  }
  /* `-(offset + 1)` is defined even for INT64_MIN; `-offset - 1` is not. */
  uint64_t pool_offset = (uint64_t)(-(offset + 1));
  if (pool_offset + (uint64_t)length > kexe_string_pool_budget ||
      pool_offset + (uint64_t)length < pool_offset) {
    raise(SIGILL);
    return NULL;
  }
  return shared->string_pool + pool_offset;
}

static int valid_utf8(const uint8_t *bytes, uint64_t length) {
  uint64_t i = 0;
  while (i < length) {
    uint8_t a = bytes[i++];
    if (a <= 0x7f) continue;
    if (a >= 0xc2 && a <= 0xdf) {
      if (i >= length || (bytes[i++] & 0xc0) != 0x80) return 0;
      continue;
    }
    if (a >= 0xe0 && a <= 0xef) {
      if (i + 1 >= length) return 0;
      uint8_t b = bytes[i++], c = bytes[i++];
      if ((b & 0xc0) != 0x80 || (c & 0xc0) != 0x80 ||
          (a == 0xe0 && b < 0xa0) || (a == 0xed && b >= 0xa0)) return 0;
      continue;
    }
    if (a >= 0xf0 && a <= 0xf4) {
      if (i + 2 >= length) return 0;
      uint8_t b = bytes[i++], c = bytes[i++], d = bytes[i++];
      if ((b & 0xc0) != 0x80 || (c & 0xc0) != 0x80 || (d & 0xc0) != 0x80 ||
          (a == 0xf0 && b < 0x90) || (a == 0xf4 && b >= 0x90)) return 0;
      continue;
    }
    return 0;
  }
  return 1;
}

/* Validate the string behind HANDLE once and remember it on the handle.
 * See pair_validated's comment for why this is sound. */
static int ensure_valid_string(struct kexe_context_v4 *context, int64_t handle,
                               const uint8_t *bytes, int64_t length) {
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
  uint64_t index = (uint64_t)handle - 1;
  if (shared->pair_validated[index]) return 1;
  if (!valid_utf8(bytes, (uint64_t)length)) return 0;
  shared->pair_validated[index] = 1;
  return 1;
}

/* Mark a freshly minted handle whose validity holds by construction: a
 * code-point-bounded view of a validated string, or a concatenation of two
 * validated strings. */
static int64_t mark_validated(struct kexe_context_v4 *context, int64_t handle) {
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
  if (handle > 0) shared->pair_validated[(uint64_t)handle - 1] = 1;
  return handle;
}

static int hex_nibble(char value) {
  if (value >= '0' && value <= '9') return value - '0';
  if (value >= 'a' && value <= 'f') return value - 'a' + 10;
  return -1;
}

static int allocate_host_pair(struct kexe_shared_v4 *shared,
                              int64_t first, int64_t second, int64_t *handle) {
  if (shared->pair_used >= kexe_pair_budget ||
      shared->pair_used >= KEXE_PAIR_MAX) return -1;
  uint64_t index = shared->pair_used++;
  shared->pairs[index].first = first;
  shared->pairs[index].second = second;
  shared->pair_validated[index] = 0;
  *handle = (int64_t)(index + 1u);
  return 0;
}

static int parse_variant_profile(const char *text, uint64_t *case_count,
                                 uint64_t *bool_mask) {
  unsigned long long cases, mask;
  int consumed = 0;
  if (sscanf(text, "variant:%llu:%llu%n", &cases, &mask, &consumed) != 2 ||
      text[consumed] != '\0' || cases == 0 || cases > 32 ||
      (mask >> cases) != 0) return 0;
  *case_count = (uint64_t)cases;
  *bool_mask = (uint64_t)mask;
  return 1;
}

/* Host strings cross the process boundary as lowercase UTF-8 hex. They are
 * decoded into the existing bounded string pool and receive the same
 * pair(offset,length) representation as guest-created strings. Scalar tokens
 * retain the historical decimal spelling, so old direct loader callers keep
 * working. */
static int parse_guest_arg(struct kexe_shared_v4 *shared,
                           const char *text, int64_t *value) {
  if (strncmp(text, "v:", 2) == 0) {
    unsigned long long cases, ordinal;
    long long payload;
    char kind;
    int consumed = 0;
    if (sscanf(text, "v:%llu:%llu:%c:%lld%n", &cases, &ordinal, &kind,
               &payload, &consumed) != 4 || text[consumed] != '\0' ||
        cases == 0 || cases > 32 || ordinal >= cases ||
        (kind != 'i' && kind != 'b') ||
        (kind == 'b' && payload != 0 && payload != 1)) return -1;
    return allocate_host_pair(shared, (int64_t)ordinal, (int64_t)payload, value);
  }
  if (strcmp(text, "o:none") == 0)
    return allocate_host_pair(shared, 0, 0, value);
  if (strncmp(text, "o:some:", 7) == 0) {
    int64_t payload;
    if (parse_i64(text + 7, &payload) != 0) return -1;
    return allocate_host_pair(shared, 1, payload, value);
  }
  if (strncmp(text, "e:ok:", 5) == 0 ||
      strncmp(text, "e:err:", 6) == 0) {
    int ok = text[2] == 'o';
    int64_t payload;
    if (parse_i64(text + (ok ? 5 : 6), &payload) != 0) return -1;
    return allocate_host_pair(shared, ok ? 1 : 0, payload, value);
  }
  if (strncmp(text, "r:", 2) == 0) {
    int64_t fields[KEXE_RECORD_FIELD_LIMIT];
    uint64_t count = 0;
    const char *cursor = text + 2;
    if (*cursor == '\0') return -1;
    while (*cursor != '\0') {
      if (count >= KEXE_RECORD_FIELD_LIMIT) return -1;
      if ((*cursor != '-' && (*cursor < '0' || *cursor > '9')) ||
          (*cursor == '-' && (cursor[1] < '0' || cursor[1] > '9'))) return -1;
      char *end = NULL;
      errno = 0;
      long long field = strtoll(cursor, &end, 10);
      if (errno == ERANGE || end == cursor || (*end != ',' && *end != '\0'))
        return -1;
      fields[count++] = (int64_t)field;
      if (*end == '\0') break;
      cursor = end + 1;
      if (*cursor == '\0') return -1;
    }
    if (count > kexe_pair_budget - shared->pair_used ||
        count > KEXE_PAIR_MAX - shared->pair_used) return -1;
    int64_t handle = 0;
    for (uint64_t i = count; i > 0; i--) {
      uint64_t index = shared->pair_used++;
      shared->pairs[index].first = fields[i - 1u];
      shared->pairs[index].second = handle;
      shared->pair_validated[index] = 0;
      handle = (int64_t)(index + 1u);
    }
    *value = handle;
    return 0;
  }
  /* granted regions: `g:<hex>` mints a region from host bytes and answers its
   * BASE ADDRESS; `gl:<n>` answers the LENGTH of the n-th region minted so
   * far. Arguments are parsed in argv order and before the fork, so `n` is
   * deterministic and the mapping is shared with the child.
   *
   * BOTH NUMBERS ARE THE LOADER'S. That is the property this pair exists for:
   * a caller can grant a region, and cannot grant a base with a length that
   * does not belong to it. The guest's own bounds check then compares an index
   * against a length it did not choose either.
   *
   * The pool lives in the MAP_SHARED mapping, so the address handed over is
   * valid in the child at the same place. It is NOT valid after this process
   * exits, which is why nothing outside a single execution may hold it. */
  if (strncmp(text, "g:", 2) == 0) {
    const char *hex = text + 2;
    size_t digits = strlen(hex);
    if ((digits & 1u) != 0) return -1;
    uint64_t length = (uint64_t)(digits / 2u);
    if (shared->region_count >= KEXE_REGION_CAPACITY) return -1;
    if (length > KEXE_REGION_POOL_BYTES - shared->region_used) return -1;
    for (size_t i = 0; i < digits; i++) {
      if (hex_nibble(hex[i]) < 0) return -1;
    }
    uint64_t start = shared->region_used;
    for (uint64_t i = 0; i < length; i++) {
      shared->region_pool[start + i] =
          (uint8_t)((hex_nibble(hex[2u * i]) << 4) |
                    hex_nibble(hex[2u * i + 1u]));
    }
    shared->regions[shared->region_count].offset = start;
    shared->regions[shared->region_count].length = length;
    shared->region_count++;
    shared->region_used += length;
    *value = (int64_t)(uintptr_t)(shared->region_pool + start);
    return 0;
  }
  if (strncmp(text, "gl:", 3) == 0) {
    uint64_t index;
    if (parse_u64(text + 3, &index) != 0) return -1;
    /* Fail closed on a length asked for before its region was minted: the
     * count is what has been minted SO FAR, so a forward reference is refused
     * rather than answered with zero. */
    if (index >= shared->region_count) return -1;
    *value = (int64_t)shared->regions[index].length;
    return 0;
  }
  if (strncmp(text, "s:", 2) != 0) return parse_i64(text, value);
  const char *hex = text + 2;
  size_t digits = strlen(hex);
  if ((digits & 1u) != 0) return -1;
  uint64_t length = (uint64_t)(digits / 2u);
  if (length > kexe_string_pool_budget - shared->string_pool_used ||
      length > KEXE_STRING_POOL_MAX - shared->string_pool_used ||
      shared->pair_used >= kexe_pair_budget ||
      shared->pair_used >= KEXE_PAIR_MAX) return -1;
  for (size_t i = 0; i < digits; i++) {
    if (hex_nibble(hex[i]) < 0) return -1;
  }
  uint64_t start = shared->string_pool_used;
  for (uint64_t i = 0; i < length; i++) {
    shared->string_pool[start + i] =
        (uint8_t)((hex_nibble(hex[2u * i]) << 4) |
                  hex_nibble(hex[2u * i + 1u]));
  }
  if (!valid_utf8(shared->string_pool + start, length)) return -1;
  uint64_t index = shared->pair_used++;
  shared->pairs[index].first = -((int64_t)start) - 1;
  shared->pairs[index].second = (int64_t)length;
  shared->pair_validated[index] = 1;
  shared->string_pool_used += length;
  *value = (int64_t)(index + 1u);
  return 0;
}

/* Read a returned string without invoking the guest-facing trapping helpers:
 * this runs in the supervisor after the sandboxed child has exited. It also
 * requires a pool slice to have actually been allocated, rather than merely
 * falling somewhere inside the pool capacity. */
static const uint8_t *inspect_string_result(const struct kexe_shared_v4 *shared,
                                            int64_t handle, uint64_t *length_out) {
  if (handle <= 0 || (uint64_t)handle > shared->pair_used) return NULL;
  const struct kexe_pair_v1 *pair = &shared->pairs[(uint64_t)handle - 1u];
  if (pair->second < 0) return NULL;
  uint64_t length = (uint64_t)pair->second;
  const uint8_t *bytes;
  if (pair->first >= 0) {
    uint64_t offset = (uint64_t)pair->first;
    if (length > shared->context.code_length ||
        offset > shared->context.code_length - length) return NULL;
    bytes = shared->context.code_base + offset;
  } else {
    uint64_t offset = (uint64_t)(-(pair->first + 1));
    if (length > shared->string_pool_used ||
        offset > shared->string_pool_used - length) return NULL;
    bytes = shared->string_pool + offset;
  }
  if (!valid_utf8(bytes, length)) return NULL;
  *length_out = length;
  return bytes;
}

static int inspect_record_result(const struct kexe_shared_v4 *shared,
                                 int64_t handle, uint64_t field_count,
                                 int64_t fields[KEXE_RECORD_FIELD_LIMIT]) {
  if (field_count == 0 || field_count > KEXE_RECORD_FIELD_LIMIT) return 0;
  for (uint64_t i = 0; i < field_count; i++) {
    if (handle <= 0 || (uint64_t)handle > shared->pair_used) return 0;
    const struct kexe_pair_v1 *pair = &shared->pairs[(uint64_t)handle - 1u];
    fields[i] = pair->first;
    handle = pair->second;
  }
  return handle == 0;
}

static int inspect_tagged_i64_result(const struct kexe_shared_v4 *shared,
                                     int64_t handle, int option,
                                     int64_t *tag, int64_t *payload) {
  if (handle <= 0 || (uint64_t)handle > shared->pair_used) return 0;
  const struct kexe_pair_v1 *pair = &shared->pairs[(uint64_t)handle - 1u];
  if (pair->first != 0 && pair->first != 1) return 0;
  if (option && pair->first == 0 && pair->second != 0) return 0;
  *tag = pair->first;
  *payload = pair->second;
  return 1;
}

static int inspect_variant_result(const struct kexe_shared_v4 *shared,
                                  int64_t handle, uint64_t case_count,
                                  uint64_t bool_mask, int64_t *ordinal,
                                  int64_t *payload) {
  if (handle <= 0 || (uint64_t)handle > shared->pair_used) return 0;
  const struct kexe_pair_v1 *pair = &shared->pairs[(uint64_t)handle - 1u];
  if (pair->first < 0 || (uint64_t)pair->first >= case_count) return 0;
  if (((bool_mask >> (uint64_t)pair->first) & 1u) != 0 &&
      pair->second != 0 && pair->second != 1) return 0;
  *ordinal = pair->first;
  *payload = pair->second;
  return 1;
}

enum kexe_typed_kind_v1 {
  KEXE_TYPED_STRING = 1,
  KEXE_TYPED_OPTION_I64 = 2,
  KEXE_TYPED_RESULT_I64 = 3,
  KEXE_TYPED_CLOCK_V1 = 4,
  KEXE_TYPED_DATASPACE_V1 = 5,
  KEXE_TYPED_UI_COMMIT_V1 = 6,
  KEXE_TYPED_UI_EVENT_V1 = 7
};

#define DS_MAX_ITEMS 32
#define DS_MAX_BYTES 256
#define DS_MAX_MAIL 8

enum {
  DS_REQ_ASSERT = 0,
  DS_REQ_RETRACT = 1,
  DS_REQ_OBSERVE = 2,
  DS_REQ_FACET_ENTER = 3,
  DS_REQ_FACET_LEAVE = 4
};

enum {
  DS_RES_ASSERTED = 0,
  DS_RES_RETRACTED = 1,
  DS_RES_MATCHES = 2,
  DS_RES_FACET = 3,
  DS_RES_ERROR = 4
};

struct ds_item {
  uint8_t bytes[DS_MAX_BYTES];
  uint64_t len;
  int64_t facet;
  int live;
};

static int64_t ds_next_facet = 1;
static uint8_t ds_live_facets[33];
static struct ds_item ds_asserts[DS_MAX_ITEMS];
static struct ds_item ds_observers[DS_MAX_ITEMS];
static uint8_t ds_mail_bytes[DS_MAX_MAIL][DS_MAX_BYTES];
static uint64_t ds_mail_len[DS_MAX_MAIL];
static int ds_mail_kind[DS_MAX_MAIL];
static int ds_mail_count;

static const char ds_empty[] = "[]";
static const char ds_assert_notice[] =
    "[{:assertion [:temperature :room/a 21] :bindings {} :kind :assert}]";
static const char ds_retract_notice[] =
    "[{:assertion [:temperature :room/a 21] :bindings {} :kind :retract}]";

/* Predicates must not trap. checked_pair_get / resolve_string_bytes raise
 * SIGILL on a bad handle; a retracted result is pair(1, pair(count, 0)) and
 * looks like a retract *request* until the terminator is walked. Walking
 * that 0 with checked_pair_get aborted a real guest after retract. */
static int peek_pair(struct kexe_context_v4 *context, int64_t handle,
                     int second, int64_t *out) {
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
  if (context == NULL || context->version != 4 || handle <= 0 ||
      (uint64_t)handle > shared->pair_used) return 0;
  struct kexe_pair_v1 *pair = &shared->pairs[(uint64_t)handle - 1];
  *out = second ? pair->second : pair->first;
  return 1;
}

static int peek_vector(struct kexe_context_v4 *context, int64_t handle,
                       uint64_t *length, const int64_t **items) {
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
  struct kexe_vector_v1 *vector;
  if (context == NULL || context->version != 4) return 0;
  vector = resolve_vector(shared, handle);
  if (vector == NULL) return 0;
  if (vector->offset + vector->length > KEXE_VECTOR_ITEM_CAPACITY) return 0;
  *length = vector->length;
  *items = shared->vector_items + vector->offset;
  return 1;
}

static const uint8_t *peek_string_bytes(struct kexe_context_v4 *context,
                                        int64_t offset, int64_t length) {
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
  if (context == NULL || context->version != 4 || length < 0) return NULL;
  if (offset >= 0) {
    if ((uint64_t)offset + (uint64_t)length > context->code_length) return NULL;
    return context->code_base + offset;
  }
  uint64_t pool_offset = (uint64_t)(-(offset + 1));
  if (pool_offset + (uint64_t)length > kexe_string_pool_budget ||
      pool_offset + (uint64_t)length < pool_offset) return NULL;
  return shared->string_pool + pool_offset;
}

static int valid_string_handle(struct kexe_context_v4 *context, int64_t value) {
  int64_t offset, length;
  if (!peek_pair(context, value, 0, &offset) ||
      !peek_pair(context, value, 1, &length)) return 0;
  const uint8_t *bytes = peek_string_bytes(context, offset, length);
  if (bytes == NULL || length < 0) return 0;
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
  if (shared->pair_validated[(uint64_t)value - 1]) return 1;
  if (!valid_utf8(bytes, (uint64_t)length)) return 0;
  shared->pair_validated[(uint64_t)value - 1] = 1;
  return 1;
}

static int read_string_handle(struct kexe_context_v4 *context, int64_t value,
                              const uint8_t **bytes, uint64_t *len) {
  int64_t offset = checked_pair_get(context, value, 0);
  int64_t length = checked_pair_get(context, value, 1);
  const uint8_t *p = resolve_string_bytes(context, offset, length);
  if (p == NULL || length < 0 ||
      !ensure_valid_string(context, value, p, length)) return 0;
  *bytes = p;
  *len = (uint64_t)length;
  return 1;
}

static int64_t intern_utf8(struct kexe_context_v4 *context,
                           const uint8_t *bytes, uint64_t length) {
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
  if (shared->string_pool_used + length > kexe_string_pool_budget ||
      shared->string_pool_used + length > KEXE_STRING_POOL_MAX) {
    raise(SIGILL);
    return 0;
  }
  uint64_t start = shared->string_pool_used;
  memcpy(shared->string_pool + start, bytes, (size_t)length);
  shared->string_pool_used += length;
  return checked_pair_new(context, -((int64_t)start) - 1, (int64_t)length);
}

static int valid_dataspace_request(struct kexe_context_v4 *context,
                                   int64_t value) {
  int64_t ordinal, payload;
  if (!peek_pair(context, value, 0, &ordinal) ||
      !peek_pair(context, value, 1, &payload)) return 0;
  if (ordinal < 0 || ordinal > DS_REQ_FACET_LEAVE) return 0;
  if (ordinal == DS_REQ_FACET_ENTER) return payload == 0 || payload == 1;
  if (ordinal == DS_REQ_FACET_LEAVE) return 1;
  int64_t doc, rest, facet, tail;
  if (!peek_pair(context, payload, 0, &doc) ||
      !peek_pair(context, payload, 1, &rest) ||
      !peek_pair(context, rest, 0, &facet) ||
      !peek_pair(context, rest, 1, &tail)) return 0;
  (void)facet;
  return tail == 0 && valid_string_handle(context, doc);
}

static int valid_dataspace_result(struct kexe_context_v4 *context,
                                  int64_t value) {
  int64_t ordinal, payload;
  if (!peek_pair(context, value, 0, &ordinal) ||
      !peek_pair(context, value, 1, &payload)) return 0;
  if (ordinal == DS_RES_ASSERTED) {
    int64_t notices_cell, notices;
    if (!peek_pair(context, payload, 1, &notices_cell) ||
        !peek_pair(context, notices_cell, 0, &notices)) return 0;
    return valid_string_handle(context, notices);
  }
  if (ordinal == DS_RES_RETRACTED) return 1;
  if (ordinal == DS_RES_MATCHES) {
    int64_t bindings, rest, notices;
    if (!peek_pair(context, payload, 0, &bindings) ||
        !peek_pair(context, payload, 1, &rest) ||
        !peek_pair(context, rest, 0, &notices)) return 0;
    return valid_string_handle(context, bindings) &&
           valid_string_handle(context, notices);
  }
  if (ordinal == DS_RES_FACET) return 1;
  if (ordinal == DS_RES_ERROR) {
    int64_t code, rest, message;
    if (!peek_pair(context, payload, 0, &code) ||
        !peek_pair(context, payload, 1, &rest) ||
        !peek_pair(context, rest, 0, &message)) return 0;
    return valid_string_handle(context, code) &&
           valid_string_handle(context, message);
  }
  return 0;
}

static int valid_ui_node(struct kexe_context_v4 *context, int64_t node) {
  int64_t id, rest, parent, rest2, kind, rest3, text, tail;
  int64_t parent_tag, parent_payload;
  if (!peek_pair(context, node, 0, &id) ||
      !peek_pair(context, node, 1, &rest) ||
      !peek_pair(context, rest, 0, &parent) ||
      !peek_pair(context, rest, 1, &rest2) ||
      !peek_pair(context, rest2, 0, &kind) ||
      !peek_pair(context, rest2, 1, &rest3) ||
      !peek_pair(context, rest3, 0, &text) ||
      !peek_pair(context, rest3, 1, &tail)) return 0;
  if (tail != 0) return 0;
  if (!valid_string_handle(context, id) ||
      !valid_string_handle(context, kind) ||
      !valid_string_handle(context, text)) return 0;
  if (!peek_pair(context, parent, 0, &parent_tag) ||
      !peek_pair(context, parent, 1, &parent_payload)) return 0;
  if (parent_tag != 0 && parent_tag != 1) return 0;
  if (parent_tag == 0) return parent_payload == 0;
  return valid_string_handle(context, parent_payload);
}

static int valid_ui_nodes(struct kexe_context_v4 *context, int64_t nodes) {
  uint64_t length = 0, i;
  const int64_t *items = NULL;
  if (!peek_vector(context, nodes, &length, &items) || length > 32) return 0;
  for (i = 0; i < length; i++) {
    if (!valid_ui_node(context, items[i])) return 0;
  }
  return 1;
}

static int valid_ui_commit_request(struct kexe_context_v4 *context,
                                   int64_t value) {
  int64_t base_rev, rest, nodes, tail;
  if (!peek_pair(context, value, 0, &base_rev) ||
      !peek_pair(context, value, 1, &rest) ||
      !peek_pair(context, rest, 0, &nodes) ||
      !peek_pair(context, rest, 1, &tail)) return 0;
  return tail == 0 && valid_ui_nodes(context, nodes);
}

static int valid_ui_commit_result(struct kexe_context_v4 *context,
                                  int64_t value) {
  int64_t revision, rest, count, tail;
  if (!peek_pair(context, value, 0, &revision) ||
      !peek_pair(context, value, 1, &rest) ||
      !peek_pair(context, rest, 0, &count) ||
      !peek_pair(context, rest, 1, &tail)) return 0;
  return tail == 0 && revision > 0 && count >= 0;
}

static int valid_ui_event_request(struct kexe_context_v4 *context,
                                  int64_t value) {
  int64_t after, tail;
  if (!peek_pair(context, value, 0, &after) ||
      !peek_pair(context, value, 1, &tail)) return 0;
  return tail == 0;
}

static int valid_ui_event(struct kexe_context_v4 *context, int64_t value) {
  int64_t revision, rest, target, rest2, kind, rest3, event_value, tail;
  if (!peek_pair(context, value, 0, &revision) ||
      !peek_pair(context, value, 1, &rest) ||
      !peek_pair(context, rest, 0, &target) ||
      !peek_pair(context, rest, 1, &rest2) ||
      !peek_pair(context, rest2, 0, &kind) ||
      !peek_pair(context, rest2, 1, &rest3) ||
      !peek_pair(context, rest3, 0, &event_value) ||
      !peek_pair(context, rest3, 1, &tail)) return 0;
  return tail == 0 && revision > 0 &&
         valid_string_handle(context, target) &&
         valid_string_handle(context, kind) &&
         valid_string_handle(context, event_value);
}

static int valid_ui_event_result(struct kexe_context_v4 *context,
                                 int64_t value) {
  int64_t tag, payload;
  if (!peek_pair(context, value, 0, &tag) ||
      !peek_pair(context, value, 1, &payload)) return 0;
  if (tag == 0) return payload == 0;
  if (tag == 1) return valid_ui_event(context, payload);
  return 0;
}

#define KEXE_CLOCK_CAPABILITY_ID 7u
#define KEXE_CLOCK_CASE_WALL 0
#define KEXE_CLOCK_CASE_MONOTONIC 1
#define KEXE_CLOCK_CASE_ERROR 2

static int64_t intern_pool_string(struct kexe_context_v4 *context,
                                  const char *text) {
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
  size_t n = strlen(text);
  if (context == NULL || text == NULL ||
      n > kexe_string_pool_budget ||
      shared->string_pool_used + n > kexe_string_pool_budget) {
    raise(SIGILL);
    return 0;
  }
  uint64_t off = shared->string_pool_used;
  memcpy(shared->string_pool + off, text, n);
  shared->string_pool_used += n;
  return checked_pair_new(context, -((int64_t)off) - 1, (int64_t)n);
}

static int valid_clock_request(const struct kexe_shared_v4 *shared, int64_t value,
                               int64_t *ordinal, int64_t *payload) {
  /* Both request cases carry a bool payload (mask 0b11). */
  return inspect_variant_result(shared, value, 2, 3u, ordinal, payload);
}

static int valid_clock_result(const struct kexe_shared_v4 *shared, int64_t value) {
  int64_t ordinal = 0, payload = 0, fields[KEXE_RECORD_FIELD_LIMIT];
  if (!inspect_variant_result(shared, value, 3, 0, &ordinal, &payload)) return 0;
  if (ordinal == KEXE_CLOCK_CASE_WALL || ordinal == KEXE_CLOCK_CASE_MONOTONIC) {
    if (!inspect_record_result(shared, payload, 2, fields)) return 0;
    return fields[0] >= 0 && fields[1] > 0;
  }
  if (ordinal == KEXE_CLOCK_CASE_ERROR) {
    return inspect_record_result(shared, payload, 2, fields);
  }
  return 0;
}

static int read_wall_millis(int64_t *out) {
  struct timespec ts;
  if (clock_gettime(CLOCK_REALTIME, &ts) != 0) return -1;
  if (ts.tv_sec < 0 || ts.tv_nsec < 0) return -1;
  if (ts.tv_sec > (INT64_MAX - ts.tv_nsec / 1000000) / 1000) return -1;
  *out = ts.tv_sec * (int64_t)1000 + ts.tv_nsec / 1000000;
  return 0;
}

static int read_monotonic_nanos(int64_t *out) {
  struct timespec ts;
  if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) return -1;
  if (ts.tv_sec < 0 || ts.tv_nsec < 0) return -1;
  if (ts.tv_sec > (INT64_MAX - ts.tv_nsec) / 1000000000LL) return -1;
  *out = ts.tv_sec * 1000000000LL + ts.tv_nsec;
  return 0;
}

static int64_t clock_error_result(struct kexe_context_v4 *context,
                                  const char *code, const char *message) {
  int64_t code_handle = intern_pool_string(context, code);
  int64_t message_handle = intern_pool_string(context, message);
  int64_t record = checked_pair_new(context, message_handle, 0);
  record = checked_pair_new(context, code_handle, record);
  return checked_pair_new(context, KEXE_CLOCK_CASE_ERROR, record);
}

static int64_t clock_success_result(struct kexe_context_v4 *context,
                                    int64_t ordinal, int64_t tick,
                                    int64_t sequence) {
  int64_t record = checked_pair_new(context, sequence, 0);
  record = checked_pair_new(context, tick, record);
  return checked_pair_new(context, ordinal, record);
}

static int64_t hosted_clock_v1(struct kexe_context_v4 *context, int64_t request) {
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
  static int64_t observation_sequence = 0;
  static int64_t last_monotonic = -1;
  int64_t ordinal = 0, payload = 0, tick = 0;
  if (!valid_clock_request(shared, request, &ordinal, &payload)) {
    raise(SIGILL);
    return 0;
  }
  if (observation_sequence == INT64_MAX) {
    raise(SIGILL);
    return 0;
  }
  if (ordinal == KEXE_CLOCK_CASE_WALL) {
    if (read_wall_millis(&tick) != 0 || tick < 0) {
      return clock_error_result(context, ":clock/source", "clock source failed");
    }
    return clock_success_result(context, KEXE_CLOCK_CASE_WALL, tick,
                                ++observation_sequence);
  }
  if (ordinal == KEXE_CLOCK_CASE_MONOTONIC) {
    if (read_monotonic_nanos(&tick) != 0 || tick < 0) {
      return clock_error_result(context, ":clock/source", "clock source failed");
    }
    if (last_monotonic >= 0 && tick < last_monotonic) {
      return clock_error_result(context, ":clock/regressed",
                                "monotonic clock regressed");
    }
    last_monotonic = tick;
    return clock_success_result(context, KEXE_CLOCK_CASE_MONOTONIC, tick,
                                ++observation_sequence);
  }
  raise(SIGILL);
  return 0;
}

static int valid_typed_value(struct kexe_context_v4 *context,
                             uint64_t kind, int64_t value) {
  if (kind == KEXE_TYPED_STRING) {
    return valid_string_handle(context, value);
  }
  if (kind == KEXE_TYPED_OPTION_I64 || kind == KEXE_TYPED_RESULT_I64) {
    int64_t tag = checked_pair_get(context, value, 0);
    int64_t payload = checked_pair_get(context, value, 1);
    if (tag != 0 && tag != 1) return 0;
    return kind != KEXE_TYPED_OPTION_I64 || tag != 0 || payload == 0;
  }
  if (kind == KEXE_TYPED_CLOCK_V1) {
    struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
    int64_t ordinal = 0, payload = 0;
    return valid_clock_request(shared, value, &ordinal, &payload) ||
           valid_clock_result(shared, value);
  }
  if (kind == KEXE_TYPED_DATASPACE_V1) {
    return valid_dataspace_request(context, value) ||
           valid_dataspace_result(context, value);
  }
  if (kind == KEXE_TYPED_UI_COMMIT_V1) {
    return valid_ui_commit_request(context, value) ||
           valid_ui_commit_result(context, value);
  }
  if (kind == KEXE_TYPED_UI_EVENT_V1) {
    return valid_ui_event_request(context, value) ||
           valid_ui_event_result(context, value);
  }
  return 0;
}

static int ds_bytes_eq(const uint8_t *a, uint64_t alen,
                       const uint8_t *b, uint64_t blen) {
  return alen == blen && memcmp(a, b, (size_t)alen) == 0;
}

static void ds_enqueue(int kind, const uint8_t *bytes, uint64_t len) {
  if (ds_mail_count >= DS_MAX_MAIL || len > DS_MAX_BYTES) return;
  memcpy(ds_mail_bytes[ds_mail_count], bytes, (size_t)len);
  ds_mail_len[ds_mail_count] = len;
  ds_mail_kind[ds_mail_count] = kind;
  ds_mail_count++;
}

static int64_t ds_result_facet(struct kexe_context_v4 *context, int64_t id) {
  return checked_pair_new(context, DS_RES_FACET,
                          checked_pair_new(context, id, 0));
}

static int64_t ds_result_retracted(struct kexe_context_v4 *context,
                                   int64_t count) {
  return checked_pair_new(context, DS_RES_RETRACTED,
                          checked_pair_new(context, count, 0));
}

static int64_t ds_result_asserted(struct kexe_context_v4 *context,
                                  int64_t count, int64_t notices) {
  return checked_pair_new(
      context, DS_RES_ASSERTED,
      checked_pair_new(context, count, checked_pair_new(context, notices, 0)));
}

static int64_t ds_result_matches(struct kexe_context_v4 *context,
                                 int64_t bindings, int64_t notices) {
  return checked_pair_new(
      context, DS_RES_MATCHES,
      checked_pair_new(context, bindings,
                       checked_pair_new(context, notices, 0)));
}

static int64_t ds_notice_handle(struct kexe_context_v4 *context, int kind) {
  const char *text = kind == 1 ? ds_retract_notice : ds_assert_notice;
  return intern_utf8(context, (const uint8_t *)text, strlen(text));
}

static int64_t ds_empty_handle(struct kexe_context_v4 *context) {
  return intern_utf8(context, (const uint8_t *)ds_empty, strlen(ds_empty));
}

static int64_t dataspace_inject(struct kexe_context_v4 *context,
                                int64_t request) {
  int64_t ordinal = checked_pair_get(context, request, 0);
  int64_t payload = checked_pair_get(context, request, 1);
  if (ordinal == DS_REQ_FACET_ENTER) {
    if (ds_next_facet > 32) {
      raise(SIGILL);
      return 0;
    }
    int64_t id = ds_next_facet++;
    ds_live_facets[id] = 1;
    return ds_result_facet(context, id);
  }
  if (ordinal == DS_REQ_FACET_LEAVE) {
    if (payload <= 0 || payload > 32 || !ds_live_facets[payload]) {
      int64_t code = intern_utf8(context, (const uint8_t *)":dataspace/unknown-facet",
                                 24);
      int64_t message = intern_utf8(context, (const uint8_t *)"unknown facet", 13);
      return checked_pair_new(
          context, DS_RES_ERROR,
          checked_pair_new(context, code, checked_pair_new(context, message, 0)));
    }
    ds_live_facets[payload] = 0;
    return ds_result_retracted(context, 1);
  }
  int64_t doc = checked_pair_get(context, payload, 0);
  int64_t rest = checked_pair_get(context, payload, 1);
  int64_t facet = checked_pair_get(context, rest, 0);
  const uint8_t *bytes = NULL;
  uint64_t len = 0;
  if (!read_string_handle(context, doc, &bytes, &len) || len > DS_MAX_BYTES) {
    raise(SIGILL);
    return 0;
  }
  if (facet != 0 && (facet <= 0 || facet > 32 || !ds_live_facets[facet])) {
    int64_t code = intern_utf8(context, (const uint8_t *)":dataspace/unknown-facet",
                               24);
    int64_t message = intern_utf8(context, (const uint8_t *)"unknown facet", 13);
    return checked_pair_new(
        context, DS_RES_ERROR,
        checked_pair_new(context, code, checked_pair_new(context, message, 0)));
  }
  if (ordinal == DS_REQ_ASSERT) {
    int i;
    for (i = 0; i < DS_MAX_ITEMS; i++) {
      if (!ds_asserts[i].live) break;
    }
    if (i == DS_MAX_ITEMS) {
      raise(SIGILL);
      return 0;
    }
    memcpy(ds_asserts[i].bytes, bytes, (size_t)len);
    ds_asserts[i].len = len;
    ds_asserts[i].facet = facet;
    ds_asserts[i].live = 1;
    int o;
    for (o = 0; o < DS_MAX_ITEMS; o++) {
      if (ds_observers[o].live &&
          ds_bytes_eq(ds_observers[o].bytes, ds_observers[o].len, bytes, len)) {
        ds_enqueue(0, bytes, len);
      }
    }
    return ds_result_asserted(context, 1, ds_notice_handle(context, 0));
  }
  if (ordinal == DS_REQ_RETRACT) {
    int removed = 0;
    int i;
    for (i = 0; i < DS_MAX_ITEMS; i++) {
      if (ds_asserts[i].live &&
          ds_bytes_eq(ds_asserts[i].bytes, ds_asserts[i].len, bytes, len)) {
        ds_asserts[i].live = 0;
        removed = 1;
      }
    }
    if (removed) {
      int o;
      for (o = 0; o < DS_MAX_ITEMS; o++) {
        if (ds_observers[o].live &&
            ds_bytes_eq(ds_observers[o].bytes, ds_observers[o].len, bytes, len)) {
          ds_enqueue(1, bytes, len);
        }
      }
    }
    return ds_result_retracted(context, removed);
  }
  if (ordinal == DS_REQ_OBSERVE) {
    int i;
    int found = 0;
    for (i = 0; i < DS_MAX_ITEMS; i++) {
      if (ds_observers[i].live &&
          ds_bytes_eq(ds_observers[i].bytes, ds_observers[i].len, bytes, len) &&
          ds_observers[i].facet == facet) {
        found = 1;
        break;
      }
    }
    if (!found) {
      for (i = 0; i < DS_MAX_ITEMS; i++) {
        if (!ds_observers[i].live) {
          memcpy(ds_observers[i].bytes, bytes, (size_t)len);
          ds_observers[i].len = len;
          ds_observers[i].facet = facet;
          ds_observers[i].live = 1;
          break;
        }
      }
    }
    int64_t notices;
    if (ds_mail_count > 0) {
      notices = ds_notice_handle(context, ds_mail_kind[0]);
      int remain = ds_mail_count - 1;
      if (remain > 0) {
        memmove(ds_mail_bytes[0], ds_mail_bytes[1],
                (size_t)remain * DS_MAX_BYTES);
        memmove(ds_mail_len, ds_mail_len + 1, (size_t)remain * sizeof(uint64_t));
        memmove(ds_mail_kind, ds_mail_kind + 1, (size_t)remain * sizeof(int));
      }
      ds_mail_count = remain;
    } else {
      notices = ds_empty_handle(context);
    }
    return ds_result_matches(context, ds_empty_handle(context), notices);
  }
  raise(SIGILL);
  return 0;
}

static int64_t ui_revision;
static int ui_event_live;
static int64_t ui_event_revision;
static int64_t ui_event_target;
static int64_t ui_event_kind;
static int64_t ui_event_value;

static int64_t ui_commit_inject(struct kexe_context_v4 *context,
                                int64_t request) {
  int64_t base_rev, rest, nodes, tail;
  uint64_t length = 0;
  const int64_t *items = NULL;
  if (!peek_pair(context, request, 0, &base_rev) ||
      !peek_pair(context, request, 1, &rest) ||
      !peek_pair(context, rest, 0, &nodes) ||
      !peek_pair(context, rest, 1, &tail) || tail != 0 ||
      !peek_vector(context, nodes, &length, &items)) {
    raise(SIGILL);
    return 0;
  }
  if (base_rev != ui_revision) {
    raise(SIGILL);
    return 0;
  }
  ui_revision += 1;
  if (length > 0) {
    int64_t id = 0, node_rest = 0, text_cell = 0, text_rest = 0, text = 0;
    if (peek_pair(context, items[0], 0, &id) &&
        peek_pair(context, items[0], 1, &node_rest) &&
        peek_pair(context, node_rest, 1, &text_rest) &&
        peek_pair(context, text_rest, 1, &text_cell) &&
        peek_pair(context, text_cell, 0, &text)) {
      ui_event_live = 1;
      ui_event_revision = ui_revision;
      ui_event_target = id;
      ui_event_kind = intern_utf8(context, (const uint8_t *)":ui/committed", 13);
      ui_event_value = text;
    }
  }
  return checked_pair_new(
      context, ui_revision,
      checked_pair_new(context, (int64_t)length, 0));
}

static int64_t ui_event_inject(struct kexe_context_v4 *context,
                               int64_t request) {
  int64_t after, tail;
  if (!peek_pair(context, request, 0, &after) ||
      !peek_pair(context, request, 1, &tail) || tail != 0) {
    raise(SIGILL);
    return 0;
  }
  if (!ui_event_live || ui_event_revision <= after) {
    return checked_pair_new(context, 0, 0);
  }
  ui_event_live = 0;
  return checked_pair_new(
      context, 1,
      checked_pair_new(
          context, ui_event_revision,
          checked_pair_new(
              context, ui_event_target,
              checked_pair_new(
                  context, ui_event_kind,
                  checked_pair_new(context, ui_event_value, 0)))));
}

static int64_t env_read_provider(struct kexe_context_v4 *context,
                                 int64_t request) {
  const uint8_t *bytes = NULL;
  uint64_t length = 0;
  if (!read_string_handle(context, request, &bytes, &length)) {
    raise(SIGILL);
    return 0;
  }
  /* getenv needs a NUL-terminated C string. Environment names cannot
   * contain '=' or NUL; reject '=' outright and anything that does not
   * fit the on-stack scratch buffer. Fail closed on malformed requests
   * rather than guessing a name. */
  if (length == 0 || length >= 4096) {
    raise(SIGILL);
    return 0;
  }
  char name[4096];
  memcpy(name, bytes, (size_t)length);
  name[length] = '\0';
  for (uint64_t i = 0; i < length; i++) {
    if (name[i] == '=') {
      raise(SIGILL);
      return 0;
    }
  }
  const char *value = getenv(name);
  if (value == NULL) {
    /* Unset: guest sees the empty string, not a trap. */
    return intern_utf8(context, (const uint8_t *)"", 0);
  }
  size_t value_length = strlen(value);
  return intern_utf8(context, (const uint8_t *)value, value_length);
}

/* wire id 37 = :io/write. The bytes a COMMAND writes to its standard output.
 *
 * The request is the payload; the result is the DECIMAL COUNT of bytes
 * written, as text. Two things pick that shape and neither is a preference.
 * `[:string :string]` is one of the four generic type pairs kotoba.kir's
 * native gate admits for `typed-cap-call`, and `:string -> :i64` is not among
 * them. And the result has to be SHORT: the string pool below is a bump
 * allocator that never reclaims, so echoing the payload back -- the shape the
 * wire-35 write form uses, where the echo is the verification -- would charge
 * every write twice and halve how much a command can print. A count is a
 * handful of bytes whatever the payload is, and is still checkable.
 *
 * Unlike every other provider here this one has NO resource scope. There is
 * nothing to narrow: the guest cannot name a destination, cannot open one,
 * and cannot ask which one it got. It writes to this process's fd 1 and to
 * nothing else, so the authority the grant carries is exactly "may produce
 * output", which is what a command needs and all of it.
 *
 * A partial write is retried; a real error fails closed with SIGILL rather
 * than reporting a count that did not happen. EINTR is retried and is not an
 * error -- a signal arriving mid-write must not look like a short answer. */
static int64_t io_write_provider(struct kexe_context_v4 *context,
                                 int64_t request) {
  const uint8_t *bytes = NULL;
  uint64_t length = 0;
  if (!read_string_handle(context, request, &bytes, &length)) {
    raise(SIGILL);
    return 0;
  }
  uint64_t written = 0;
  while (written < length) {
    ssize_t n = write(1, bytes + written, (size_t)(length - written));
    if (n < 0) {
      if (errno == EINTR) continue;
      raise(SIGILL);
      return 0;
    }
    if (n == 0) {
      /* Neither progress nor an error. Refusing beats spinning. */
      raise(SIGILL);
      return 0;
    }
    written += (uint64_t)n;
  }
  /* Decimal, no sign, no padding: at most 20 digits for a uint64. */
  char count[24];
  int digits = snprintf(count, sizeof(count), "%llu",
                        (unsigned long long)written);
  if (digits <= 0 || (size_t)digits >= sizeof(count)) {
    raise(SIGILL);
    return 0;
  }
  return intern_utf8(context, (const uint8_t *)count, (size_t)digits);
}

/* wire id 39 = :io/write-error. The bytes a COMMAND writes to its DIAGNOSTIC
 * output.
 *
 * Byte for byte the same provider as wire 37 with fd 2 instead of fd 1, and
 * that similarity is the point: what differs is not the mechanism but the
 * AUTHORITY. A pipeline reads stdout and a person reads stderr, so a grant
 * carrying both would let a guest put into the answer what it was only
 * permitted to complain with. Six commands in this family had shipped saying
 * "the error paths are not matched" because there was nothing to match them
 * with.
 *
 * Same result: the decimal count of bytes written, short for the same reason
 * -- the arena never reclaims, and an echo would charge every write twice. */
static int64_t io_write_error_provider(struct kexe_context_v4 *context,
                                       int64_t request) {
  const uint8_t *bytes = NULL;
  uint64_t length = 0;
  if (!read_string_handle(context, request, &bytes, &length)) {
    raise(SIGILL);
    return 0;
  }
  uint64_t written = 0;
  while (written < length) {
    ssize_t n = write(2, bytes + written, (size_t)(length - written));
    if (n < 0) {
      if (errno == EINTR) continue;
      raise(SIGILL);
      return 0;
    }
    if (n == 0) {
      raise(SIGILL);
      return 0;
    }
    written += (uint64_t)n;
  }
  char count[24];
  int digits = snprintf(count, sizeof(count), "%llu",
                        (unsigned long long)written);
  if (digits <= 0 || (size_t)digits >= sizeof(count)) {
    raise(SIGILL);
    return 0;
  }
  return intern_utf8(context, (const uint8_t *)count, (size_t)digits);
}

/* wire id 38 = :cli/args. The arguments a COMMAND was invoked with.
 *
 * The loader's own positional arguments and the guest's are separated on the
 * command line by `--`: everything after the first one belongs to the guest
 * and nothing before it does. That keeps the existing strict arity check --
 * `argc != 6 + arity` -- meaning what it always meant, instead of turning it
 * into a lower bound that would stop catching a miscounted invocation.
 *
 * Request and result are both `:string`, because those are the type pairs the
 * native gate admits, so the index travels as decimal text:
 *
 *   ""    -> the COUNT of arguments, as decimal text
 *   "<i>" -> argument i, zero-based, or the empty string past the end
 *
 * The empty request is what makes the count unambiguous: an index is a
 * non-empty decimal, so no argument index can collide with it. A guest cannot
 * discover the count by probing for the empty answer, because an empty
 * ARGUMENT is legal and answers the same thing.
 *
 * There is no resource scope, for the same reason :io/write has none: the
 * guest names nothing and chooses nothing. The grant means "may see how this
 * process was invoked". */
static char **kexe_guest_argv = NULL;
static int kexe_guest_argc = 0;

static int64_t cli_args_provider(struct kexe_context_v4 *context,
                                 int64_t request) {
  const uint8_t *bytes = NULL;
  uint64_t length = 0;
  if (!read_string_handle(context, request, &bytes, &length)) {
    raise(SIGILL);
    return 0;
  }
  if (length == 0) {
    char count[24];
    int digits = snprintf(count, sizeof(count), "%d", kexe_guest_argc);
    if (digits <= 0 || (size_t)digits >= sizeof(count)) {
      raise(SIGILL);
      return 0;
    }
    return intern_utf8(context, (const uint8_t *)count, (size_t)digits);
  }
  /* A decimal index, and nothing else. A malformed request is refused rather
   * than read as zero -- answering argv[0] for "1x" would be a silent wrong
   * answer, which is the one outcome worth trapping over. */
  if (length >= 20) {
    raise(SIGILL);
    return 0;
  }
  char index_text[24];
  memcpy(index_text, bytes, (size_t)length);
  index_text[length] = '\0';
  for (uint64_t i = 0; i < length; i++) {
    if (index_text[i] < '0' || index_text[i] > '9') {
      raise(SIGILL);
      return 0;
    }
  }
  errno = 0;
  char *end = NULL;
  unsigned long long index = strtoull(index_text, &end, 10);
  if (errno != 0 || end == NULL || *end != '\0') {
    raise(SIGILL);
    return 0;
  }
  if (index >= (unsigned long long)kexe_guest_argc) {
    return intern_utf8(context, (const uint8_t *)"", 0);
  }
  const char *value = kexe_guest_argv[index];
  return intern_utf8(context, (const uint8_t *)value, strlen(value));
}

/* ----------------------------------------------------------------------
 * Filesystem capability scopes: wire id 35 = :fs/app-data (runtime id 202;
 * read, write and ranged read of one file) and wire id 34 = :fs/browse (one
 * directory listing). Each scope is a colon-separated list of absolute path
 * prefixes the kbb shim hands over in KEXE_CAP_RESOURCES_<wire-id>, taken
 * from the policy's resource scope. Entries are realpath'ed in the PARENT,
 * before fork, while the process is still unsandboxed; both the Seatbelt
 * profile and every provider use only these resolved spellings, so no
 * sandboxed code needs to realpath a path outside the grant (e.g. through
 * the /tmp -> /private/tmp symlink). A missing or empty scope admits
 * nothing. The loader decides nothing here: the grant is the shim's, the
 * loader only enforces the list it was given, fail closed -- any malformed
 * request, scope breach or I/O failure raises SIGILL. */
#define KEXE_SCOPE_ENTRIES 16

struct kexe_scope {
  char resolved[KEXE_SCOPE_ENTRIES][4096];
  char orig[KEXE_SCOPE_ENTRIES][4096];
  int count;
};

static struct kexe_scope kexe_scope35; /* :fs/app-data read / write / range */
static struct kexe_scope kexe_scope34; /* :fs/browse directory listing      */

/* Fill SCOPE from a colon-separated list of path prefixes. Each entry is
 * kept in both spellings -- as written and as realpath resolved it -- so a
 * guest may name either and the resolved form still fails closed outside the
 * scope. An entry that does not resolve is dropped, not guessed at. */
static void kexe_scope_from_text(struct kexe_scope *scope, const char *scope_env) {
  scope->count = 0;
  if (scope_env == NULL || scope_env[0] == '\0') return;
  const char *cursor = scope_env;
  while (*cursor != '\0' && scope->count < KEXE_SCOPE_ENTRIES) {
    const char *end = strchr(cursor, ':');
    size_t entry_length = (end != NULL) ? (size_t)(end - cursor) : strlen(cursor);
    if (entry_length > 0 && entry_length < 4096) {
      char entry[4096];
      memcpy(entry, cursor, entry_length);
      entry[entry_length] = '\0';
      char resolved[4096];
      if (realpath(entry, resolved) != NULL &&
          strlen(resolved) < sizeof(scope->resolved[0])) {
        strcpy(scope->resolved[scope->count], resolved);
        strcpy(scope->orig[scope->count], entry);
        scope->count++;
      }
    }
    if (end != NULL) cursor = end + 1;
    else cursor += entry_length;
  }
}

/* Where a scope COMES FROM, which is the whole question for a packaged
 * command.
 *
 * A loader invocation takes it from the environment: the kbb shim resolves
 * the policy's resource scope and hands it over in KEXE_CAP_RESOURCES_<wire>.
 *
 * A packaged command must not, and the environment is ignored there. The
 * allow list is already a constant of the binary, and a scope taken from the
 * caller would let that caller widen what the command may read while the
 * grant it was packaged with says otherwise -- `KEXE_CAP_RESOURCES_35=/ ./cat
 * anything` would work on a binary packaged for one directory. So in an
 * embedded build the scope is a constant too, and there is no argument or
 * variable that moves it. */
static void kexe_scope_init(struct kexe_scope *scope, const char *env_name) {
#ifdef KEXE_EMBEDDED
  (void)env_name;
  kexe_scope_from_text(scope,
                       scope == &kexe_scope35 ? KEXE_EMBEDDED_SCOPE35
                                              : KEXE_EMBEDDED_SCOPE34);
#else
  kexe_scope_from_text(scope, getenv(env_name));
#endif
}

/* Lexical admission. `target` (absolute, NUL-terminated) must equal a scope
 * entry -- in either its literal or its resolved spelling -- or lie beneath
 * one. On success `candidate` is the target re-spelled under that entry's
 * RESOLVED prefix, so the open that follows happens on canonical bytes.
 * Returns 1 when admitted; nothing is opened here. */
static int kexe_scope_admit(const struct kexe_scope *scope, const char *target,
                            char candidate[4096]) {
  for (int s = 0; s < scope->count; s++) {
    for (int v = 0; v < 2; v++) {
      const char *base = (v == 0) ? scope->orig[s] : scope->resolved[s];
      size_t base_length = strlen(base);
      if (strncmp(target, base, base_length) != 0 ||
          (target[base_length] != '/' && target[base_length] != '\0')) continue;
      const char *suffix = target + base_length;
      size_t suffix_length = strlen(suffix);
      size_t real_length = strlen(scope->resolved[s]);
      if (real_length + suffix_length >= 4096) continue;
      memcpy(candidate, scope->resolved[s], real_length);
      memcpy(candidate + real_length, suffix, suffix_length + 1);
      return 1;
    }
  }
  return 0;
}

/* Containment of an OPENED fd -- the second check, after admission, because
 * the path that was admitted and the object that was opened can differ.
 * macOS: F_GETPATH gives the kernel's path for the fd, compared against each
 * resolved entry. Linux: the candidate was re-spelled under a resolved entry
 * (lexically inside the grant) and opened O_NOFOLLOW, so a (st_dev, st_ino)
 * match between the fd and a fresh stat of the candidate proves the fd IS
 * the granted object. Returns 1 when contained. */
static int kexe_scope_contains_fd(const struct kexe_scope *scope, int fd,
                                  const char *candidate) {
#if defined(__APPLE__)
  (void)candidate;
  char actual[4096];
  if (fcntl(fd, F_GETPATH, actual) != 0) return 0;
  size_t actual_length = strlen(actual);
  for (int s = 0; s < scope->count; s++) {
    const char *base = scope->resolved[s];
    size_t base_length = strlen(base);
    if (actual_length >= base_length &&
        memcmp(actual, base, base_length) == 0 &&
        (actual_length == base_length || actual[base_length] == '/')) return 1;
  }
  return 0;
#else
  /* The scope is consulted through `candidate`, which admission re-spelled
   * under a resolved entry; the parameter is kept so both branches share one
   * signature (GCC -Wunused-parameter, measured on the Linux CI hosts). */
  (void)scope;
  struct stat fd_sb, cand_sb;
  if (fstat(fd, &fd_sb) != 0 || stat(candidate, &cand_sb) != 0) return 0;
  return fd_sb.st_dev == cand_sb.st_dev && fd_sb.st_ino == cand_sb.st_ino;
#endif
}

/* Copies a request's path bytes into a NUL-terminated buffer, refusing the
 * empty, over-long and relative forms no provider admits. */
static int kexe_request_path(const uint8_t *bytes, size_t length,
                             char target[4096]) {
  if (bytes == NULL || length == 0 || length >= 4096 || bytes[0] != '/') return 0;
  memcpy(target, bytes, length);
  target[length] = '\0';
  return 1;
}

/* The single occurrence of `token` in `bytes`, or NULL when it is absent or
 * occurs again. The separators are ASCII tokens rather than control
 * characters because a Kotoba guest cannot emit a control character and has
 * no char-to-string builtin, so it builds the request with string-concat; a
 * second occurrence -- content or a path that contains the token -- is
 * refused fail-closed rather than escaped. */
static const uint8_t *kexe_single_token(const uint8_t *bytes, size_t length,
                                        const char *token) {
  size_t token_len = strlen(token);
  const uint8_t *first = NULL;
  for (size_t i = 0; i + token_len <= length; i++) {
    if (memcmp(bytes + i, token, token_len) != 0) continue;
    if (first != NULL) return NULL;
    first = bytes + i;
    i += token_len - 1;
  }
  return first;
}

/* memmem fallback for platforms without it (glibc has it; macOS lacks <string> memmem). */
static void *shim_memmem(const void *hay, size_t hlen, const void *needle, size_t nlen) {
  if (nlen == 0) return (void *)hay;
  if (hlen < nlen) return NULL;
  const uint8_t *h = (const uint8_t *)hay, *n = (const uint8_t *)needle;
  for (size_t i = 0; i + nlen <= hlen; i++) {
    if (memcmp(h + i, n, nlen) == 0) return (void *)(h + i);
  }
  return NULL;
}
#define memmem shim_memmem

/* wire id 35, READ form. The request string is an absolute path; the result
 * is the file's bytes as a string. The whole file is interned, so a file
 * larger than the string arena budget in force for the run cannot be read this
 * way -- that is what the RANGE form is for. */
/* wire id 35, EXISTS form: "<path>EXISTS_SEP" -> "1" when the path is a
 * readable file inside the granted scope, "0" otherwise.
 *
 * This exists because a guest could not report a missing operand. The read
 * form TRAPS on a path it cannot serve, and a trap cannot be caught, so the
 * guest never got control back to write `head: FILE: No such file or
 * directory` -- six commands in this family shipped saying so. The proper
 * answer would be a capability returning [:result T E], but the native gate
 * admits `[:result-i64 :result-i64]` and not a result over a string, so that
 * is a change to the gate. This is a change to a request form, on a wire
 * that already tells three of them apart by an ASCII token.
 *
 * A path OUTSIDE the scope answers "0", not a trap and not "1". That is the
 * safe answer and the deliberate one: "0" is indistinguishable from absent,
 * so a guest cannot use this to probe for the existence of files it was
 * never granted. It learns exactly one thing -- whether the operand it was
 * given is one it may read -- which is the question a command asks. */
static int64_t fs_app_data_exists_provider(struct kexe_context_v4 *context,
                                           int64_t request) {
  const uint8_t *bytes = NULL;
  uint64_t length = 0;
  char target[4096], candidate[4096];
  if (!read_string_handle(context, request, &bytes, &length)) {
    raise(SIGILL);
    return 0;
  }
  /* Strip the token before resolving: the path is everything before it. */
  const uint8_t *token = (const uint8_t *)memmem(bytes, (size_t)length,
                                                 "EXISTS_SEP", 10);
  if (token == NULL) {
    raise(SIGILL);
    return 0;
  }
  size_t path_length = (size_t)(token - bytes);
  if (!kexe_request_path(bytes, path_length, target) ||
      !kexe_scope_admit(&kexe_scope35, target, candidate)) {
    return intern_utf8(context, (const uint8_t *)"0", 1);
  }
  int fd = open(candidate, O_RDONLY | O_NOFOLLOW);
  if (fd < 0) {
    return intern_utf8(context, (const uint8_t *)"0", 1);
  }
  int inside = kexe_scope_contains_fd(&kexe_scope35, fd, candidate);
  close(fd);
  return intern_utf8(context, (const uint8_t *)(inside ? "1" : "0"), 1);
}

static int64_t fs_app_data_read_provider(struct kexe_context_v4 *context,
                                         int64_t request) {
  const uint8_t *bytes = NULL;
  uint64_t length = 0;
  char target[4096], candidate[4096];
  if (!read_string_handle(context, request, &bytes, &length) ||
      !kexe_request_path(bytes, (size_t)length, target) ||
      !kexe_scope_admit(&kexe_scope35, target, candidate)) {
    raise(SIGILL);
    return 0;
  }
  int fd = open(candidate, O_RDONLY | O_NOFOLLOW);
  if (fd < 0 || !kexe_scope_contains_fd(&kexe_scope35, fd, candidate)) {
    if (fd >= 0) close(fd);
    raise(SIGILL);
    return 0;
  }

  size_t capacity = 65536;
  uint8_t *buffer = (uint8_t *)malloc(capacity);
  size_t total = 0;
  if (buffer == NULL) {
    close(fd);
    raise(SIGILL);
    return 0;
  }
  for (;;) {
    if (total == capacity) {
      size_t next = capacity * 2;
      uint8_t *grown = (uint8_t *)realloc(buffer, next);
      if (grown == NULL) {
        free(buffer);
        close(fd);
        raise(SIGILL);
        return 0;
      }
      buffer = grown;
      capacity = next;
    }
    ssize_t got = read(fd, buffer + total, capacity - total);
    if (got < 0) {
      if (errno == EINTR) continue;
      free(buffer);
      close(fd);
      raise(SIGILL);
      return 0;
    }
    if (got == 0) break;
    total += (size_t)got;
  }
  close(fd);
  int64_t result = intern_utf8(context, buffer, total);
  free(buffer);
  return result;
}

/* wire id 35, WRITE form: "<path>WRITE_SEP<content>" -> the content written
 * back (so the guest can verify the write via string-byte-length and the
 * capability keeps its typed :string result). Same scope and containment as
 * the read form. The file is created/truncated O_NOFOLLOW; writing through a
 * symlink is impossible, and a directory target is refused. */
static int64_t fs_app_data_write_provider(struct kexe_context_v4 *context,
                                          int64_t request) {
  const uint8_t *bytes = NULL;
  uint64_t length = 0;
  if (!read_string_handle(context, request, &bytes, &length) || bytes == NULL) {
    raise(SIGILL);
    return 0;
  }
  static const char write_token[] = "WRITE_SEP";
  const size_t token_len = sizeof(write_token) - 1u;
  const uint8_t *sep = kexe_single_token(bytes, (size_t)length, write_token);
  char target[4096], candidate[4096];
  if (sep == NULL ||
      !kexe_request_path(bytes, (size_t)(sep - bytes), target) ||
      !kexe_scope_admit(&kexe_scope35, target, candidate)) {
    raise(SIGILL);
    return 0;
  }
  const uint8_t *content = sep + token_len;
  size_t content_length = (size_t)(bytes + length - content);

  struct stat st;
  if (stat(candidate, &st) == 0 && S_ISDIR(st.st_mode)) {
    raise(SIGILL);
    return 0;
  }
  int fd = open(candidate, O_WRONLY | O_CREAT | O_TRUNC | O_NOFOLLOW, 0644);
  if (fd < 0 || !kexe_scope_contains_fd(&kexe_scope35, fd, candidate)) {
    if (fd >= 0) close(fd);
    raise(SIGILL);
    return 0;
  }

  size_t off = 0;
  while (off < content_length) {
    ssize_t w = write(fd, content + off, content_length - off);
    if (w < 0) {
      if (errno == EINTR) continue;
      close(fd);
      raise(SIGILL);
      return 0;
    }
    off += (size_t)w;
  }
  close(fd);
  return intern_utf8(context, content, content_length);
}

static int64_t kexe_answer_bool(struct kexe_context_v4 *context, int ok) {
  return intern_utf8(context, (const uint8_t *)(ok ? "1" : "0"), 1);
}

/* wire id 35, STAT form: "<path>STAT_SEP" -> "<mode> <size> <blocks> <isdir>"
 * in decimal, space separated, or the EMPTY string when the path cannot be
 * stat'ed.
 *
 * This widens a wire-35 grant by strictly less than nothing it did not
 * already allow: a grant that can read a file's CONTENTS can already tell its
 * size. The mode and the block count are what `du`, `chmod` and `ls -l` need
 * and what no other form answers -- `du` in particular reports DISK BLOCKS
 * and not bytes, so st_size cannot produce it (a one-byte file occupies a
 * whole block, measured: du reports 8 512-byte units for a directory holding
 * one 1-byte file).
 *
 * Same confinement as reading: open with O_NOFOLLOW, then prove the
 * descriptor is inside the scope before trusting it. */
static int64_t fs_app_data_stat_provider(struct kexe_context_v4 *context,
                                         int64_t request) {
  const uint8_t *bytes = NULL;
  uint64_t length = 0;
  static const char token[] = "STAT_SEP";
  char target[4096], candidate[4096];
  const uint8_t *sep = NULL;
  if (!read_string_handle(context, request, &bytes, &length) || bytes == NULL ||
      (sep = kexe_single_token(bytes, (size_t)length, token)) == NULL ||
      !kexe_request_path(bytes, (size_t)(sep - bytes), target) ||
      !kexe_scope_admit(&kexe_scope35, target, candidate)) {
    raise(SIGILL);
    return 0;
  }
  int fd = open(candidate, O_RDONLY | O_NOFOLLOW);
  if (fd < 0) return intern_utf8(context, (const uint8_t *)"", 0);
  if (!kexe_scope_contains_fd(&kexe_scope35, fd, candidate)) {
    close(fd);
    raise(SIGILL);
    return 0;
  }
  struct stat sb;
  if (fstat(fd, &sb) != 0) {
    close(fd);
    return intern_utf8(context, (const uint8_t *)"", 0);
  }
  close(fd);
  char answer[128];
  int n = snprintf(answer, sizeof(answer),
                   "%u %lld %lld %d",
                   (unsigned)(sb.st_mode & 0777), (long long)sb.st_size,
                   (long long)sb.st_blocks, S_ISDIR(sb.st_mode) ? 1 : 0);
  if (n <= 0 || (size_t)n >= sizeof(answer)) {
    raise(SIGILL);
    return 0;
  }
  return intern_utf8(context, (const uint8_t *)answer, (size_t)n);
}

/* wire id 35, CHMOD form: "<path>CHMOD_SEP<octal>" -> "1"/"0".
 *
 * The mode arrives as OCTAL TEXT, which is how chmod(1) is written and how
 * the guest received it, so neither side re-renders it. Only the twelve
 * permission bits are honoured: setuid, setgid and the sticky bit are NOT
 * settable through this form, because a grant to write a file's bytes is not
 * a grant to make it run as someone else. */
static int64_t fs_app_data_chmod_provider(struct kexe_context_v4 *context,
                                          int64_t request) {
  const uint8_t *bytes = NULL;
  uint64_t length = 0;
  static const char token[] = "CHMOD_SEP";
  const size_t token_len = sizeof(token) - 1u;
  char target[4096], candidate[4096];
  const uint8_t *sep = NULL;
  if (!read_string_handle(context, request, &bytes, &length) || bytes == NULL ||
      (sep = kexe_single_token(bytes, (size_t)length, token)) == NULL ||
      !kexe_request_path(bytes, (size_t)(sep - bytes), target) ||
      !kexe_scope_admit(&kexe_scope35, target, candidate)) {
    raise(SIGILL);
    return 0;
  }
  const uint8_t *digits = sep + token_len;
  size_t digit_count = (size_t)(bytes + length - digits);
  if (digit_count == 0 || digit_count > 6) {
    raise(SIGILL);
    return 0;
  }
  unsigned mode = 0;
  for (size_t i = 0; i < digit_count; i++) {
    if (digits[i] < '0' || digits[i] > '7') {
      raise(SIGILL);
      return 0;
    }
    mode = mode * 8u + (unsigned)(digits[i] - '0');
  }
  /* Permission bits only. */
  mode &= 0777u;
  int fd = open(candidate, O_RDONLY | O_NOFOLLOW);
  if (fd < 0) return kexe_answer_bool(context, 0);
  if (!kexe_scope_contains_fd(&kexe_scope35, fd, candidate)) {
    close(fd);
    raise(SIGILL);
    return 0;
  }
  int ok = fchmod(fd, (mode_t)mode) == 0;
  close(fd);
  return kexe_answer_bool(context, ok);
}

/* --- scoped mutation -------------------------------------------------------
 *
 * mkdir, unlink, rmdir and rename, each confined to the wire-35 scope.
 *
 * The read and write providers above are safe because they OPEN the target
 * and then ask `kexe_scope_contains_fd`, which resolves the descriptor
 * (F_GETPATH on macOS, dev+ino comparison elsewhere) and so cannot be fooled
 * by a `..` component or a symlink. `kexe_scope_admit` alone would be: it
 * matches text, and `/granted/../../etc` prefixes `/granted` at a `/`
 * boundary.
 *
 * A mutation has no descriptor for the thing it acts on -- unlink removes a
 * name, not an open file -- so the same guarantee is obtained one level up:
 * open the PARENT directory, put it through the identical containment check,
 * and then act relative to that descriptor with mkdirat/unlinkat/renameat.
 * The name operated on is a single component, so it cannot walk anywhere.
 *
 * These ANSWER "1" or "0" rather than trapping when the operation fails --
 * `rm` of a name that is not there is a diagnostic the guest must write, not
 * a fault. A request OUTSIDE the scope still traps, exactly as writing does:
 * that is not a question, it is a grant violation. */
static int kexe_split_parent(const char *candidate, char parent[4096],
                             char base[256]) {
  const char *slash = strrchr(candidate, '/');
  if (slash == NULL || slash == candidate) return 0;
  size_t parent_length = (size_t)(slash - candidate);
  size_t base_length = strlen(slash + 1);
  if (parent_length == 0 || parent_length >= 4096) return 0;
  if (base_length == 0 || base_length >= 256) return 0;
  /* A single component: no traversal, no re-entry into the path resolver. */
  if (strcmp(slash + 1, ".") == 0 || strcmp(slash + 1, "..") == 0) return 0;
  memcpy(parent, candidate, parent_length);
  parent[parent_length] = '\0';
  memcpy(base, slash + 1, base_length + 1);
  return 1;
}

/* The parent directory of `candidate`, open and proven inside the scope, or
 * -1. The caller closes it.
 *
 * `*fatal` separates the two ways this fails, and the distinction is the
 * whole contract: a parent that cannot be OPENED is an operational failure
 * the guest has to report (`mkdir x/y` when `x` is absent is a diagnostic,
 * not a fault), while a malformed request or a parent outside the grant is a
 * violation and traps. Answering "0" for the second would turn a grant breach
 * into a routine `false`; trapping on the first made `mkdir x/y` die with
 * SIGILL where mkdir(1) prints one line and exits 1. */
static int kexe_scoped_parent_fd(const char *candidate, char base[256],
                                 int *fatal) {
  char parent[4096];
  *fatal = 0;
  if (!kexe_split_parent(candidate, parent, base)) {
    *fatal = 1;
    return -1;
  }
  int dfd = open(parent, O_RDONLY | O_DIRECTORY);
  if (dfd < 0) return -1;
  if (!kexe_scope_contains_fd(&kexe_scope35, dfd, parent)) {
    close(dfd);
    *fatal = 1;
    return -1;
  }
  return dfd;
}

/* wire id 35, MKDIR form: "<path>MKDIR_SEP" -> "1" if the directory was
 * created, "0" if it was not (it already exists, the parent is missing, the
 * filesystem refused). 0777 is passed and the process umask applies, which is
 * what mkdir(1) itself does. */
static int64_t fs_app_data_mkdir_provider(struct kexe_context_v4 *context,
                                          int64_t request) {
  const uint8_t *bytes = NULL;
  uint64_t length = 0;
  static const char token[] = "MKDIR_SEP";
  char target[4096], candidate[4096], base[256];
  const uint8_t *sep = NULL;
  if (!read_string_handle(context, request, &bytes, &length) || bytes == NULL ||
      (sep = kexe_single_token(bytes, (size_t)length, token)) == NULL ||
      !kexe_request_path(bytes, (size_t)(sep - bytes), target) ||
      !kexe_scope_admit(&kexe_scope35, target, candidate)) {
    raise(SIGILL);
    return 0;
  }
  int fatal = 0;
  int dfd = kexe_scoped_parent_fd(candidate, base, &fatal);
  if (dfd < 0) {
    if (fatal) {
      raise(SIGILL);
      return 0;
    }
    return kexe_answer_bool(context, 0);
  }
  int ok = mkdirat(dfd, base, 0777) == 0;
  close(dfd);
  return kexe_answer_bool(context, ok);
}

/* wire id 35, UNLINK form: "<path>UNLINK_SEP" -> "1" if the name was removed.
 * AT_REMOVEDIR is NOT passed, so this refuses a directory the way unlink(2)
 * does; RMDIR_SEP is the separate form for that, because `rm` and `rmdir` are
 * separate commands and answering both from one request would let a guest
 * remove a tree it only asked to remove a file from. */
static int64_t fs_app_data_unlink_provider(struct kexe_context_v4 *context,
                                           int64_t request) {
  const uint8_t *bytes = NULL;
  uint64_t length = 0;
  static const char token[] = "UNLINK_SEP";
  char target[4096], candidate[4096], base[256];
  const uint8_t *sep = NULL;
  if (!read_string_handle(context, request, &bytes, &length) || bytes == NULL ||
      (sep = kexe_single_token(bytes, (size_t)length, token)) == NULL ||
      !kexe_request_path(bytes, (size_t)(sep - bytes), target) ||
      !kexe_scope_admit(&kexe_scope35, target, candidate)) {
    raise(SIGILL);
    return 0;
  }
  int fatal = 0;
  int dfd = kexe_scoped_parent_fd(candidate, base, &fatal);
  if (dfd < 0) {
    if (fatal) {
      raise(SIGILL);
      return 0;
    }
    return kexe_answer_bool(context, 0);
  }
  int ok = unlinkat(dfd, base, 0) == 0;
  close(dfd);
  return kexe_answer_bool(context, ok);
}

/* wire id 35, RMDIR form: "<path>RMDIR_SEP" -> "1" if the EMPTY directory was
 * removed. A non-empty one answers "0"; there is no recursive form, and a
 * guest that wants one walks the tree itself under its own fuel. */
static int64_t fs_app_data_rmdir_provider(struct kexe_context_v4 *context,
                                          int64_t request) {
  const uint8_t *bytes = NULL;
  uint64_t length = 0;
  static const char token[] = "RMDIR_SEP";
  char target[4096], candidate[4096], base[256];
  const uint8_t *sep = NULL;
  if (!read_string_handle(context, request, &bytes, &length) || bytes == NULL ||
      (sep = kexe_single_token(bytes, (size_t)length, token)) == NULL ||
      !kexe_request_path(bytes, (size_t)(sep - bytes), target) ||
      !kexe_scope_admit(&kexe_scope35, target, candidate)) {
    raise(SIGILL);
    return 0;
  }
  int fatal = 0;
  int dfd = kexe_scoped_parent_fd(candidate, base, &fatal);
  if (dfd < 0) {
    if (fatal) {
      raise(SIGILL);
      return 0;
    }
    return kexe_answer_bool(context, 0);
  }
  int ok = unlinkat(dfd, base, AT_REMOVEDIR) == 0;
  close(dfd);
  return kexe_answer_bool(context, ok);
}

/* wire id 35, RENAME form: "<from>RENAME_SEP<to>" -> "1" if renamed. BOTH
 * sides are admitted and BOTH parents are proven in scope, so this cannot be
 * used to move a file out of the grant or to pull one in. */
static int64_t fs_app_data_rename_provider(struct kexe_context_v4 *context,
                                           int64_t request) {
  const uint8_t *bytes = NULL;
  uint64_t length = 0;
  static const char token[] = "RENAME_SEP";
  const size_t token_len = sizeof(token) - 1u;
  char from_target[4096], from_candidate[4096], from_base[256];
  char to_target[4096], to_candidate[4096], to_base[256];
  const uint8_t *sep = NULL;
  if (!read_string_handle(context, request, &bytes, &length) || bytes == NULL ||
      (sep = kexe_single_token(bytes, (size_t)length, token)) == NULL ||
      !kexe_request_path(bytes, (size_t)(sep - bytes), from_target) ||
      !kexe_request_path(sep + token_len,
                         (size_t)(bytes + length - (sep + token_len)),
                         to_target) ||
      !kexe_scope_admit(&kexe_scope35, from_target, from_candidate) ||
      !kexe_scope_admit(&kexe_scope35, to_target, to_candidate)) {
    raise(SIGILL);
    return 0;
  }
  int fatal = 0;
  int from_fd = kexe_scoped_parent_fd(from_candidate, from_base, &fatal);
  if (from_fd < 0) {
    if (fatal) {
      raise(SIGILL);
      return 0;
    }
    return kexe_answer_bool(context, 0);
  }
  int to_fd = kexe_scoped_parent_fd(to_candidate, to_base, &fatal);
  if (to_fd < 0) {
    close(from_fd);
    if (fatal) {
      raise(SIGILL);
      return 0;
    }
    return kexe_answer_bool(context, 0);
  }
  int ok = renameat(from_fd, from_base, to_fd, to_base) == 0;
  close(from_fd);
  close(to_fd);
  return kexe_answer_bool(context, ok);
}

/* Bounded decimal parse over a byte span: digits only (no sign, no '+', no
 * whitespace), at most 20 of them, overflow refused. */
static int kexe_parse_u64_span(const uint8_t *text, size_t length,
                               uint64_t *value) {
  if (length == 0 || length > 20) return 0;
  uint64_t acc = 0;
  for (size_t i = 0; i < length; i++) {
    if (text[i] < '0' || text[i] > '9') return 0;
    uint64_t digit = (uint64_t)(text[i] - '0');
    if (acc > (UINT64_MAX - digit) / 10u) return 0;
    acc = acc * 10u + digit;
  }
  *value = acc;
  return 1;
}

/* wire id 35, RANGE form: "<path>RANGE_SEP<offset>:<length>" -> exactly
 * `length` bytes of the file starting at byte `offset`, as a string. The
 * window must lie inside the file ([offset, offset+length) within its size
 * -- a short read is never answered) and `length` must fit the string pool.
 * The result is then validated as canonical UTF-8 by the typed dispatch like
 * every other string result, so a window that cuts a code point traps rather
 * than answering bytes no guest string may hold. Same scope and containment
 * as the read form. This is what lets a guest read a file larger than one
 * guest string, one bounded window at a time. */
static int64_t fs_app_data_range_read_provider(struct kexe_context_v4 *context,
                                               int64_t request) {
  const uint8_t *bytes = NULL;
  uint64_t length = 0;
  if (!read_string_handle(context, request, &bytes, &length) || bytes == NULL) {
    raise(SIGILL);
    return 0;
  }
  static const char range_token[] = "RANGE_SEP";
  const size_t token_len = sizeof(range_token) - 1u;
  const uint8_t *sep = kexe_single_token(bytes, (size_t)length, range_token);
  char target[4096], candidate[4096];
  if (sep == NULL ||
      !kexe_request_path(bytes, (size_t)(sep - bytes), target) ||
      !kexe_scope_admit(&kexe_scope35, target, candidate)) {
    raise(SIGILL);
    return 0;
  }
  const uint8_t *spec = sep + token_len;
  size_t spec_length = (size_t)(bytes + length - spec);
  const uint8_t *colon = memchr(spec, ':', spec_length);
  uint64_t offset = 0, window = 0;
  if (colon == NULL ||
      !kexe_parse_u64_span(spec, (size_t)(colon - spec), &offset) ||
      !kexe_parse_u64_span(colon + 1, (size_t)(spec + spec_length - colon - 1), &window) ||
      window > kexe_string_pool_budget) {
    raise(SIGILL);
    return 0;
  }

  int fd = open(candidate, O_RDONLY | O_NOFOLLOW);
  if (fd < 0 || !kexe_scope_contains_fd(&kexe_scope35, fd, candidate)) {
    if (fd >= 0) close(fd);
    raise(SIGILL);
    return 0;
  }
  struct stat st;
  if (fstat(fd, &st) != 0 || !S_ISREG(st.st_mode) || st.st_size < 0 ||
      offset > (uint64_t)st.st_size || window > (uint64_t)st.st_size - offset) {
    close(fd);
    raise(SIGILL);
    return 0;
  }
  uint8_t *buffer = (uint8_t *)malloc(window == 0 ? 1u : (size_t)window);
  if (buffer == NULL) {
    close(fd);
    raise(SIGILL);
    return 0;
  }
  size_t total = 0;
  while (total < (size_t)window) {
    ssize_t got = pread(fd, buffer + total, (size_t)window - total,
                        (off_t)(offset + total));
    if (got < 0) {
      if (errno == EINTR) continue;
      free(buffer);
      close(fd);
      raise(SIGILL);
      return 0;
    }
    if (got == 0) break; /* the file shrank under us: a short window is refused below */
    total += (size_t)got;
  }
  close(fd);
  if (total != (size_t)window) {
    free(buffer);
    raise(SIGILL);
    return 0;
  }
  int64_t result = intern_utf8(context, buffer, total);
  free(buffer);
  return result;
}

/* wire id 34 = :fs/browse. The request string is an absolute DIRECTORY path
 * inside KEXE_CAP_RESOURCES_34; the result is the directory's entries, one
 * "NAME<TAB>D" line each -- D is "1" for a directory and "0" for a file --
 * sorted bytewise by NAME and joined by a single "\n" (the empty string for
 * an empty directory). "." and ".." are never listed. This is the same wire
 * the js host answers for the same id (kotoba bin/kbb_js.cljs wire 34) and
 * the wire lib/kbb/browse.kotoba is written against: the is-directory flag
 * is what a recursive scan needs, so a guest can walk a tree without
 * guessing which entry is a directory. Bounds: at most
 * KEXE_BROWSE_ENTRY_LIMIT entries and a listing that fits the string pool;
 * more is refused, not truncated (a truncated listing would look like a
 * smaller directory). Names are validated as UTF-8 by the typed dispatch,
 * so a non-UTF-8 name traps the call. The directory is opened
 * O_NOFOLLOW|O_DIRECTORY and contained like a file. */
#define KEXE_BROWSE_ENTRY_LIMIT 4096u

/* The dirent type byte's DT_DIR value; defined here so the module compiles
 * the same under -std=c11 on macOS and Linux (both platforms use 4). */
#ifndef DT_DIR
#define DT_DIR 4
#endif

/* One listing entry: the name plus the is-directory flag taken from the SAME
 * dirent record that supplied the name (a separate stat would follow a
 * symlink where the dirent type does not -- the js host's readdirSync
 * withFileTypes answers DT_LNK the same way, so both hosts agree). */
struct kexe_browse_entry {
  char *name;
  uint8_t is_dir;
};

static int kexe_browse_compare(const void *a, const void *b) {
  return strcmp(((const struct kexe_browse_entry *)a)->name,
                ((const struct kexe_browse_entry *)b)->name);
}

static void kexe_free_browse_entries(struct kexe_browse_entry *entries,
                                     size_t count) {
  for (size_t i = 0; i < count; i++) free(entries[i].name);
  free(entries);
}

/* One entry into the listing under construction; 0 = refuse (over the name
 * or byte bound, or out of memory). "." and ".." are skipped here. Each
 * entry contributes its name, a TAB and the one-byte D flag; a newline
 * separates every entry after the first -- the byte total is what the
 * provider later mallocs, so the check and the accumulation count the same
 * bytes. */
static int kexe_browse_add(const char *name, uint8_t is_dir,
                           struct kexe_browse_entry **entries, size_t *count,
                           size_t *capacity, size_t *total) {
  if (strcmp(name, ".") == 0 || strcmp(name, "..") == 0) return 1;
  size_t name_length = strlen(name);
  size_t entry_bytes = name_length + 2u + (*count > 0 ? 1u : 0u);
  if (*count >= KEXE_BROWSE_ENTRY_LIMIT ||
      *total + entry_bytes > kexe_string_pool_budget) return 0;
  if (*count == *capacity) {
    size_t next = *capacity == 0 ? 64u : *capacity * 2u;
    struct kexe_browse_entry *grown =
        (struct kexe_browse_entry *)realloc(*entries,
                                            next * sizeof(struct kexe_browse_entry));
    if (grown == NULL) return 0;
    *entries = grown;
    *capacity = next;
  }
  char *copy = (char *)malloc(name_length + 1u);
  if (copy == NULL) return 0;
  memcpy(copy, name, name_length + 1u);
  (*entries)[*count].name = copy;
  (*entries)[*count].is_dir = is_dir ? 1u : 0u;
  (*count)++;
  *total += entry_bytes;
  return 1;
}

/* Directory enumeration. Linux reads the raw getdents64 records into a
 * static buffer: glibc's fdopendir would fcntl(F_GETFL) and then
 * fcntl(F_SETFD, FD_CLOEXEC) on the fd (measured with strace on glibc 2.39:
 * the second one trips the seccomp filter as SIGSYS), and admitting fcntl
 * for that is more surface than reading the records the kernel already
 * hands over. macOS uses fdopendir/readdir; Seatbelt filters paths, not
 * syscalls. Both consume the fd. Returns 0 on refusal. */
#if defined(__linux__)
static int kexe_enumerate_directory(int fd, struct kexe_browse_entry **entries,
                                    size_t *count, size_t *capacity,
                                    size_t *total) {
  static uint8_t records[32768];
  for (;;) {
    long got = syscall(SYS_getdents64, fd, records, sizeof(records));
    if (got < 0) {
      if (errno == EINTR) continue;
      close(fd);
      return 0;
    }
    if (got == 0) break;
    long pos = 0;
    while (pos < got) {
      /* struct linux_dirent64: u64 d_ino, s64 d_off, u16 d_reclen,
       * u8 d_type, char d_name[] -- the type is byte 18, the name starts
       * at byte 19 and is NUL-terminated within d_reclen. */
      if (got - pos < 19) { close(fd); return 0; }
      uint16_t reclen = 0;
      memcpy(&reclen, records + pos + 16, sizeof(reclen));
      if (reclen < 20 || pos + (long)reclen > got) { close(fd); return 0; }
      const char *name = (const char *)(records + pos + 19);
      uint8_t d_type = records[pos + 18];
      if (memchr(name, '\0', (size_t)reclen - 19u) == NULL) { close(fd); return 0; }
      if (!kexe_browse_add(name, d_type == DT_DIR, entries, count, capacity, total)) {
        close(fd);
        return 0;
      }
      pos += reclen;
    }
  }
  close(fd);
  return 1;
}
#else
static int kexe_enumerate_directory(int fd, struct kexe_browse_entry **entries,
                                    size_t *count, size_t *capacity,
                                    size_t *total) {
  DIR *dir = fdopendir(fd);
  if (dir == NULL) {
    close(fd);
    return 0;
  }
  int ok = 1;
  for (;;) {
    errno = 0;
    struct dirent *entry = readdir(dir);
    if (entry == NULL) {
      if (errno != 0) ok = 0;
      break;
    }
    if (!kexe_browse_add(entry->d_name, entry->d_type == DT_DIR,
                         entries, count, capacity, total)) { ok = 0; break; }
  }
  closedir(dir);
  return ok;
}
#endif

static int64_t fs_browse_provider(struct kexe_context_v4 *context,
                                  int64_t request) {
  const uint8_t *bytes = NULL;
  uint64_t length = 0;
  char target[4096], candidate[4096];
  if (!read_string_handle(context, request, &bytes, &length) ||
      !kexe_request_path(bytes, (size_t)length, target) ||
      !kexe_scope_admit(&kexe_scope34, target, candidate)) {
    raise(SIGILL);
    return 0;
  }
  int fd = open(candidate, O_RDONLY | O_DIRECTORY | O_NOFOLLOW);
  if (fd < 0 || !kexe_scope_contains_fd(&kexe_scope34, fd, candidate)) {
    if (fd >= 0) close(fd);
    raise(SIGILL);
    return 0;
  }
  struct kexe_browse_entry *entries = NULL;
  size_t count = 0, capacity = 0, total = 0;
  if (!kexe_enumerate_directory(fd, &entries, &count, &capacity, &total)) {
    kexe_free_browse_entries(entries, count);
    raise(SIGILL);
    return 0;
  }
  qsort(entries, count, sizeof(struct kexe_browse_entry), kexe_browse_compare);
  uint8_t *listing = (uint8_t *)malloc(total == 0 ? 1u : total);
  if (listing == NULL) {
    kexe_free_browse_entries(entries, count);
    raise(SIGILL);
    return 0;
  }
  size_t used = 0;
  for (size_t i = 0; i < count; i++) {
    if (i > 0) listing[used++] = '\n';
    size_t name_length = strlen(entries[i].name);
    memcpy(listing + used, entries[i].name, name_length);
    used += name_length;
    listing[used++] = '\t';
    listing[used++] = entries[i].is_dir ? '1' : '0';
  }
  kexe_free_browse_entries(entries, count);
  int64_t result = intern_utf8(context, listing, used);
  free(listing);
  return result;
}


static int64_t checked_typed_cap_call(struct kexe_context_v4 *context,
                                      uint64_t id, uint64_t request_kind,
                                      uint64_t result_kind, int64_t request) {
  if (context == NULL || context->version != 4 || id > 255 ||
      !(context->allow[id / 64] & (UINT64_C(1) << (id % 64))) ||
      request_kind != result_kind ||
      !valid_typed_value(context, request_kind, request)) {
    raise(SIGILL);
    return 0;
  }
  int64_t result;
  if (request_kind == KEXE_TYPED_CLOCK_V1) {
    /* Hosted oracle for the nested clock-v1 codec. Identity would echo the
     * request pair and cannot produce a wall record; production native-aot
     * remains the C-free aiueos syscall (ADR 0271). */
    if (id != KEXE_CLOCK_CAPABILITY_ID) {
      raise(SIGILL);
      return 0;
    }
    result = hosted_clock_v1(context, request);
  } else if (id == 24 && request_kind == KEXE_TYPED_DATASPACE_V1) {
    result = dataspace_inject(context, request);
  } else if (id == 9 && request_kind == KEXE_TYPED_UI_COMMIT_V1) {
    result = ui_commit_inject(context, request);
  } else if (id == 10 && request_kind == KEXE_TYPED_UI_EVENT_V1) {
    result = ui_event_inject(context, request);
  } else if (id == 35 && request_kind == KEXE_TYPED_STRING) {
    /* wire id 35 = :fs/app-data, told apart by an ASCII token:
     *   "<path>WRITE_SEP<content>"      write
     *   "<path>RANGE_SEP<off>:<len>"    one bounded window
     *   "<path>EXISTS_SEP"              "1"/"0"
     *   "<path>MKDIR_SEP"               create a directory
     *   "<path>UNLINK_SEP"              remove a name
     *   "<path>RMDIR_SEP"               remove an empty directory
     *   "<from>RENAME_SEP<to>"          rename
     *   a bare absolute path            read the whole file
     *
     * WRITE_SEP is tested FIRST and stays first: written content may itself
     * contain any of these tokens, and only the write form has content. The
     * mutation forms carry no content, so their order among themselves does
     * not matter. Scope is KEXE_CAP_RESOURCES_35 for all of them. */
    uint64_t rlen = 0;
    const uint8_t *rb = NULL;
    if (read_string_handle(context, request, &rb, &rlen) && rb &&
        memmem(rb, (size_t)rlen, "WRITE_SEP", 9) != NULL) {
      result = fs_app_data_write_provider(context, request);
    } else if (rb != NULL && memmem(rb, (size_t)rlen, "EXISTS_SEP", 10) != NULL) {
      /* Tested before RANGE_SEP and after WRITE_SEP for the same reason the
       * existing order has: written content may contain any of these tokens,
       * and an EXISTS request carries no content at all. */
      result = fs_app_data_exists_provider(context, request);
    } else if (rb != NULL && memmem(rb, (size_t)rlen, "RANGE_SEP", 9) != NULL) {
      result = fs_app_data_range_read_provider(context, request);
    } else if (rb != NULL && memmem(rb, (size_t)rlen, "STAT_SEP", 8) != NULL) {
      result = fs_app_data_stat_provider(context, request);
    } else if (rb != NULL && memmem(rb, (size_t)rlen, "CHMOD_SEP", 9) != NULL) {
      result = fs_app_data_chmod_provider(context, request);
    } else if (rb != NULL && memmem(rb, (size_t)rlen, "MKDIR_SEP", 9) != NULL) {
      result = fs_app_data_mkdir_provider(context, request);
    } else if (rb != NULL && memmem(rb, (size_t)rlen, "UNLINK_SEP", 10) != NULL) {
      result = fs_app_data_unlink_provider(context, request);
    } else if (rb != NULL && memmem(rb, (size_t)rlen, "RMDIR_SEP", 9) != NULL) {
      result = fs_app_data_rmdir_provider(context, request);
    } else if (rb != NULL && memmem(rb, (size_t)rlen, "RENAME_SEP", 10) != NULL) {
      result = fs_app_data_rename_provider(context, request);
    } else {
      result = fs_app_data_read_provider(context, request);
    }
  } else if (id == 34 && request_kind == KEXE_TYPED_STRING) {
    /* wire id 34 = :fs/browse. Real host provider: the request string is an
     * absolute directory path inside KEXE_CAP_RESOURCES_34; the result is the
     * sorted NAME<TAB>D lines ("1" = directory, "0" = file), the same wire
     * the js host answers. */
    result = fs_browse_provider(context, request);
  } else if (id == 39 && request_kind == KEXE_TYPED_STRING) {
    /* wire id 39 = :io/write-error. Real host provider: the request string is
     * written to fd 2 and the result is the decimal byte count. No resource
     * scope, for the same reason wire 37 has none. */
    result = io_write_error_provider(context, request);
  } else if (id == 38 && request_kind == KEXE_TYPED_STRING) {
    /* wire id 38 = :cli/args. Real host provider: the empty request answers
     * the argument count as decimal text, a decimal index answers that
     * argument, past the end answers the empty string. */
    result = cli_args_provider(context, request);
  } else if (id == 37 && request_kind == KEXE_TYPED_STRING) {
    /* wire id 37 = :io/write. Real host provider: the request string is
     * written to fd 1 and the result is the decimal byte count. No resource
     * scope -- the guest names no destination, so there is nothing to
     * narrow. */
    result = io_write_provider(context, request);
  } else if (id == 33 && request_kind == KEXE_TYPED_STRING) {
    /* wire id 33 = :env/read. Real host provider: the request string is
     * the environment variable name; the result is its value (empty
     * string when unset). Other string-capability ids keep the
     * deterministic identity stub below. */
    result = env_read_provider(context, request);
  } else {
    /* The qualification host's deterministic typed provider is identity
     * for the one-word string/option/result slice. */
    result = request;
  }
  if (!valid_typed_value(context, result_kind, result)) {
    raise(SIGILL);
    return 0;
  }
  return result;
}

/* Explicit 16-byte equality lane used by every native string comparison.
 * `memcmp` is still the bounded scalar/tail oracle, but the hot body no longer
 * depends on a libc implementation choosing SIMD for these short guest
 * strings. Unaligned loads are intentional: string views may begin at any
 * validated UTF-8 boundary. */
static int simd_bytes_equal(const uint8_t *a, const uint8_t *b, size_t length) {
  size_t i = 0;
#if defined(__aarch64__)
  for (; i + 16u <= length; i += 16u) {
    uint8x16_t av = vld1q_u8(a + i);
    uint8x16_t bv = vld1q_u8(b + i);
    if (vminvq_u8(vceqq_u8(av, bv)) != UINT8_MAX) return 0;
  }
#elif defined(__SSE2__)
  for (; i + 16u <= length; i += 16u) {
    __m128i av = _mm_loadu_si128((const __m128i *)(const void *)(a + i));
    __m128i bv = _mm_loadu_si128((const __m128i *)(const void *)(b + i));
    if (_mm_movemask_epi8(_mm_cmpeq_epi8(av, bv)) != 0xffff) return 0;
  }
#endif
  return memcmp(a + i, b + i, length - i) == 0;
}

static int64_t checked_string_equal(struct kexe_context_v4 *context,
                                    int64_t handle_a, int64_t handle_b) {
  if (context == NULL || context->version != 4) { raise(SIGILL); return 0; }
  int64_t offset_a = checked_pair_get(context, handle_a, 0);
  int64_t length_a = checked_pair_get(context, handle_a, 1);
  int64_t offset_b = checked_pair_get(context, handle_b, 0);
  int64_t length_b = checked_pair_get(context, handle_b, 1);
  if (length_a != length_b) return 0;
  const uint8_t *a = resolve_string_bytes(context, offset_a, length_a);
  const uint8_t *b = resolve_string_bytes(context, offset_b, length_b);
  return simd_bytes_equal(a, b, (size_t)length_a) ? 1 : 0;
}

static int64_t checked_string_concat(struct kexe_context_v4 *context,
                                     int64_t handle_a, int64_t handle_b) {
  struct kexe_shared_v4 *shared = (struct kexe_shared_v4 *)context;
  if (context == NULL || context->version != 4) { raise(SIGILL); return 0; }
  int64_t offset_a = checked_pair_get(context, handle_a, 0);
  int64_t length_a = checked_pair_get(context, handle_a, 1);
  int64_t offset_b = checked_pair_get(context, handle_b, 0);
  int64_t length_b = checked_pair_get(context, handle_b, 1);
  /* Overflow must be ruled out BEFORE the addition, not after: signed
   * overflow is undefined behaviour, so a compiler is entitled to assume it
   * cannot happen and delete a `total < 0` test that only makes sense if it
   * did. The lengths come from pair cells, and this function exists precisely
   * because it does not trust what a guest put there. kexe_loader_windows.c's
   * string_concat has always checked in this order; this one had not. */
  if (length_a < 0 || length_b < 0 || length_a > INT64_MAX - length_b) {
    raise(SIGILL);
    return 0;
  }
  int64_t total = length_a + length_b;
  if (shared->string_pool_used + (uint64_t)total > kexe_string_pool_budget ||
      shared->string_pool_used + (uint64_t)total < shared->string_pool_used) {
    raise(SIGILL);
    return 0;
  }
  const uint8_t *a = resolve_string_bytes(context, offset_a, length_a);
  const uint8_t *b = resolve_string_bytes(context, offset_b, length_b);
  int inputs_validated =
      shared->pair_validated[(uint64_t)handle_a - 1] &&
      shared->pair_validated[(uint64_t)handle_b - 1];
  uint64_t pool_offset = shared->string_pool_used;
  memcpy(shared->string_pool + pool_offset, a, (size_t)length_a);
  memcpy(shared->string_pool + pool_offset + (uint64_t)length_a, b, (size_t)length_b);
  shared->string_pool_used += (uint64_t)total;
  int64_t result = checked_pair_new(context, -((int64_t)pool_offset) - 1, total);
  /* Concatenation of two valid UTF-8 strings is valid UTF-8. */
  if (inputs_validated) mark_validated(context, result);
  return result;
}

/* Mirrors backend/cljs.clj's kotoba$utf8-substring, which is the oracle for
 * this operation on every target. That function's two distinct failures are
 * reproduced here in its order:
 *   1. :substring-bounds -- unless 0 <= start <= end <= byte-length.
 *   2. :substring-code-point-boundary -- it maps byte offsets to code points
 *      and fails when either index is absent from that map. An index is in
 *      the map exactly when it is 0, the byte length, or addresses a
 *      non-continuation byte -- PROVIDED the source is canonical UTF-8, so
 *      that is checked rather than assumed: a guest can hand over any pair,
 *      and over invalid UTF-8 "not a continuation byte" would not mean
 *      "code-point boundary". */
static int64_t checked_string_substring(struct kexe_context_v4 *context,
                                        int64_t handle, int64_t start,
                                        int64_t end) {
  if (context == NULL || context->version != 4) { raise(SIGILL); return 0; }
  int64_t offset = checked_pair_get(context, handle, 0);
  int64_t length = checked_pair_get(context, handle, 1);
  if (length < 0 || start < 0 || end < start || end > length) {
    raise(SIGILL);
    return 0;
  }
  const uint8_t *bytes = resolve_string_bytes(context, offset, length);
  if (bytes == NULL) { raise(SIGILL); return 0; }
  if (!ensure_valid_string(context, handle, bytes, length)) { raise(SIGILL); return 0; }
  if (start < length && (bytes[start] & 0xc0) == 0x80) { raise(SIGILL); return 0; }
  if (end < length && (bytes[end] & 0xc0) == 0x80) { raise(SIGILL); return 0; }
  /* No copy and no pool allocation: the result addresses the source's own
   * bytes. `offset` spans one uniform byte space whose two halves run in
   * OPPOSITE directions -- non-negative indexes code+literal data forward,
   * negative indexes string_pool through `-offset - 1` -- so advancing by
   * `start` bytes means adding there and SUBTRACTING here. Neither can
   * overflow: resolve_string_bytes has already established that the whole
   * [offset, offset+length) range lies inside its half, and start <= length. */
  int64_t result_offset = offset >= 0 ? offset + start : offset - start;
  /* A code-point-bounded view of a valid string is itself valid. */
  return mark_validated(context,
                        checked_pair_new(context, result_offset, end - start));
}

/* Mirrors kotoba.kir.value/utf8-code-point-at!: the offset must be a
 * code-point boundary in [0, byte-length) -- note the EXCLUSIVE upper bound,
 * unlike substring, since there is no code point starting at the end. The
 * guest derives the width from the returned value to advance, so this one op
 * walks a string. valid_utf8 has already established that a sequence starting
 * at a non-continuation byte has all of its continuation bytes inside the
 * string, which is why they are read without further bounds checks. */
static int64_t checked_string_code_point_at(struct kexe_context_v4 *context,
                                            int64_t handle, int64_t byte_offset) {
  if (context == NULL || context->version != 4) { raise(SIGILL); return 0; }
  int64_t offset = checked_pair_get(context, handle, 0);
  int64_t length = checked_pair_get(context, handle, 1);
  if (length < 0 || byte_offset < 0 || byte_offset >= length) {
    raise(SIGILL);
    return 0;
  }
  const uint8_t *bytes = resolve_string_bytes(context, offset, length);
  if (bytes == NULL) { raise(SIGILL); return 0; }
  if (!ensure_valid_string(context, handle, bytes, length)) { raise(SIGILL); return 0; }
  const uint8_t *p = bytes + byte_offset;
  uint8_t a = p[0];
  if ((a & 0xc0) == 0x80) { raise(SIGILL); return 0; }
  if (a <= 0x7f) return a;
  if (a >= 0xc2 && a <= 0xdf) return ((int64_t)(a & 0x1f) << 6) | (p[1] & 0x3f);
  if (a >= 0xe0 && a <= 0xef)
    return ((int64_t)(a & 0x0f) << 12) | ((int64_t)(p[1] & 0x3f) << 6) | (p[2] & 0x3f);
  if (a >= 0xf0 && a <= 0xf4)
    return ((int64_t)(a & 0x07) << 18) | ((int64_t)(p[1] & 0x3f) << 12) |
           ((int64_t)(p[2] & 0x3f) << 6) | (p[3] & 0x3f);
  raise(SIGILL);
  return 0;
}

static int parse_allow(const char *text, uint64_t allow[4]) {
  if (strcmp(text, "-") == 0) return 0;
  const char *cursor = text;
  while (*cursor) {
    if (*cursor < '0' || *cursor > '9') return -1;
    char *end = NULL;
    errno = 0;
    unsigned long id = strtoul(cursor, &end, 10);
    if (errno == ERANGE || end == cursor || id > 255 ||
        (*end != ',' && *end != '\0')) return -1;
    allow[id / 64] |= UINT64_C(1) << (id % 64);
    if (*end == '\0') return 0;
    cursor = end + 1;
    if (*cursor == '\0') return -1;
  }
  return -1;
}

static void fail(const char *message) {
  fprintf(stderr, "kexe-loader: %s: %s\n", message, strerror(errno));
  exit(1);
}

static void trap_handler(int signal_number) {
  static const char sigill[] = "KEXE_TRAP {:kind :signal :signal :SIGILL}\n";
  static const char sigtrap[] = "KEXE_TRAP {:kind :signal :signal :SIGTRAP}\n";
  static const char sigfpe[] = "KEXE_TRAP {:kind :signal :signal :SIGFPE}\n";
  static const char sigbus[] = "KEXE_TRAP {:kind :signal :signal :SIGBUS}\n";
  static const char sigsegv[] = "KEXE_TRAP {:kind :signal :signal :SIGSEGV}\n";
  static const char sigxcpu[] = "KEXE_TRAP {:kind :signal :signal :SIGXCPU}\n";
  static const char sigalrm[] = "KEXE_TRAP {:kind :signal :signal :SIGALRM}\n";
#if defined(SIGSYS)
  static const char sigsys[] = "KEXE_TRAP {:kind :signal :signal :SIGSYS}\n";
#endif
  static const char unknown[] = "KEXE_TRAP {:kind :signal :signal :unknown}\n";
  const char *message = unknown;
  size_t length = sizeof(unknown) - 1;
#define SELECT_SIGNAL(number, text) \
  case number:                       \
    message = text;                  \
    length = sizeof(text) - 1;       \
    break
  switch (signal_number) {
    SELECT_SIGNAL(SIGILL, sigill);
    SELECT_SIGNAL(SIGTRAP, sigtrap);
    SELECT_SIGNAL(SIGFPE, sigfpe);
    SELECT_SIGNAL(SIGBUS, sigbus);
    SELECT_SIGNAL(SIGSEGV, sigsegv);
    SELECT_SIGNAL(SIGXCPU, sigxcpu);
    SELECT_SIGNAL(SIGALRM, sigalrm);
#if defined(SIGSYS)
    SELECT_SIGNAL(SIGSYS, sigsys);
#endif
    default:
      break;
  }
#undef SELECT_SIGNAL
  ssize_t written = write(STDERR_FILENO, message, length);
  (void)written;
  _exit(120);
}

static void supervisor_alarm_handler(int signal_number) {
  (void)signal_number;
  supervisor_timed_out = 1;
  if (supervised_pid > 0) (void)kill((pid_t)supervised_pid, SIGKILL);
}

static int supervise(pid_t child) {
  struct sigaction action;
  memset(&action, 0, sizeof(action));
  action.sa_handler = supervisor_alarm_handler;
  sigemptyset(&action.sa_mask);
  if (sigaction(SIGALRM, &action, NULL) != 0) fail("supervisor sigaction");
  supervised_pid = (sig_atomic_t)child;
  alarm(3);

  int status = 0;
  while (waitpid(child, &status, 0) < 0) {
    if (errno == EINTR) continue;
    fail("waitpid");
  }
  alarm(0);
  supervised_pid = -1;
  if (supervisor_timed_out) {
    static const char timeout[] =
        "KEXE_TRAP {:kind :supervisor :reason :wall-timeout}\n";
    ssize_t written = write(STDERR_FILENO, timeout, sizeof(timeout) - 1);
    (void)written;
    return 122;
  }
  if (WIFEXITED(status)) return WEXITSTATUS(status);
  static const char signal[] =
      "KEXE_TRAP {:kind :supervisor :reason :unhandled-child-signal}\n";
  ssize_t written = write(STDERR_FILENO, signal, sizeof(signal) - 1);
  (void)written;
  return 123;
}

/* The tail every supervisor report ends with, defined ONCE because there are
 * ten of them -- one per result type, plus the traps -- and a report that
 * carries a different set of keys than `kototama.native.executor`'s
 * `valid-supervisor-report?` expects is rejected as "malformed native
 * supervisor evidence" no matter what the run actually did.
 *
 * The two VECTOR arenas are here because that is what the disagreement was.
 * `kototama-native` added them to the expected key set on 2026-09-08 -- the
 * arenas are separately exhaustible and were the only bounded resource a run
 * could hit without the report mentioning it, arriving as a bare SIGILL
 * beside a `:heap` line about the PAIR arena, which vector work never
 * touches -- and this loader never gained the other half. It was invisible
 * because amu pinned an older kototama-native; advancing that pin is what
 * surfaced it. */
/* The reported capacity is the budget IN FORCE, not the default. It was the
 * literal 4096 until 2026-09-10, which was true while the pair heap was a
 * compile-time constant and became a lie the moment it became a budget: a
 * run with KEXE_PAIRS=200000 reported `:capacity 4096 :used 8013`, a used
 * larger than its own capacity. `:arena-bounds` says a bound you can see is
 * a bound you can plan against; one you can see WRONG is worse than one you
 * cannot see. The string arena joins the report for the same reason -- it
 * had no line at all, so a guest that exhausted it had nothing to read. */
#define KEXE_REPORT_TAIL_FMT                                                  \
  "} :heap {:capacity %" PRIu64 " :used %" PRIu64                             \
  "} :string-pool {:capacity %" PRIu64 " :used %" PRIu64                      \
  "} :vectors {:capacity %u :used %"                                          \
  PRIu64 "} :vector-items {:capacity %u :used %" PRIu64 "}}\n"
#define KEXE_REPORT_TAIL_ARGS(s)                                              \
  kexe_pair_budget, (s)->pair_used,                                           \
      kexe_string_pool_budget, (s)->string_pool_used,                          \
      (unsigned)KEXE_VECTOR_CAPACITY, (s)->vector_used,                        \
      (unsigned)KEXE_VECTOR_ITEM_CAPACITY, (s)->vector_item_used

static int write_supervisor_report(const struct kexe_shared_v4 *shared,
                                   int child_status,
                                   const char *result_type,
                                   uint64_t record_field_count,
                                   uint64_t variant_case_count,
                                   uint64_t variant_bool_mask) {
  if (child_status == 0 && shared->completed == 1) {
    if (strcmp(result_type, "string") == 0) {
      uint64_t length = 0;
      const uint8_t *bytes = inspect_string_result(shared, shared->result, &length);
      if (bytes == NULL) {
        static const char trap[] =
            "KEXE_TRAP {:kind :result :reason :invalid-string-handle}\n";
        write_stderr_checked(trap, sizeof(trap) - 1u);
        printf("{:status :trap :exit 126 :fuel {:initial %" PRIu64 " :remaining %" PRIu64
               KEXE_REPORT_TAIL_FMT,
               kexe_initial_fuel, shared->context.fuel, KEXE_REPORT_TAIL_ARGS(shared));
        return 126;
      }
      printf("{:status :ok :result %" PRId64
             " :result-type :string :result-utf8-hex \"",
             shared->result);
      for (uint64_t i = 0; i < length; i++) printf("%02x", bytes[i]);
      printf("\" :fuel {:initial %" PRIu64 " :remaining %" PRIu64
             KEXE_REPORT_TAIL_FMT,
             kexe_initial_fuel, shared->context.fuel, KEXE_REPORT_TAIL_ARGS(shared));
    } else if (record_field_count > 0) {
      int64_t fields[KEXE_RECORD_FIELD_LIMIT];
      if (!inspect_record_result(shared, shared->result,
                                 record_field_count, fields)) {
        static const char trap[] =
            "KEXE_TRAP {:kind :result :reason :invalid-record-chain}\n";
        write_stderr_checked(trap, sizeof(trap) - 1u);
        printf("{:status :trap :exit 127 :fuel {:initial %" PRIu64 " :remaining %" PRIu64
               KEXE_REPORT_TAIL_FMT,
               kexe_initial_fuel, shared->context.fuel, KEXE_REPORT_TAIL_ARGS(shared));
        return 127;
      }
      printf("{:status :ok :result %" PRId64
             " :result-type :record :result-words [", shared->result);
      for (uint64_t i = 0; i < record_field_count; i++)
        printf(i == 0 ? "%" PRId64 : " %" PRId64, fields[i]);
      printf("] :fuel {:initial %" PRIu64 " :remaining %" PRIu64
             KEXE_REPORT_TAIL_FMT,
             kexe_initial_fuel, shared->context.fuel, KEXE_REPORT_TAIL_ARGS(shared));
    } else if (strcmp(result_type, "option-i64") == 0 ||
               strcmp(result_type, "result-i64") == 0) {
      int option = strcmp(result_type, "option-i64") == 0;
      int64_t tag, payload;
      if (!inspect_tagged_i64_result(shared, shared->result, option,
                                     &tag, &payload)) {
        int trap_exit = option ? 128 : 129;
        const char *reason = option ? "invalid-option-i64" : "invalid-result-i64";
        fprintf(stderr, "KEXE_TRAP {:kind :result :reason :%s}\n", reason);
        printf("{:status :trap :exit %d :fuel {:initial %" PRIu64 " :remaining %" PRIu64
               KEXE_REPORT_TAIL_FMT,
               trap_exit, kexe_initial_fuel, shared->context.fuel, KEXE_REPORT_TAIL_ARGS(shared));
        return trap_exit;
      }
      printf("{:status :ok :result %" PRId64 " :result-type :%s "
             ":result-tag %s :result-word %" PRId64
             " :fuel {:initial %" PRIu64 " :remaining %" PRIu64
             KEXE_REPORT_TAIL_FMT,
             shared->result, result_type, tag == 1 ? "true" : "false", payload,
             kexe_initial_fuel, shared->context.fuel, KEXE_REPORT_TAIL_ARGS(shared));
    } else if (variant_case_count > 0) {
      int64_t ordinal, payload;
      if (!inspect_variant_result(shared, shared->result, variant_case_count,
                                  variant_bool_mask, &ordinal, &payload)) {
        static const char trap[] =
            "KEXE_TRAP {:kind :result :reason :invalid-variant}\n";
        write_stderr_checked(trap, sizeof(trap) - 1u);
        printf("{:status :trap :exit 130 :fuel {:initial %" PRIu64 " :remaining %" PRIu64
               KEXE_REPORT_TAIL_FMT,
               kexe_initial_fuel, shared->context.fuel, KEXE_REPORT_TAIL_ARGS(shared));
        return 130;
      }
      printf("{:status :ok :result %" PRId64
             " :result-type :variant :result-ordinal %" PRId64
             " :result-word %" PRId64
             " :fuel {:initial %" PRIu64 " :remaining %" PRIu64
             KEXE_REPORT_TAIL_FMT,
             shared->result, ordinal, payload, kexe_initial_fuel, shared->context.fuel,
             KEXE_REPORT_TAIL_ARGS(shared));
    } else {
      printf("{:status :ok :result %" PRId64
             " :fuel {:initial %" PRIu64 " :remaining %" PRIu64
             KEXE_REPORT_TAIL_FMT,
             shared->result, kexe_initial_fuel, shared->context.fuel, KEXE_REPORT_TAIL_ARGS(shared));
    }
  } else {
    printf("{:status :trap :exit %d :fuel {:initial %" PRIu64 " :remaining %" PRIu64
           KEXE_REPORT_TAIL_FMT,
           child_status, kexe_initial_fuel, shared->context.fuel, KEXE_REPORT_TAIL_ARGS(shared));
  }
  return child_status;
}

/* Keep post-sandbox output independent of libc stdio's lazy initialization. */
static void write_i64(int64_t value) {
  char buffer[32];
  size_t cursor = sizeof(buffer);
  uint64_t magnitude;
  buffer[--cursor] = '\n';
  if (value < 0) {
    /* This form is defined for INT64_MIN. */
    magnitude = (uint64_t)(-(value + 1)) + 1;
  } else {
    magnitude = (uint64_t)value;
  }
  do {
    buffer[--cursor] = (char)('0' + magnitude % 10);
    magnitude /= 10;
  } while (magnitude != 0);
  if (value < 0) buffer[--cursor] = '-';

  size_t remaining = sizeof(buffer) - cursor;
  while (remaining != 0) {
    ssize_t written = write(STDOUT_FILENO, buffer + cursor, remaining);
    if (written < 0) {
      if (errno == EINTR) continue;
      _exit(121);
    }
    cursor += (size_t)written;
    remaining -= (size_t)written;
  }
}

static void install_limits(void) {
  struct rlimit limit;
  limit.rlim_cur = limit.rlim_max = 0;
  if (setrlimit(RLIMIT_CORE, &limit) != 0) fail("setrlimit core");
  limit.rlim_cur = 1;
  limit.rlim_max = 2;
  if (setrlimit(RLIMIT_CPU, &limit) != 0) fail("setrlimit cpu");
#if !defined(__APPLE__) && !defined(KEXE_SANITIZER_TEST)
  /* ASan owns a platform-dependent shadow address space, so the sanitizer
   * harness cannot share the production virtual-memory ceiling. The guest's
   * own arenas remain bounded and production children retain this 64 MiB
   * process limit. */
  limit.rlim_cur = limit.rlim_max = 64u * 1024u * 1024u;
  if (setrlimit(RLIMIT_AS, &limit) != 0) fail("setrlimit address-space");
#endif
  limit.rlim_cur = limit.rlim_max = 1024u * 1024u;
  if (setrlimit(RLIMIT_STACK, &limit) != 0) fail("setrlimit stack");

  struct sigaction action;
  memset(&action, 0, sizeof(action));
  action.sa_handler = trap_handler;
  sigemptyset(&action.sa_mask);
  action.sa_flags = SA_RESETHAND;
  const int signals[] = {SIGILL, SIGTRAP, SIGFPE, SIGBUS, SIGSEGV, SIGXCPU, SIGALRM
#if defined(SIGSYS)
                         , SIGSYS
#endif
  };
  for (size_t i = 0; i < sizeof(signals) / sizeof(signals[0]); i++) {
    if (sigaction(signals[i], &action, NULL) != 0) fail("sigaction");
  }
  alarm(2);
}

#if defined(__linux__) && !defined(KEXE_SANITIZER_TEST)
static void install_syscall_sandbox(void) {
#if defined(__x86_64__)
  const uint32_t expected_arch = AUDIT_ARCH_X86_64;
#elif defined(__aarch64__)
  const uint32_t expected_arch = AUDIT_ARCH_AARCH64;
#else
#error "unsupported Linux architecture for KEXE seccomp"
#endif
  struct sock_filter filter[96];
  int n = 0;
#define ADD(stmt) do { filter[n++] = (stmt); } while (0)
  ADD((struct sock_filter)BPF_STMT(BPF_LD | BPF_W | BPF_ABS,
                                   offsetof(struct seccomp_data, arch)));
  ADD((struct sock_filter)BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K,
                                   expected_arch, 1, 0));
  ADD((struct sock_filter)BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS));
  ADD((struct sock_filter)BPF_STMT(BPF_LD | BPF_W | BPF_ABS,
                                   offsetof(struct seccomp_data, nr)));
  /* fs/app-data (wire id 35) and fs/browse (wire id 34) syscalls are
   * admitted only when the matching scope was granted (KEXE_CAP_RESOURCES_35
   * / _34 set). The conformance filesystem probe runs with no scope and must
   * still be denied; the kbb native runner sets the scopes and the providers'
   * realpath compare enforces them. */
  const int fs_reads = kexe_scope35.count > 0 || kexe_scope34.count > 0;
  if (kexe_scope34.count > 0) {
#ifdef __NR_getdents64
    ADD((struct sock_filter)BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K,
                                     __NR_getdents64, 0, 1));
    ADD((struct sock_filter)BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW));
#endif
    /* No fcntl: the listing is read with raw getdents64, so glibc's
     * fdopendir (F_GETFL, then F_SETFD -- the one that tripped this filter,
     * measured) is never called in the child. */
  }
  if (fs_reads) {
#ifdef __NR_read
    ADD((struct sock_filter)BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K,
                                     __NR_read, 0, 1));
    ADD((struct sock_filter)BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW));
#endif
#ifdef __NR_open
    ADD((struct sock_filter)BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K,
                                     __NR_open, 0, 1));
    ADD((struct sock_filter)BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW));
#endif
#ifdef __NR_openat
    ADD((struct sock_filter)BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K,
                                     __NR_openat, 0, 1));
    ADD((struct sock_filter)BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW));
#endif
    ADD((struct sock_filter)BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K,
                                     __NR_close, 0, 1));
    ADD((struct sock_filter)BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW));
    ADD((struct sock_filter)BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K,
                                     __NR_lseek, 0, 1));
    ADD((struct sock_filter)BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW));
#ifdef __NR_pread64
    ADD((struct sock_filter)BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K,
                                     __NR_pread64, 0, 1));
    ADD((struct sock_filter)BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW));
#endif
#ifdef __NR_fstat
    ADD((struct sock_filter)BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K,
                                     __NR_fstat, 0, 1));
    ADD((struct sock_filter)BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW));
#endif
#ifdef __NR_newfstatat
    ADD((struct sock_filter)BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K,
                                     __NR_newfstatat, 0, 1));
    ADD((struct sock_filter)BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW));
#endif
#ifdef __NR_access
    ADD((struct sock_filter)BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K,
                                     __NR_access, 0, 1));
    ADD((struct sock_filter)BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW));
#endif
#ifndef __NR_faccessat2
#define __NR_faccessat2 439
#endif
    ADD((struct sock_filter)BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K,
                                     __NR_faccessat2, 0, 1));
    ADD((struct sock_filter)BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW));
  }
#define ALLOW_SYSCALL_AT(number) \
    ADD((struct sock_filter)BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, (number), 0, 1)); \
    ADD((struct sock_filter)BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW))
  ALLOW_SYSCALL_AT(__NR_write);
  ALLOW_SYSCALL_AT(__NR_exit);
  ALLOW_SYSCALL_AT(__NR_exit_group);
  ALLOW_SYSCALL_AT(__NR_rt_sigreturn);
  ALLOW_SYSCALL_AT(__NR_rt_sigprocmask);
  ALLOW_SYSCALL_AT(__NR_getpid);
  ALLOW_SYSCALL_AT(__NR_gettid);
  ALLOW_SYSCALL_AT(__NR_tgkill);
  ALLOW_SYSCALL_AT(__NR_munmap);
  ALLOW_SYSCALL_AT(__NR_brk);
  ALLOW_SYSCALL_AT(__NR_clock_gettime);
  ADD((struct sock_filter)BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_TRAP));
  struct sock_fprog program = {
      .len = (unsigned short)n,
      .filter = filter,
  };
  if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0) fail("no_new_privs");
  if (prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &program) != 0) fail("seccomp");
}
#elif defined(__APPLE__) && !defined(KEXE_SANITIZER_TEST)
static void install_syscall_sandbox(void) {
  /* file-read* is NOT blanket: each :fs/app-data (wire id 35) and
   * :fs/browse (wire id 34) scope entry becomes a (subpath ...) filter, so
   * reads are possible only beneath the granted directories. Entries come
   * from KEXE_CAP_RESOURCES_35 / _34 (colon-separated) -- the same scope
   * strings the providers check per-call; Seatbelt is the second
   * enforcement layer. Both the
   * literal entry spelling and its realpath are granted, so the guest
   * may use either spelling and realpath still fails closed outside
   * the scope. */
  static char profile[32768];
  size_t used = 0;
  used += (size_t)snprintf(profile + used, sizeof(profile) - used,
      "(version 1)(deny default)(allow file-write-data)"
      "(allow signal (target self))(allow process-info-pidinfo)"
      "(allow process-info-setcontrol)(allow sysctl-read)");
  for (int s = 0; s < kexe_scope35.count; s++) {
    used += (size_t)snprintf(profile + used, sizeof(profile) - used,
              "(allow file-read* (subpath \"%s\"))",
              kexe_scope35.resolved[s]);
    used += (size_t)snprintf(profile + used, sizeof(profile) - used,
              "(allow file-write* (subpath \"%s\"))",
              kexe_scope35.resolved[s]);
  }
  /* :fs/browse (wire id 34) lists directories: read-only, no write grant. */
  for (int s = 0; s < kexe_scope34.count; s++) {
    used += (size_t)snprintf(profile + used, sizeof(profile) - used,
              "(allow file-read* (subpath \"%s\"))",
              kexe_scope34.resolved[s]);
  }
  char *error = NULL;
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
  int result = sandbox_init(profile, 0, &error);
  if (result != 0) {
    if (error != NULL) {
      static const char prefix[] = "kexe-loader: sandbox_init: ";
      write_stderr_checked(prefix, sizeof(prefix) - 1);
      write_stderr_checked(error, strlen(error));
      write_stderr_checked("\n", 1);
      sandbox_free_error(error);
    }
    _exit(125);
  }
#pragma clang diagnostic pop
}
#else
static void install_syscall_sandbox(void) {}
#endif

static void probe_denied(const char *reason) {
  static const char prefix[] = "KEXE_TRAP {:kind :sandbox :reason :";
  ssize_t written = write(STDERR_FILENO, prefix, sizeof(prefix) - 1);
  written = write(STDERR_FILENO, reason, strlen(reason));
  written = write(STDERR_FILENO, "}\n", 2);
  (void)written;
  _exit(124);
}

int main(int argc, char **argv) {
  /* Everything after the first `--` is the GUEST's argv (wire 38), and is
   * removed from this loader's own argument vector before any of the checks
   * below run -- so `argc != 6 + arity` keeps meaning exactly what it meant
   * and still catches a miscounted invocation. A `--` with nothing after it
   * is a guest argv of length zero, which is different from no `--` at all
   * only in that the guest may ask and be told zero. */
#ifdef KEXE_EMBEDDED
  /* A packaged command owns its whole command line: there is no loader
   * invocation in front of it to separate off, so every argument after the
   * program name belongs to the guest and `--` is just another argument --
   * which is what a caller writing `grep -- -x file` means by it. */
  kexe_guest_argv = argv + 1;
  kexe_guest_argc = argc - 1;
  argc = 1;
#else
  for (int i = 1; i < argc; i++) {
    if (strcmp(argv[i], "--") == 0) {
      kexe_guest_argv = argv + i + 1;
      kexe_guest_argc = argc - i - 1;
      argc = i;
      break;
    }
  }
#endif
  /* Command mode: the guest's answer is the process's EXIT STATUS and the
   * loader prints no report of its own, so stdout carries only what the guest
   * wrote through wire 37. Without it the loader keeps printing the result,
   * which is what every existing caller reads. Truncated to 0..255 the way a
   * shell would; a negative answer therefore arrives as 256 + it, which is
   * the same thing `exit(-1)` does anywhere else. */
#ifdef KEXE_EMBEDDED
  /* A command always answers with its exit status and never prints a report
   * of its own -- that is what makes it a command rather than a loader
   * invocation, so it is not left to an environment variable. */
  const int command_mode = 1;
#else
  const int command_mode = getenv("KEXE_COMMAND") != NULL;
#endif
#ifndef KEXE_EMBEDDED
  if (argc < 6 || argc > 11) {
    fprintf(stderr, "usage: kexe-loader <raw-code> <offset> <arity> <x86_64|aarch64> <allow-csv|-> [i64 ...]\n");
    return 2;
  }
#else
  (void)argc;
#endif
#ifdef KEXE_EMBEDDED
  /* The machine code is a constant of this binary, not a file it is told to
   * read. Nothing on the command line can point it at other bytes, so a
   * packaged command has no argument that selects what it executes. */
  const uint64_t offset = KEXE_EMBEDDED_OFFSET;
  const unsigned long arity = KEXE_EMBEDDED_ARITY;
  const char *isa = KEXE_EMBEDDED_ISA;
  const long length = (long)sizeof(kexe_embedded_code);
  if (arity != 0) {
    /* A command receives its input through :cli/args, not through i64
     * parameters there is nowhere to write. */
    fprintf(stderr, "kexe-command: packaged entry must have arity 0\n");
    return 2;
  }
  if (length <= 0 || offset >= (uint64_t)length) {
    fprintf(stderr, "kexe-command: invalid embedded code length or offset\n");
    return 2;
  }
  long pagesize = sysconf(_SC_PAGESIZE);
  size_t mapped = ((size_t)length + (size_t)pagesize - 1) & ~((size_t)pagesize - 1);
  void *memory = mmap(NULL, mapped, PROT_READ | PROT_WRITE,
                      MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (memory == MAP_FAILED) fail("mmap RW");
  memcpy(memory, kexe_embedded_code, (size_t)length);
#else
  uint64_t offset;
  if (parse_u64(argv[2], &offset) != 0) return 2;
  unsigned long arity;
  if (parse_ulong_decimal(argv[3], &arity) != 0 || arity > 5 ||
      argc != (int)(6 + arity)) return 2;
  const char *isa = argv[4];
  if (strcmp(isa, "x86_64") != 0 && strcmp(isa, "aarch64") != 0) return 2;
  FILE *file = fopen(argv[1], "rb");
  if (!file) fail("open");
  if (fseek(file, 0, SEEK_END) != 0) fail("seek");
  long length = ftell(file);
  if (length <= 0 || offset >= (uint64_t)length) {
    fprintf(stderr, "kexe-loader: invalid code length or offset\n");
    return 2;
  }
  rewind(file);

  long pagesize = sysconf(_SC_PAGESIZE);
  size_t mapped = ((size_t)length + (size_t)pagesize - 1) & ~((size_t)pagesize - 1);
  void *memory = mmap(NULL, mapped, PROT_READ | PROT_WRITE,
                      MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (memory == MAP_FAILED) fail("mmap RW");
  if (fread(memory, 1, (size_t)length, file) != (size_t)length) fail("read");
  if (fclose(file) != 0) fail("close");
#endif

  /* The security boundary: writable code is never executable. */
  if (mprotect(memory, mapped, PROT_READ | PROT_EXEC) != 0) fail("mprotect RX");
  __builtin___clear_cache((char *)memory, (char *)memory + length);

  const char *result_type = getenv("KEXE_RESULT_TYPE");
  unsigned long record_field_count = 0;
  uint64_t variant_case_count = 0, variant_bool_mask = 0;
  if (result_type == NULL) result_type = "i64";
  if (strncmp(result_type, "record:", 7) == 0) {
    if (parse_ulong_decimal(result_type + 7, &record_field_count) != 0 ||
        record_field_count == 0 || record_field_count > KEXE_RECORD_FIELD_LIMIT)
      return 2;
  } else if (strncmp(result_type, "variant:", 8) == 0) {
    if (!parse_variant_profile(result_type, &variant_case_count,
                               &variant_bool_mask)) return 2;
  } else if (strcmp(result_type, "i64") != 0 &&
             strcmp(result_type, "string") != 0 &&
             strcmp(result_type, "option-i64") != 0 &&
             strcmp(result_type, "result-i64") != 0) return 2;
  int64_t args[6] = {0, 0, 0, 0, 0, 0};
  struct kexe_shared_v4 *shared =
      mmap(NULL, sizeof(*shared), PROT_READ | PROT_WRITE,
           MAP_SHARED | MAP_ANONYMOUS, -1, 0);
  if (shared == MAP_FAILED) fail("mmap shared execution state");
  /* No memset: MAP_ANONYMOUS pages are zero-filled by the kernel, so this
   * only ever re-zeroed memory that was already zero -- and it TOUCHED every
   * page while doing it, which is what would make a large string arena cost
   * its full size at startup instead of faulting in as the bump allocator
   * reaches it. Measured with the arena mapped over 256 MiB: with the memset
   * a run costs the whole mapping; without it, a run that allocates 64 KiB
   * faults 64 KiB. */
  shared->context.version = 4;
#ifdef KEXE_EMBEDDED
  /* Fuel is a constant of a packaged command for the same reason its grant,
   * its scopes and its string arena are: a caller that could raise the fuel
   * through the environment would be choosing the command's resource bound
   * on its behalf. This was the last of the four still readable from
   * outside. */
  kexe_initial_fuel = KEXE_EMBEDDED_FUEL;
#else
  const char *fuel_env = getenv("KEXE_FUEL");
  if (fuel_env != NULL && fuel_env[0] != '\0') {
    if (parse_u64(fuel_env, &kexe_initial_fuel) != 0 || kexe_initial_fuel == 0) {
      fprintf(stderr, "kexe-loader: KEXE_FUEL must be a positive decimal integer\n");
      return 2;
    }
  }
#endif
  /* The string arena budget, in force for this run only. Same shape as
   * KEXE_FUEL above: absent means the default, present means a positive
   * decimal, and anything else is refused BEFORE the guest starts rather
   * than clamped -- a budget silently reduced to something the caller did
   * not ask for is a bound nobody can plan against. */
#ifdef KEXE_EMBEDDED
  kexe_string_pool_budget = KEXE_EMBEDDED_STRING_POOL;
#else
  const char *pool_env = getenv("KEXE_STRING_POOL");
  if (pool_env != NULL && pool_env[0] != '\0') {
    if (parse_u64(pool_env, &kexe_string_pool_budget) != 0 ||
        kexe_string_pool_budget == 0) {
      fprintf(stderr, "kexe-loader: KEXE_STRING_POOL must be a positive decimal integer\n");
      return 2;
    }
  }
#endif
#ifdef KEXE_EMBEDDED
  kexe_pair_budget = KEXE_EMBEDDED_PAIRS;
#else
  const char *pairs_env = getenv("KEXE_PAIRS");
  if (pairs_env != NULL && pairs_env[0] != '\0') {
    if (parse_u64(pairs_env, &kexe_pair_budget) != 0 || kexe_pair_budget == 0) {
      fprintf(stderr, "kexe-loader: KEXE_PAIRS must be a positive decimal integer\n");
      return 2;
    }
  }
#endif
  if (kexe_pair_budget > KEXE_PAIR_MAX) {
    fprintf(stderr, "kexe-loader: KEXE_PAIRS exceeds the %u-entry ceiling\n",
            (unsigned)KEXE_PAIR_MAX);
    return 2;
  }
  if (kexe_string_pool_budget > KEXE_STRING_POOL_MAX) {
    fprintf(stderr, "kexe-loader: KEXE_STRING_POOL exceeds the %u-byte ceiling\n",
            (unsigned)KEXE_STRING_POOL_MAX);
    return 2;
  }
  shared->context.fuel = kexe_initial_fuel;
  shared->context.cap_call = checked_cap_call;
  shared->context.pair_new = checked_pair_new;
  shared->context.pair_first = checked_pair_first;
  shared->context.pair_second = checked_pair_second;
  shared->context.kgraph_assert = checked_kgraph_assert;
  shared->context.kgraph_get = checked_kgraph_get;
  shared->context.kgraph_count = checked_kgraph_count;
  shared->context.kgraph_entity_at = checked_kgraph_entity_at;
  shared->context.string_equal = checked_string_equal;
  shared->context.string_concat = checked_string_concat;
  shared->context.string_substring = checked_string_substring;
  shared->context.string_code_point_at = checked_string_code_point_at;
  shared->context.typed_cap_call = checked_typed_cap_call;
  shared->context.vector_new_empty = checked_vector_new_empty;
  shared->context.vector_conj = checked_vector_conj;
  shared->context.vector_count = checked_vector_count;
  shared->context.vector_at = checked_vector_at;
  shared->context.vector_assoc = checked_vector_assoc;
  shared->context.vector_drop = checked_vector_drop;
  shared->context.vector_alloc = checked_vector_alloc;
  shared->context.vector_assoc_in_place = checked_vector_assoc_in_place;
  shared->context.code_base = (const uint8_t *)memory;
  shared->context.code_length = (uint64_t)length;
  kexe_scope_init(&kexe_scope35, "KEXE_CAP_RESOURCES_35");
  kexe_scope_init(&kexe_scope34, "KEXE_CAP_RESOURCES_34");
#ifdef KEXE_EMBEDDED
  /* The grant is a constant too, and it is the SAME text a loader invocation
   * would have been given, parsed by the same function -- a packaged command
   * cannot widen its own authority and cannot be told to. */
  if (parse_allow(KEXE_EMBEDDED_ALLOW, shared->context.allow) != 0) return 2;
#else
  if (parse_allow(argv[5], shared->context.allow) != 0) return 2;
#endif
  for (unsigned long i = 0; i < arity; i++) {
    if (parse_guest_arg(shared, argv[6 + i], &args[i]) != 0) return 2;
  }
  int structured_report = getenv("KEXE_STRUCTURED_REPORT") != NULL;

  pid_t child = fork();
  if (child < 0) fail("fork");
  if (child > 0) {
    int child_status = supervise(child);
    if (structured_report)
      child_status = write_supervisor_report(shared, child_status, result_type,
                                             record_field_count,
                                             variant_case_count,
                                             variant_bool_mask);
    if (munmap(shared, sizeof(*shared)) != 0) fail("supervisor shared munmap");
    if (munmap(memory, mapped) != 0) fail("supervisor munmap");
    return child_status;
  }

  supervised_pid = -1;
  alarm(0);
  if (getenv("KEXE_TIMEOUT_PROBE") != NULL) {
    for (;;) {
    }
  }
  install_limits();
  install_syscall_sandbox();
  if (getenv("KEXE_FILESYSTEM_PROBE") != NULL) {
    int probe = open("/etc/passwd", O_RDONLY);
    if (probe >= 0) {
      (void)close(probe);
      fprintf(stderr, "kexe-loader: filesystem probe unexpectedly succeeded\n");
      return 3;
    }
    probe_denied("filesystem-denied");
  }
  if (getenv("KEXE_NETWORK_PROBE") != NULL) {
    int probe = socket(AF_INET, SOCK_STREAM, 0);
    if (probe < 0) probe_denied("network-denied");
    struct sockaddr_in address;
    memset(&address, 0, sizeof(address));
    address.sin_family = AF_INET;
    address.sin_port = htons(9);
    address.sin_addr.s_addr = htonl(UINT32_C(0x7f000001));
    errno = 0;
    if (connect(probe, (const struct sockaddr *)&address, sizeof(address)) == 0 ||
        (errno != EPERM && errno != EACCES)) {
      int probe_errno = errno;
      (void)close(probe);
      errno = probe_errno;
      fprintf(stderr, "kexe-loader: network probe was not policy-denied: %s\n",
              strerror(errno));
      return 3;
    }
    (void)close(probe);
    probe_denied("network-denied");
  }
  if (getenv("KEXE_PROCESS_PROBE") != NULL) {
    pid_t probe = fork();
    if (probe == 0) _exit(0);
    if (probe > 0) {
      (void)waitpid(probe, NULL, 0);
      fprintf(stderr, "kexe-loader: process probe unexpectedly succeeded\n");
      return 3;
    }
    probe_denied("process-denied");
  }
  int64_t result;
  if (strcmp(isa, "x86_64") == 0) {
    kexe_fn6 fn = (kexe_fn6)((uint8_t *)memory + offset);
    result = fn(args[0], args[1], args[2], args[3], args[4],
                (int64_t)(uintptr_t)&shared->context);
  } else {
    kexe_fn8 fn = (kexe_fn8)((uint8_t *)memory + offset);
    result = fn(args[0], args[1], args[2], args[3], args[4], 0, 0,
                (int64_t)(uintptr_t)&shared->context);
  }
  shared->result = result;
  shared->completed = 1;
  if (!structured_report && !command_mode) write_i64(result);

  if (munmap(memory, mapped) != 0) fail("munmap");
  if (munmap(shared, sizeof(*shared)) != 0) fail("shared munmap");
  _exit(command_mode ? (int)((uint64_t)result & 0xffu) : 0);
}
