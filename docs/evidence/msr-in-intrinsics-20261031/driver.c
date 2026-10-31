/* JUN-600 / ADR 0399 hand check: msr.kotoba (the gate's source) against inline-asm C under QEMU. */
#include <stdint.h>
extern int64_t kotoba_aiueos_msr_read(int64_t), kotoba_aiueos_msr_write(int64_t, int64_t), pcr(int64_t);
extern int64_t guarded_call(void *, int64_t, int64_t);
extern volatile int64_t guard_vector;
void guard_init(void);
static void outb(uint16_t p, uint8_t v) { __asm__ volatile("outb %0, %1" :: "a"(v), "Nd"(p)); }
static void outl(uint16_t p, uint32_t v) { __asm__ volatile("outl %0, %1" :: "a"(v), "Nd"(p)); }
static uint32_t inl(uint16_t p) { uint32_t v; __asm__ volatile("inl %1, %0" : "=a"(v) : "Nd"(p)); return v; }
static void putc_(char c) { outb(0xe9, (uint8_t)c); }
static void puts_(const char *s) { while (*s) putc_(*s++); }
static void hex(uint64_t v, int n) { for (int i = n - 1; i >= 0; i--) putc_("0123456789abcdef"[(v >> (4 * i)) & 15]); putc_(' '); }
static uint64_t rdmsr(uint32_t i) { uint32_t lo, hi; __asm__ volatile("rdmsr" : "=a"(lo), "=d"(hi) : "c"(i)); return (uint64_t)hi << 32 | lo; }
static void wrmsr(uint32_t i, uint64_t v) { __asm__ volatile("wrmsr" :: "c"(i), "a"((uint32_t)v), "d"((uint32_t)(v >> 32))); }
static void cpuid(uint32_t l, uint32_t r[4]) { __asm__ volatile("cpuid" : "=a"(r[0]), "=b"(r[1]), "=c"(r[2]), "=d"(r[3]) : "a"(l), "c"(0)); }
static uint64_t seed = 600;
static uint64_t rnd(void) { seed = seed * 6364136223846793005ull + 1442695040888963407ull; return seed >> 17; }
static uint64_t rnd64(void) { return rnd() << 40 ^ rnd() << 20 ^ rnd(); }
static unsigned bad, n_read, n_write, n_trap, n_pci, n_refused;
static const uint32_t MSR[5] = {0x1b, 0xc0000080, 0xc0000081, 0xc0000082, 0xc0000084};
#define W(i, v) guarded_call((void *)kotoba_aiueos_msr_write, (int64_t)(i), (int64_t)(v))
/* a write the object admits: same register value as the C write, the object answers the value, no trap */
static void same(uint32_t i, uint64_t v) {
  uint64_t before = rdmsr(i); wrmsr(i, v); uint64_t c = rdmsr(i); wrmsr(i, before);
  int64_t r = W(i, v); uint64_t o = rdmsr(i); wrmsr(i, before);
  n_write++; if (guard_vector || o != c || (uint64_t)r != v) { bad++; puts_("WRITE-DIFF "); hex(i, 8); hex(v, 16); hex(c, 16); hex(o, 16); hex(guard_vector, 2); putc_('\n'); }
}
/* a write the object must refuse with ud2 before the wrmsr: the register keeps its value */
static void trap(uint32_t i, uint64_t v) {
  uint64_t before = rdmsr(i); W(i, v); uint64_t after = rdmsr(i);
  n_trap++; if (guard_vector != 6 || after != before) { bad++; puts_("TRAP-DIFF "); hex(i, 8); hex(v, 16); hex(guard_vector, 2); hex(after, 16); putc_('\n'); }
}
void test_main(void) {
  guard_init();
  puts_("MSR-IN\n");
  uint32_t r[4]; cpuid(0x80000001, r); int nx = (r[3] >> 20) & 1;
  for (int k = 0; k < 5; k++) {           /* reads: object against rdmsr */
    uint64_t c = rdmsr(MSR[k]), o = (uint64_t)kotoba_aiueos_msr_read(MSR[k]);
    puts_("READ "); hex(MSR[k], 8); hex(c, 16); puts_(o == c ? "equal\n" : "READ-DIFF\n"); n_read++; if (o != c) bad++;
  }
  static const int64_t OTHER[] = {0, 16, 0x277, 0xc0000083, 0xc0000100, 0xc0000085, 0x1a, 0x1c, -1, (int64_t)0x1000000001bll};
  for (unsigned k = 0; k < sizeof OTHER / 8; k++) {   /* not in the list: the object answers 0 and touches nothing */
    uint64_t s = rdmsr(0xc0000081);
    n_refused++; if (kotoba_aiueos_msr_read(OTHER[k]) != 0 || W(OTHER[k], 0x1234) != 0 || guard_vector || rdmsr(0xc0000081) != s) bad++;
  }
  for (int k = 0; k < 200; k++) {         /* STAR: any value; LSTAR: canonical; FMASK: 32 bits */
    uint64_t v = rnd64(), a = rnd64() & 0x7fffffffffffull;
    same(0xc0000081, v);
    same(0xc0000082, (k & 1) ? a : (a | 0xffff800000000000ull));
    same(0xc0000084, v & 0xffffffffull);
  }
  uint64_t efer = rdmsr(0xc0000080), apic = rdmsr(0x1b);
  puts_("EFER "); hex(efer, 16); puts_("APIC_BASE "); hex(apic, 16); puts_(nx ? "NX\n" : "no-NX\n");
  same(0xc0000080, efer); same(0xc0000080, efer | 1);                /* EFER: unchanged, SCE */
  if (nx) { same(0xc0000080, efer | 0x800); same(0xc0000080, efer | 0x801); }
  same(0x1b, apic); same(0x1b, apic | 0x800);                        /* APIC_BASE: unchanged, global enable */
  wrmsr(0xc0000080, efer | 1);
  trap(0xc0000080, efer);                 /* clears SCE */
  trap(0xc0000080, (efer | 1) & ~0x100ull);  /* clears LME */
  trap(0xc0000080, efer | 1 | 0x4000);    /* sets FFXSR, not admitted */
  trap(0xc0000080, 0);
  trap(0xc0000080, ~0ull);
  wrmsr(0xc0000080, efer);
  trap(0x1b, apic ^ 0x1000);              /* moves the APIC window */
  trap(0x1b, apic & ~0x800ull);           /* clears the global enable */
  trap(0x1b, apic | 0x400);               /* sets x2APIC enable, not admitted */
  for (int k = 0; k < 64; k++) { uint64_t v = rnd64(); if ((v | efer) != efer && (v & ~0x801ull & ~efer) != 0) trap(0xc0000080, v | efer); }
  /* in-u32: PCI configuration reads, the object against outl 0xcf8 / inl 0xcfc */
  for (uint32_t b = 0; b < 2; b++) for (uint32_t d = 0; d < 32; d++) for (uint32_t f = 0; f < 8; f++) for (uint32_t o = 0; o < 256; o += 4) {
    uint32_t a = 0x80000000u | b << 16 | d << 11 | f << 8 | o;
    outl(0xcf8, a); uint32_t c = inl(0xcfc); uint64_t v = (uint64_t)pcr(a);
    n_pci++; if (v != c) { bad++; puts_("PCI-DIFF "); hex(a, 8); hex(c, 8); hex(v, 16); putc_('\n'); }
  }
  outl(0xcf8, 0x80000000u); puts_("PCI 0:0.0 "); hex(inl(0xcfc), 8); hex((uint64_t)pcr(0x80000000u), 16); putc_('\n');
  puts_("READS "); hex(n_read, 4); puts_("REFUSED "); hex(n_refused, 4); puts_("WRITES "); hex(n_write, 4);
  puts_("TRAPS "); hex(n_trap, 4); puts_("PCI "); hex(n_pci, 8); puts_("DIFFS "); hex(bad, 4); putc_('\n'); puts_("DONE\n");
}
