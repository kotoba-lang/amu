#define _GNU_SOURCE
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

#define KEXE_PAIR_CAPACITY 4096u
#define KEXE_KGRAPH_CAPACITY 4096u
#define KEXE_STRING_POOL_BYTES 65536u
#define KEXE_RECORD_FIELD_LIMIT 128u

static void write_stderr_checked(const char *bytes, size_t length) {
  ssize_t written = write(STDERR_FILENO, bytes, length);
  (void)written;
}
/* Vector handles, and the element words they slice. The element arena is
 * deliberately four times `kotoba.kir.value/vector-item-limit` (16384), the
 * longest single vector KIR admits: every operation that changes an element
 * allocates rather than mutates, so an arena exactly one maximum vector wide
 * could build such a vector and then never touch it again. This bounds total
 * LIVE allocation, not any one vector's length -- the same distinction the
 * string pool above already makes, in bytes rather than words. */
#define KEXE_VECTOR_CAPACITY 4096u
#define KEXE_VECTOR_ITEM_CAPACITY 65536u

struct kexe_context_v3 {
  uint64_t version;
  uint64_t fuel;
  uint64_t allow[4];
  int64_t (*cap_call)(struct kexe_context_v3 *, uint64_t, int64_t);
  int64_t (*pair_new)(struct kexe_context_v3 *, int64_t, int64_t);
  int64_t (*pair_first)(struct kexe_context_v3 *, int64_t);
  int64_t (*pair_second)(struct kexe_context_v3 *, int64_t);
  /* kgraph-* (ADR-2607198300): an all-integer EAVT datom store, the native
   * analog of kotoba-lang/kotoba's string/EDN-based kgraph-assert!/
   * kgraph-query -- this loader has no addressable guest buffer for EDN
   * text, so entity/attribute/value are caller-assigned integer ids. */
  int64_t (*kgraph_assert)(struct kexe_context_v3 *, int64_t, int64_t, int64_t);
  int64_t (*kgraph_get)(struct kexe_context_v3 *, int64_t, int64_t);
  int64_t (*kgraph_count)(struct kexe_context_v3 *, int64_t);
  int64_t (*kgraph_entity_at)(struct kexe_context_v3 *, int64_t, int64_t);
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
  int64_t (*string_equal)(struct kexe_context_v3 *, int64_t, int64_t);
  int64_t (*string_concat)(struct kexe_context_v3 *, int64_t, int64_t);
  int64_t (*typed_cap_call)(struct kexe_context_v3 *, uint64_t, uint64_t,
                            uint64_t, int64_t);
  /* string-substring over an arbitrary string value. Unlike string_concat
   * this allocates no pool bytes: a substring is a contiguous byte range of
   * its source, so the result is a VIEW -- a new pair(offset', length')
   * addressing the same bytes. Only the boundary CHECK needs the host (the
   * guest cannot load a byte), which is why this is a whole-operation
   * callback like string_equal/string_concat rather than a byte accessor. */
  int64_t (*string_substring)(struct kexe_context_v3 *, int64_t, int64_t,
                              int64_t);
  /* string-code-point-at. Like string_substring this exists only because the
   * guest cannot load a byte; unlike it the result is a scalar, not a handle,
   * so nothing is allocated at all. */
  int64_t (*string_code_point_at)(struct kexe_context_v3 *, int64_t, int64_t);
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
   * is a vector of those words. Both KIR families reach these six slots.
   *
   * `vector_new_empty` has no KIR operation of its own -- KIR's `vector-new`
   * is variadic and this ABI is not, so the backends expand a literal into
   * an empty vector plus one `vector_conj` per element. */
  int64_t (*vector_new_empty)(struct kexe_context_v3 *);
  int64_t (*vector_conj)(struct kexe_context_v3 *, int64_t, int64_t);
  int64_t (*vector_count)(struct kexe_context_v3 *, int64_t);
  int64_t (*vector_at)(struct kexe_context_v3 *, int64_t, int64_t);
  int64_t (*vector_assoc)(struct kexe_context_v3 *, int64_t, int64_t, int64_t);
  int64_t (*vector_drop)(struct kexe_context_v3 *, int64_t, int64_t);
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

struct kexe_shared_v3 {
  struct kexe_context_v3 context;
  int64_t result;
  uint64_t completed;
  uint64_t pair_used;
  struct kexe_pair_v1 pairs[KEXE_PAIR_CAPACITY];
  uint64_t kgraph_used;
  struct kexe_datom_v1 datoms[KEXE_KGRAPH_CAPACITY];
  uint64_t string_pool_used;
  uint8_t string_pool[KEXE_STRING_POOL_BYTES];
  /* Two arenas, because a vector table entry and the elements it spans are
   * separately exhaustible: many small vectors run out of entries first, one
   * growing vector runs out of elements first, and neither bound implies the
   * other. */
  uint64_t vector_used;
  struct kexe_vector_v1 vectors[KEXE_VECTOR_CAPACITY];
  uint64_t vector_item_used;
  int64_t vector_items[KEXE_VECTOR_ITEM_CAPACITY];
};

_Static_assert(offsetof(struct kexe_context_v3, fuel) == 8, "fuel ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, allow) == 16, "allow ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, cap_call) == 48, "cap ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, pair_new) == 56, "pair ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, pair_first) == 64, "pair ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, pair_second) == 72, "pair ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, kgraph_assert) == 80, "kgraph ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, kgraph_get) == 88, "kgraph ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, kgraph_count) == 96, "kgraph ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, kgraph_entity_at) == 104, "kgraph ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, typed_cap_call) == 128, "typed cap ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, string_equal) == 112, "string ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, string_concat) == 120, "string ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, string_substring) == 136, "string ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, string_code_point_at) == 144, "string ABI drift");
_Static_assert(sizeof(((struct kexe_shared_v3 *)0)->pairs) == 65536,
               "pair arena size drift");
