struct S_7 { m0: u32, m1: u32, };
@group(0) @binding(0) var<storage, read> b_0: S_7;
@group(0) @binding(1) var<storage, read> b_1: array<f32>;
@group(0) @binding(2) var<storage, read> b_2: array<f32>;
@group(0) @binding(3) var<storage, read_write> b_3: array<f32>;
var<workgroup> s_23: array<f32, 256>;
@compute @workgroup_size(256, 1, 1)
fn main(@builtin(workgroup_id) i_33: vec3<u32>, @builtin(local_invocation_id) i_36: vec3<u32>) {
  var f_25: u32;
  var f_26: u32;
  var f_28: f32;
  let v_34 = i_33;
  let v_35 = v_34.x;
  let v_37 = i_36;
  let v_38 = v_37.x;
  let v_41 = b_0.m0;
  let v_43 = (v_35 >= v_41);
  if (v_43) {
  return;
  } else {
  }
  let v_49 = b_0.m1;
  f_28 = bitcast<f32>(0u);
  f_25 = v_38;
  loop {
  let v_54 = f_25;
  let v_55 = (v_54 < v_49);
  if (!(v_55)) { break; }
  let v_57 = f_25;
  let v_58 = (v_35 * v_49);
  let v_59 = (v_58 + v_57);
  let v_62 = b_1[v_59];
  let v_64 = b_2[v_57];
  let v_65 = (v_62 * v_64);
  let v_66 = f_28;
  let v_67 = (v_66 + v_65);
  f_28 = v_67;
  continuing {
  let v_68 = f_25;
  let v_69 = (v_68 + 256u);
  f_25 = v_69;
  }
  }
  let v_72 = f_28;
  s_23[v_38] = v_72;
  workgroupBarrier();
  f_26 = 128u;
  loop {
  let v_80 = f_26;
  let v_81 = (v_80 > 0u);
  if (!(v_81)) { break; }
  let v_83 = f_26;
  let v_84 = (v_38 < v_83);
  if (v_84) {
  let v_89 = s_23[v_38];
  let v_90 = (v_38 + v_83);
  let v_92 = s_23[v_90];
  let v_94 = (v_89 + v_92);
  s_23[v_38] = v_94;
  } else {
  }
  workgroupBarrier();
  continuing {
  let v_95 = f_26;
  let v_96 = (v_95 >> 1u);
  f_26 = v_96;
  }
  }
  let v_97 = (v_38 == 0u);
  if (v_97) {
  let v_103 = s_23[0u];
  b_3[v_35] = v_103;
  } else {
  }
  return;
}
