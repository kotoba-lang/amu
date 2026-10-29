// probe p01 -- the infinite neutral in a const-declaration initializer
// (initializer "must be a const-expression", W3C WGSL 7.2.1).
// Expected per spec 15.7 Finite Math Assumption: shader-creation error.
@group(0) @binding(0) var<storage,read> x: array<f32>;
@group(0) @binding(1) var<storage,read_write> out: array<f32>;
@compute @workgroup_size(1) fn main() {
  const k: f32 = bitcast<f32>(0xFF800000u);
  out[0] = k + x[0] * 0.0;
}
