// dot_rows (kotoba-lang/inference verify/native/gpu/dot_rows.comp) in WGSL:
// o[row] = sum over k of w[row cols + k] x[k], one workgroup per row.
// The golden text for ADR 0379's SPIR-V to WGSL translator (identifiers are
// generated: b<binding>, s<n> workgroup arrays; `meta` is a reserved word).
// Checked 2026-10-28 in browser WebGPU on Apple M1 Max (Metal 3): max
// relative error 1.5e-5 against an f64 sum, 4096 x 4096.
struct B0 { rows: u32, cols: u32 };
@group(0) @binding(0) var<storage, read> b0: B0;
@group(0) @binding(1) var<storage, read> b1: array<f32>;
@group(0) @binding(2) var<storage, read> b2: array<f32>;
@group(0) @binding(3) var<storage, read_write> b3: array<f32>;
var<workgroup> s0: array<f32, 256>;
@compute @workgroup_size(256)
fn main(@builtin(workgroup_id) wid: vec3<u32>, @builtin(local_invocation_id) lid: vec3<u32>) {
  let row = wid.x; let t = lid.x;
  var acc = 0.0;
  if (row < b0.rows) {
    for (var k = t; k < b0.cols; k += 256u) { acc += b1[row * b0.cols + k] * b2[k]; }
  }
  s0[t] = acc;
  workgroupBarrier();
  for (var s = 128u; s > 0u; s >>= 1u) {
    if (t < s) { s0[t] += s0[t + s]; }
    workgroupBarrier();
  }
  if (t == 0u && row < b0.rows) { b3[row] = s0[0]; }
}
