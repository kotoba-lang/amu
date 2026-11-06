#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#define N (4864 * 896)
static double now(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
int main(void) {
    int64_t *w = malloc(8 * (size_t)N), *x = malloc(8 * 896);
    for (long i = 0; i < N; i++) w[i] = 0x3c000000;  /* 1/128 as sign-extended f32 bits */
    for (long i = 0; i < 896; i++) x[i] = 0x3c000000;
    for (int v = 0; v < 6; v++) {
        double best = 1e9; int64_t accw = 0; float accf = 0;
        for (int rep = 0; rep < 5; rep++) {
            double t0 = now();
            for (long r = 0; r < 4864; r++) {
                const int64_t *wr = w + r * 896; int64_t acc = 0; float fa = 0;
                for (long k = 0; k < 896; k++) {
                    int64_t a = wr[k], b = x[k], p = 0;
                    if (v == 0) {  /* Kotoba today: 4 to-fp, 2 from-fp, 2 sxtw */
                        __asm__ volatile("fmov s0, %w1\n fmov s1, %w2\n fmul s0, s0, s1\n fmov %w0, s0\n sxtw %0, %w0\n"
                                         : "=r"(p) : "r"(a), "r"(b) : "v0", "v1");
                        __asm__ volatile("fmov s0, %w1\n fmov s1, %w2\n fadd s0, s0, s1\n fmov %w0, s0\n sxtw %0, %w0\n"
                                         : "=r"(acc) : "r"(acc), "r"(p) : "v0", "v1");
                    } else if (v == 1) {  /* product stays in FP: 3 to-fp, 1 from-fp */
                        __asm__ volatile("fmov s0, %w1\n fmov s1, %w2\n fmul s1, s0, s1\n fmov s0, %w0\n fadd s0, s0, s1\n fmov %w0, s0\n sxtw %0, %w0\n"
                                         : "+r"(acc) : "r"(a), "r"(b) : "v0", "v1");
                    } else if (v == 2) {  /* accumulator in an FP register: 2 to-fp */
                        __asm__ volatile("fmov s0, %w1\n fmov s1, %w2\n fmul s1, s0, s1\n fadd %s0, %s0, s1\n"
                                         : "+w"(fa) : "r"(a), "r"(b) : "v0", "v1");
                    } else if (v == 4) {  /* S1 as built: accumulator in s16, product through a general register */
                        __asm__ volatile("fmov s0, %w1\n fmov s1, %w2\n fmul s0, s0, s1\n fmov %w3, s0\n sxtw %3, %w3\n fmov s1, %w3\n fadd %s0, %s0, s1\n"
                                         : "+w"(fa) : "r"(a), "r"(b), "r"(p) : "v0", "v1");
                    } else if (v == 5) {  /* plus the product fused into the add */
                        __asm__ volatile("fmov s0, %w1\n fmov s1, %w2\n fmul s1, s0, s1\n fadd %s0, %s0, s1\n"
                                         : "+w"(fa) : "r"(a), "r"(b) : "v0", "v1");
                    } else {  /* loads straight into FP registers */
                        __asm__ volatile("ldr s0, [%1]\n ldr s1, [%2]\n fmul s1, s0, s1\n fadd %s0, %s0, s1\n"
                                         : "+w"(fa) : "r"(wr + k), "r"(x + k) : "v0", "v1", "memory");
                    }
                }
                accw += acc; accf += fa;
            }
            double dt = now() - t0; if (dt < best) best = dt;
        }
        printf("variant %d: %.2f ms per matvec  (%lld %g)\n", v, best * 1e3, (long long)accw, accf);
    }
    return 0;
}
