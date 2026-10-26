// probe p08 CONTROL for the Naga refusal class -- a FINITE bitcast in a
// const-declaration (IEEE-754 max finite, 0x7F7FFFFFu). Naga refused p01
// with "Not implemented as constant expression: bitcast built-in function"
// -- if p08 is refused the same way, that refusal is about bitcast
// const-eval being unimplemented in Naga, NOT about the infinite value.
// Expected: Chrome/Tint VALIDATES CLEAN (finite value, const-evaluable);
// Naga's verdict is recorded, not predicted.
@group(0) @binding(0) var<storage,read> x: array<f32>;
@group(0) @binding(1) var<storage,read_write> out: array<f32>;
@compute @workgroup_size(1) fn main() {
  const k: f32 = bitcast<f32>(0x7F7FFFFFu);
  out[0] = k + x[0] * 0.0;
}
