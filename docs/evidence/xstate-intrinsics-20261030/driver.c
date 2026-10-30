#include <stdint.h>
extern int64_t cr4on(void), xcr0on(void), rc(void), xg(void);
static void putc_(char c) { __asm__ volatile("outb %0, %1" :: "a"(c), "Nd"((uint16_t)0xe9)); }
static void puts_(const char *s) { while (*s) putc_(*s++); }
static void hex(uint64_t v, int n) { for (int i = n - 1; i >= 0; i--) putc_("0123456789abcdef"[(v >> (4 * i)) & 15]); putc_(' '); }
static uint64_t c_cr4(void) { uint64_t v; __asm__ volatile("mov %%cr4, %0" : "=r"(v)); return v; }
static uint64_t c_xgetbv(void) { uint32_t lo, hi; __asm__ volatile("xgetbv" : "=a"(lo), "=d"(hi) : "c"(0)); return ((uint64_t)hi << 32) | lo; }
static void cpuid(uint32_t l, uint32_t r[4]) { __asm__ volatile("cpuid" : "=a"(r[0]), "=b"(r[1]), "=c"(r[2]), "=d"(r[3]) : "a"(l), "c"(0)); }
void test_main(void) {
  unsigned bad = 0;
  puts_("XSTATE\n");
  uint64_t before = c_cr4(), o = (uint64_t)rc();
  puts_("CR4 "); hex(before, 8); puts_(o == before ? "read-equal\n" : "READ-DIFF\n"); if (o != before) bad++;
  uint32_t r[4]; cpuid(1, r);
  int xsave = (r[2] >> 26) & 1, avx = (r[2] >> 28) & 1;
  puts_("XSAVE "); puts_(xsave ? "present\n" : "absent\n");
  if (xsave) {
    uint64_t set = (uint64_t)cr4on(), after = c_cr4();
    puts_("CR4-SET "); hex(set, 8); hex(after, 8);
    if (set != after || after != (before | 0x40600)) { bad++; puts_("SET-DIFF\n"); } else puts_("or-ed 0x40600\n");
    uint64_t x0 = c_xgetbv(), xo = (uint64_t)xg();
    puts_("XCR0 "); hex(x0, 8); puts_(xo == x0 ? "read-equal\n" : "READ-DIFF\n"); if (xo != x0) bad++;
    if (avx) {
      uint64_t xs = (uint64_t)xcr0on(), x1 = c_xgetbv();
      puts_("XCR0-SET "); hex(xs, 8); hex(x1, 8);
      if (xs != x1 || x1 != (x0 | 7)) { bad++; puts_("SET-DIFF\n"); } else puts_("or-ed 7\n");
    }
  }
  puts_("DIFFS "); hex(bad, 2); putc_('\n'); puts_("DONE\n");
}
