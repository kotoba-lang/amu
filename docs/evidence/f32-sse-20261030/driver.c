/* JUN-633 slice 3 (ADR 0391): kotoba_aiueos_fop (fops.kotoba through the aiueos object route) against the same
   operation in C, compiled by zig cc for x86_64 with SSE (no -ffast-math, no FMA contraction), bit for bit. */
#include <stdint.h>
int64_t kotoba_aiueos_fop(int64_t op, int64_t x, int64_t y);
static void putc_(char c) { __asm__ volatile("outb %0, %1" :: "a"(c), "Nd"((uint16_t)0xe9)); }
static void puts_(const char *s) { while (*s) putc_(*s++); }
static void hex(uint64_t v, int n) { for (int i = n - 1; i >= 0; i--) putc_("0123456789abcdef"[(v >> (4 * i)) & 15]); putc_(' '); }
static float F(int64_t x) { union { uint32_t u; float f; } c; c.u = (uint32_t)x; return c.f; }
static double D(int64_t x) { union { uint64_t u; double d; } c; c.u = (uint64_t)x; return c.d; }
static int64_t FB(float f) { union { uint32_t u; float f; } c; c.f = f; return (int64_t)(int32_t)c.u; }
static int64_t DB(double d) { union { uint64_t u; double d; } c; c.d = d; return (int64_t)c.u; }
static int64_t cref(int op, int64_t x, int64_t y) {
  float a = F(x), b = F(y); double p = D(x), q = D(y);
  switch (op) {
  case 0: return FB(a + b); case 1: return FB(a - b); case 2: return FB(a * b); case 3: return FB(a / b);
  case 4: return DB(p + q); case 5: return DB(p - q); case 6: return DB(p * q); case 7: return DB(p / q);
  case 8: return a == b; case 9: return a < b; case 10: return a <= b; case 11: return a > b; case 12: return a >= b;
  case 13: return __builtin_isunordered(a, b);
  case 14: return p == q; case 15: return p < q; case 16: return p <= q; case 17: return p > q; case 18: return p >= q;
  case 19: return __builtin_isunordered(p, q);
  case 20: return FB(-a); case 21: return FB(__builtin_fabsf(a)); case 22: return FB(__builtin_sqrtf(a));
  case 23: return DB(-p); case 24: return DB(__builtin_fabs(p)); case 25: return DB(__builtin_sqrt(p));
  case 26: return FB((float)x); case 27: return DB((double)x);
  case 28: return FB((float)p); case 29: return DB((double)a);
  }
  return -1;
}
static const uint32_t S32[] = {0, 0x80000000u, 0x3f800000u, 0xbf800000u, 0x7f800000u, 0xff800000u, 0x7fc00000u, 0xffc00000u,
  0x7fa00001u, 0xffa12345u, 0x7fc12345u, 0x00000001u, 0x807fffffu, 0x00800000u, 0x7f7fffffu, 0xff7fffffu, 0x3dcccccdu,
  0x4b800000u, 0xc0490fdbu, 0x33800000u, 0x3f800001u, 0x40000000u};
static const uint64_t S64[] = {0, 0x8000000000000000ull, 0x3ff0000000000000ull, 0xbff0000000000000ull, 0x7ff0000000000000ull,
  0xfff0000000000000ull, 0x7ff8000000000000ull, 0xfff8000000000000ull, 0x7ff4000000000001ull, 0xfff4000000012345ull,
  0x7ff8000000012345ull, 1, 0x800fffffffffffffull, 0x0010000000000000ull, 0x7fefffffffffffffull, 0xffefffffffffffffull,
  0x3fb999999999999aull, 0x47efffffe0000000ull, 0x47efffffefffffffull, 0x36a0000000000000ull, 0x3810000000000000ull,
  0x380fffffffffffffull, 0xc00921fb54442d18ull, 0x3ff0000010000000ull};
static const uint64_t SI[] = {0, 1, (uint64_t)-1, (1ull << 53) + 1, 0x7fffffffffffffffull, 0x8000000000000000ull,
  (1ull << 24) + 1, (1ull << 24) + 3, 0x7fffff8000000000ull, 0xfffffffffffffff1ull};
static uint64_t seed = 633;
static uint64_t rnd(void) { seed = seed * 6364136223846793005ull + 1442695040888963407ull; return seed ^ (seed >> 29); }
static unsigned cases[30], diffs[30];
static void one(int op, int64_t x, int64_t y) {
  int64_t k = kotoba_aiueos_fop(op, x, y), c = cref(op, x, y);
  cases[op]++;
  if (k != c) { if (diffs[op]++ < 3) { puts_("DIFF "); hex(op, 2); hex(x, 16); hex(y, 16); hex(k, 16); hex(c, 16); putc_('\n'); } }
}
static int is32(int op) { return op < 4 || (op >= 8 && op <= 13) || (op >= 20 && op <= 22) || op == 29; }
void test_main(void) {
  puts_("F32SSE\n");
  unsigned n32 = sizeof S32 / sizeof S32[0], n64 = sizeof S64 / sizeof S64[0], ni = sizeof SI / sizeof SI[0];
  for (int op = 0; op < 30; op++) {
    if (op == 26 || op == 27) {
      for (unsigned i = 0; i < ni; i++) one(op, (int64_t)SI[i], 0);
      for (unsigned i = 0; i < 20000; i++) { uint64_t r = rnd(); one(op, (int64_t)(r >> (r & 63)) * ((r & 64) ? -1 : 1), 0); }
    } else if (is32(op)) {
      for (unsigned i = 0; i < n32; i++) for (unsigned j = 0; j < n32; j++) one(op, (int32_t)S32[i], (int32_t)S32[j]);
      for (unsigned i = 0; i < 20000; i++) one(op, (int32_t)(uint32_t)rnd(), (int32_t)(uint32_t)rnd());
      for (unsigned i = 0; i < 5000; i++) { uint32_t a = (uint32_t)rnd(); one(op, (int32_t)a, (int32_t)(a ^ (uint32_t)(rnd() & 0x3ff))); }
    } else {
      for (unsigned i = 0; i < n64; i++) for (unsigned j = 0; j < n64; j++) one(op, (int64_t)S64[i], (int64_t)S64[j]);
      for (unsigned i = 0; i < 20000; i++) one(op, (int64_t)rnd(), (int64_t)rnd());
      for (unsigned i = 0; i < 5000; i++) { uint64_t a = rnd(); one(op, (int64_t)a, (int64_t)(a ^ (rnd() & 0xfffff))); }
    }
  }
  unsigned tc = 0, td = 0;
  for (int op = 0; op < 30; op++) { tc += cases[op]; td += diffs[op]; }
  puts_("OPS 1e CASES "); hex(tc, 6); puts_("DIFFS "); hex(td, 6); putc_('\n');
  for (int op = 0; op < 30; op++) { hex(op, 2); hex(cases[op], 5); hex(diffs[op], 4); putc_('\n'); }
  puts_("DONE\n");
}
