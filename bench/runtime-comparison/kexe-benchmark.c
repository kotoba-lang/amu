#define _GNU_SOURCE

#include <errno.h>
#include <dlfcn.h>
#include <fcntl.h>
#include <inttypes.h>
#include <signal.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#if defined(__aarch64__)
#include <arm_neon.h>
#elif defined(__SSE2__)
#include <emmintrin.h>
#endif

typedef int64_t (*kexe_fn8)(int64_t, int64_t, int64_t, int64_t, int64_t,
                            int64_t, int64_t, int64_t);

static const char *const native_artifact_abi =
    "kotoba.native-artifact-i64x8-to-i64-indirect/v1";

/* The benchmark context now carries the pair/string slots of the real v3
 * contract (ABI offsets asserted below, mirroring tools/kexe_loader.c), so
 * string-bearing kernels can run under the same harness as arithmetic ones.
 * kgraph/cap slots stay NULL: a guest touching them crashes loudly
 * instead of being silently mis-measured. This remains benchmark
 * scaffolding, not an alternate production loader or safety boundary. */
struct kexe_context_v3 {
  uint64_t version;
  uint64_t fuel;
  uint64_t allow[4];
  int64_t (*cap_call)(struct kexe_context_v3 *, uint64_t, int64_t);
  int64_t (*pair_new)(struct kexe_context_v3 *, int64_t, int64_t);
  int64_t (*pair_first)(struct kexe_context_v3 *, int64_t);
  int64_t (*pair_second)(struct kexe_context_v3 *, int64_t);
  int64_t (*kgraph_assert)(struct kexe_context_v3 *, int64_t, int64_t, int64_t);
  int64_t (*kgraph_get)(struct kexe_context_v3 *, int64_t, int64_t);
  int64_t (*kgraph_count)(struct kexe_context_v3 *, int64_t);
  int64_t (*kgraph_entity_at)(struct kexe_context_v3 *, int64_t, int64_t);
  int64_t (*string_equal)(struct kexe_context_v3 *, int64_t, int64_t);
  int64_t (*string_concat)(struct kexe_context_v3 *, int64_t, int64_t);
  int64_t (*typed_cap_call)(struct kexe_context_v3 *, uint64_t, uint64_t,
                            uint64_t, int64_t);
  int64_t (*string_substring)(struct kexe_context_v3 *, int64_t, int64_t,
                              int64_t);
  int64_t (*string_code_point_at)(struct kexe_context_v3 *, int64_t, int64_t);
  int64_t (*vector_new_empty)(struct kexe_context_v3 *);
  int64_t (*vector_conj)(struct kexe_context_v3 *, int64_t, int64_t);
  int64_t (*vector_count)(struct kexe_context_v3 *, int64_t);
  int64_t (*vector_at)(struct kexe_context_v3 *, int64_t, int64_t);
  int64_t (*vector_assoc)(struct kexe_context_v3 *, int64_t, int64_t, int64_t);
  int64_t (*vector_drop)(struct kexe_context_v3 *, int64_t, int64_t);
  const uint8_t *code_base;
  uint64_t code_length;
};

_Static_assert(offsetof(struct kexe_context_v3, fuel) == 8, "fuel ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, allow) == 16, "allow ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, cap_call) == 48, "cap ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, pair_new) == 56, "pair ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, pair_first) == 64, "pair ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, pair_second) == 72, "pair ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, string_equal) == 112, "string ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, string_concat) == 120, "string ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, typed_cap_call) == 128, "typed cap ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, string_substring) == 136, "string ABI drift");
_Static_assert(offsetof(struct kexe_context_v3, string_code_point_at) == 144, "string ABI drift");

#define BENCH_PAIR_CAPACITY 4096u
#define BENCH_STRING_POOL_BYTES 65536u
#define BENCH_VECTOR_CAPACITY 4096u
#define BENCH_VECTOR_ITEM_CAPACITY 65536u

