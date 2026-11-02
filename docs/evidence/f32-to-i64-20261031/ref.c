/* The f32 -> i64 semantics of ADR 0395, from the bit pattern alone: integer arithmetic, no floating-point instruction,
   so it shares nothing with the SSE conversion it checks.
   Truncation toward zero. A NaN, an infinity and every finite value outside [-2^63, 2^63) trap (answer 1); otherwise
   the answer is 0 and *out holds the integer. -2^63 (0xdf000000) is in range and answers INT64_MIN. */
#include <stdint.h>
int ref_f32_to_i64(uint32_t b, int64_t *out) {
  uint32_t s = b >> 31, e = (b >> 23) & 0xffu, m = b & 0x7fffffu;
  if (e == 0xffu) return 1;                       /* NaN (any payload, either sign) or +-Inf */
  if (e < 127u) { *out = 0; return 0; }           /* |x| < 1: +-0, denormals, (0, 1) -> 0 */
  int sh = (int)e - 127;                          /* x = (-1)^s * 1.m * 2^sh, sh >= 0 */
  if (sh >= 63) {                                 /* |x| >= 2^63: only -2^63 itself is representable */
    if (s && sh == 63 && m == 0) { *out = INT64_MIN; return 0; }
    return 1;
  }
  uint64_t sig = (uint64_t)(m | 0x800000u);
  uint64_t mag = sh >= 23 ? sig << (sh - 23) : sig >> (23 - sh);   /* the fraction is dropped: toward zero */
  *out = s ? -(int64_t)mag : (int64_t)mag;
  return 0;
}
