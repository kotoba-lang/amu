/* J-B falsification control: upper bound of runtime constant-divisor
 * specialization on the serial imod chain (ADR 0289's residual).
 * Arm A: divisor opaque (what amu emits today -- hardware sdiv per element).
 * Arm B: divisor a compile-time constant at a CALL boundary (noinline callee
 *        -- smulh+asr strength reduction, same shape gcc/clang emit).
 * Arm C: same constant-divisor strength-reduced body INLINED into the loop
 *        (no call boundary). C exists to separate lever 2 (call overhead)
 *        from lever 1 (sdiv->mulh instruction swap): lever1 = A vs B,
 *        lever2 = B vs C.
 * Serial dependency chain acc = imod(acc*31 + v[i], M), latency-bound.
 * All three arms return the same checksum; no loop is deletable. */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <time.h>

#define N 200
#define M 1000003

volatile int64_t g_m = M; /* truly opaque: volatile load, compiler cannot fold */

static int c1(const void *x, const void *y){ double a=*(const double*)x,b=*(const double*)y; return (a>b)-(a<b); }

__attribute__((noinline)) static int64_t imod_opaque(int64_t a, int64_t m) {
    /* exactly the guard shape ADR 0289 counted: overflow guard + sdiv */
    int64_t q = a / m;
    int64_t r = a % m;
    return r < 0 ? r + m : r;
}

__attribute__((noinline)) static int64_t imod_const(int64_t a) {
    int64_t q = a / M;   /* constant divisor: clang emits mulh+asr, no sdiv */
    int64_t r = a % M;
    return r < 0 ? r + M : r;
}

/* Same strength-reduced body as imod_const, but a plain static fn that
 * clang -O2 inlines into the caller (verify by disassembly: no bl, smulh
 * present in the loop body). */
static int64_t imod_const_inl(int64_t a) {
    int64_t q = a / M;
    int64_t r = a % M;
    return r < 0 ? r + M : r;
}

static int64_t data[N];

__attribute__((noinline)) static int64_t arm_opaque(int64_t acc) {
    for (int i = 0; i < N; i++) acc = imod_opaque(acc * 31 + data[i], g_m);
    return acc;
}

__attribute__((noinline)) static int64_t arm_const(int64_t acc) {
    for (int i = 0; i < N; i++) acc = imod_const(acc * 31 + data[i]);
    return acc;
}

__attribute__((noinline)) static int64_t arm_inl(int64_t acc) {
    for (int i = 0; i < N; i++) acc = imod_const_inl(acc * 31 + data[i]);
    return acc;
}

static double now_ns(void) {
    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1e9 + ts.tv_nsec;
}

int main(int argc, char **argv) {
    long iters = argc > 1 ? atol(argv[1]) : 200000;
    srandom(7);
    for (int i = 0; i < N; i++) data[i] = (int64_t)(random() % 1000000);

    /* calibrate + correctness */
    int64_t a0 = arm_opaque(5), b0 = arm_const(5), c0 = arm_inl(5);
    if (a0 != b0 || a0 != c0) { printf("MISMATCH %lld %lld %lld\n", (long long)a0, (long long)b0, (long long)c0); return 1; }

    /* ABC-interleaved alternations; report medians (loaded-host diagnostic,
     * ADR 0289 style: ratios only). lever1 = A vs B (sdiv->mulh, call
     * boundary kept); lever2 = B vs C (same strength-reduced body inlined,
     * call boundary removed). */
    int alts = argc > 2 ? atoi(argv[2]) : 40;
    long block = iters / 10;
    double *na = malloc(sizeof(double) * alts), *nb = malloc(sizeof(double) * alts), *nc = malloc(sizeof(double) * alts);
    for (int r = 0; r < alts; r++) {
        double t0 = now_ns();
        int64_t acc = 5;
        for (long k = 0; k < block; k++) acc += arm_opaque(k & 1023) - (acc & 0);
        double t1 = now_ns();
        int64_t acc2 = 5;
        for (long k = 0; k < block; k++) acc2 += arm_const(k & 1023) - (acc2 & 0);
        double t2 = now_ns();
        int64_t acc3 = 5;
        for (long k = 0; k < block; k++) acc3 += arm_inl(k & 1023) - (acc3 & 0);
        double t3 = now_ns();
        if (acc != acc2 || acc != acc3) { printf("MISMATCH run\n"); return 1; }
        na[r] = (t1 - t0) / ((double)block * N);
        nb[r] = (t2 - t1) / ((double)block * N);
        nc[r] = (t3 - t2) / ((double)block * N);
    }
    qsort(na, alts, sizeof(double), c1); qsort(nb, alts, sizeof(double), c1); qsort(nc, alts, sizeof(double), c1);
    double medA = na[alts/2], medB = nb[alts/2], medC = nc[alts/2];
    printf("median over %d alternations:\n", alts);
    printf("  A opaque(sdiv)        %.3f ns/elem\n", medA);
    printf("  B const-call(mulh)    %.3f ns/elem\n", medB);
    printf("  C const-inline(mulh)  %.3f ns/elem\n", medC);
    printf("  lever1 A/B ratio %.3f saving %.1f%%   lever2 B/C ratio %.3f saving %.1f%%\n",
           medA / medB, 100.0 * (medA - medB) / medA,
           medB / medC, 100.0 * (medB - medC) / medB);
    printf("checksum ok (arms agree: %lld)\n", (long long)a0);
    return 0;
}
