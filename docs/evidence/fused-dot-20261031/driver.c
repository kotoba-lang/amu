/* kernel-dot-f32 and kernel-dequant-dot-ptq1-0 on amu's native object route (dot-native.o, dq-native.o, JUN-633 slice 6)
   against the kotoba-compiler/1 object qwen35-matvec.o (kotoba main), whose matvec reaches the same two builtins: an
   F32 (type 0) one-row plan with cols a multiple of 8 and <= 16384 takes kernel-dot-f32 (the AVX2 / scalar arm), and a
   PTQ1_0 (type 143) plan with cols <= 16384 takes kernel-dequant-dot-ptq1-0 (the fused arm). Random f32 data with NaN
   (quiet and signalling payloads), +-Inf, +-0, denormals and overflowing magnitudes; random PTQ1_0 blocks with every
   fp16 scale class. The answer bits must be equal; the native answer must be the sign-extended f32 word; the F32
   scratch must hold the weights' bits. A C model of the tree (ref.c) is compared modulo NaN payloads. Then the guards:
   each input past one must raise #UD (ud2) in the native object, and the boundary must not. */
#include <stdint.h>
typedef int64_t (*fn5)(uint64_t, uint64_t, uint64_t, uint64_t, uint64_t);
extern int64_t kotoba_aiueos_qwen35_matvec(uint64_t arena, uint64_t alen, uint64_t plan, uint64_t plen);
extern int64_t kotoba_native_dot_f32(uint64_t, uint64_t, uint64_t, uint64_t, uint64_t);
extern int64_t kotoba_native_dequant_dot_ptq1_0(uint64_t, uint64_t, uint64_t, uint64_t, uint64_t);
extern int64_t trapcall(fn5 f, uint64_t a, uint64_t b, uint64_t c, uint64_t d, uint64_t e, int64_t *result);
extern uint32_t ref_dot(const uint32_t *a, const uint32_t *b, uint64_t n);
extern uint32_t ref_ptq1(const uint8_t *w, const uint32_t *x, uint64_t blocks);
static void outb(uint16_t p, uint8_t v) { __asm__ volatile("outb %0, %1" :: "a"(v), "Nd"(p)); }
static void putc_(char c) { outb(0xe9, (uint8_t)c); }
static void puts_(const char *s) { while (*s) putc_(*s++); }
static void hex(uint64_t v, int n) { for (int i = n - 1; i >= 0; i--) putc_("0123456789abcdef"[(v >> (4 * i)) & 15]); putc_(' '); }
#define W_OFF 0u
#define I_OFF 65536u
#define O_OFF 131072u
#define S_OFF 135168u
#define ALEN (S_OFF + 65536u)
static uint8_t arena[ALEN + 64] __attribute__((aligned(64)));
static uint64_t plan[12];
static uint64_t seed = 633;
static uint64_t rnd(void) { seed = seed * 6364136223846793005ull + 1442695040888963407ull; return seed >> 17; }
static uint32_t rf32(unsigned mode) {
  uint32_t s = (uint32_t)(rnd() & 1) << 31, m = (uint32_t)rnd() & 0x7fffff;
  /* mode 0: ordinary magnitudes only; 1: 30% specials; 2: about one special in 1000; 3: no NaN / Inf inputs, 30% of
     zeros, denormals and overflowing magnitudes */
  unsigned r = mode == 2 ? (unsigned)(rnd() % 100000) / 33 : (unsigned)(rnd() % 100);
  if (mode == 3 && r < 9) r = 9 + (unsigned)(rnd() % 17);
  if (mode == 0 || r >= 30) return s | ((uint32_t)(112 + rnd() % 32) << 23) | m;      /* ordinary magnitudes */
  if (r < 5) return s | 0x7f800000u | (m ? m : 1);                                  /* NaN: quiet or signalling payload */
  if (r < 9) return s | 0x7f800000u;                                                 /* +-Inf */
  if (r < 14) return s;                                                              /* +-0 */
  if (r < 21) return s | m;                                                          /* denormal */
  if (r < 26) return s | ((uint32_t)(250 + rnd() % 5) << 23) | m;                    /* overflows a product */
  return (uint32_t)rnd() ^ ((uint32_t)rnd() << 15);                                  /* any bits */
}
static uint16_t rhalf(void) {
  unsigned r = (unsigned)(rnd() % 100); uint16_t s = (uint16_t)((rnd() & 1) << 15), m = (uint16_t)(rnd() & 0x3ff);
  if (r < 70) return s | (uint16_t)((1 + rnd() % 30) << 10) | m;
  if (r < 80) return s | m;                      /* subnormal or zero */
  if (r < 88) return s | 0x7c00;                 /* inf */
  if (r < 94) return s | 0x7c00 | (m ? m : 1);   /* nan */
  return (uint16_t)rnd();
}
static int is_nan(uint32_t v) { return (v & 0x7f800000u) == 0x7f800000u && (v & 0x7fffff); }
static uint64_t fnv = 1469598103934665603ull;
static void mix(uint32_t v) { for (int i = 0; i < 4; i++) { fnv ^= (v >> (8 * i)) & 255; fnv *= 1099511628211ull; } }
static void setplan(uint64_t type, uint64_t cols, uint64_t wbytes) {
  for (int i = 0; i < 12; i++) plan[i] = 0;
  plan[0] = type; plan[1] = 1; plan[2] = cols; plan[3] = W_OFF; plan[4] = wbytes; plan[5] = I_OFF; plan[6] = O_OFF;
  plan[7] = S_OFF; plan[8] = 0; plan[9] = 1;
}
static unsigned bad, refbad, refnan, nancase, scratchbad, extbad, cases_dot, cases_dq, traps_ok, traps_bad;
static void report(const char *tag, uint64_t k, uint64_t n, uint64_t a, uint64_t b) {
  if (bad + extbad + scratchbad < 12) { puts_(tag); hex(k, 5); hex(n, 5); hex(a, 16); hex(b, 16); putc_('\n'); }
}
static int64_t native(fn5 f, uint64_t a, uint64_t an, uint64_t b, uint64_t bn, uint64_t c, int *trapped) {
  int64_t r = 0; *trapped = (int)trapcall(f, a, an, b, bn, c, &r); return r;
}
static void guard(const char *name, fn5 f, uint64_t a, uint64_t an, uint64_t b, uint64_t bn, uint64_t c, int want) {
  int t; native(f, a, an, b, bn, c, &t);
  if (t == want) traps_ok++; else traps_bad++;
  puts_("GUARD "); puts_(name); puts_(t ? " ud2\n" : " returned\n");
}
static int avx2_usable(void) {
  uint32_t a, b, c, d;
  __asm__ volatile("cpuid" : "=a"(a), "=b"(b), "=c"(c), "=d"(d) : "a"(0), "c"(0)); if (a < 7) return 0;
  __asm__ volatile("cpuid" : "=a"(a), "=b"(b), "=c"(c), "=d"(d) : "a"(1), "c"(0)); if ((c & 0x18000000u) != 0x18000000u) return 0;
  uint32_t lo, hi; __asm__ volatile("xgetbv" : "=a"(lo), "=d"(hi) : "c"(0)); if ((lo & 6) != 6) return 0;
  __asm__ volatile("cpuid" : "=a"(a), "=b"(b), "=c"(c), "=d"(d) : "a"(7), "c"(0)); return (b >> 5) & 1;
}
void test_main(void) {
  puts_("DOTDIFF\n");
#ifndef NO_XSAVE
  { uint32_t a, b, c, d; __asm__ volatile("cpuid" : "=a"(a), "=b"(b), "=c"(c), "=d"(d) : "a"(1), "c"(0));
    if ((c & (1u << 26)) && (c & (1u << 28))) {  /* XSAVE and AVX: CR4.OSXSAVE, then XCR0 = x87 | SSE | AVX */
      uint64_t cr4; __asm__ volatile("mov %%cr4, %0" : "=r"(cr4)); cr4 |= 1u << 18; __asm__ volatile("mov %0, %%cr4" :: "r"(cr4));
      __asm__ volatile("xsetbv" :: "a"(7), "d"(0), "c"(0)); } }
#endif
  puts_(avx2_usable() ? "ARM avx2\n" : "ARM scalar\n");
  uint32_t *w = (uint32_t *)(arena + W_OFF), *x = (uint32_t *)(arena + I_OFF), *o = (uint32_t *)(arena + O_OFF);
  uint32_t *s = (uint32_t *)(arena + S_OFF);
  for (unsigned k = 0; k < NDOT; k++) {
    uint64_t blocks = k == 0 ? 2048 : k == 1 ? 1 : (rnd() & 1) ? 1 + rnd() % 16 : 1 + rnd() % 2048, n = blocks * 8;
    unsigned mode = (unsigned)(k % 4);
    for (uint64_t i = 0; i < n; i++) { w[i] = rf32(mode); x[i] = rf32(mode); }
    o[0] = 0x5a5a5a5au;
    setplan(0, n, n * 4);
    int64_t v = kotoba_aiueos_qwen35_matvec((uint64_t)(uintptr_t)arena, ALEN, (uint64_t)(uintptr_t)plan, 96);
    int t; int64_t r = native((fn5)kotoba_native_dot_f32, (uint64_t)(uintptr_t)w, n * 4, (uint64_t)(uintptr_t)x, n * 4, n, &t);
    for (uint64_t i = 0; i < n; i++) if (s[i] != w[i]) { scratchbad++; break; }
    uint32_t c = ref_dot(w, x, n); cases_dot++; mix((uint32_t)r);
    if (v != 0 || t || (uint32_t)r != o[0]) { report("DOT-DIFF ", k, n, (uint64_t)o[0] | ((uint64_t)v << 32), (uint64_t)r); bad++; }
    if (r != (int64_t)(int32_t)(uint32_t)r) { report("DOT-EXT ", k, n, 0, (uint64_t)r); extbad++; }
    if (is_nan((uint32_t)r)) nancase++;
    if (is_nan(c) && is_nan((uint32_t)r)) refnan++;
    else if (c != (uint32_t)r) { refbad++; if (refbad < 6) { puts_("DOT-REF "); hex(k, 5); hex(n, 5); hex(c, 8); hex((uint32_t)r, 8); putc_('\n'); } }
    if (k % 500 == 499) { puts_("AT "); hex(k + 1, 5); putc_('\n'); }
  }
  uint8_t *q = arena + W_OFF;
  for (unsigned k = 0; k < NDQ; k++) {
    uint64_t blocks = k == 0 ? 128 : k == 1 ? 1 : (rnd() & 1) ? 1 + rnd() % 8 : 1 + rnd() % 128, n = blocks * 128;
    unsigned mode = (unsigned)(k % 4);
    for (uint64_t b = 0; b < blocks; b++) {
      for (int i = 0; i < 26; i++) q[28 * b + i] = (uint8_t)(k % 4 == 3 ? rnd() % 243 : rnd());
      uint16_t h = rhalf(); q[28 * b + 26] = (uint8_t)h; q[28 * b + 27] = (uint8_t)(h >> 8);
    }
    for (uint64_t i = 0; i < n; i++) x[i] = rf32(mode);
    o[0] = 0x5a5a5a5au;
    setplan(143, n, blocks * 28);
    int64_t v = kotoba_aiueos_qwen35_matvec((uint64_t)(uintptr_t)arena, ALEN, (uint64_t)(uintptr_t)plan, 96);
    int t; int64_t r = native((fn5)kotoba_native_dequant_dot_ptq1_0, (uint64_t)(uintptr_t)q, blocks * 28, (uint64_t)(uintptr_t)x, n * 4, blocks, &t);
    uint32_t c = ref_ptq1(q, x, blocks); cases_dq++; mix((uint32_t)r);
    if (v != 0 || t || (uint32_t)r != o[0]) { report("DQ-DIFF ", k, n, (uint64_t)o[0] | ((uint64_t)v << 32), (uint64_t)r); bad++; }
    if (r != (int64_t)(int32_t)(uint32_t)r) { report("DQ-EXT ", k, n, 0, (uint64_t)r); extbad++; }
    if (is_nan((uint32_t)r)) nancase++;
    if (is_nan(c) && is_nan((uint32_t)r)) refnan++;
    else if (c != (uint32_t)r) { refbad++; if (refbad < 6) { puts_("DQ-REF "); hex(k, 5); hex(n, 5); hex(c, 8); hex((uint32_t)r, 8); putc_('\n'); } }
    if (k % 500 == 499) { puts_("AT "); hex(k + 1, 5); putc_('\n'); }
  }
  uint64_t A = (uint64_t)(uintptr_t)w, B = (uint64_t)(uintptr_t)x;
  fn5 D = (fn5)kotoba_native_dot_f32, Q = (fn5)kotoba_native_dequant_dot_ptq1_0;
  guard("dot-boundary", D, A, 65536, B, 65536, 16384, 0);
  guard("dot-a-len-65537", D, A, 65537, B, 65536, 8, 1);
  guard("dot-b-len-65537", D, A, 65536, B, 65537, 8, 1);
  guard("dot-a-null", D, 0, 64, B, 64, 8, 1);
  guard("dot-b-null", D, A, 64, 0, 64, 8, 1);
  guard("dot-count-16385", D, A, 65536, B, 65536, 16385, 1);
  guard("dot-count-2^62", D, A, 65536, B, 65536, 1ull << 62, 1);
  guard("dot-a-short", D, A, 31, B, 64, 8, 1);
  guard("dot-b-short", D, A, 64, B, 31, 8, 1);
  guard("dot-a-len-2^63", D, A, 1ull << 63, B, 64, 8, 1);
  guard("dq-boundary", Q, A, 3584, B, 65536, 128, 0);
  guard("dq-w-len-65537", Q, A, 65537, B, 65536, 1, 1);
  guard("dq-x-len-65537", Q, A, 3584, B, 65537, 1, 1);
  guard("dq-w-null", Q, 0, 3584, B, 65536, 1, 1);
  guard("dq-x-null", Q, A, 3584, 0, 65536, 1, 1);
  guard("dq-blocks-129", Q, A, 65536, B, 65536, 129, 1);
  guard("dq-blocks-2^60", Q, A, 65536, B, 65536, 1ull << 60, 1);
  guard("dq-w-short", Q, A, 55, B, 1024, 2, 1);
  guard("dq-x-short", Q, A, 56, B, 1023, 2, 1);
  puts_("CASES "); hex(cases_dot, 5); hex(cases_dq, 5); puts_("DIFFS "); hex(bad, 5); puts_("EXT "); hex(extbad, 4);
  puts_("SCRATCH "); hex(scratchbad, 4); puts_("NANS "); hex(nancase, 5); putc_('\n');
  puts_("REF-MISMATCH "); hex(refbad, 5); puts_("REF-NAN-BOTH "); hex(refnan, 5); putc_('\n');
  puts_("GUARDS "); hex(traps_ok, 3); puts_("BAD "); hex(traps_bad, 3); putc_('\n');
  puts_("HASH "); hex(fnv, 16); putc_('\n');
  puts_("DONE\n");
}
