#include <stdint.h>
int64_t ld8(uint8_t *, int64_t, int64_t); int64_t st8(uint8_t *, int64_t, int64_t, int64_t);
int64_t ld16(uint8_t *, int64_t, int64_t); int64_t st16(uint8_t *, int64_t, int64_t, int64_t);
int64_t ld64(uint8_t *, int64_t, int64_t); int64_t st64(uint8_t *, int64_t, int64_t, int64_t);
static void putc_(char c) { __asm__ volatile("outb %0, %1" :: "a"(c), "Nd"((uint16_t)0xe9)); }
static void puts_(const char *s) { while (*s) putc_(*s++); }
static void hex(uint64_t v) { for (int i = 15; i >= 0; i--) putc_("0123456789abcdef"[(v >> (4 * i)) & 15]); putc_(' '); }
static uint8_t buf[16384] __attribute__((aligned(16)));
void test_main(void) {
  puts_("W16\n");
  st8(buf, 16384, 600, 0x5a); hex(ld8(buf, 16384, 600)); hex(buf[600]);
  st8(buf, 16384, 16383, 0xa5); hex(ld8(buf, 16384, 16383));
  st16(buf, 16384, 16382, 0xbeef); hex(ld16(buf, 16384, 16382)); hex(buf[16383]);
  st64(buf, 16384, 16376, 0x1122334455667788ull); hex(ld64(buf, 16384, 16376));
  st64(buf, 16384, 8192, 0x0123456789abcdefull); hex(ld64(buf, 16384, 8192));
  putc_('\n'); puts_("TRAP-NEXT\n");
  hex(ld8(buf, 16384, 16384));
  puts_("NOT-TRAPPED\n");
}
