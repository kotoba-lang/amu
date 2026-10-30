/* JUN-633 slice 5 (ADR 0393): kotoba_aiueos_spin -- one call of kernel-pause -- executed 100000 times under QEMU: each
   returns 0 with RFLAGS.IF as it was. */
#include <stdint.h>
int64_t kotoba_aiueos_spin(void);
static void outb(uint16_t p, uint8_t v) { __asm__ volatile("outb %0, %1" :: "a"(v), "Nd"(p)); }
static void puts_(const char *s) { while (*s) outb(0xe9, (uint8_t)*s++); }
static void hex(uint64_t v, int n) { for (int i = n - 1; i >= 0; i--) outb(0xe9, (uint8_t)"0123456789abcdef"[(v >> (4 * i)) & 15]); outb(0xe9, ' '); }
static uint64_t rflags(void) { uint64_t f; __asm__ volatile("pushfq; popq %0" : "=r"(f)); return f; }
void test_main(void) {
  puts_("PAUSEINTRINSIC\n");
  unsigned ok = 0, n = 100000;
  for (unsigned i = 0; i < n; i++) {
    uint64_t f0 = rflags(); int64_t r = kotoba_aiueos_spin(); uint64_t f1 = rflags();
    ok += r == 0 && (f0 & 0x200) == (f1 & 0x200);
  }
  puts_("CALLS "); hex(n, 5); puts_("RETURNED-0-IF-UNCHANGED "); hex(ok, 5); puts_("\nDONE\n");
}