struct kexe_pair_v1 { int64_t first; int64_t second; };
struct kexe_vector_v1 { uint64_t offset; uint64_t length; };

struct bench_shared {
  struct kexe_context_v3 context;
  uint64_t pair_used;
  struct kexe_pair_v1 pairs[BENCH_PAIR_CAPACITY];
  uint64_t string_pool_used;
  uint8_t string_pool[BENCH_STRING_POOL_BYTES];
  uint64_t vector_used;
  struct kexe_vector_v1 vectors[BENCH_VECTOR_CAPACITY];
  uint64_t vector_item_used;
  int64_t vector_items[BENCH_VECTOR_ITEM_CAPACITY];
};

/* pair/string machinery ported from tools/kexe_loader.c: same trapping
 * behaviour (raise(SIGILL) on contract violation), same one-byte-space
 * addressing (non-negative offsets index code+literal data, negative
 * offsets index the dynamic pool via -offset - 1). */

static int64_t checked_pair_new(struct kexe_context_v3 *context,
                                int64_t first, int64_t second) {
  struct bench_shared *shared = (struct bench_shared *)context;
  if (context == NULL || context->version != 3 ||
      shared->pair_used >= BENCH_PAIR_CAPACITY) {
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
  struct bench_shared *shared = (struct bench_shared *)context;
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

static const uint8_t *resolve_string_bytes(struct kexe_context_v3 *context,
                                           int64_t offset, int64_t length) {
  struct bench_shared *shared = (struct bench_shared *)context;
  if (length < 0) { raise(SIGILL); return NULL; }
  if (offset >= 0) {
    if ((uint64_t)offset + (uint64_t)length > context->code_length) {
      raise(SIGILL);
      return NULL;
    }
    return context->code_base + offset;
  }
  uint64_t pool_offset = (uint64_t)(-(offset + 1));
  if (pool_offset + (uint64_t)length > BENCH_STRING_POOL_BYTES ||
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
  return simd_bytes_equal(a, b, (size_t)length_a) ? 1 : 0;
}

static int64_t checked_string_concat(struct kexe_context_v3 *context,
                                     int64_t handle_a, int64_t handle_b) {
  struct bench_shared *shared = (struct bench_shared *)context;
  if (context == NULL || context->version != 3) { raise(SIGILL); return 0; }
  int64_t offset_a = checked_pair_get(context, handle_a, 0);
  int64_t length_a = checked_pair_get(context, handle_a, 1);
  int64_t offset_b = checked_pair_get(context, handle_b, 0);
  int64_t length_b = checked_pair_get(context, handle_b, 1);
  if (length_a < 0 || length_b < 0 || length_a > INT64_MAX - length_b) {
    raise(SIGILL);
    return 0;
  }
  int64_t total = length_a + length_b;
  if (shared->string_pool_used + (uint64_t)total > BENCH_STRING_POOL_BYTES ||
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
  int64_t result_offset = offset >= 0 ? offset + start : offset - start;
  return checked_pair_new(context, result_offset, end - start);
}

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

/* vector-i64/f64 machinery ported from tools/kexe_loader.c: handles are
 * immutable values over a shared arena; conj appends in place only when the
 * slice already ends at the arena top, and copies otherwise. */

static struct kexe_vector_v1 *resolve_vector(struct bench_shared *shared,
                                             int64_t handle) {
  if (handle <= 0 || (uint64_t)handle > shared->vector_used) return NULL;
  return &shared->vectors[(uint64_t)handle - 1];
}

static int64_t intern_vector(struct bench_shared *shared,
                             uint64_t offset, uint64_t length) {
  if (shared->vector_used >= BENCH_VECTOR_CAPACITY) return 0;
  uint64_t index = shared->vector_used++;
  shared->vectors[index].offset = offset;
  shared->vectors[index].length = length;
  return (int64_t)(index + 1);
}

static int64_t checked_vector_new_empty(struct kexe_context_v3 *context) {
  struct bench_shared *shared = (struct bench_shared *)context;
  if (context == NULL || context->version != 3) { raise(SIGILL); return 0; }
  int64_t handle = intern_vector(shared, shared->vector_item_used, 0);
  if (handle == 0) { raise(SIGILL); return 0; }
  return handle;
}

static int64_t checked_vector_count(struct kexe_context_v3 *context,
                                    int64_t handle) {
  struct bench_shared *shared = (struct bench_shared *)context;
  if (context == NULL || context->version != 3) { raise(SIGILL); return 0; }
  struct kexe_vector_v1 *vector = resolve_vector(shared, handle);
  if (vector == NULL) { raise(SIGILL); return 0; }
  return (int64_t)vector->length;
}

static int64_t checked_vector_at(struct kexe_context_v3 *context,
                                 int64_t handle, int64_t index) {
  struct bench_shared *shared = (struct bench_shared *)context;
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
  struct bench_shared *shared = (struct bench_shared *)context;
  if (context == NULL || context->version != 3) { raise(SIGILL); return 0; }
  struct kexe_vector_v1 *vector = resolve_vector(shared, handle);
  if (vector == NULL) { raise(SIGILL); return 0; }
  uint64_t offset = vector->offset;
  uint64_t length = vector->length;
  if (length >= 16384u) { raise(SIGILL); return 0; }
  if (offset + length != shared->vector_item_used) {
    if (shared->vector_item_used + length + 1u > BENCH_VECTOR_ITEM_CAPACITY) {
      raise(SIGILL);
      return 0;
    }
    uint64_t destination = shared->vector_item_used;
    memmove(&shared->vector_items[destination], &shared->vector_items[offset],
            (size_t)length * sizeof(int64_t));
    shared->vector_item_used += length;
    offset = destination;
  }
  if (shared->vector_item_used >= BENCH_VECTOR_ITEM_CAPACITY) {
    raise(SIGILL);
    return 0;
  }
  shared->vector_items[shared->vector_item_used++] = item;
  int64_t result = intern_vector(shared, offset, length + 1u);
  if (result == 0) { raise(SIGILL); return 0; }
  return result;
}

static int64_t checked_vector_assoc(struct kexe_context_v3 *context,
                                    int64_t handle, int64_t index,
                                    int64_t item) {
  struct bench_shared *shared = (struct bench_shared *)context;
  if (context == NULL || context->version != 3) { raise(SIGILL); return 0; }
  struct kexe_vector_v1 *vector = resolve_vector(shared, handle);
  if (vector == NULL || index < 0 || (uint64_t)index >= vector->length) {
    raise(SIGILL);
    return 0;
  }
  uint64_t offset = vector->offset;
  uint64_t length = vector->length;
  if (shared->vector_item_used + length > BENCH_VECTOR_ITEM_CAPACITY) {
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

static int64_t checked_vector_drop(struct kexe_context_v3 *context,
                                   int64_t handle, int64_t count) {
  struct bench_shared *shared = (struct bench_shared *)context;
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

static void fail(const char *operation) {
  perror(operation);
  exit(1);
}

static uint64_t bounded(const char *text, const char *name, int allow_zero,
                        uint64_t maximum) {
  if (text == NULL || *text < '0' || *text > '9') {
    fprintf(stderr, "%s must be a decimal integer\n", name);
    exit(2);
  }
  char *end = NULL;
  errno = 0;
  unsigned long long value = strtoull(text, &end, 10);
  if (errno == ERANGE || *end != '\0' || (!allow_zero && value == 0) ||
      value > maximum) {
    fprintf(stderr, "%s is outside the admitted range\n", name);
    exit(2);
  }
  return (uint64_t)value;
}

static uint64_t nanoseconds(void) {
  struct timespec value;
  if (clock_gettime(CLOCK_MONOTONIC, &value) != 0) fail("clock_gettime");
  return (uint64_t)value.tv_sec * UINT64_C(1000000000) +
         (uint64_t)value.tv_nsec;
}

/* Resolve isa once. strcmp inside the timed loop was ~5 ns on a 4-byte
 * `ret` identity (codegen co-scientist iteration 13). That is harness
 * overhead, not guest work. Fuel is still stored every call so recursive
 * exports keep a bound; a leaf does not read it. Pair and string-pool
 * cursors are likewise reset every call: each timed call runs as a fresh
 * instance, which is also what keeps a million-call loop from exhausting
 * the bounded arenas. */

static struct bench_shared shared;

int main(int argc, char **argv) {
  if (argc != 9) {
    fprintf(stderr,
            "usage: kexe-benchmark <raw|dylib> <artifact> <entry> <isa> <n> <calls> <warmup> <fuel>\n");
    return 2;
  }
  int raw = strcmp(argv[1], "raw") == 0;
  int dylib = strcmp(argv[1], "dylib") == 0;
  if (!raw && !dylib) {
    fprintf(stderr, "artifact kind must be raw or dylib\n");
    return 2;
  }
  int aarch64 = strcmp(argv[4], "aarch64") == 0;
  if (!aarch64 && strcmp(argv[4], "x86_64") != 0) {
    fprintf(stderr, "isa must be x86_64 or aarch64\n");
    return 2;
  }
  int64_t input = (int64_t)bounded(argv[5], "n", 1, UINT64_C(2147483646));
  uint64_t calls = bounded(argv[6], "calls", 0, UINT64_C(100000000));
  uint64_t warmup = bounded(argv[7], "warmup", 1, UINT64_C(100000000));
  uint64_t fuel = bounded(argv[8], "fuel", 0, UINT64_C(1048576));
  size_t mapped = 0;
  size_t artifact_bytes = 0;
  void *memory = NULL;
  void *library = NULL;
  kexe_fn8 fn = NULL;
  if (raw) {
    uint64_t offset = bounded(argv[3], "offset", 1, UINT64_MAX);
    int fd = open(argv[2], O_RDONLY);
    if (fd < 0) fail("open");
    struct stat metadata;
    if (fstat(fd, &metadata) != 0) fail("fstat");
    if (metadata.st_size <= 0 || offset >= (uint64_t)metadata.st_size) {
      fprintf(stderr, "offset outside code artifact\n");
      return 2;
    }
    long page = sysconf(_SC_PAGESIZE);
    if (page <= 0) fail("sysconf");
    artifact_bytes = (size_t)metadata.st_size;
    mapped = (artifact_bytes + (size_t)page - 1) /
             (size_t)page * (size_t)page;
#if defined(MAP_ANONYMOUS)
    int anonymous = MAP_ANONYMOUS;
#else
    int anonymous = MAP_ANON;
#endif
    memory = mmap(NULL, mapped, PROT_READ | PROT_WRITE,
                  MAP_PRIVATE | anonymous, -1, 0);
    if (memory == MAP_FAILED) fail("mmap");
    size_t consumed = 0;
    while (consumed < artifact_bytes) {
      ssize_t count = read(fd, (uint8_t *)memory + consumed,
                           artifact_bytes - consumed);
      if (count <= 0) fail("read");
      consumed += (size_t)count;
    }
    if (close(fd) != 0) fail("close");
    if (mprotect(memory, mapped, PROT_READ | PROT_EXEC) != 0) fail("mprotect");
    fn = (kexe_fn8)((uint8_t *)memory + offset);
  } else {
    library = dlopen(argv[2], RTLD_NOW | RTLD_LOCAL);
    if (library == NULL) {
      fprintf(stderr, "dlopen: %s\n", dlerror());
      return 1;
    }
    dlerror();
    fn = (kexe_fn8)dlsym(library, argv[3]);
    const char *symbol_error = dlerror();
    if (symbol_error != NULL) {
      fprintf(stderr, "dlsym: %s\n", symbol_error);
      return 1;
    }
  }

  memset(&shared, 0, sizeof(shared));
  struct kexe_context_v3 *context = &shared.context;
  context->version = 3;
  context->pair_new = checked_pair_new;
  context->pair_first = checked_pair_first;
  context->pair_second = checked_pair_second;
  context->string_equal = checked_string_equal;
  context->string_concat = checked_string_concat;
  context->string_substring = checked_string_substring;
  context->string_code_point_at = checked_string_code_point_at;
  context->vector_new_empty = checked_vector_new_empty;
  context->vector_conj = checked_vector_conj;
  context->vector_count = checked_vector_count;
  context->vector_at = checked_vector_at;
  context->vector_assoc = checked_vector_assoc;
  context->vector_drop = checked_vector_drop;
  /* String literals resolve into the mapped artifact itself: raw extraction
   * appends literal data past the last function's code, so the whole file is
   * the code+literal-data region. dylib twins are plain C and never receive
   * this context, so the zero length there just means any stray string call
   * traps instead of reading wild memory. */
  context->code_base = (const uint8_t *)memory;
  context->code_length = raw ? (uint64_t)artifact_bytes : 0;
  int64_t result = 0;
  uint64_t started;
  uint64_t elapsed;
  for (uint64_t index = 0; index < warmup; index++) {
    context->fuel = fuel;
    shared.pair_used = 0;
    shared.string_pool_used = 0;
    shared.vector_used = 0;
    shared.vector_item_used = 0;
    if (aarch64) {
      result = fn(input, 0, 0, 0, 0, 0, 0, (int64_t)(uintptr_t)context);
    } else {
      result = fn(input, 0, 0, 0, 0, (int64_t)(uintptr_t)context, 0, 0);
    }
  }
  started = nanoseconds();
  for (uint64_t index = 0; index < calls; index++) {
    context->fuel = fuel;
    shared.pair_used = 0;
    shared.string_pool_used = 0;
    shared.vector_used = 0;
    shared.vector_item_used = 0;
    if (aarch64) {
      result = fn(input, 0, 0, 0, 0, 0, 0, (int64_t)(uintptr_t)context);
    } else {
      result = fn(input, 0, 0, 0, 0, (int64_t)(uintptr_t)context, 0, 0);
    }
  }
  elapsed = nanoseconds() - started;
  uint64_t context_fuel_after = context->fuel;
  uint64_t context_fuel_consumed = fuel >= context_fuel_after
                                     ? fuel - context_fuel_after : 0;
  struct rusage usage;
  if (getrusage(RUSAGE_SELF, &usage) != 0) fail("getrusage");
#if defined(__APPLE__)
  uint64_t rss = (uint64_t)usage.ru_maxrss;
#else
  uint64_t rss = (uint64_t)usage.ru_maxrss * UINT64_C(1024);
#endif
  printf("{\"format\":\"kotoba.runtime-sample/v1\","
         "\"calls\":%" PRIu64 ",\"warmupCalls\":%" PRIu64 ","
         "\"elapsedNanoseconds\":%" PRIu64 ",\"result\":%" PRId64 ","
         "\"maxRssBytes\":%" PRIu64 ",\"fuelPerCall\":%" PRIu64 ","
         "\"contextFuelBefore\":%" PRIu64 ",\"contextFuelAfter\":%" PRIu64 ","
         "\"contextFuelConsumed\":%" PRIu64 ","
         "\"nativeArtifactAbi\":\"%s\",\"artifactKind\":\"%s\"}\n",
         calls, warmup, elapsed, result, rss, fuel, fuel, context_fuel_after,
         context_fuel_consumed, native_artifact_abi,
         raw ? "raw" : "dylib");
  if (raw && munmap(memory, mapped) != 0) fail("munmap");
  if (dylib && dlclose(library) != 0) fail("dlclose");
  return 0;
}
