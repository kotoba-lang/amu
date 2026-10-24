// probe p06 -- the :min row's spelling, positive infinity
// (bitcast<f32>(0x7F800000u)). Expected per spec 15.7: shader-creation error.
@group(0) @binding(0) var<storage,read> x: array<f32>;
@group(0) @binding(1) var<storage,read_write> out: array<f32>;
@compute @workgroup_size(1) fn main() {
  let k = bitcast<f32>(0x7F800000u);
  out[0] = k + x[0] * 0.0;
}
