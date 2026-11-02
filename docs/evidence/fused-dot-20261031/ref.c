/* The contract's accumulation tree in C (kotoba-native machine_ir x86-kernel-dot-f32 / x86-kernel-dequant-dot comments,
   qwen35_infer.c dot_scalar): four lanes, element k of each eight-block's lower half then upper half into lane k,
   (l0+l1)+(l2+l3), then the tail. Compiled with SSE, no FMA, no contraction. Compared modulo NaN payloads only, since a
   C compiler may commute a multiplication's operands. */
#include <stdint.h>
static float f(uint32_t u) { union { uint32_t u; float f; } v = { u }; return v.f; }
static uint32_t u(float x) { union { float f; uint32_t u; } v = { x }; return v.u; }
uint32_t ref_dot(const uint32_t *a, const uint32_t *b, uint64_t n) {
  float l[4] = {0, 0, 0, 0}; uint64_t i = 0;
  for (; i + 8 <= n; i += 8) {
    for (int k = 0; k < 4; k++) l[k] = l[k] + f(a[i + k]) * f(b[i + k]);
    for (int k = 0; k < 4; k++) l[k] = l[k] + f(a[i + 4 + k]) * f(b[i + 4 + k]);
  }
  float s = (l[0] + l[1]) + (l[2] + l[3]);
  for (; i < n; i++) s = s + f(a[i]) * f(b[i]);
  return u(s);
}
static uint32_t fp16(uint16_t h) {
  uint32_t sign = (uint32_t)(h & 0x8000) << 16, e = (h >> 10) & 31, m = h & 0x3ff;
  if (e == 31) return sign | 0x7f800000u | (m << 13);
  if (e == 0) { if (m == 0) return sign; float v = (float)m * (1.0f / 16777216.0f); return sign | u(v); }
  return sign | ((e + 112) << 23) | (m << 13);
}
static int ptq1_digit(uint8_t byte, int n) { static const int p[5] = {1, 3, 9, 27, 81}; return (int)((((unsigned)byte * p[n]) & 255) * 3 >> 8); }
uint32_t ref_ptq1(const uint8_t *w, const uint32_t *x, uint64_t blocks) {
  float l[4] = {0, 0, 0, 0};
  for (uint64_t k = 0; k < blocks; k++, w += 28, x += 128) {
    float d = f(fp16((uint16_t)(w[26] | (w[27] << 8))));
    for (int e = 0; e < 128; e++) {
      int o, n;
      if (e < 80) { o = e % 16; n = e / 16; } else if (e < 120) { o = 16 + (e - 80) % 8; n = (e - 80) / 8; }
      else { o = 24 + (e - 120) % 2; n = (e - 120) / 2; }
      float y = (float)(ptq1_digit(w[o], n) - 1) * d;
      l[e % 4] = l[e % 4] + y * f(x[e]);
    }
  }
  return u((l[0] + l[1]) + (l[2] + l[3]));
}
