/* JUN-708 / ADR 0401 hand check: the 4 KiB window tier and the fences (the gates' sources) under QEMU, against a C
 * model of the reference: kotoba-native machine-ir's x86-kernel-bounds-check + x86-memory-access + x86-store-answer for
 * [:gmir/kernel-<op>-<w> 4096], aligned (kotoba-compiler/1's 4 KiB windows). */
#include <stdint.h>
typedef int64_t (*ld_fn)(int64_t, int64_t, int64_t);
typedef int64_t (*st_fn)(int64_t, int64_t, int64_t, int64_t);
extern int64_t ld8(int64_t, int64_t, int64_t), ld16(int64_t, int64_t, int64_t), ld32(int64_t, int64_t, int64_t),
    ld64(int64_t, int64_t, int64_t);
extern int64_t st8(int64_t, int64_t, int64_t, int64_t), st16(int64_t, int64_t, int64_t, int64_t),
    st32(int64_t, int64_t, int64_t, int64_t), st64(int64_t, int64_t, int64_t, int64_t);
extern int64_t fl(void), fs(void), ff(void), submit(int64_t, int64_t, int64_t), poll(int64_t, int64_t);
extern int64_t guarded_call(void *, int64_t, int64_t, int64_t, int64_t);
extern volatile int64_t guard_vector;
void guard_init(void);
static void outb(uint16_t p, uint8_t v) { __asm__ volatile("outb %0, %1" :: "a"(v), "Nd"(p)); }
static void putc_(char c) { outb(0xe9, (uint8_t)c); }
static void puts_(const char *s) { while (*s) putc_(*s++); }
static void hex(uint64_t v, int n) { for (int i = n - 1; i >= 0; i--) putc_("0123456789abcdef"[(v >> (4 * i)) & 15]); putc_(' '); }
static uint64_t seed = 4096;
static uint64_t rnd(void) { seed = seed * 6364136223846793005ull + 1442695040888963407ull; return seed >> 17; }
static uint64_t rnd64(void) { return rnd() << 40 ^ rnd() << 20 ^ rnd(); }

/* 8 KiB, page aligned: a window of up to 4096 bytes at any offset below 4096 stays inside it */
static uint8_t buf[8192] __attribute__((aligned(4096)));
static uint8_t want[8192] __attribute__((aligned(4096)));
static void *const LD[4] = {(void *)ld8, (void *)ld16, (void *)ld32, (void *)ld64};
static void *const ST[4] = {(void *)st8, (void *)st16, (void *)st32, (void *)st64};
static unsigned bad, n_ok, n_trap, n_len, n_null, n_index, n_tail, n_align;

/* the reference guard, in its order: length > 4096; base = 0; index >= length; length - index < width; index % width */
static int ref_trap(uint64_t b, uint64_t n, uint64_t i, int w) {
  if (n > 4096) { n_len++; return 1; }
  if (b == 0) { n_null++; return 1; }
  if (i >= n) { n_index++; return 1; }
  if (w > 1 && (int64_t)(n - i) < w) { n_tail++; return 1; }
  if (w > 1 && (i & (uint64_t)(w - 1))) { n_align++; return 1; }
  return 0;
}
static uint64_t get(const uint8_t *p, int w) { uint64_t v = 0; for (int k = w - 1; k >= 0; k--) v = v << 8 | p[k]; return v; }
static void put(uint8_t *p, int w, uint64_t v) { for (int k = 0; k < w; k++) p[k] = (uint8_t)(v >> (8 * k)); }
static void fill(void) { for (int k = 0; k < 8192; k++) want[k] = buf[k] = (uint8_t)rnd(); }
static int same_buf(void) { for (int k = 0; k < 8192; k++) if (buf[k] != want[k]) return 0; return 1; }

static void one(int wi, int store, uint64_t b, uint64_t n, uint64_t i, uint64_t v) {
  int w = 1 << wi, trap = ref_trap(b, n, i, w);
  int64_t r = store ? guarded_call(ST[wi], (int64_t)b, (int64_t)n, (int64_t)i, (int64_t)v)
                    : guarded_call(LD[wi], (int64_t)b, (int64_t)n, (int64_t)i, 0);
  uint64_t expect = 0;
  if (!trap) {
    uint8_t *p = (uint8_t *)(uintptr_t)b - buf + want + i;
    if (store) { put(p, w, v); expect = v; } else expect = get(p, w);
  }
  int ok = trap ? (guard_vector == 6 && r == 0) : (guard_vector == 0 && (uint64_t)r == expect);
  ok = ok && same_buf();
  if (trap) n_trap++; else n_ok++;
  if (!ok) {
    bad++; puts_("DIFF "); hex((uint64_t)(8 << wi), 2); hex((uint64_t)store, 1); hex(b, 16); hex(n, 16); hex(i, 16);
    hex(v, 16); hex((uint64_t)r, 16); hex(expect, 16); hex((uint64_t)guard_vector, 2); putc_('\n');
    for (int k = 0; k < 8192; k++) buf[k] = want[k];
  }
}

