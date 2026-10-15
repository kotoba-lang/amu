#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
static uint64_t start_ns;
static uint64_t now_ns(void) {
  struct timespec t;
  if (clock_gettime(CLOCK_MONOTONIC_RAW, &t)) abort();
  return (uint64_t)t.tv_sec * 1000000000ull + t.tv_nsec;
}
void initialise_board(void) {}
void start_trigger(void) { start_ns = now_ns(); }
void stop_trigger(void) {
  uint64_t end = now_ns();
  if (end <= start_ns) abort();
  printf("EMBENCH_NS=%llu\n", (unsigned long long)(end-start_ns));
}
