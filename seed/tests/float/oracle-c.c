/* seed/tests/float/oracle-c.c -- FLOAT (r6j) BOOTSTRAP-TOOL oracle for the float operations stage-0 refuses natively
   (f32-min, f32-max, f64-to-i64-truncating, f32-to-i64-truncating). Semantics of the JVM reference (kir.interp's host reading):
   Math.min/Math.max (a NaN operand is the result; -0.0 < +0.0) and the (long) narrowing (NaN -> 0, saturating).
   A signalling-NaN operand of f32-min/f32-max is marked: the line is "snan <java value>". The seed (fmin/fmax s, as stage-0's
   native f64-min/f64-max fmin/fmax d, measured identical to stage-0 on the f64 sNaN vectors) answers the QUIETED NaN there
   (hardware rule: an sNaN operand wins and is quieted), Java's interpreted Math.min the raw operand; float-diff.sh counts these
   as SNAN, not as a difference (a JIT-compiled Math.min on aarch64 is fmin too).
   usage: oracle-c <op> <a> <b>  (bit patterns as signed decimal; prints the export's i64 result) */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
static float f32(int64_t b) { uint32_t u = (uint32_t)b; float f; memcpy(&f, &u, 4); return f; }
static double f64(int64_t b) { double d; memcpy(&d, &b, 8); return d; }
static int64_t bits32(float f) { int32_t i; memcpy(&i, &f, 4); return (int64_t)i; }
static float jmin(float a, float b) { if (a != a) return a; if (a == 0.0f && b == 0.0f && signbit(b)) return b; return (a <= b) ? a : b; }
static float jmax(float a, float b) { if (a != a) return a; if (a == 0.0f && b == 0.0f && signbit(a)) return b; return (a >= b) ? a : b; }
static int64_t jlong(double x) { if (x != x) return 0; if (x >= 9223372036854775807.0) return INT64_MAX; if (x <= -9223372036854775808.0) return INT64_MIN; return (int64_t)x; }
int main(int argc, char **argv) {
  if (argc < 4) return 2;
  const char *op = argv[1]; int64_t a = strtoll(argv[2], 0, 10), b = strtoll(argv[3], 0, 10);
  int snan = (((uint32_t)a & 0x7fc00000u) == 0x7f800000u && ((uint32_t)a & 0x3fffffu)) ||
             (((uint32_t)b & 0x7fc00000u) == 0x7f800000u && ((uint32_t)b & 0x3fffffu));
  if (snan && (!strcmp(op, "f32-min") || !strcmp(op, "f32-max"))) printf("snan ");
  if (!strcmp(op, "f32-min")) printf("%lld\n", (long long)bits32(jmin(f32(a), f32(b))));
  else if (!strcmp(op, "f32-max")) printf("%lld\n", (long long)bits32(jmax(f32(a), f32(b))));
  else if (!strcmp(op, "f64-to-i64-truncating")) printf("%lld\n", (long long)jlong(f64(a)));
  else if (!strcmp(op, "f32-to-i64-truncating")) printf("%lld\n", (long long)jlong((double)f32(a)));
  else { fprintf(stderr, "oracle-c: no oracle for %s\n", op); return 2; }
  return 0;
}
