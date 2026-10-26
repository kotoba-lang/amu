// probe p05 -- the RUNTIME-ESCAPE hypothesis: same infinite bit pattern,
// but the expression carries a runtime operand (r & 0u, r from a storage
// read), so `bitcast<f32>(0xFF800000u | (r & 0u))` is a RUNTIME expression,
// not a const-expression (spec 8.1.1: a const-expression's identifiers all
// resolve to const-declarations/const-functions/type aliases/structure
// names). This discriminates "const-eval-only refusal" from "the value
// itself is banned". If a validator accepts this, the refusal is scoped to
// const-evaluation -- but the Finite Math Assumption ("implementations may
// assume that overflow, infinities, and NaNs are not present during shader
// execution ... the final result will be an indeterminate value") still
// makes the escape non-portable as a sentinel. DISCRIMINATING PROBE: the
// verdict is recorded, not predicted.
@group(0) @binding(0) var<storage,read> x: array<f32>;
@group(0) @binding(1) var<storage,read_write> out: array<f32>;
@compute @workgroup_size(1) fn main() {
  let r = u32(x[0] > x[1]);
  let k = bitcast<f32>(0xFF800000u | (r & 0u));
  out[0] = k + x[0] * 0.0;
}