static const uint64_t LENS[] = {0, 1, 2, 3, 4, 7, 8, 9, 15, 16, 511, 512, 513, 2048, 4088, 4092, 4094, 4095, 4096, 4097,
                                4104, 8192, 65536, 0x7fffffffffffffffull, 0x8000000000000000ull, ~0ull};
void test_main(void) {
  guard_init();
  puts_("WINDOWS4K-FENCE\n");
  fill();
  uintptr_t B = (uintptr_t)buf;
  for (int wi = 0; wi < 4; wi++)
    for (int store = 0; store < 2; store++) {
      for (unsigned l = 0; l < sizeof LENS / 8; l++) {
        uint64_t n = LENS[l];
        uint64_t m = n > 4096 ? 4096 : n;
        uint64_t idx[] = {0, 1, 2, 3, 4, 5, 7, 8, m - 1, m - 2, m - 3, m - 4, m - 5, m - 8, m - 9, m, m + 1, n, n - 1,
                          4095, 4096, 4088, 4092, 4094, ~0ull, 0x8000000000000000ull};
        for (unsigned k = 0; k < sizeof idx / 8; k++) {
          one(wi, store, B, n, idx[k], rnd64());
          one(wi, store, B + 1, n, idx[k], rnd64());      /* a misaligned BASE: the reference checks the index only */
          one(wi, store, B + 4096 - (m & ~7ull), n, idx[k], rnd64());
          one(wi, store, 0, n, idx[k], rnd64());          /* null base */
        }
      }
      for (int k = 0; k < 4000; k++) {                    /* random tuples around the boundaries */
        uint64_t n = (rnd() & 1) ? rnd() % 4100 : (rnd() & 3) ? 4096 - rnd() % 16 : rnd64();
        uint64_t i = (rnd() & 1) ? rnd() % 4104 : n - 1 - rnd() % 16;
        uint64_t b = (rnd() % 64) ? B + rnd() % 8 : 0;   /* base + index < buf + 4104 when admitted */
        one(wi, store, b, n, i, rnd64());
      }
      puts_("FORM "); hex((uint64_t)(8 << wi), 2); puts_(store ? "store " : "load "); hex(n_ok, 8); hex(n_trap, 8); putc_('\n');
    }
  /* fences: each answers 0, without a trap */
  unsigned fences = 0;
  for (int k = 0; k < 3; k++) {
    void *f = k == 0 ? (void *)fl : k == 1 ? (void *)fs : (void *)ff;
    int64_t r = guarded_call(f, 0, 0, 0, 0);
    fences++; if (r != 0 || guard_vector) { bad++; puts_("FENCE-DIFF "); hex((uint64_t)k, 1); hex((uint64_t)r, 16); putc_('\n'); }
  }
  /* driver shape: store; sfence; doorbell store -- load; lfence; load */
  for (int k = 0; k < 64; k++) {
    uint64_t v = rnd64();
    int64_t r = guarded_call((void *)submit, (int64_t)B, 4096, (int64_t)v, 0);
    put(want, 4, v); want[56] = 64;
    if (r != (int64_t)v || guard_vector || !same_buf()) { bad++; puts_("SUBMIT-DIFF\n"); }
    int64_t p = guarded_call((void *)poll, (int64_t)B, 4096, 0, 0);
    if ((uint64_t)p != get(want, 4) + get(want + 8, 8) || guard_vector) { bad++; puts_("POLL-DIFF\n"); }
    fences += 2;
  }
  guarded_call((void *)submit, (int64_t)B, 4097, 1, 0);   /* the doorbell window over 4096 traps before any store */
  if (guard_vector != 6 || !same_buf()) { bad++; puts_("SUBMIT-TRAP-DIFF\n"); }
  puts_("ACCESSES "); hex(n_ok, 8); puts_("TRAPS "); hex(n_trap, 8);
  puts_("LEN "); hex(n_len, 8); puts_("NULL "); hex(n_null, 8); puts_("INDEX "); hex(n_index, 8);
  puts_("TAIL "); hex(n_tail, 8); puts_("ALIGN "); hex(n_align, 8); puts_("FENCES "); hex(fences, 4);
  puts_("DIFFS "); hex(bad, 4); putc_('\n'); puts_("DONE\n");
}
