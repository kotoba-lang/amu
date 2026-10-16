#include "kotoba_ios_host.h"

#include <limits.h>
#include <setjmp.h>
#include <signal.h>
#include <stdatomic.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#if defined(__APPLE__)
#include <TargetConditionals.h>
#endif
#if defined(__APPLE__) && defined(__aarch64__)
#include <pthread.h>
#include <sched.h>
#include <sys/ucontext.h>
#endif

#ifndef KOTOBA_IOS_TARGET
#if defined(__APPLE__) && defined(__aarch64__) && TARGET_OS_OSX
#define KOTOBA_IOS_TARGET "aarch64-macos-static-kotoba-v1"
#else
#define KOTOBA_IOS_TARGET "aarch64-ios-kotoba-v1"
#endif
#endif

extern const unsigned char kotoba_ios_entry[];
extern const unsigned char kotoba_ios_code_start[];
extern const unsigned char kotoba_ios_code_end[];
extern const char kotoba_ios_target_profile[];

struct kotoba_pair_v1;
struct kotoba_context_v2 {
  uint64_t version;
  uint64_t fuel;
  uint64_t allow[4];
  int64_t (*cap_call)(struct kotoba_context_v2 *, uint64_t, int64_t);
  int64_t (*pair_new)(struct kotoba_context_v2 *, int64_t, int64_t);
  int64_t (*pair_first)(struct kotoba_context_v2 *, int64_t);
  int64_t (*pair_second)(struct kotoba_context_v2 *, int64_t);
  void *kgraph_assert;
  void *kgraph_get;
  void *kgraph_count;
  void *kgraph_entity_at;
  int64_t (*string_equal)(struct kotoba_context_v2 *, int64_t, int64_t);
  int64_t (*string_concat)(struct kotoba_context_v2 *, int64_t, int64_t);
  int64_t (*typed_cap_call)(struct kotoba_context_v2 *, uint64_t, uint64_t,
                            uint64_t, int64_t);
  /* Slots 136-280 of the full context (strings, vectors, kgraph, the text
   * and line heads, the region pair) are not served by this host: a program
   * that names one is refused at packaging, and the words stay NULL so a
   * call through one is a null jump rather than a wrong answer. They are
   * laid out so the six INLINE pointers below sit at 288-328, where
   * kotoba-native (ADR 0084, context ABI v9) reads them without a call:
   * pair-first / pair-second (string-byte-length) are emitted in line for
   * every target, this one included, and read the pair table through these
   * -- measured 2026-09-16, the simulator conformance's `string-byte-length`
   * read past a context that ended at code_length. */
  void *unserved_slots[19];
  uint64_t *pair_used_pointer;
  struct kotoba_pair_v1 *pairs_base;
  uint8_t *pair_validated_base;
  uint64_t *vector_used_pointer;
  void *vectors_base;
  int64_t *vector_items_base;
  /* ABI v10 (2026-09-16): the two range slots, unserved here (NULL). */
  void *unserved_range_slots[2];
  /* ABI v11 (2026-09-25): the string constructor and three bytes slots,
   * unserved here (NULL). */
  void *unserved_bytes_slots[4];
  const uint8_t *code_base;
  uint64_t code_length;
};

struct kotoba_pair_v1 { int64_t first; int64_t second; };
struct kotoba_shared_v2 {
  struct kotoba_context_v2 context;
  uint64_t pair_used;
  struct kotoba_pair_v1 pairs[KOTOBA_IOS_PAIR_CAPACITY];
  uint64_t string_pool_used;
  uint8_t string_pool[KOTOBA_IOS_STRING_POOL_BYTES];
  /* No vectors on this host: an empty table, so an inline vector-at on any
   * handle fails its range check (0 used) exactly as a host call would. */
  uint64_t vector_used;
  uint8_t pair_validated[KOTOBA_IOS_PAIR_CAPACITY];
};

