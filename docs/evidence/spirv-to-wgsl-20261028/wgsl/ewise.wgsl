@group(0) @binding(0) var<storage, read> b_0: array<f32>;
@group(0) @binding(1) var<storage, read> b_1: array<f32>;
@group(0) @binding(2) var<storage, read_write> b_2: array<f32>;
struct S_17 { m0: u32, };
@group(0) @binding(3) var<storage, read> b_3: S_17;
@compute @workgroup_size(64, 1, 1)
fn main(@builtin(global_invocation_id) i_22: vec3<u32>) {
  let v_23 = i_22;
  let v_24 = v_23.x;
  let v_28 = b_3.m0;
  let v_30 = (v_24 < v_28);
  if (v_30) {
  let v_36 = b_0[v_24];
  let v_38 = b_1[v_24];
  let v_39 = (v_36 + v_38);
  b_2[v_24] = v_39;
  } else {
  }
  return;
}
