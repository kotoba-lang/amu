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
#include <time.h>
#include <unistd.h>

typedef int64_t (*kexe_fn6)(int64_t, int64_t, int64_t, int64_t, int64_t,
                            int64_t);
typedef int64_t (*kexe_fn8)(int64_t, int64_t, int64_t, int64_t, int64_t,
                            int64_t, int64_t, int64_t);

/* This pure kernel consumes only version and fuel. The buffer is deliberately
 * large enough for the complete v3 context, but this remains benchmark
 * scaffolding, not an alternate production loader or safety boundary. */
struct benchmark_context_v3 {
  uint64_t version;
  uint64_t fuel;
  uint64_t remaining_context[30];
};

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
 * exports keep a bound; a leaf does not read it. */

int main(int argc, char **argv) {
  if (argc != 7) {
    fprintf(stderr,
            "usage: kexe-benchmark <raw-code> <offset> <isa> <n> <calls> <warmup>\n");
    return 2;
  }
  uint64_t offset = bounded(argv[2], "offset", 1, UINT64_MAX);
  int aarch64 = strcmp(argv[3], "aarch64") == 0;
  if (!aarch64 && strcmp(argv[3], "x86_64") != 0) {
    fprintf(stderr, "isa must be x86_64 or aarch64\n");
    return 2;
  }
  int64_t input = (int64_t)bounded(argv[4], "n", 0, UINT64_C(2147483646));
  uint64_t calls = bounded(argv[5], "calls", 0, UINT64_C(100000000));
  uint64_t warmup = bounded(argv[6], "warmup", 0, UINT64_C(100000000));
  int fd = open(argv[1], O_RDONLY);
  if (fd < 0) fail("open");
  struct stat metadata;
  if (fstat(fd, &metadata) != 0) fail("fstat");
  if (metadata.st_size <= 0 || offset >= (uint64_t)metadata.st_size) {
    fprintf(stderr, "offset outside code artifact\n");
    return 2;
  }
  long page = sysconf(_SC_PAGESIZE);
  if (page <= 0) fail("sysconf");
  size_t mapped = ((size_t)metadata.st_size + (size_t)page - 1) /
                  (size_t)page * (size_t)page;
#if defined(MAP_ANONYMOUS)
  int anonymous = MAP_ANONYMOUS;
#else
  int anonymous = MAP_ANON;
#endif
  void *memory = mmap(NULL, mapped, PROT_READ | PROT_WRITE,
                      MAP_PRIVATE | anonymous, -1, 0);
  if (memory == MAP_FAILED) fail("mmap");
  size_t consumed = 0;
  while (consumed < (size_t)metadata.st_size) {
    ssize_t count = read(fd, (uint8_t *)memory + consumed,
                         (size_t)metadata.st_size - consumed);
    if (count <= 0) fail("read");
    consumed += (size_t)count;
  }
  if (close(fd) != 0) fail("close");
  if (mprotect(memory, mapped, PROT_READ | PROT_EXEC) != 0) fail("mprotect");

  struct benchmark_context_v3 context = {0};
  context.version = 3;
  int64_t result = 0;
  uint64_t started;
  uint64_t elapsed;
  if (aarch64) {
    kexe_fn8 fn = (kexe_fn8)((uint8_t *)memory + offset);
    for (uint64_t index = 0; index < warmup; index++) {
      context.fuel = 512;
      result = fn(input, 0, 0, 0, 0, 0, 0, (int64_t)(uintptr_t)&context);
    }
    started = nanoseconds();
    for (uint64_t index = 0; index < calls; index++) {
      context.fuel = 512;
      result = fn(input, 0, 0, 0, 0, 0, 0, (int64_t)(uintptr_t)&context);
    }
    elapsed = nanoseconds() - started;
  } else {
    kexe_fn6 fn = (kexe_fn6)((uint8_t *)memory + offset);
    for (uint64_t index = 0; index < warmup; index++) {
      context.fuel = 512;
      result = fn(input, 0, 0, 0, 0, (int64_t)(uintptr_t)&context);
    }
    started = nanoseconds();
    for (uint64_t index = 0; index < calls; index++) {
      context.fuel = 512;
      result = fn(input, 0, 0, 0, 0, (int64_t)(uintptr_t)&context);
    }
    elapsed = nanoseconds() - started;
  }
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
         "\"maxRssBytes\":%" PRIu64 "}\n",
         calls, warmup, elapsed, result, rss);
  if (munmap(memory, mapped) != 0) fail("munmap");
  return 0;
}
