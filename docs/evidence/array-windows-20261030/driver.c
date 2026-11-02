#include <stdint.h>
int64_t put(int64_t, int64_t); int64_t get(int64_t); int64_t sum(void); int64_t big(int64_t, int64_t); int64_t part(int64_t);
static void putc_(char c) { __asm__ volatile("outb %0, %1" :: "a"(c), "Nd"((uint16_t)0xe9)); }
static void puts_(const char *s) { while (*s) putc_(*s++); }
static void hex(uint64_t v) { for (int i = 15; i >= 0; i--) putc_("0123456789abcdef"[(v >> (4 * i)) & 15]); putc_(' '); }
void test_main(void) {
  puts_("AW\n");
  hex(get(5));                                   /* zero-initialised: 0 */
  for (int i = 0; i < 64; i++) put(i, i + 1);
  hex(get(0)); hex(get(63)); hex(sum());         /* 1, 64, u64@0 + u64@56 */
  hex(part(0)); hex(part(15));                   /* bytes 32 and 47: 33, 48 */
  hex(big(4094, 0xbeef)); hex(big(100, 0x1234));
  putc_('\n'); puts_("TRAP-NEXT\n");
  hex(get(64));
  puts_("NOT-TRAPPED\n");
}