_Static_assert(offsetof(struct kotoba_context_v2, fuel) == 8, "fuel ABI drift");
_Static_assert(offsetof(struct kotoba_context_v2, allow) == 16, "allow ABI drift");
_Static_assert(offsetof(struct kotoba_context_v2, cap_call) == 48, "cap ABI drift");
_Static_assert(offsetof(struct kotoba_context_v2, pair_new) == 56, "pair ABI drift");
_Static_assert(offsetof(struct kotoba_context_v2, typed_cap_call) == 128, "typed ABI drift");
_Static_assert(offsetof(struct kotoba_context_v2, pair_used_pointer) == 288, "inline ABI drift");
_Static_assert(offsetof(struct kotoba_context_v2, vector_items_base) == 328, "inline ABI drift");
_Static_assert(offsetof(struct kotoba_context_v2, pair_first) == 64, "pair ABI drift");
_Static_assert(offsetof(struct kotoba_context_v2, pair_second) == 72, "pair ABI drift");
_Static_assert(offsetof(struct kotoba_context_v2, string_equal) == 112, "string ABI drift");
_Static_assert(offsetof(struct kotoba_context_v2, string_concat) == 120, "string ABI drift");
_Static_assert(offsetof(struct kotoba_context_v2, typed_cap_call) == 128, "typed cap ABI drift");

static void guest_trap(void) { __builtin_trap(); }

static int64_t cap_call(struct kotoba_context_v2 *context,
                        uint64_t cap_id, int64_t value) {
  if (context == NULL || context->version != 2 || cap_id > 255 ||
      (context->allow[cap_id / 64] & (UINT64_C(1) << (cap_id % 64))) == 0) {
    guest_trap();
  }
  return (int64_t)((uint64_t)value + UINT64_C(1));
}

static int64_t pair_new(struct kotoba_context_v2 *context,
                        int64_t first, int64_t second) {
  struct kotoba_shared_v2 *shared = (struct kotoba_shared_v2 *)context;
  if (context == NULL || context->version != 2 ||
      shared->pair_used >= KOTOBA_IOS_PAIR_CAPACITY) guest_trap();
  uint64_t index = shared->pair_used++;
  shared->pairs[index].first = first;
  shared->pairs[index].second = second;
  return (int64_t)(index + 1);
}

static int64_t pair_get(struct kotoba_context_v2 *context,
                        int64_t handle, int second) {
  struct kotoba_shared_v2 *shared = (struct kotoba_shared_v2 *)context;
  if (context == NULL || context->version != 2 || handle <= 0 ||
      (uint64_t)handle > shared->pair_used) guest_trap();
  const struct kotoba_pair_v1 *pair = &shared->pairs[(uint64_t)handle - 1];
  return second ? pair->second : pair->first;
}

static int64_t pair_first(struct kotoba_context_v2 *context, int64_t handle) {
  return pair_get(context, handle, 0);
}
static int64_t pair_second(struct kotoba_context_v2 *context, int64_t handle) {
  return pair_get(context, handle, 1);
}

static int valid_utf8(const uint8_t *bytes, uint64_t length);

static const uint8_t *resolve_string_bytes(struct kotoba_context_v2 *context,
                                           int64_t offset, int64_t length) {
  struct kotoba_shared_v2 *shared = (struct kotoba_shared_v2 *)context;
  const uint8_t *bytes;
  if (context == NULL || context->version != 2 || length < 0) guest_trap();
  if (offset >= 0) {
    if ((uint64_t)offset + (uint64_t)length > context->code_length ||
        (uint64_t)offset + (uint64_t)length < (uint64_t)offset) guest_trap();
    bytes = context->code_base + offset;
  } else {
    if (offset == INT64_MIN) guest_trap();
    uint64_t pool_offset = (uint64_t)(-offset - 1);
    if (pool_offset + (uint64_t)length > shared->string_pool_used ||
        pool_offset + (uint64_t)length < pool_offset) guest_trap();
    bytes = shared->string_pool + pool_offset;
  }
  /* String handles are untrusted KIR data. Bounds alone are not enough:
     arbitrary in-range code bytes must not pass as a valid Kotoba string. */
  if (!valid_utf8(bytes, (uint64_t)length)) guest_trap();
  return bytes;
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
      uint8_t b, c;
      if (i + 1 >= length) return 0;
      b = bytes[i++]; c = bytes[i++];
      if ((b & 0xc0) != 0x80 || (c & 0xc0) != 0x80 ||
          (a == 0xe0 && b < 0xa0) || (a == 0xed && b >= 0xa0)) return 0;
      continue;
    }
    if (a >= 0xf0 && a <= 0xf4) {
      uint8_t b, c, d;
      if (i + 2 >= length) return 0;
      b = bytes[i++]; c = bytes[i++]; d = bytes[i++];
      if ((b & 0xc0) != 0x80 || (c & 0xc0) != 0x80 ||
          (d & 0xc0) != 0x80 || (a == 0xf0 && b < 0x90) ||
          (a == 0xf4 && b >= 0x90)) return 0;
      continue;
    }
    return 0;
  }
  return 1;
}

