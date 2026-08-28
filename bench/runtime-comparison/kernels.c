#include <stdint.h>

#if defined(__GNUC__)
#define NOINLINE __attribute__((noinline))
#else
#define NOINLINE
#endif

static inline int64_t step_inline(int64_t x) {
  const int64_t value = x * INT64_C(48271) + INT64_C(1);
  return value - (value / INT64_C(2147483647)) * INT64_C(2147483647);
}

NOINLINE int64_t kotoba_bench_step_c(int64_t x) {
#if defined(__GNUC__)
  __asm__ volatile("" : "+r"(x));
#endif
  return step_inline(x);
}

NOINLINE int64_t kotoba_bench_id_c(int64_t x) {
#if defined(__GNUC__)
  __asm__ volatile("" : "+r"(x));
#endif
  return x;
}

#define ABI_ARGS int64_t n, int64_t a1, int64_t a2, int64_t a3, int64_t a4, int64_t a5, int64_t a6, int64_t a7
#define IGNORE_ARGS (void)a1; (void)a2; (void)a3; (void)a4; (void)a5; (void)a6; (void)a7

NOINLINE int64_t kotoba_bench_kernel(ABI_ARGS) {
  IGNORE_ARGS;
  int64_t x = n;
  x = step_inline(x); x = step_inline(x); x = step_inline(x); x = step_inline(x);
  x = step_inline(x); x = step_inline(x); x = step_inline(x); x = step_inline(x);
  return x;
}

NOINLINE int64_t kotoba_bench_kernel_wide(ABI_ARGS) {
  IGNORE_ARGS;
  const int64_t a = step_inline(step_inline(n));
  const int64_t b = step_inline(step_inline(n + 1));
  const int64_t c = step_inline(step_inline(n + 2));
  const int64_t d = step_inline(step_inline(n + 3));
  const int64_t e = step_inline(step_inline(n + 4));
  const int64_t f = step_inline(step_inline(n + 5));
  const int64_t g = step_inline(step_inline(n + 6));
  const int64_t h = step_inline(step_inline(n + 7));
  return a + b + c + d + e + f + g + h;
}

NOINLINE int64_t kotoba_bench_kernel_deep(ABI_ARGS) {
  IGNORE_ARGS;
  const int64_t a = step_inline(n + 0), b = step_inline(n + 1);
  const int64_t c = step_inline(n + 2), d = step_inline(n + 3);
  const int64_t e = step_inline(n + 4), f = step_inline(n + 5);
  const int64_t g = step_inline(n + 6), h = step_inline(n + 7);
  const int64_t i = step_inline(n + 8), j = step_inline(n + 9);
  const int64_t k = step_inline(n + 10), l = step_inline(n + 11);
  const int64_t m = step_inline(n + 12), shadow_n = step_inline(n + 13);
  const int64_t o = step_inline(shadow_n + 14), p = step_inline(shadow_n + 15);
  const int64_t q = step_inline(shadow_n + 16), r = step_inline(shadow_n + 17);
  const int64_t s = step_inline(shadow_n + 18), t = step_inline(shadow_n + 19);
  const int64_t u = step_inline(shadow_n + 20), v = step_inline(shadow_n + 21);
  const int64_t w = step_inline(shadow_n + 22), x = step_inline(shadow_n + 23);
  return a+b+c+d+e+f+g+h+i+j+k+l+m+shadow_n+o+p+q+r+s+t+u+v+w+x;
}

static int64_t call_sum(int64_t n) {
  const int64_t a = kotoba_bench_step_c(n), b = kotoba_bench_step_c(n + 1);
  const int64_t c = kotoba_bench_step_c(n + 2), d = kotoba_bench_step_c(n + 3);
  const int64_t e = kotoba_bench_step_c(a), f = kotoba_bench_step_c(b);
  const int64_t g = kotoba_bench_step_c(c), h = kotoba_bench_step_c(d);
  return a+b+c+d+e+f+g+h;
}

NOINLINE int64_t kotoba_bench_kernel_call(ABI_ARGS) {
  IGNORE_ARGS;
  return call_sum(n);
}

NOINLINE int64_t kotoba_bench_kernel_call_branch(ABI_ARGS) {
  IGNORE_ARGS;
  const int64_t result = call_sum(n);
  return n == 0 ? 0 : result;
}

NOINLINE int64_t kotoba_bench_kernel_loop_call(ABI_ARGS) {
  IGNORE_ARGS;
  int64_t i = n, acc = 0;
  while (i != 0) { acc += kotoba_bench_id_c(1); i -= 1; }
  return acc;
}
