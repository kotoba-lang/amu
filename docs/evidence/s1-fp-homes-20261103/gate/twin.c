/* C twins of the gate programs. Build: cc -O2 -ffp-contract=off -DPROG=n [-DROWS -DCOLS -DREPS -DACC]. */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define MASK48 281474976710655LL
static int64_t lcg(int64_t s) { return (s * 1103515245 + 12345) & 2147483647; }
static uint32_t bits(float f) { uint32_t u; memcpy(&u, &f, 4); return u; }
static float fb(uint32_t u) { float f; memcpy(&f, &u, 4); return f; }
static int64_t mix(int64_t c, float x) { return (c * 31 + (int64_t)bits(x)) & MASK48; }
static int64_t fill(float *v, int64_t n, int64_t s) {
    for (int64_t i = 0; i < n; i++) { s = lcg(s); v[i] = (float)(((s >> 16) & 255) - 128) * fb(0x3c2f5c29); }
    return s;
}
#if PROG == 1
static float row_dot(const float *W, const float *x) {
#if ACC == 1
    float acc = 0.0f;
    for (int k = 0; k < COLS; k++) acc = acc + W[k] * x[k];
    return acc;
#else
    float a0 = 0, a1 = 0, a2 = 0, a3 = 0;
    for (int k = 0; k < COLS; k += 4) {
        a0 = a0 + W[k] * x[k]; a1 = a1 + W[k + 1] * x[k + 1];
        a2 = a2 + W[k + 2] * x[k + 2]; a3 = a3 + W[k + 3] * x[k + 3];
    }
    return (a0 + a1) + (a2 + a3);
#endif
}
int main(void) {
    float *W = malloc(sizeof(float) * ROWS * COLS), *x = malloc(sizeof(float) * COLS);
    int64_t s = fill(W, (int64_t)ROWS * COLS, 12345); s = fill(x, COLS, s);
    int64_t c = s & MASK48;
    for (int i = 0; i < REPS; i++) for (int r = 0; r < ROWS; r++) c = mix(c, row_dot(W + (int64_t)r * COLS, x));
    printf("%lld\n", (long long)c);
}
#elif PROG == 2
int main(void) {  /* rms.kotoba */
    float x[COLS], w[COLS];
    int64_t s = fill(x, COLS, 777); s = fill(w, COLS, s);
    int64_t c = s & MASK48;
    for (int rep = 0; rep < REPS; rep++) {
        float ss = 0.0f;
        for (int i = 0; i < COLS; i++) ss = ss + x[i] * x[i];
        float r = sqrtf(ss / (float)COLS + fb(0x3727c5ac));
        for (int i = 0; i < COLS; i++) c = mix(c, (x[i] / r) * w[i]);
    }
    printf("%lld\n", (long long)c);
}
#elif PROG == 3
static float tri(int64_t n) { float acc = (float)1; for (int64_t i = 0; i < n; i++) acc = acc + (float)i * fb(0x3c2f5c29); return acc; }
static int64_t wave(int64_t n) {
    int64_t c = 0; float b = 0, a = 0;
    for (int64_t i = 0; i < n; i++) {
        int64_t c2 = (a < b) ? c + 1 : ((a >= fb(0x40400000)) ? c + 3 : c);
        float b2 = (float)(i - 37) * fb(0x3c2f5c29) - fb(0x3f000000);
        float a2 = sqrtf(fabsf(a)) + -b;
        c = c2; b = b2; a = a2;
    }
    return mix(mix(c, a), b);
}
static float conv(int64_t n) { float acc = (float)0.25; for (int64_t i = 0; i < n; i++) acc = acc + (float)((double)i * 0.001); return acc; }
static float swap(int64_t n) { float p = 1.0f, q = 2.0f; for (int64_t i = 0; i < n; i++) { float p2 = q * fb(0x3f000000), q2 = p + q; p = p2; q = q2; } return p - q; }
static float rot(int64_t n) { float p = 3.0f, q = 5.0f; for (int64_t i = 0; i < n; i++) { float p2 = q, q2 = p * fb(0x3f000000) + q; p = p2; q = q2; } return p / q; }
int main(void) {
    int64_t c = 7;
    c = mix(c, tri(1000));
    c = (c * 31 + wave(500)) & MASK48;
    c = mix(c, conv(300));
    c = mix(c, swap(40));
    c = mix(c, rot(25));
    printf("%lld\n", (long long)c);
}
#endif