static int64_t string_equal(struct kotoba_context_v2 *context,
                            int64_t left, int64_t right) {
  int64_t left_length = pair_get(context, left, 1);
  int64_t right_length = pair_get(context, right, 1);
  const uint8_t *left_bytes =
      resolve_string_bytes(context, pair_get(context, left, 0), left_length);
  const uint8_t *right_bytes =
      resolve_string_bytes(context, pair_get(context, right, 0), right_length);
  if (left_length != right_length) return 0;
  return memcmp(left_bytes, right_bytes, (size_t)left_length) == 0 ? 1 : 0;
}

static int64_t string_concat(struct kotoba_context_v2 *context,
                             int64_t left, int64_t right) {
  struct kotoba_shared_v2 *shared = (struct kotoba_shared_v2 *)context;
  int64_t left_length = pair_get(context, left, 1);
  int64_t right_length = pair_get(context, right, 1);
  if (left_length < 0 || right_length < 0 ||
      left_length > INT64_MAX - right_length) guest_trap();
  int64_t total = left_length + right_length;
  if (shared->string_pool_used + (uint64_t)total >
          KOTOBA_IOS_STRING_POOL_BYTES ||
      shared->string_pool_used + (uint64_t)total < shared->string_pool_used)
    guest_trap();
  const uint8_t *left_bytes =
      resolve_string_bytes(context, pair_get(context, left, 0), left_length);
  const uint8_t *right_bytes =
      resolve_string_bytes(context, pair_get(context, right, 0), right_length);
  uint64_t start = shared->string_pool_used;
  memcpy(shared->string_pool + start, left_bytes, (size_t)left_length);
  memcpy(shared->string_pool + start + (uint64_t)left_length,
         right_bytes, (size_t)right_length);
  shared->string_pool_used += (uint64_t)total;
  return pair_new(context, -((int64_t)start) - 1, total);
}

static int valid_typed_value(struct kotoba_context_v2 *context,
                             uint64_t kind, int64_t value) {
  int64_t tag_or_offset = pair_get(context, value, 0);
  int64_t payload_or_length = pair_get(context, value, 1);
  if (kind == 1) {
    const uint8_t *bytes =
        resolve_string_bytes(context, tag_or_offset, payload_or_length);
    return valid_utf8(bytes, (uint64_t)payload_or_length);
  }
  if (kind == 2 || kind == 3) {
    if (tag_or_offset != 0 && tag_or_offset != 1) return 0;
    return kind != 2 || tag_or_offset != 0 || payload_or_length == 0;
  }
  return 0;
}

static int64_t typed_cap_call(struct kotoba_context_v2 *context,
                              uint64_t cap_id, uint64_t request_kind,
                              uint64_t result_kind, int64_t request) {
  if (context == NULL || context->version != 2 || cap_id > 255 ||
      (context->allow[cap_id / 64] & (UINT64_C(1) << (cap_id % 64))) == 0 ||
      request_kind != result_kind ||
      !valid_typed_value(context, request_kind, request)) guest_trap();
  int64_t result = request;
  if (!valid_typed_value(context, result_kind, result)) guest_trap();
  return result;
}

#if defined(__APPLE__) && defined(__aarch64__)
typedef int64_t (*kotoba_fn8)(int64_t, int64_t, int64_t, int64_t,
                              int64_t, int64_t, int64_t, int64_t);

