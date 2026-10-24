// probe p00 CONTROL -- finite bitcast, same spelling class as the arm's
// neutral but a FINITE value (IEEE-754 max finite, 0x7F7FFFFFu). If the
// refusal class were about `bitcast` itself this file would also fail.
// Expected: VALIDATES CLEAN.
@group(0) @binding(0) var<storage,read> x: array<f32>;
@group(0) @binding(1) var<storage,read_write> out: array<f32>;
@compute @workgroup_size(1) fn main() {
  let k = bitcast<f32>(0x7F7FFFFFu);
  out[0] = k + x[0] * 0.0;
}
