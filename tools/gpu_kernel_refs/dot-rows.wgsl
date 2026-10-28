struct S7 { m0: u32, m1: u32, };
@group(0) @binding(0) var<storage, read> b0: S7;
@group(0) @binding(1) var<storage, read> b1: array<f32>;
@group(0) @binding(2) var<storage, read> b2: array<f32>;
@group(0) @binding(3) var<storage, read_write> b3: array<f32>;
var<workgroup> s23: array<f32, 256>;
@compute @workgroup_size(256, 1, 1)
fn main(@builtin(workgroup_id) i33: vec3<u32>, @builtin(local_invocation_id) i36: vec3<u32>) {
  var f25: u32;
  var f26: u32;
  var f28: f32;
  let v34 = i33;
  let v35 = v34.x;
  let v37 = i36;
  let v38 = v37.x;
  let v41 = b0.m0;
  let v43 = (v35 >= v41);
  if (v43) {
  return;
  } else {
  }
  let v49 = b0.m1;
  f28 = bitcast<f32>(0u);
  f25 = v38;
  loop {
  let v54 = f25;
  let v55 = (v54 < v49);
  if (!(v55)) { break; }
  let v57 = f25;
  let v58 = (v35 * v49);
  let v59 = (v58 + v57);
  let v62 = b1[v59];
  let v64 = b2[v57];
  let v65 = (v62 * v64);
  let v66 = f28;
  let v67 = (v66 + v65);
  f28 = v67;
  continuing {
  let v68 = f25;
  let v69 = (v68 + 256u);
  f25 = v69;
  }
  }
  let v72 = f28;
  s23[v38] = v72;
  workgroupBarrier();
  f26 = 128u;
  loop {
  let v80 = f26;
  let v81 = (v80 > 0u);
  if (!(v81)) { break; }
  let v83 = f26;
  let v84 = (v38 < v83);
  if (v84) {
  let v89 = s23[v38];
  let v90 = (v38 + v83);
  let v92 = s23[v90];
  let v94 = (v89 + v92);
  s23[v38] = v94;
  } else {
  }
  workgroupBarrier();
  continuing {
  let v95 = f26;
  let v96 = (v95 >> 1u);
  f26 = v96;
  }
  }
  let v97 = (v38 == 0u);
  if (v97) {
  let v103 = s23[0u];
  b3[v35] = v103;
  } else {
  }
  return;
}
