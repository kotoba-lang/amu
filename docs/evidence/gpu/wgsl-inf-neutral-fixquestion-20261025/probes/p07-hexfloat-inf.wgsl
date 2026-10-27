// probe p07 -- spelling infinity through a hex float literal instead of a
// bitcast: 0x1p128 = 2^128, finite as AbstractFloat, converts to f32 as
// +inf. gpuweb resolved 2021-08-03 (issue 1769): "When writing hex float
// literals, it is impossible to spell infinity or nan, or values larger
// than the max float ... and doing so would be a compile error".
// Expected: shader-creation error (which message is recorded, not predicted).
@group(0) @binding(0) var<storage,read> x: array<f32>;
@group(0) @binding(1) var<storage,read_write> out: array<f32>;
@compute @workgroup_size(1) fn main() {
  let k: f32 = 0x1p128;
  out[0] = k + x[0] * 0.0;
}
