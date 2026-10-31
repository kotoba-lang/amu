/* f32 -> i64 truncation on amu's aarch64 route (seed/41, JUN-633, ADR 0397) against ../f32-to-i64-20261031/ref.c, the
   integer-only C reference that the x86 object run (ADR 0395) uses. The payload is f2i.kotoba compiled with
   --target aarch64-macos and cut out with extract-native; it runs natively, called with x7 = a context whose fuel
   ([x7,#8]) is reset before each call and whose code_base ([x7,#384]) is the mapped payload.
   Each case either returns (the answer must equal the reference's integer) or traps; a trap must be SIGTRAP from the
   guard's brk #0 (any other trap is BADTRAP and must be 0), and the reference must trap too. INDEF counts answers of
   0x8000000000000000 for operands other than -2^63 and must be 0.
   The cases and their order are driver.c's (x86), so the FNV hash is comparable across the ISAs. The two passes run
   with FPCR.RMode = round to nearest, then round toward +Inf (x86: MXCSR RC), since truncation must not depend on it.
   The stride sweep runs on THREADS worker threads per block; the main thread checks and hashes the block in order. */
#define _DARWIN_C_SOURCE 1
#define _GNU_SOURCE 1
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <pthread.h>
#include <sys/mman.h>
#ifdef __APPLE__
#include <sys/ucontext.h>
#include <libkern/OSCacheControl.h>
#else
#include <ucontext.h>
#endif
#ifndef STRIDE
#define STRIDE 4099ull
#endif
#ifndef NRAND
#define NRAND 1000000
#endif
extern int ref_f32_to_i64(uint32_t b, int64_t *out);
extern int64_t a64call(void *fn, uint64_t arg, void *ctx, int64_t *res, uint64_t *spslot);
extern char a64resume[];

static uint8_t *code;
static uint64_t guard_pc;
static __thread uint64_t tl_sp, tl_pc;
static __thread int tl_sig;
static __thread uint64_t tl_ctx[64];
static uint64_t fpcr_mode;

static void handler(int sig, siginfo_t *si, void *uv) {
  (void)si;
  ucontext_t *uc = (ucontext_t *)uv;
#ifdef __APPLE__
  tl_pc = uc->uc_mcontext->__ss.__pc;
  uc->uc_mcontext->__ss.__sp = tl_sp;
  uc->uc_mcontext->__ss.__pc = (uint64_t)a64resume;
#else
  tl_pc = uc->uc_mcontext.pc;
  uc->uc_mcontext.sp = tl_sp;
  uc->uc_mcontext.pc = (uint64_t)a64resume;
#endif
  tl_sig = sig;
}
static void setfpcr(uint64_t v) { __asm__ volatile("msr fpcr, %0" :: "r"(v)); }
static unsigned long badtrap;   /* main thread only; workers report through the block buffer */
/* 0 returned, 1 trapped at the guard, 2 any other trap */
static int call(uint32_t b, int64_t *r) {
  tl_ctx[1] = 1000000; tl_ctx[48] = (uint64_t)code;
  tl_sig = 0;
  int t = (int)a64call(code, (uint64_t)(int64_t)(int32_t)b, tl_ctx, r, &tl_sp);
  if (!t) return 0;
  return (tl_sig == SIGTRAP && tl_pc == guard_pc) ? 1 : 2;
}
static void puts_(const char *s) { fputs(s, stdout); }
static void hex(uint64_t v, int n) { printf("%0*llx ", n, (unsigned long long)v); }
static void dec(uint64_t v) { printf("%llu ", (unsigned long long)v); }
static uint64_t seed = 633;
static uint64_t rnd(void) { seed = seed * 6364136223846793005ull + 1442695040888963407ull; return seed >> 17; }
static uint64_t fnv = 1469598103934665603ull;
static void mix(uint64_t v) { for (int i = 0; i < 8; i++) { fnv ^= (v >> (8 * i)) & 255; fnv *= 1099511628211ull; } }
static unsigned long cases, returned, traps, diffs, indef, shown;
static void account(uint32_t b, int k, int64_t r) {
  int64_t want = 0;
  int wt = ref_f32_to_i64(b, &want);
  if (k == 2) badtrap++;
  int t = k != 0;
  cases++;
  if (t) traps++; else returned++;
  mix(((uint64_t)t << 32) ^ b); if (!t) mix((uint64_t)r);
  if (!t && r == INT64_MIN && b != 0xdf000000u) indef++;
  if (t != wt || (!t && r != want) || k == 2) {
    diffs++;
    if (shown++ < 12) { puts_("DIFF "); hex(b, 8); puts_(k == 2 ? "badtrap " : t ? "trap " : "ret "); if (!t) hex((uint64_t)r, 16);
      puts_(wt ? "want-trap" : "want "); if (!wt) hex((uint64_t)want, 16); putchar('\n'); }
  }
}
static void one(uint32_t b) { int64_t r = 0; int k = call(b, &r); account(b, k, r); }

