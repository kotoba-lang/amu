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

struct benchmark_context_v4 {
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

int main(int argc, char **argv) {
  if (argc != 8) {
    fprintf(stderr,
            "usage: kexe-batch-benchmark <raw-code> <offset> <isa> <n> <iterations> <fuel> <expected-fuel>\n");
    return 2;
  }
  uint64_t offset = bounded(argv[2], "offset", 1, UINT64_MAX);
  int aarch64 = strcmp(argv[3], "aarch64") == 0;
  if (!aarch64 && strcmp(argv[3], "x86_64") != 0) {
    fprintf(stderr, "isa must be x86_64 or aarch64\n");
    return 2;
  }
  int64_t input = (int64_t)bounded(argv[4], "n", 0, UINT64_C(2147483646));
  uint64_t iterations = bounded(argv[5], "iterations", 0, UINT64_C(1048574));
  uint64_t fuel = bounded(argv[6], "fuel", 0, UINT64_C(1048576));
  uint64_t expected_fuel = bounded(argv[7], "expected-fuel", 0,
                                   UINT64_C(1048576));
  if (fuel != expected_fuel || fuel != iterations + UINT64_C(2)) {
    fprintf(stderr, "fuel must equal iterations + 2\n");
    return 2;
  }
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

  struct benchmark_context_v4 context = {0};
  context.version = 4;
  context.fuel = fuel;
  int64_t result;
  uint64_t started = nanoseconds();
  if (aarch64) {
    kexe_fn8 fn = (kexe_fn8)((uint8_t *)memory + offset);
    result = fn(input, (int64_t)iterations, 0, 0, 0, 0, 0,
                (int64_t)(uintptr_t)&context);
  } else {
    kexe_fn6 fn = (kexe_fn6)((uint8_t *)memory + offset);
    result = fn(input, (int64_t)iterations, 0, 0, 0,
                (int64_t)(uintptr_t)&context);
  }
  uint64_t elapsed = nanoseconds() - started;
  uint64_t consumed_fuel = fuel - context.fuel;
  struct rusage usage;
  if (getrusage(RUSAGE_SELF, &usage) != 0) fail("getrusage");
#if defined(__APPLE__)
  uint64_t rss = (uint64_t)usage.ru_maxrss;
#else
  uint64_t rss = (uint64_t)usage.ru_maxrss * UINT64_C(1024);
#endif
  printf("{\"format\":\"kotoba.runtime-sample/v1\","
         "\"calls\":1,\"warmupCalls\":0,\"iterations\":%" PRIu64 ","
         "\"hostCalls\":1,\"elapsedNanoseconds\":%" PRIu64 ","
         "\"result\":%" PRId64 ",\"maxRssBytes\":%" PRIu64 ","
         "\"fuelInitial\":%" PRIu64 ",\"fuelRemaining\":%" PRIu64 ","
         "\"fuelConsumed\":%" PRIu64 "}\n",
         iterations, elapsed, result, rss, fuel, context.fuel, consumed_fuel);
  if (munmap(memory, mapped) != 0) fail("munmap");
  return 0;
}