/* ---- Trap containment -------------------------------------------------
 *
 * The compiled guest reaches `brk #0` for fuel exhaustion, division by zero,
 * INT64_MIN/-1 overflow, bounds violations, and denied capabilities; this
 * host's own guest_trap() adds __builtin_trap(). kexe_loader.c contains all
 * of those by running the guest in a forked child and reporting the wait
 * status. iOS has no such supervisor available to an app process, so without
 * the handlers below a single guest trap terminates the ENTIRE application.
 *
 * That is reachable from ordinary, policy-allowed code: a divisor supplied by
 * the host through cap-call is not a constant, so the compiler's static fuel
 * and constant analysis cannot reject it, and `(quot x host-value)` with a
 * zero host-value traps at runtime.
 *
 * This is mechanism, not policy: the handler only converts a synchronous
 * trap into a normal return path. What that means -- the guest is rejected,
 * with KOTOBA_IOS_GUEST_TRAP -- stays a typed result the caller decides on.
 *
 * Scope and limits, stated rather than implied:
 *  - Signal dispositions are process-wide, so execution is serialized by
 *    `containment_busy` and concurrent/reentrant calls are refused. The jump
 *    environment is thread-local; signals delivered to another thread are
 *    forwarded to the disposition that was installed before this call.
 *  - siglongjmp out of a handler abandons the guest's stack frames. That is
 *    sound here only because the guest allocates nothing that needs
 *    unwinding: its heap is the arena in `shared`, which the caller frees.
 *  - Only synchronous SIGTRAP/SIGILL from the executing guest are contained.
 *    Other signals and other causes keep their prior disposition. */
static atomic_flag containment_busy = ATOMIC_FLAG_INIT;
static atomic_uint containment_handlers = ATOMIC_VAR_INIT(0);
_Static_assert(ATOMIC_INT_LOCK_FREE == 2, "signal handler counter must be lock-free");
static _Thread_local sigjmp_buf containment_return;
static _Thread_local volatile sig_atomic_t containment_active;
static struct sigaction containment_previous_trap;
static struct sigaction containment_previous_ill;
static struct sigaction containment_action;

static void containment_forward(int signal_number, siginfo_t *info,
                                void *context) {
  (void)info;
  (void)context;
  const struct sigaction *previous = signal_number == SIGTRAP
      ? &containment_previous_trap : &containment_previous_ill;
  if (previous->sa_handler == SIG_IGN) return;
  if (previous->sa_handler == SIG_DFL) {
    /* Restore the default disposition for this delivery. If a debugger
       resumes a default SIGTRAP, put containment back before returning.
       The signal is blocked while its handler runs, so unblock it before
       raising it; otherwise it remains pending until this handler returns. */
    if (sigaction(signal_number, previous, NULL) != 0)
      _Exit(128 + signal_number);
    sigset_t signal_set;
    sigemptyset(&signal_set);
    sigaddset(&signal_set, signal_number);
    if (pthread_sigmask(SIG_UNBLOCK, &signal_set, NULL) != 0)
      _Exit(128 + signal_number);
    if (raise(signal_number) != 0) _Exit(128 + signal_number);
    if (pthread_sigmask(SIG_BLOCK, &signal_set, NULL) != 0)
      _Exit(128 + signal_number);
    if (sigaction(signal_number, &containment_action, NULL) != 0)
      _Exit(128 + signal_number);
    return;
  }
  /* containment_install admits only default and ignored dispositions. */
  _Exit(128 + signal_number);
}

static int containment_is_guest_brk(void *context) {
#if defined(__APPLE__) && defined(__aarch64__)
  if (context == NULL) return 0;
  const ucontext_t *signal_context = (const ucontext_t *)context;
  uint32_t exception_class =
      (uint32_t)((signal_context->uc_mcontext->__es.__esr >> 26) & 0x3f);
  if (exception_class != 0x3c) return 0;
  uintptr_t pc = (uintptr_t)signal_context->uc_mcontext->__ss.__pc;
  uintptr_t start = (uintptr_t)kotoba_ios_code_start;
  uintptr_t end = (uintptr_t)kotoba_ios_code_end;
  if (pc < start || pc > end || end - pc < sizeof(uint32_t) || (pc & 3) != 0)
    return 0;
  uint32_t instruction = *(const volatile uint32_t *)pc;
  return (instruction & UINT32_C(0xFFE0001F)) == UINT32_C(0xD4200000);
#else
  (void)context;
  return 0;
#endif
}

