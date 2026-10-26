// probe p02 -- the infinite neutral in a let-declaration initializer.
// `bitcast` is `@const`, so the initializer is a const-expression.
// Expected per spec 15.7 Finite Math Assumption: shader-creation error.
@group(0) @binding(0) var<storage,read> x: array<f32>;
@group(0) @binding(1) var<storage,read_write> out: array<f32>;
@compute @workgroup_size(1) fn main() {
  let k = bitcast<f32>(0xFF800000u);
  out[0] = k + x[0] * 0.0;
}
