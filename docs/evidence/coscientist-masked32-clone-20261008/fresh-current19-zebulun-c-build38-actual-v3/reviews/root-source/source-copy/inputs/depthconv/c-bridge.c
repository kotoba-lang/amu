/* BOOTSTRAP-TOOL: matched batch boundary around unchanged upstream C. */
#include <stdint.h>
#include <limits.h>
#define GLOBAL_SCALE_FACTOR 1
#include "../upstream/src/depthconv/depthconv.c"
int64_t batch(int64_t n,int64_t a,int64_t b,int64_t c,int64_t d,int64_t e,int64_t f,int64_t ctx) {
  (void)a;(void)b;(void)c;(void)d;(void)e;(void)f;(void)ctx;
  if (n < 1 || n > UINT_MAX) return 0;
  return verify_benchmark(benchmark_body(1,(unsigned int)n));
}
int64_t channel(int64_t n,int64_t a,int64_t b,int64_t c,int64_t d,int64_t e,int64_t f,int64_t ctx) {
  (void)a;(void)b;(void)c;(void)d;(void)e;(void)f;(void)ctx;
  if (n < 0 || n >= 32) return 0;
  benchmark_body(1,1);
  return OUTPUT_DATA[n];
}
