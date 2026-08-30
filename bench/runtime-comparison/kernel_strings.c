/* C twin of kernel_strings.kotoba: same chunk/view + build-by-append + byte
 * scan + head compare, written the way a C programmer writes it (pointer
 * views, memcpy append, direct byte walk). Exported through the same
 * eight-i64 indirect-call ABI the benchmark runner times. */
#include <stdint.h>
#include <string.h>

static int64_t imod(int64_t x, int64_t m) { return x - (x / m) * m; }

int64_t kernel(int64_t n, int64_t a1, int64_t a2, int64_t a3, int64_t a4,
               int64_t a5, int64_t a6, int64_t a7) {
  (void)a1; (void)a2; (void)a3; (void)a4; (void)a5; (void)a6; (void)a7;
  static const char base[] =
      "the quick brown fox jumps over the lazy dog 0123456789";
  int64_t r16 = imod(n, 16);
  int64_t r8 = imod(n, 8);
  const char *chunk = base + r16;
  char s[256];
  int64_t len = 0;
  for (int64_t k = 8 + r8; k > 0; k--) {
    memcpy(s + len, chunk, 8);
    len += 8;
  }
  int64_t h = 7;
  for (int64_t i = 0; i < len; i++) {
    h = imod(h * 31 + (int64_t)(unsigned char)s[i], 1000003);
  }
  return memcmp(chunk, s, 8) == 0 ? h : -h;
}
