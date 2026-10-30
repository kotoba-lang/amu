/* JUN-633 slice 4 (ADR 0392): kotoba_aiueos_wait -- one call of kernel-wait-interrupt -- under a real timer interrupt.
   The PIC is remapped to vectors 32..47 with only IRQ0 unmasked, the PIT ticks at 100 Hz, and the IRQ0 gate counts the
   ticks and sends EOI. Each wait must return after at least one tick has been taken, with RFLAGS.IF clear again. */
#include <stdint.h>
int64_t kotoba_aiueos_wait(void);
static void outb(uint16_t p, uint8_t v) { __asm__ volatile("outb %0, %1" :: "a"(v), "Nd"(p)); }
static void putc_(char c) { outb(0xe9, (uint8_t)c); }
static void puts_(const char *s) { while (*s) putc_(*s++); }
static void hex(uint64_t v, int n) { for (int i = n - 1; i >= 0; i--) putc_("0123456789abcdef"[(v >> (4 * i)) & 15]); putc_(' '); }
volatile uint64_t ticks;
void irq0_stub(void);
__asm__(".globl irq0_stub\nirq0_stub:\n  pushq %rax\n  lock incq ticks(%rip)\n  movb $0x20, %al\n  outb %al, $0x20\n  popq %rax\n  iretq\n");
struct gate { uint16_t lo, sel; uint8_t ist, attr; uint16_t mid; uint32_t hi, zero; } __attribute__((packed));
static struct gate idt[48] __attribute__((aligned(16)));
static uint64_t rflags(void) { uint64_t f; __asm__ volatile("pushfq; popq %0" : "=r"(f)); return f; }
void test_main(void) {
  puts_("HALTINTRINSIC\n");
  uint64_t a = (uint64_t)(uintptr_t)irq0_stub;
  idt[32] = (struct gate){(uint16_t)a, 0x08, 0, 0x8e, (uint16_t)(a >> 16), (uint32_t)(a >> 32), 0};
  struct { uint16_t limit; uint64_t base; } __attribute__((packed)) idtr = {sizeof idt - 1, (uint64_t)(uintptr_t)idt};
  __asm__ volatile("lidt %0" :: "m"(idtr));
  outb(0x20, 0x11); outb(0xa0, 0x11); outb(0x21, 32); outb(0xa1, 40); outb(0x21, 4); outb(0xa1, 2);
  outb(0x21, 1); outb(0xa1, 1); outb(0x21, 0xfe); outb(0xa1, 0xff);            /* only IRQ0 */
  outb(0x43, 0x34); outb(0x40, 0x9c); outb(0x40, 0x2e);                          /* 1193182 / 11932 = 100 Hz */
  unsigned ok = 0, waits = 20;
  for (unsigned i = 0; i < waits; i++) {
    uint64_t before = ticks, f0 = rflags();
    int64_t r = kotoba_aiueos_wait();
    uint64_t after = ticks, f1 = rflags();
    int good = r == 0 && after > before && !(f0 & 0x200) && !(f1 & 0x200);
    ok += good;
    if (i < 3 || !good) { puts_("WAIT "); hex(i, 2); hex((uint64_t)r, 1); hex(before, 4); hex(after, 4); hex(f1 & 0x200 ? 1 : 0, 1); putc_('\n'); }
  }
  puts_("WAITS "); hex(waits, 2); puts_("RETURNED-AFTER-A-TICK-WITH-IF-CLEAR "); hex(ok, 2); puts_("TICKS "); hex(ticks, 4); putc_('\n');
  puts_("DONE\n");
}
