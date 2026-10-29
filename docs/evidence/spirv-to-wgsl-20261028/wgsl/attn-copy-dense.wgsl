struct S_7 { m0: u32, m1: u32, m2: u32, m3: u32, m4: f32, m5: f32, m6: f32, m7: f32, };
@group(0) @binding(0) var<storage, read> b_0: S_7;
@group(0) @binding(1) var<storage, read> b_1: array<f32>;
@group(0) @binding(2) var<storage, read_write> b_2: array<f32>;
@group(0) @binding(3) var<storage, read_write> b_3: array<f32>;
@group(0) @binding(4) var<storage, read_write> b_4: array<f32>;
@group(0) @binding(5) var<storage, read> b_5: array<f32>;
@group(0) @binding(6) var<storage, read> b_6: array<f32>;
@group(0) @binding(7) var<storage, read_write> b_7: array<u32>;
var<workgroup> s_36: array<f32, 256>;
@compute @workgroup_size(256, 1, 1)
fn main(@builtin(workgroup_id) i_52: vec3<u32>, @builtin(local_invocation_id) i_57: vec3<u32>) {
  var f_38: u32;
  var f_39: u32;
  var f_41: f32;
  var f_42: f32;
  var f_43: f32;
  var f_44: f32;
  var f_45: u32;
  var f_46: f32;
  let v_53 = i_52;
  let v_54 = v_53.x;
  let v_55 = i_52;
  let v_56 = v_55.y;
  let v_58 = i_57;
  let v_59 = v_58.x;
  let v_62 = b_0.m0;
  let v_66 = b_0.m7;
  let v_68 = (v_66 != bitcast<f32>(0u));
  let v_70 = b_7[0u];
  let v_71 = (v_70 + 1u);
  let v_74 = b_0.m2;
  let v_75 = select(v_74, v_71, v_68);
  let v_76 = (v_75 + v_56);
  let v_79 = b_0.m3;
  let v_81 = b_0.m1;
  let v_82 = (v_81 / v_79);
  let v_83 = (v_54 / v_82);
  let v_85 = b_0.m1;
  let v_86 = (v_56 * v_85);
  let v_87 = (v_86 * v_62);
  let v_88 = (v_54 % v_82);
  let v_89 = (v_88 == 0u);
  if (v_89) {
  let v_94 = b_7[0u];
  let v_95 = (v_94 * v_79);
  let v_96 = (v_95 * v_62);
  let v_97 = (v_83 * v_62);
  let v_98 = (v_96 + v_97);
  f_38 = v_59;
  loop {
  let v_103 = f_38;
  let v_104 = (v_103 < v_62);
  if (!(v_104)) { break; }
  let v_106 = f_38;
  let v_107 = (v_98 + v_106);
  let v_109 = (v_83 * v_62);
  let v_110 = (v_109 + v_106);
  let v_112 = b_6[v_110];
  b_2[v_107] = v_112;
  let v_113 = (v_98 + v_106);
  let v_115 = (v_83 * v_62);
  let v_116 = (v_115 + v_106);
  let v_118 = b_5[v_116];
  b_3[v_113] = v_118;
  continuing {
  let v_119 = f_38;
  let v_120 = (v_119 + 256u);
  f_38 = v_120;
  }
  }
  } else {
  }
  let v_122 = b_7[0u];
  f_41 = bitcast<f32>(4048155338u);
  let v_124 = (v_59 < v_76);
  if (v_124) {
  f_42 = bitcast<f32>(0u);
  f_38 = 0u;
  loop {
  let v_132 = f_38;
  let v_133 = (v_132 < v_62);
  if (!(v_133)) { break; }
  let v_135 = f_38;
  let v_136 = (v_59 == v_122);
  if (v_136) {
  let v_140 = (v_83 * v_62);
  let v_141 = (v_140 + v_135);
  let v_143 = b_6[v_141];
  f_43 = v_143;
  } else {
  let v_144 = (v_59 * v_79);
  let v_145 = (v_144 + v_83);
  let v_146 = (v_145 * v_62);
  let v_147 = (v_146 + v_135);
  let v_149 = b_2[v_147];
  f_43 = v_149;
  }
  let v_150 = (v_54 * v_62);
  let v_151 = (v_87 + v_150);
  let v_152 = (v_151 + v_135);
  let v_154 = b_1[v_152];
  let v_155 = f_42;
  let v_156 = f_43;
  let v_157 = (v_154 * v_156);
  let v_158 = (v_155 + v_157);
  f_42 = v_158;
  continuing {
  let v_159 = f_38;
  let v_160 = (v_159 + 1u);
  f_38 = v_160;
  }
  }
  let v_161 = f_42;
  let v_164 = b_0.m5;
  let v_165 = (v_161 * v_164);
  f_41 = v_165;
  } else {
  }
  let v_166 = f_41;
  s_36[v_59] = v_166;
  workgroupBarrier();
  f_39 = 128u;
  loop {
  let v_175 = f_39;
  let v_176 = (v_175 > 0u);
  if (!(v_176)) { break; }
  let v_178 = f_39;
  let v_179 = (v_59 < v_178);
  if (v_179) {
  let v_184 = s_36[v_59];
  let v_185 = (v_59 + v_178);
  let v_187 = s_36[v_185];
  let v_190 = max(v_184, v_187);
  s_36[v_59] = v_190;
  } else {
  }
  workgroupBarrier();
  continuing {
  let v_191 = f_39;
  let v_192 = (v_191 >> 1u);
  f_39 = v_192;
  }
  }
  let v_194 = s_36[0u];
  workgroupBarrier();
  let v_195 = (v_59 < v_76);
  let v_196 = (v_166 - v_194);
  let v_197 = exp(v_196);
  let v_198 = select(bitcast<f32>(0u), v_197, v_195);
  s_36[v_59] = v_198;
  workgroupBarrier();
  f_39 = 128u;
  loop {
  let v_204 = f_39;
  let v_205 = (v_204 > 0u);
  if (!(v_205)) { break; }
  let v_207 = f_39;
  let v_208 = (v_59 < v_207);
  if (v_208) {
  let v_213 = s_36[v_59];
  let v_214 = (v_59 + v_207);
  let v_216 = s_36[v_214];
  let v_218 = (v_213 + v_216);
  s_36[v_59] = v_218;
  } else {
  }
  workgroupBarrier();
  continuing {
  let v_219 = f_39;
  let v_220 = (v_219 >> 1u);
  f_39 = v_220;
  }
  }
  let v_222 = s_36[0u];
  workgroupBarrier();
  let v_224 = (v_198 / v_222);
  s_36[v_59] = v_224;
  workgroupBarrier();
  f_38 = v_59;
  loop {
  let v_229 = f_38;
  let v_230 = (v_229 < v_62);
  if (!(v_230)) { break; }
  let v_232 = f_38;
  f_44 = bitcast<f32>(0u);
  f_45 = 0u;
  loop {
  let v_237 = f_45;
  let v_238 = (v_237 < v_76);
  if (!(v_238)) { break; }
  let v_240 = f_45;
  let v_241 = (v_240 == v_122);
  if (v_241) {
  let v_245 = (v_83 * v_62);
  let v_246 = (v_245 + v_232);
  let v_248 = b_5[v_246];
  f_46 = v_248;
  } else {
  let v_249 = (v_240 * v_79);
  let v_250 = (v_249 + v_83);
  let v_251 = (v_250 * v_62);
  let v_252 = (v_251 + v_232);
  let v_254 = b_3[v_252];
  f_46 = v_254;
  }
  let v_255 = f_44;
  let v_257 = s_36[v_240];
  let v_258 = f_46;
  let v_259 = (v_257 * v_258);
  let v_260 = (v_255 + v_259);
  f_44 = v_260;
  continuing {
  let v_261 = f_45;
  let v_262 = (v_261 + 1u);
  f_45 = v_262;
  }
  }
  let v_263 = (v_54 * v_62);
  let v_264 = (v_87 + v_263);
  let v_265 = (v_264 + v_232);
  let v_267 = f_44;
  b_4[v_265] = v_267;
  continuing {
  let v_268 = f_38;
  let v_269 = (v_268 + 256u);
  f_38 = v_269;
  }
  }
  return;
}
