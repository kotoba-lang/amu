/* C twin of kernel_collections.kotoba: fill -> hash walk -> single-element
 * update -> suffix view -> second walk, written the way a C programmer
 * writes it (stack array, in-place update, pointer suffix). Same
 * eight-i64 indirect-call ABI. */
#include <stdint.h>

static int64_t imod(int64_t x, int64_t m) { return x - (x / m) * m; }

int64_t kernel(int64_t n, int64_t a1, int64_t a2, int64_t a3, int64_t a4,
               int64_t a5, int64_t a6, int64_t a7) {
  (void)a1; (void)a2; (void)a3; (void)a4; (void)a5; (void)a6; (void)a7;
  int64_t len = 48 + imod(n, 16);
  int64_t seed = 7 + imod(n, 65521);
  int64_t v[64];
  for (int64_t i = 0; i < len; i++) {
    v[i] = imod(seed * 31 + i * 17, 1000003);
  }
  int64_t s1 = 7;
  for (int64_t i = 0; i < len; i++) {
    s1 = imod(s1 * 31 + v[i], 1000003);
  }
  int64_t j = imod(s1, len);
  v[j] = imod(s1 + 13, 1000003);
  int64_t d = imod(n, 8);
  const int64_t *v3 = v + d;
  int64_t c3 = len - d;
  int64_t s2 = s1;
  for (int64_t i = 0; i < c3; i++) {
    s2 = imod(s2 * 31 + v3[i], 1000003);
  }
  return s2;
}