#define BLK (1u << 22)
static int nthreads = 8;
static uint8_t *bk; static int64_t *br;
struct job { uint64_t lo, hi, base; };
static void *worker(void *p) {
  struct job *j = p;
  setfpcr(fpcr_mode);
  for (uint64_t i = j->lo; i < j->hi; i++) { int64_t r = 0; bk[i] = (uint8_t)call((uint32_t)((j->base + i) * STRIDE), &r); br[i] = r; }
  return 0;
}
static void sweep(void) {
  uint64_t n = (0x100000000ull + STRIDE - 1) / STRIDE;
  pthread_t th[64]; struct job jb[64];
  for (uint64_t base = 0; base < n; base += BLK) {
    uint64_t m = n - base < BLK ? n - base : BLK;
    for (int t = 0; t < nthreads; t++) {
      jb[t].lo = m * t / nthreads; jb[t].hi = m * (t + 1) / nthreads; jb[t].base = base;
      pthread_attr_t a; pthread_attr_init(&a); pthread_attr_setstacksize(&a, 1 << 20);
      if (pthread_create(&th[t], &a, worker, &jb[t])) { puts_("pthread_create failed\n"); exit(2); }
    }
    for (int t = 0; t < nthreads; t++) pthread_join(th[t], 0);
    for (uint64_t i = 0; i < m; i++) account((uint32_t)((base + i) * STRIDE), bk[i], br[i]);
  }
}
static const uint32_t SPECIAL[] = {
  0x00000000u, 0x80000000u,
  0x00000001u, 0x00000002u, 0x003fffffu, 0x00400000u, 0x007fffffu,
  0x80000001u, 0x80000002u, 0x803fffffu, 0x80400000u, 0x807fffffu,
  0x00800000u, 0x80800000u, 0x3effffffu, 0x3f000000u, 0xbf000000u, 0x3f7fffffu, 0xbf7fffffu,
  0x3f800000u, 0xbf800000u, 0x3fc00000u, 0xbfc00000u, 0x40200000u, 0xc0200000u, 0x40600000u, 0xc0600000u,
  0x7f800000u, 0xff800000u,
  0x7fc00000u, 0xffc00000u, 0x7fc00001u, 0x7fc12345u, 0xffe5a5a5u, 0x7fffffffu, 0xffffffffu,
  0x7f800001u, 0xff800001u, 0x7f812345u, 0x7fbfffffu, 0xffbfffffu, 0xffa5a5a5u,
  0x5f000000u, 0x5effffffu, 0x5f000001u, 0x5f7fffffu, 0x5f800000u,
  0xdf000000u, 0xdeffffffu, 0xdf000001u, 0xdf7fffffu, 0xdf800000u,
  0x5e800000u, 0x5e7fffffu, 0x5e800001u, 0xde800000u, 0xde7fffffu, 0xde800001u,
  0x4f000000u, 0x4effffffu, 0x4f000001u, 0xcf000000u, 0xceffffffu, 0xcf000001u,
  0x4f800000u, 0x4f7fffffu, 0x4f800001u, 0xcf800000u, 0xcf7fffffu, 0xcf800001u,
  0x4b800000u, 0x4b7fffffu, 0x4b800001u, 0xcb800000u, 0xcb7fffffu, 0xcb800001u,
  0x4b000000u, 0x4b000001u, 0x4affffffu, 0xcb000001u, 0xcaffffffu,
  0x7f7fffffu, 0xff7fffffu,
};
static void suite(void) {
  setfpcr(fpcr_mode);
  for (unsigned i = 0; i < sizeof SPECIAL / sizeof SPECIAL[0]; i++) one(SPECIAL[i]);
  for (uint32_t e = 0; e < 256; e++)
    for (uint32_t s = 0; s < 2; s++)
      for (uint32_t k = 0; k < 8; k++) { one((s << 31) | (e << 23) | k); one((s << 31) | (e << 23) | (0x7fffffu - k)); }
  sweep();
  setfpcr(fpcr_mode);
  for (unsigned k = 0; k < NRAND; k++) one((uint32_t)rnd() ^ ((uint32_t)rnd() << 13));
  for (unsigned k = 0; k < NRAND; k++)
    one((uint32_t)(rnd() & 1) << 31 | (uint32_t)(123 + rnd() % 67) << 23 | ((uint32_t)rnd() & 0x7fffffu));
}
/* the guard's tail: fcmp s1,s0 ; b.gt +2 ; brk #0 ; fcvtzs */
static long find_guard(const uint8_t *p, size_t n) {
  long at = -1; int hits = 0;
  for (size_t i = 0; i + 16 <= n; i += 4) {
    uint32_t w[4]; memcpy(w, p + i, 16);
    if (w[0] == 0x1e202020u && w[1] == 0x5400004cu && w[2] == 0xd4200000u && (w[3] & 0xfffffc00u) == 0x9e380000u) { at = (long)i + 8; hits++; }
  }
  return hits == 1 ? at : -1;
}
int main(int argc, char **argv) {
  if (argc < 2) { fprintf(stderr, "usage: %s f2i.bin [threads]\n", argv[0]); return 2; }
  if (argc > 2) nthreads = atoi(argv[2]);
  if (nthreads < 1 || nthreads > 64) return 2;
  FILE *f = fopen(argv[1], "rb"); if (!f) return 2;
  static uint8_t img[1 << 16]; size_t n = fread(img, 1, sizeof img, f); fclose(f);
  long g = find_guard(img, n);
  /* a mutant may have removed the guard's brk: then BADTRAP / DIFFS say so; the offset of the unmutated guard is given */
  if (g < 0 && argc > 3) g = strtol(argv[3], 0, 0);
  if (g < 0) { fprintf(stderr, "guard not found exactly once\n"); return 2; }
#ifdef __APPLE__
  code = mmap(0, 1 << 16, PROT_READ | PROT_WRITE | PROT_EXEC, MAP_PRIVATE | MAP_ANON | MAP_JIT, -1, 0);
  if (code == MAP_FAILED) return 3;
  pthread_jit_write_protect_np(0); memcpy(code, img, n); pthread_jit_write_protect_np(1);
  sys_icache_invalidate(code, n);
#else
  code = mmap(0, 1 << 16, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (code == MAP_FAILED) return 3;
  memcpy(code, img, n);
  if (mprotect(code, 1 << 16, PROT_READ | PROT_EXEC)) return 3;
  __builtin___clear_cache((char *)code, (char *)code + n);
#endif
  guard_pc = (uint64_t)code + (uint64_t)g;
  bk = malloc(BLK); br = malloc(sizeof(int64_t) * BLK);
  struct sigaction sa; memset(&sa, 0, sizeof sa); sa.sa_sigaction = handler; sa.sa_flags = SA_SIGINFO | SA_NODEFER;
  sigaction(SIGTRAP, &sa, 0); sigaction(SIGILL, &sa, 0); sigaction(SIGSEGV, &sa, 0); sigaction(SIGBUS, &sa, 0);
  printf("F2IDIFF payload %zu bytes guard brk at +0x%lx threads %d stride %llu nrand %d\n", n, g, nthreads,
         (unsigned long long)STRIDE, NRAND);
  fpcr_mode = 0;                puts_("FPCR 0\n"); suite();
  fpcr_mode = 1ull << 22;       puts_("FPCR 400000\n"); suite();
  setfpcr(0);
  puts_("CASES "); dec(cases); puts_("RETURNED "); dec(returned); puts_("TRAPS "); dec(traps); putchar('\n');
  puts_("DIFFS "); dec(diffs); puts_("INDEF "); dec(indef); puts_("BADTRAP "); dec(badtrap); putchar('\n');
  puts_("HASH "); hex(fnv, 16); putchar('\n');
  puts_("DONE\n");
  return 0;
}
