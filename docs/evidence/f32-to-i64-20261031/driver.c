/* f32 -> i64 truncation on amu's native object route (f2i.o, JUN-633 slice 7, ADR 0395) against ref.c, the defined
   semantics in integer C. Each case calls the object through trapcall: either it returns (the answer must equal the
   reference's integer) or it raises #UD by ud2 (the reference must trap). An answer of 0x8000000000000000 for any
   operand other than -2^63 is counted separately (INDEF) and must be 0.
   Cases: named specials (+-0, +-denormals, +-Inf, NaNs with payloads, +-2^63 and neighbours, +-2^31 / 2^32 / 2^24 /
   2^62 and neighbours, halves, the finite extremes); for every exponent and sign the first and last 8 mantissas;
   a stride sweep of the whole 32-bit space; uniform random patterns; random in-range values. All of it twice: MXCSR at
   its reset value (round to nearest) and with RC = round up, since truncation must not depend on the rounding mode. */
#include <stdint.h>
typedef int64_t (*fn5)(uint64_t, uint64_t, uint64_t, uint64_t, uint64_t);
extern int64_t kotoba_aiueos_f32_to_i64(uint64_t);
extern int64_t trapcall(fn5 f, uint64_t a, uint64_t b, uint64_t c, uint64_t d, uint64_t e, int64_t *result);
extern int ref_f32_to_i64(uint32_t b, int64_t *out);
static void outb(uint16_t p, uint8_t v) { __asm__ volatile("outb %0, %1" :: "a"(v), "Nd"(p)); }
static void putc_(char c) { outb(0xe9, (uint8_t)c); }
static void puts_(const char *s) { while (*s) putc_(*s++); }
static void hex(uint64_t v, int n) { for (int i = n - 1; i >= 0; i--) putc_("0123456789abcdef"[(v >> (4 * i)) & 15]); putc_(' '); }
static void dec(uint64_t v) { char b[24]; int n = 0; do { b[n++] = (char)('0' + v % 10); v /= 10; } while (v); while (n) putc_(b[--n]); putc_(' '); }
static uint64_t seed = 633;
static uint64_t rnd(void) { seed = seed * 6364136223846793005ull + 1442695040888963407ull; return seed >> 17; }
static uint64_t fnv = 1469598103934665603ull;
static void mix(uint64_t v) { for (int i = 0; i < 8; i++) { fnv ^= (v >> (8 * i)) & 255; fnv *= 1099511628211ull; } }
static unsigned long cases, returned, traps, diffs, indef, shown;
static void one(uint32_t b) {
  int64_t r = 0, want = 0;
  int t = (int)trapcall((fn5)kotoba_aiueos_f32_to_i64, (uint64_t)(int64_t)(int32_t)b, 0, 0, 0, 0, &r);
  int wt = ref_f32_to_i64(b, &want);
  cases++;
  if (t) traps++; else returned++;
  mix(((uint64_t)t << 32) ^ b); if (!t) mix((uint64_t)r);
  if (!t && r == INT64_MIN && b != 0xdf000000u) indef++;
  if (t != wt || (!t && r != want)) {
    diffs++;
    if (shown++ < 12) { puts_("DIFF "); hex(b, 8); puts_(t ? "trap " : "ret "); if (!t) hex((uint64_t)r, 16);
      puts_(wt ? "want-trap" : "want "); if (!wt) hex((uint64_t)want, 16); putc_('\n'); }
  }
}
static const uint32_t SPECIAL[] = {
  0x00000000u, 0x80000000u,                                     /* +-0 */
  0x00000001u, 0x00000002u, 0x003fffffu, 0x00400000u, 0x007fffffu, /* +denormals */
  0x80000001u, 0x80000002u, 0x803fffffu, 0x80400000u, 0x807fffffu, /* -denormals */
  0x00800000u, 0x80800000u, 0x3effffffu, 0x3f000000u, 0xbf000000u, 0x3f7fffffu, 0xbf7fffffu,
  0x3f800000u, 0xbf800000u, 0x3fc00000u, 0xbfc00000u, 0x40200000u, 0xc0200000u, 0x40600000u, 0xc0600000u,
  0x7f800000u, 0xff800000u,                                     /* +-Inf */
  0x7fc00000u, 0xffc00000u, 0x7fc00001u, 0x7fc12345u, 0xffe5a5a5u, 0x7fffffffu, 0xffffffffu,  /* quiet NaNs */
  0x7f800001u, 0xff800001u, 0x7f812345u, 0x7fbfffffu, 0xffbfffffu, 0xffa5a5a5u,              /* signalling NaNs */
  0x5f000000u, 0x5effffffu, 0x5f000001u, 0x5f7fffffu, 0x5f800000u,   /* 2^63 and neighbours */
  0xdf000000u, 0xdeffffffu, 0xdf000001u, 0xdf7fffffu, 0xdf800000u,   /* -2^63 and neighbours */
  0x5e800000u, 0x5e7fffffu, 0x5e800001u, 0xde800000u, 0xde7fffffu, 0xde800001u,   /* +-2^62 */
  0x4f000000u, 0x4effffffu, 0x4f000001u, 0xcf000000u, 0xceffffffu, 0xcf000001u,   /* +-2^31 */
  0x4f800000u, 0x4f7fffffu, 0x4f800001u, 0xcf800000u, 0xcf7fffffu, 0xcf800001u,   /* +-2^32 */
  0x4b800000u, 0x4b7fffffu, 0x4b800001u, 0xcb800000u, 0xcb7fffffu, 0xcb800001u,   /* +-2^24 */
  0x4b000000u, 0x4b000001u, 0x4affffffu, 0xcb000001u, 0xcaffffffu,                /* 2^23: the last fraction bit */
  0x7f7fffffu, 0xff7fffffu,                                     /* the finite extremes */
};
static void suite(void) {
  for (unsigned i = 0; i < sizeof SPECIAL / sizeof SPECIAL[0]; i++) one(SPECIAL[i]);
  for (uint32_t e = 0; e < 256; e++)
    for (uint32_t s = 0; s < 2; s++)
      for (uint32_t k = 0; k < 8; k++) { one((s << 31) | (e << 23) | k); one((s << 31) | (e << 23) | (0x7fffffu - k)); }
  for (uint64_t b = 0; b < 0x100000000ull; b += STRIDE) one((uint32_t)b);
  for (unsigned k = 0; k < NRAND; k++) one((uint32_t)rnd() ^ ((uint32_t)rnd() << 13));
  for (unsigned k = 0; k < NRAND; k++)    /* in range or near it: exponents 2^-4 .. 2^66 */
    one((uint32_t)(rnd() & 1) << 31 | (uint32_t)(123 + rnd() % 67) << 23 | ((uint32_t)rnd() & 0x7fffffu));
}
static void setmxcsr(uint32_t v) { __asm__ volatile("ldmxcsr %0" :: "m"(v)); }
void test_main(void) {
  puts_("F2IDIFF\n");
  setmxcsr(0x1f80u); puts_("MXCSR 1f80\n"); suite();
  setmxcsr(0x5f80u); puts_("MXCSR 5f80\n"); suite();
  setmxcsr(0x1f80u);
  puts_("CASES "); dec(cases); puts_("RETURNED "); dec(returned); puts_("TRAPS "); dec(traps); putc_('\n');
  puts_("DIFFS "); dec(diffs); puts_("INDEF "); dec(indef); putc_('\n');
  puts_("HASH "); hex(fnv, 16); putc_('\n');
  puts_("DONE\n");
}