static int containment_is_synchronous_trap(int signal_number,
                                           const siginfo_t *info,
                                           void *context) {
  if (info == NULL || (signal_number != SIGTRAP && signal_number != SIGILL))
    return 0;
  /* Darwin arm64 may report BRK #0 as SIGTRAP with si_code 0, the same value
     used by raise(SIGTRAP). Accept that form only for a BRK exception whose
     saved PC points at a BRK instruction inside the linked guest code. */
  if (signal_number == SIGTRAP && info->si_code == 0)
    return containment_is_guest_brk(context);
  return info->si_code > 0 && info->si_code < SI_USER;
}

static void containment_handler(int signal_number, siginfo_t *info,
                                void *context) {
  atomic_fetch_add_explicit(&containment_handlers, 1, memory_order_acq_rel);
  if (containment_active &&
      containment_is_synchronous_trap(signal_number, info, context)) {
    atomic_fetch_sub_explicit(&containment_handlers, 1, memory_order_release);
    siglongjmp(containment_return, 1);
  }
  containment_forward(signal_number, info, context);
  atomic_fetch_sub_explicit(&containment_handlers, 1, memory_order_release);
}

struct containment_state {
  int installed;
};

static void containment_wait_for_handlers(void) {
  while (atomic_load_explicit(&containment_handlers, memory_order_acquire) != 0) {
    sched_yield();
  }
}

static int containment_install(struct containment_state *state) {
  memset(&containment_action, 0, sizeof(containment_action));
  containment_action.sa_sigaction = containment_handler;
  sigemptyset(&containment_action.sa_mask);
  containment_action.sa_flags = SA_SIGINFO;
  state->installed = 0;
  containment_active = 0;
  if (sigaction(SIGTRAP, NULL, &containment_previous_trap) != 0 ||
      sigaction(SIGILL, NULL, &containment_previous_ill) != 0) return 0;
  /* Preserve application semantics: this host forwards only default/ignored
     dispositions. It refuses to emulate a custom handler's mask and flags. */
  if ((containment_previous_trap.sa_handler != SIG_DFL &&
       containment_previous_trap.sa_handler != SIG_IGN) ||
      (containment_previous_ill.sa_handler != SIG_DFL &&
       containment_previous_ill.sa_handler != SIG_IGN)) return 0;
  if (sigaction(SIGTRAP, &containment_action, NULL) != 0) return 0;
  if (sigaction(SIGILL, &containment_action, NULL) != 0) {
    sigaction(SIGTRAP, &containment_previous_trap, NULL);
    containment_wait_for_handlers();
    return 0;
  }
  state->installed = 1;
  return 1;
}

static void containment_restore(struct containment_state *state) {
  if (!state->installed) return;
  sigaction(SIGTRAP, &containment_previous_trap, NULL);
  sigaction(SIGILL, &containment_previous_ill, NULL);
  state->installed = 0;
  containment_wait_for_handlers();
}
#endif

