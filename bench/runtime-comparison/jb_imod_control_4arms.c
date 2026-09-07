/* J-B falsification control v2 (4-arm): separates lever 1 (constant-divisor
 * strength reduction sdiv->mulh+asr) from lever 2 (helper-call inlining) on
 * the serial imod chain of ADR 0289's residual.
 *
 * The sealed control jb_imod_control.c is UNTOUCHED; arms A and B here are
 * the same shapes as its two arms (both keep a real noinline call).
 *   A: opaque divisor, helper NOT inlined   (what amu emits today)
 *   B: constant divisor, helper NOT inlined (lever 1 only  = sealed arm B)
 *   C: opaque divisor, body hand-INLINED    (lever 2 only: inlining without
 *                                            divisor specialization; sdiv stays)
 *   D: constant divisor, body hand-INLINED  (levers 1+2 combined)
 * Additivity check: if saving(A->D) ~= saving(A->B) + saving(B->D) then the
 * levers are independent; if lever-2 share dominates, J-B alone cannot reach
 * the 5% bar and must be re-composed with inlining (evolution rule 5).
 * All four arms must return the same checksum from the same seed. */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <time.h>

#define N 200
#define M 1000003

volatile int64_t g_m = M; /* truly opaque: volatile load, compiler cannot fold */

static int c1(const void *x, const void *y){ double a=*(const double*)x,b=*(const double*)y; return (a>b)-(a<b); }

__attribute__((noinline)) static int64_t imod_opaque(int64_t a, int64_t m) {
    int64_t q = a / m;
    int64_t r = a % m;
    return r < 0 ? r + m : r; /* same guard shape as sealed control */
}

__attribute__((noinline)) static int64_t imod_const(int64_t a) {
    int64_t q = a / M;
    int64_t r = a % M;
    return r < 0 ? r + M : r;
}

static int64_t data[N];

/* A: opaque, call preserved (identical to sealed control arm A) */
__attribute__((noinline)) static int64_t arm_opaque(int64_t acc) {
    for (int i = 0; i < N; i++) acc = imod_opaque(acc * 31 + data[i], g_m);
    return acc;
}
/* B: constant divisor, call preserved (identical to sealed control arm B) */
__attribute__((noinline)) static int64_t arm_const(int64_t acc) {
    for (int i = 0; i < N; i++) acc = imod_const(acc * 31 + data[i]);
    return acc;
}
/* C: opaque divisor, helper body inlined by hand; sdiv stays.
 * Guard written exactly as the callee body so only inlining differs. */
__attribute__((noinline)) static int64_t arm_opaque_inl(int64_t acc) {
    for (int i = 0; i < N; i++) {
        int64_t t = acc * 31 + data[i];
        int64_t r = t % g_m;              /* opaque: hardware sdiv path */
        acc = r < 0 ? r + g_m : r;
    }
    return acc;
}
/* D: constant divisor inlined (levers 1+2). Compiler folds %M to mulh+asr. */
__attribute__((noinline)) static int64_t arm_const_inl(int64_t acc) {
    for (int i = 0; i < N; i++) {
        int64_t t = acc * 31 + data[i];
        int64_t r = t % M;
        acc = r < 0 ? r + M : r;
    }
    return acc;
}

static double now_ns(void) {
    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1e9 + ts.tv_nsec;
}

int main(int argc, char **argv) {
    long iters = argc > 1 ? atol(argv[1]) : 200000;
    int alts = argc > 2 ? atoi(argv[2]) : 24;
    srandom(7);
    for (int i = 0; i < N; i++) data[i] = (int64_t)(random() % 1000000);

    /* correctness: all four arms must agree */
    int64_t a0 = arm_opaque(5), b0 = arm_const(5), c0 = arm_opaque_inl(5), d0 = arm_const_inl(5);
    if (!(a0 == b0 && b0 == c0 && c0 == d0)) {
        printf("MISMATCH %lld %lld %lld %lld\n", (long long)a0, (long long)b0, (long long)c0, (long long)d0);
        return 1;
    }

    long block = iters / 4;
    double *s[4] = {malloc(sizeof(double)*alts),malloc(sizeof(double)*alts),malloc(sizeof(double)*alts),malloc(sizeof(double)*alts)};
    /* rotate arm order per alternation to kill position bias */
    for (int r = 0; r < alts; r++) {
        int64_t accs[4];
        for (int p = 0; p < 4; p++) {
            int arm = (p + r) & 3; /* rotation order varies per alternation */
            int64_t (*f)(int64_t) = arm==0?arm_opaque:arm==1?arm_const:arm==2?arm_opaque_inl:arm_const_inl;
            double tt0 = now_ns();
            int64_t acc = 5;
            for (long k = 0; k < block; k++) acc += f(k & 1023) - (acc & 0);
            double tt1 = now_ns();
            accs[arm] = acc;
            s[arm][r] = (tt1 - tt0) / ((double)block * N);
        }
        if (!(accs[0]==accs[1] && accs[1]==accs[2] && accs[2]==accs[3])) { printf("MISMATCH run %d\n", r); return 1; }
    }
    double med[4]; const char *nm[4] = {"A opaque+call","B const+call","C opaque+inl","D const+inl"};
    for (int a = 0; a < 4; a++) { qsort(s[a], alts, sizeof(double), c1); med[a] = s[a][alts/2]; }
    printf("medians over %d alternations x %ld iters:\n", alts, block);
    for (int a = 0; a < 4; a++)
        printf("  %s: %.3f ns/elem  saving vs A %+.1f%%\n", nm[a], med[a], 100.0*(med[0]-med[a])/med[0]);
    printf("lever1 (A->B) %+.1f%% | lever2 (A->C) %+.1f%% | both (A->D) %+.1f%% | B->D (marginal lever2 on const) %+.1f%% | C->D (marginal lever1 on inl) %+.1f%%\n",
        100.0*(med[0]-med[1])/med[0], 100.0*(med[0]-med[2])/med[0], 100.0*(med[0]-med[3])/med[0],
        100.0*(med[1]-med[3])/med[1], 100.0*(med[2]-med[3])/med[2]);
    printf("checksum ok (4 arms agree: %lld)\n", (long long)a0);
    return 0;
}
