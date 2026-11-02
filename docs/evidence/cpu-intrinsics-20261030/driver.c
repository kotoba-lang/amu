#include <stdint.h>
extern int64_t ca(int64_t, int64_t), cb(int64_t, int64_t), cc(int64_t, int64_t), cd(int64_t, int64_t), ts(void), rr(void);
static void putc_(char c) { __asm__ volatile("outb %0, %1" :: "a"(c), "Nd"((uint16_t)0xe9)); }
static void puts_(const char *s) { while (*s) putc_(*s++); }
static void hex(uint64_t v, int n) { for (int i = n - 1; i >= 0; i--) putc_("0123456789abcdef"[(v >> (4 * i)) & 15]); putc_(' '); }
static void cpuid(uint32_t l, uint32_t s, uint32_t r[4]) { __asm__ volatile("cpuid" : "=a"(r[0]), "=b"(r[1]), "=c"(r[2]), "=d"(r[3]) : "a"(l), "c"(s)); }
void test_main(void) {
  static const uint32_t leaves[][2] = {{0, 0}, {1, 0}, {7, 0}, {7, 1}, {0xd, 0}, {0xd, 1}, {0x80000000u, 0}, {0x80000001u, 0}, {0x80000002u, 0}};
  unsigned bad = 0, n = 0;
  puts_("CPUINTR\n");
  for (unsigned k = 0; k < sizeof leaves / sizeof *leaves; k++) {
    uint32_t r[4]; cpuid(leaves[k][0], leaves[k][1], r);
    int64_t o[4] = {ca(leaves[k][0], leaves[k][1]), cb(leaves[k][0], leaves[k][1]), cc(leaves[k][0], leaves[k][1]), cd(leaves[k][0], leaves[k][1])};
    for (int i = 0; i < 4; i++) { n++; if ((uint64_t)o[i] != r[i]) { bad++; puts_("CPUID-DIFF "); hex(leaves[k][0], 8); hex(i, 1); hex((uint64_t)o[i], 16); hex(r[i], 8); putc_('\n'); } }
  }
  int64_t prev = ts(); unsigned monotonic = 1;
  for (int i = 0; i < 1000; i++) { int64_t t = ts(); if ((uint64_t)t < (uint64_t)prev) monotonic = 0; prev = t; }
  /* RDRAND raises #UD on a CPU without it: the caller checks CPUID.1:ECX[30] first, as the C it replaces does */
  uint32_t r1[4]; cpuid(1, 0, r1);
  int has_rdrand = (r1[2] >> 30) & 1;
  int64_t a = has_rdrand ? rr() : 0, b = has_rdrand ? rr() : 0;
  puts_("CPUID "); hex(n, 3); puts_("DIFFS "); hex(bad, 3); putc_('\n');
  puts_("RDTSC "); puts_(monotonic ? "monotonic\n" : "NOT-MONOTONIC\n");
  puts_("RDRAND "); puts_(has_rdrand ? "present " : "absent "); puts_((a | b) ? "nonzero\n" : "zero\n");
  puts_("DONE\n");
}