__attribute__((visibility("default")))
int kotoba_ios_execute_static_v1(const struct kotoba_ios_request_v1 *request,
                                 struct kotoba_ios_result_v1 *result) {
  if (result == NULL) return KOTOBA_IOS_INVALID_REQUEST;
  memset(result, 0, sizeof(*result));
  result->abi_version = KOTOBA_IOS_HOST_ABI_V1;
#if !defined(__APPLE__) || !defined(__aarch64__)
  (void)request;
  result->status = KOTOBA_IOS_UNSUPPORTED_HOST;
  return KOTOBA_IOS_UNSUPPORTED_HOST;
#else
  if (request == NULL || request->abi_version != KOTOBA_IOS_HOST_ABI_V1 ||
      request->arity > KOTOBA_IOS_MAX_ARITY || request->target_profile == NULL ||
      strcmp(request->target_profile, KOTOBA_IOS_TARGET) != 0 ||
      strcmp(kotoba_ios_target_profile, KOTOBA_IOS_TARGET) != 0 ||
      (uintptr_t)kotoba_ios_code_end <= (uintptr_t)kotoba_ios_code_start ||
      (uintptr_t)kotoba_ios_code_end - (uintptr_t)kotoba_ios_code_start >
          KOTOBA_IOS_MAX_CODE_BYTES) {
    result->status = KOTOBA_IOS_INVALID_REQUEST;
    return KOTOBA_IOS_INVALID_REQUEST;
  }
  struct kotoba_shared_v2 *shared = calloc(1, sizeof(*shared));
  if (shared == NULL) {
    result->status = KOTOBA_IOS_ALLOCATION_ERROR;
    return KOTOBA_IOS_ALLOCATION_ERROR;
  }
  shared->context.version = 2;
  shared->context.fuel = 512;
  memcpy(shared->context.allow, request->allow, sizeof(request->allow));
  shared->context.cap_call = cap_call;
  shared->context.pair_new = pair_new;
  shared->context.pair_first = pair_first;
  shared->context.pair_second = pair_second;
  shared->context.string_equal = string_equal;
  shared->context.string_concat = string_concat;
  shared->context.typed_cap_call = typed_cap_call;
  shared->context.pair_used_pointer = &shared->pair_used;
  shared->context.pairs_base = shared->pairs;
  shared->context.pair_validated_base = shared->pair_validated;
  shared->context.vector_used_pointer = &shared->vector_used;
  shared->context.vectors_base = NULL;
  shared->context.vector_items_base = NULL;
  shared->context.code_base = kotoba_ios_code_start;
  shared->context.code_length =
      (uint64_t)((uintptr_t)kotoba_ios_code_end -
                 (uintptr_t)kotoba_ios_code_start);
  kotoba_fn8 entry = (kotoba_fn8)(uintptr_t)kotoba_ios_entry;
  /* Process-wide signal dispositions cannot be shared: refuse rather than
     run a second guest with the first one's handlers half-installed. */
  if (atomic_flag_test_and_set_explicit(&containment_busy,
                                        memory_order_acquire)) {
    free(shared);
    result->status = KOTOBA_IOS_CONTAINMENT_UNAVAILABLE;
    return KOTOBA_IOS_CONTAINMENT_UNAVAILABLE;
  }
  struct containment_state containment;
  if (!containment_install(&containment)) {
    atomic_flag_clear_explicit(&containment_busy, memory_order_release);
    free(shared);
    result->status = KOTOBA_IOS_CONTAINMENT_UNAVAILABLE;
    return KOTOBA_IOS_CONTAINMENT_UNAVAILABLE;
  }

  if (sigsetjmp(containment_return, 1) != 0) {
    containment_active = 0;
    /* Reached from containment_handler: the guest trapped. Report the fuel
       and heap state as of the trap -- it is the caller's evidence for WHY
       the guest was rejected -- but never the (undefined) return value. */
    containment_restore(&containment);
    atomic_flag_clear_explicit(&containment_busy, memory_order_release);
    result->value = 0;
    result->fuel_remaining = shared->context.fuel;
    result->pairs_used = shared->pair_used;
    result->status = KOTOBA_IOS_GUEST_TRAP;
    free(shared);
    return KOTOBA_IOS_GUEST_TRAP;
  }

  containment_active = 1;
  result->value = entry(request->args[0], request->args[1], request->args[2],
                        request->args[3], request->args[4], 0, 0,
                        (int64_t)(intptr_t)&shared->context);

  containment_active = 0;
  containment_restore(&containment);
  atomic_flag_clear_explicit(&containment_busy, memory_order_release);
  result->fuel_remaining = shared->context.fuel;
  result->pairs_used = shared->pair_used;
  result->status = KOTOBA_IOS_OK;
  free(shared);
  return KOTOBA_IOS_OK;
#endif
}