_Static_assert(sizeof(((struct kexe_shared_v3 *)0)->datoms) == 98304,
               "kgraph arena size drift");
_Static_assert(offsetof(struct kexe_context_v3, vector_new_empty) == 152, "vector ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, vector_conj) == 160, "vector ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, vector_count) == 168, "vector ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, vector_at) == 176, "vector ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, vector_assoc) == 184, "vector ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, vector_drop) == 192, "vector ABI drift");
_Static_assert(sizeof(((struct kexe_shared_v3 *)0)->string_pool) == 65536,
               "string pool size drift");
_Static_assert(sizeof(((struct kexe_shared_v3 *)0)->vectors) == 65536,
               "vector table size drift");
_Static_assert(sizeof(((struct kexe_shared_v3 *)0)->vector_items) == 524288,
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

static int64_t checked_cap_call(struct kexe_context_v3 *context,
                                uint64_t cap_id, int64_t value) {
  if (context == NULL || context->version != 3 || cap_id > 255 ||
      (context->allow[cap_id / 64] & (UINT64_C(1) << (cap_id % 64))) == 0) {
    raise(SIGILL);
    return 0;
  }
  return value + 1;
}

static int64_t checked_pair_new(struct kexe_context_v3 *context,
                                int64_t first, int64_t second) {
  struct kexe_shared_v3 *shared = (struct kexe_shared_v3 *)context;
  if (context == NULL || context->version != 3 ||
      shared->pair_used >= KEXE_PAIR_CAPACITY) {
    raise(SIGILL);
    return 0;
  }
  uint64_t index = shared->pair_used++;
  shared->pairs[index].first = first;
  shared->pairs[index].second = second;
  return (int64_t)(index + 1);
}

static int64_t checked_pair_get(struct kexe_context_v3 *context,
                                int64_t handle, int second) {
  struct kexe_shared_v3 *shared = (struct kexe_shared_v3 *)context;
  if (context == NULL || context->version != 3 || handle <= 0 ||
      (uint64_t)handle > shared->pair_used) {
    raise(SIGILL);
    return 0;
  }
  struct kexe_pair_v1 *pair = &shared->pairs[(uint64_t)handle - 1];
  return second ? pair->second : pair->first;
}

static int64_t checked_pair_first(struct kexe_context_v3 *context, int64_t handle) {
  return checked_pair_get(context, handle, 0);
}

static int64_t checked_pair_second(struct kexe_context_v3 *context, int64_t handle) {
  return checked_pair_get(context, handle, 1);
}

/* vector-i64 / vector-f64 host table.
 *
 * Every operation that changes an element allocates a new slice and a new
 * handle; nothing ever writes inside a slice an existing handle covers. That
 * is what makes a handle an immutable VALUE despite the shared arena, and it
 * is the whole safety argument for `checked_vector_conj`'s in-place append
 * below -- so the two must be read together. */

static struct kexe_vector_v1 *resolve_vector(struct kexe_shared_v3 *shared,
                                             int64_t handle) {
  if (handle <= 0 || (uint64_t)handle > shared->vector_used) return NULL;
  return &shared->vectors[(uint64_t)handle - 1];
}

/* Mints a handle for an already-populated slice. Returns 0 when the handle
 * table is full; every caller turns that into SIGILL, so exhaustion is a trap
 * rather than a silently wrong vector. */
static int64_t intern_vector(struct kexe_shared_v3 *shared,
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
static int64_t checked_vector_new_empty(struct kexe_context_v3 *context) {
  struct kexe_shared_v3 *shared = (struct kexe_shared_v3 *)context;
  if (context == NULL || context->version != 3) { raise(SIGILL); return 0; }
  int64_t handle = intern_vector(shared, shared->vector_item_used, 0);
  if (handle == 0) { raise(SIGILL); return 0; }
  return handle;
}

static int64_t checked_vector_count(struct kexe_context_v3 *context,
                                    int64_t handle) {
  struct kexe_shared_v3 *shared = (struct kexe_shared_v3 *)context;
  if (context == NULL || context->version != 3) { raise(SIGILL); return 0; }
  struct kexe_vector_v1 *vector = resolve_vector(shared, handle);
  if (vector == NULL) { raise(SIGILL); return 0; }
  return (int64_t)vector->length;
}

/* Traps out of range, matching `kotoba.kir`'s own vector-at. The total
 * variant is vector-get, which the backends lower to a bounds test around
 * this call rather than to a host function of its own. */
static int64_t checked_vector_at(struct kexe_context_v3 *context,
                                 int64_t handle, int64_t index) {
  struct kexe_shared_v3 *shared = (struct kexe_shared_v3 *)context;
  if (context == NULL || context->version != 3) { raise(SIGILL); return 0; }
  struct kexe_vector_v1 *vector = resolve_vector(shared, handle);
  if (vector == NULL || index < 0 || (uint64_t)index >= vector->length) {
    raise(SIGILL);
    return 0;
  }
  return shared->vector_items[vector->offset + (uint64_t)index];
}

static int64_t checked_vector_conj(struct kexe_context_v3 *context,
                                   int64_t handle, int64_t item) {
  struct kexe_shared_v3 *shared = (struct kexe_shared_v3 *)context;
  if (context == NULL || context->version != 3) { raise(SIGILL); return 0; }
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
static int64_t checked_vector_assoc(struct kexe_context_v3 *context,
                                    int64_t handle, int64_t index,
                                    int64_t item) {
  struct kexe_shared_v3 *shared = (struct kexe_shared_v3 *)context;
  if (context == NULL || context->version != 3) { raise(SIGILL); return 0; }
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

/* A VIEW, for the same reason string_substring is one: a suffix is contiguous
 * within its source, so it needs a handle but no elements. Dropping zero
 * elements is admitted and yields a distinct handle over the same slice. */
static int64_t checked_vector_drop(struct kexe_context_v3 *context,
                                   int64_t handle, int64_t count) {
  struct kexe_shared_v3 *shared = (struct kexe_shared_v3 *)context;
  if (context == NULL || context->version != 3) { raise(SIGILL); return 0; }
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

static int64_t checked_kgraph_assert(struct kexe_context_v3 *context,
                                     int64_t e, int64_t a, int64_t v) {
  struct kexe_shared_v3 *shared = (struct kexe_shared_v3 *)context;
  if (context == NULL || context->version != 3 ||
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
static int64_t checked_kgraph_get(struct kexe_context_v3 *context,
                                  int64_t e, int64_t a) {
  struct kexe_shared_v3 *shared = (struct kexe_shared_v3 *)context;
  if (context == NULL || context->version != 3) {
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
static int kgraph_entity_seen_before(const struct kexe_shared_v3 *shared,
                                     uint64_t upto, int64_t a, int64_t e) {
  for (uint64_t j = 0; j < upto; j++) {
    if (shared->datoms[j].a == a && shared->datoms[j].e == e) return 1;
  }
  return 0;
}

static int64_t checked_kgraph_count(struct kexe_context_v3 *context, int64_t a) {
  struct kexe_shared_v3 *shared = (struct kexe_shared_v3 *)context;
  if (context == NULL || context->version != 3) {
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

static int64_t checked_kgraph_entity_at(struct kexe_context_v3 *context,
                                        int64_t a, int64_t index) {
  struct kexe_shared_v3 *shared = (struct kexe_shared_v3 *)context;
  if (context == NULL || context->version != 3 || index < 0) {
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
static const uint8_t *resolve_string_bytes(struct kexe_context_v3 *context,
                                           int64_t offset, int64_t length) {
  struct kexe_shared_v3 *shared = (struct kexe_shared_v3 *)context;
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
  if (pool_offset + (uint64_t)length > KEXE_STRING_POOL_BYTES ||
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

static int hex_nibble(char value) {
  if (value >= '0' && value <= '9') return value - '0';
  if (value >= 'a' && value <= 'f') return value - 'a' + 10;
  return -1;
}

static int allocate_host_pair(struct kexe_shared_v3 *shared,
                              int64_t first, int64_t second, int64_t *handle) {
  if (shared->pair_used >= KEXE_PAIR_CAPACITY) return -1;
  uint64_t index = shared->pair_used++;
  shared->pairs[index].first = first;
  shared->pairs[index].second = second;
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
static int parse_guest_arg(struct kexe_shared_v3 *shared,
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
    if (count > KEXE_PAIR_CAPACITY - shared->pair_used) return -1;
    int64_t handle = 0;
    for (uint64_t i = count; i > 0; i--) {
      uint64_t index = shared->pair_used++;
      shared->pairs[index].first = fields[i - 1u];
      shared->pairs[index].second = handle;
      handle = (int64_t)(index + 1u);
    }
    *value = handle;
    return 0;
  }
  if (strncmp(text, "s:", 2) != 0) return parse_i64(text, value);
  const char *hex = text + 2;
  size_t digits = strlen(hex);
  if ((digits & 1u) != 0) return -1;
  uint64_t length = (uint64_t)(digits / 2u);
  if (length > KEXE_STRING_POOL_BYTES - shared->string_pool_used ||
      shared->pair_used >= KEXE_PAIR_CAPACITY) return -1;
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
  shared->string_pool_used += length;
  *value = (int64_t)(index + 1u);
  return 0;
}

/* Read a returned string without invoking the guest-facing trapping helpers:
 * this runs in the supervisor after the sandboxed child has exited. It also
 * requires a pool slice to have actually been allocated, rather than merely
 * falling somewhere inside the pool capacity. */
static const uint8_t *inspect_string_result(const struct kexe_shared_v3 *shared,
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

static int inspect_record_result(const struct kexe_shared_v3 *shared,
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

static int inspect_tagged_i64_result(const struct kexe_shared_v3 *shared,
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

static int inspect_variant_result(const struct kexe_shared_v3 *shared,
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
static int peek_pair(struct kexe_context_v3 *context, int64_t handle,
                     int second, int64_t *out) {
  struct kexe_shared_v3 *shared = (struct kexe_shared_v3 *)context;
  if (context == NULL || context->version != 3 || handle <= 0 ||
      (uint64_t)handle > shared->pair_used) return 0;
  struct kexe_pair_v1 *pair = &shared->pairs[(uint64_t)handle - 1];
  *out = second ? pair->second : pair->first;
  return 1;
}

static int peek_vector(struct kexe_context_v3 *context, int64_t handle,
                       uint64_t *length, const int64_t **items) {
  struct kexe_shared_v3 *shared = (struct kexe_shared_v3 *)context;
  struct kexe_vector_v1 *vector;
  if (context == NULL || context->version != 3) return 0;
  vector = resolve_vector(shared, handle);
  if (vector == NULL) return 0;
  if (vector->offset + vector->length > KEXE_VECTOR_ITEM_CAPACITY) return 0;
  *length = vector->length;
  *items = shared->vector_items + vector->offset;
  return 1;
}

static const uint8_t *peek_string_bytes(struct kexe_context_v3 *context,
                                        int64_t offset, int64_t length) {
  struct kexe_shared_v3 *shared = (struct kexe_shared_v3 *)context;
  if (context == NULL || context->version != 3 || length < 0) return NULL;
  if (offset >= 0) {
    if ((uint64_t)offset + (uint64_t)length > context->code_length) return NULL;
    return context->code_base + offset;
  }
  uint64_t pool_offset = (uint64_t)(-(offset + 1));
  if (pool_offset + (uint64_t)length > KEXE_STRING_POOL_BYTES ||
      pool_offset + (uint64_t)length < pool_offset) return NULL;
  return shared->string_pool + pool_offset;
}

static int valid_string_handle(struct kexe_context_v3 *context, int64_t value) {
  int64_t offset, length;
  if (!peek_pair(context, value, 0, &offset) ||
      !peek_pair(context, value, 1, &length)) return 0;
  const uint8_t *bytes = peek_string_bytes(context, offset, length);
  return bytes != NULL && length >= 0 && valid_utf8(bytes, (uint64_t)length);
}

static int read_string_handle(struct kexe_context_v3 *context, int64_t value,
                              const uint8_t **bytes, uint64_t *len) {
  int64_t offset = checked_pair_get(context, value, 0);
  int64_t length = checked_pair_get(context, value, 1);
  const uint8_t *p = resolve_string_bytes(context, offset, length);
  if (p == NULL || length < 0 || !valid_utf8(p, (uint64_t)length)) return 0;
  *bytes = p;
  *len = (uint64_t)length;
  return 1;
}

static int64_t intern_utf8(struct kexe_context_v3 *context,
                           const uint8_t *bytes, uint64_t length) {
  struct kexe_shared_v3 *shared = (struct kexe_shared_v3 *)context;
  if (shared->string_pool_used + length > KEXE_STRING_POOL_BYTES) {
    raise(SIGILL);
    return 0;
  }
  uint64_t start = shared->string_pool_used;
  memcpy(shared->string_pool + start, bytes, (size_t)length);
  shared->string_pool_used += length;
  return checked_pair_new(context, -((int64_t)start) - 1, (int64_t)length);
}

static int valid_dataspace_request(struct kexe_context_v3 *context,
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

static int valid_dataspace_result(struct kexe_context_v3 *context,
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

static int valid_ui_node(struct kexe_context_v3 *context, int64_t node) {
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

static int valid_ui_nodes(struct kexe_context_v3 *context, int64_t nodes) {
  uint64_t length = 0, i;
  const int64_t *items = NULL;
  if (!peek_vector(context, nodes, &length, &items) || length > 32) return 0;
  for (i = 0; i < length; i++) {
    if (!valid_ui_node(context, items[i])) return 0;
  }
  return 1;
}

static int valid_ui_commit_request(struct kexe_context_v3 *context,
                                   int64_t value) {
  int64_t base_rev, rest, nodes, tail;
  if (!peek_pair(context, value, 0, &base_rev) ||
      !peek_pair(context, value, 1, &rest) ||
      !peek_pair(context, rest, 0, &nodes) ||
      !peek_pair(context, rest, 1, &tail)) return 0;
  return tail == 0 && valid_ui_nodes(context, nodes);
}

static int valid_ui_commit_result(struct kexe_context_v3 *context,
                                  int64_t value) {
  int64_t revision, rest, count, tail;
  if (!peek_pair(context, value, 0, &revision) ||
      !peek_pair(context, value, 1, &rest) ||
      !peek_pair(context, rest, 0, &count) ||
      !peek_pair(context, rest, 1, &tail)) return 0;
  return tail == 0 && revision > 0 && count >= 0;
}

static int valid_ui_event_request(struct kexe_context_v3 *context,
                                  int64_t value) {
  int64_t after, tail;
  if (!peek_pair(context, value, 0, &after) ||
      !peek_pair(context, value, 1, &tail)) return 0;
  return tail == 0;
}

static int valid_ui_event(struct kexe_context_v3 *context, int64_t value) {
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

static int valid_ui_event_result(struct kexe_context_v3 *context,
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

static int64_t intern_pool_string(struct kexe_context_v3 *context,
                                  const char *text) {
  struct kexe_shared_v3 *shared = (struct kexe_shared_v3 *)context;
  size_t n = strlen(text);
  if (context == NULL || text == NULL ||
      n > KEXE_STRING_POOL_BYTES ||
      shared->string_pool_used + n > KEXE_STRING_POOL_BYTES) {
    raise(SIGILL);
    return 0;
  }
  uint64_t off = shared->string_pool_used;
  memcpy(shared->string_pool + off, text, n);
  shared->string_pool_used += n;
  return checked_pair_new(context, -((int64_t)off) - 1, (int64_t)n);
}

static int valid_clock_request(const struct kexe_shared_v3 *shared, int64_t value,
                               int64_t *ordinal, int64_t *payload) {
  /* Both request cases carry a bool payload (mask 0b11). */
  return inspect_variant_result(shared, value, 2, 3u, ordinal, payload);
}

static int valid_clock_result(const struct kexe_shared_v3 *shared, int64_t value) {
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

static int64_t clock_error_result(struct kexe_context_v3 *context,
                                  const char *code, const char *message) {
  int64_t code_handle = intern_pool_string(context, code);
  int64_t message_handle = intern_pool_string(context, message);
  int64_t record = checked_pair_new(context, message_handle, 0);
  record = checked_pair_new(context, code_handle, record);
  return checked_pair_new(context, KEXE_CLOCK_CASE_ERROR, record);
}

static int64_t clock_success_result(struct kexe_context_v3 *context,
                                    int64_t ordinal, int64_t tick,
                                    int64_t sequence) {
  int64_t record = checked_pair_new(context, sequence, 0);
  record = checked_pair_new(context, tick, record);
  return checked_pair_new(context, ordinal, record);
}

static int64_t hosted_clock_v1(struct kexe_context_v3 *context, int64_t request) {
  struct kexe_shared_v3 *shared = (struct kexe_shared_v3 *)context;
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

static int valid_typed_value(struct kexe_context_v3 *context,
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
    struct kexe_shared_v3 *shared = (struct kexe_shared_v3 *)context;
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

static int64_t ds_result_facet(struct kexe_context_v3 *context, int64_t id) {
  return checked_pair_new(context, DS_RES_FACET,
                          checked_pair_new(context, id, 0));
}

static int64_t ds_result_retracted(struct kexe_context_v3 *context,
                                   int64_t count) {
  return checked_pair_new(context, DS_RES_RETRACTED,
                          checked_pair_new(context, count, 0));
}

static int64_t ds_result_asserted(struct kexe_context_v3 *context,
                                  int64_t count, int64_t notices) {
  return checked_pair_new(
      context, DS_RES_ASSERTED,
      checked_pair_new(context, count, checked_pair_new(context, notices, 0)));
}

static int64_t ds_result_matches(struct kexe_context_v3 *context,
                                 int64_t bindings, int64_t notices) {
  return checked_pair_new(
      context, DS_RES_MATCHES,
      checked_pair_new(context, bindings,
                       checked_pair_new(context, notices, 0)));
}

static int64_t ds_notice_handle(struct kexe_context_v3 *context, int kind) {
  const char *text = kind == 1 ? ds_retract_notice : ds_assert_notice;
  return intern_utf8(context, (const uint8_t *)text, strlen(text));
}

static int64_t ds_empty_handle(struct kexe_context_v3 *context) {
  return intern_utf8(context, (const uint8_t *)ds_empty, strlen(ds_empty));
}

static int64_t dataspace_inject(struct kexe_context_v3 *context,
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

static int64_t ui_commit_inject(struct kexe_context_v3 *context,
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

static int64_t ui_event_inject(struct kexe_context_v3 *context,
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

static int64_t checked_typed_cap_call(struct kexe_context_v3 *context,
                                      uint64_t id, uint64_t request_kind,
                                      uint64_t result_kind, int64_t request) {
  if (context == NULL || context->version != 3 || id > 255 ||
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

static int64_t checked_string_equal(struct kexe_context_v3 *context,
                                    int64_t handle_a, int64_t handle_b) {
  if (context == NULL || context->version != 3) { raise(SIGILL); return 0; }
  int64_t offset_a = checked_pair_get(context, handle_a, 0);
  int64_t length_a = checked_pair_get(context, handle_a, 1);
  int64_t offset_b = checked_pair_get(context, handle_b, 0);
  int64_t length_b = checked_pair_get(context, handle_b, 1);
  if (length_a != length_b) return 0;
  const uint8_t *a = resolve_string_bytes(context, offset_a, length_a);
  const uint8_t *b = resolve_string_bytes(context, offset_b, length_b);
  return memcmp(a, b, (size_t)length_a) == 0 ? 1 : 0;
}

static int64_t checked_string_concat(struct kexe_context_v3 *context,
                                     int64_t handle_a, int64_t handle_b) {
  struct kexe_shared_v3 *shared = (struct kexe_shared_v3 *)context;
  if (context == NULL || context->version != 3) { raise(SIGILL); return 0; }
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
  if (shared->string_pool_used + (uint64_t)total > KEXE_STRING_POOL_BYTES ||
      shared->string_pool_used + (uint64_t)total < shared->string_pool_used) {
    raise(SIGILL);
    return 0;
  }
  const uint8_t *a = resolve_string_bytes(context, offset_a, length_a);
  const uint8_t *b = resolve_string_bytes(context, offset_b, length_b);
  uint64_t pool_offset = shared->string_pool_used;
  memcpy(shared->string_pool + pool_offset, a, (size_t)length_a);
  memcpy(shared->string_pool + pool_offset + (uint64_t)length_a, b, (size_t)length_b);
  shared->string_pool_used += (uint64_t)total;
  return checked_pair_new(context, -((int64_t)pool_offset) - 1, total);
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
static int64_t checked_string_substring(struct kexe_context_v3 *context,
                                        int64_t handle, int64_t start,
                                        int64_t end) {
  if (context == NULL || context->version != 3) { raise(SIGILL); return 0; }
  int64_t offset = checked_pair_get(context, handle, 0);
  int64_t length = checked_pair_get(context, handle, 1);
  if (length < 0 || start < 0 || end < start || end > length) {
    raise(SIGILL);
    return 0;
  }
  const uint8_t *bytes = resolve_string_bytes(context, offset, length);
  if (bytes == NULL) { raise(SIGILL); return 0; }
  if (!valid_utf8(bytes, (uint64_t)length)) { raise(SIGILL); return 0; }
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
  return checked_pair_new(context, result_offset, end - start);
}

/* Mirrors kotoba.kir.value/utf8-code-point-at!: the offset must be a
 * code-point boundary in [0, byte-length) -- note the EXCLUSIVE upper bound,
 * unlike substring, since there is no code point starting at the end. The
 * guest derives the width from the returned value to advance, so this one op
 * walks a string. valid_utf8 has already established that a sequence starting
 * at a non-continuation byte has all of its continuation bytes inside the
 * string, which is why they are read without further bounds checks. */
static int64_t checked_string_code_point_at(struct kexe_context_v3 *context,
                                            int64_t handle, int64_t byte_offset) {
  if (context == NULL || context->version != 3) { raise(SIGILL); return 0; }
  int64_t offset = checked_pair_get(context, handle, 0);
  int64_t length = checked_pair_get(context, handle, 1);
  if (length < 0 || byte_offset < 0 || byte_offset >= length) {
    raise(SIGILL);
    return 0;
  }
  const uint8_t *bytes = resolve_string_bytes(context, offset, length);
  if (bytes == NULL) { raise(SIGILL); return 0; }
  if (!valid_utf8(bytes, (uint64_t)length)) { raise(SIGILL); return 0; }
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

static int write_supervisor_report(const struct kexe_shared_v3 *shared,
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
        printf("{:status :trap :exit 126 :fuel {:initial 512 :remaining %" PRIu64
               "} :heap {:capacity 4096 :used %" PRIu64 "}}\n",
               shared->context.fuel, shared->pair_used);
        return 126;
      }
      printf("{:status :ok :result %" PRId64
             " :result-type :string :result-utf8-hex \"",
             shared->result);
      for (uint64_t i = 0; i < length; i++) printf("%02x", bytes[i]);
      printf("\" :fuel {:initial 512 :remaining %" PRIu64
             "} :heap {:capacity 4096 :used %" PRIu64 "}}\n",
             shared->context.fuel, shared->pair_used);
    } else if (record_field_count > 0) {
      int64_t fields[KEXE_RECORD_FIELD_LIMIT];
      if (!inspect_record_result(shared, shared->result,
                                 record_field_count, fields)) {
        static const char trap[] =
            "KEXE_TRAP {:kind :result :reason :invalid-record-chain}\n";
        write_stderr_checked(trap, sizeof(trap) - 1u);
        printf("{:status :trap :exit 127 :fuel {:initial 512 :remaining %" PRIu64
               "} :heap {:capacity 4096 :used %" PRIu64 "}}\n",
               shared->context.fuel, shared->pair_used);
        return 127;
      }
      printf("{:status :ok :result %" PRId64
             " :result-type :record :result-words [", shared->result);
      for (uint64_t i = 0; i < record_field_count; i++)
        printf(i == 0 ? "%" PRId64 : " %" PRId64, fields[i]);
      printf("] :fuel {:initial 512 :remaining %" PRIu64
             "} :heap {:capacity 4096 :used %" PRIu64 "}}\n",
             shared->context.fuel, shared->pair_used);
    } else if (strcmp(result_type, "option-i64") == 0 ||
               strcmp(result_type, "result-i64") == 0) {
      int option = strcmp(result_type, "option-i64") == 0;
      int64_t tag, payload;
      if (!inspect_tagged_i64_result(shared, shared->result, option,
                                     &tag, &payload)) {
        int trap_exit = option ? 128 : 129;
        const char *reason = option ? "invalid-option-i64" : "invalid-result-i64";
        fprintf(stderr, "KEXE_TRAP {:kind :result :reason :%s}\n", reason);
        printf("{:status :trap :exit %d :fuel {:initial 512 :remaining %" PRIu64
               "} :heap {:capacity 4096 :used %" PRIu64 "}}\n",
               trap_exit, shared->context.fuel, shared->pair_used);
        return trap_exit;
      }
      printf("{:status :ok :result %" PRId64 " :result-type :%s "
             ":result-tag %s :result-word %" PRId64
             " :fuel {:initial 512 :remaining %" PRIu64
             "} :heap {:capacity 4096 :used %" PRIu64 "}}\n",
             shared->result, result_type, tag == 1 ? "true" : "false", payload,
             shared->context.fuel, shared->pair_used);
    } else if (variant_case_count > 0) {
      int64_t ordinal, payload;
      if (!inspect_variant_result(shared, shared->result, variant_case_count,
                                  variant_bool_mask, &ordinal, &payload)) {
        static const char trap[] =
            "KEXE_TRAP {:kind :result :reason :invalid-variant}\n";
        write_stderr_checked(trap, sizeof(trap) - 1u);
        printf("{:status :trap :exit 130 :fuel {:initial 512 :remaining %" PRIu64
               "} :heap {:capacity 4096 :used %" PRIu64 "}}\n",
               shared->context.fuel, shared->pair_used);
        return 130;
      }
      printf("{:status :ok :result %" PRId64
             " :result-type :variant :result-ordinal %" PRId64
             " :result-word %" PRId64
             " :fuel {:initial 512 :remaining %" PRIu64
             "} :heap {:capacity 4096 :used %" PRIu64 "}}\n",
             shared->result, ordinal, payload, shared->context.fuel,
             shared->pair_used);
    } else {
      printf("{:status :ok :result %" PRId64
             " :fuel {:initial 512 :remaining %" PRIu64
             "} :heap {:capacity 4096 :used %" PRIu64 "}}\n",
             shared->result, shared->context.fuel, shared->pair_used);
    }
  } else {
    printf("{:status :trap :exit %d :fuel {:initial 512 :remaining %" PRIu64
           "} :heap {:capacity 4096 :used %" PRIu64 "}}\n",
           child_status, shared->context.fuel, shared->pair_used);
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
#define ALLOW_SYSCALL(number) \
  BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, (number), 0, 1), \
  BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW)

static void install_syscall_sandbox(void) {
#if defined(__x86_64__)
  const uint32_t expected_arch = AUDIT_ARCH_X86_64;
#elif defined(__aarch64__)
  const uint32_t expected_arch = AUDIT_ARCH_AARCH64;
#else
#error "unsupported Linux architecture for KEXE seccomp"
#endif
  struct sock_filter filter[] = {
      BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, arch)),
      BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, expected_arch, 1, 0),
      BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),
      BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, nr)),
      ALLOW_SYSCALL(__NR_write),
      ALLOW_SYSCALL(__NR_exit),
      ALLOW_SYSCALL(__NR_exit_group),
      ALLOW_SYSCALL(__NR_rt_sigreturn),
      ALLOW_SYSCALL(__NR_rt_sigprocmask),
      ALLOW_SYSCALL(__NR_getpid),
      ALLOW_SYSCALL(__NR_gettid),
      ALLOW_SYSCALL(__NR_tgkill),
      ALLOW_SYSCALL(__NR_munmap),
      ALLOW_SYSCALL(__NR_brk),
      ALLOW_SYSCALL(__NR_clock_gettime),
      BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_TRAP),
  };
  struct sock_fprog program = {
      .len = (unsigned short)(sizeof(filter) / sizeof(filter[0])),
      .filter = filter,
  };
  if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0) fail("no_new_privs");
  if (prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &program) != 0) fail("seccomp");
}
#elif defined(__APPLE__) && !defined(KEXE_SANITIZER_TEST)
static void install_syscall_sandbox(void) {
  static const char profile[] =
      "(version 1)"
      "(deny default)"
      "(allow file-write-data)"
      "(allow signal (target self))"
      "(allow process-info-pidinfo)"
      "(allow process-info-setcontrol)"
      "(allow sysctl-read)";
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
  if (argc < 6 || argc > 11) {
    fprintf(stderr, "usage: kexe-loader <raw-code> <offset> <arity> <x86_64|aarch64> <allow-csv|-> [i64 ...]\n");
    return 2;
  }
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
  struct kexe_shared_v3 *shared =
      mmap(NULL, sizeof(*shared), PROT_READ | PROT_WRITE,
           MAP_SHARED | MAP_ANONYMOUS, -1, 0);
  if (shared == MAP_FAILED) fail("mmap shared execution state");
  memset(shared, 0, sizeof(*shared));
  shared->context.version = 3;
  shared->context.fuel = 512;
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
  shared->context.code_base = (const uint8_t *)memory;
  shared->context.code_length = (uint64_t)length;
  if (parse_allow(argv[5], shared->context.allow) != 0) return 2;
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
  if (!structured_report) write_i64(result);

  if (munmap(memory, mapped) != 0) fail("munmap");
  if (munmap(shared, sizeof(*shared)) != 0) fail("shared munmap");
  _exit(0);
}
