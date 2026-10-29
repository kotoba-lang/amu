struct S_9 { m0: u32, m1: u32, };
@group(0) @binding(0) var<storage, read> b_0: S_9;
@group(0) @binding(1) var<storage, read> b_1: array<vec4<u32>>;
@group(0) @binding(2) var<storage, read> b_2: array<vec4<f32>>;
@group(0) @binding(3) var<storage, read_write> b_3: array<f32>;
@group(0) @binding(4) var<storage, read> b_4: array<f32>;
var<workgroup> s_30: array<f32, 32>;
@compute @workgroup_size(32, 1, 1)
fn main(@builtin(workgroup_id) i_44: vec3<u32>, @builtin(local_invocation_id) i_47: vec3<u32>) {
  var f_32: u32;
  var f_33: u32;
  var f_35: f32;
  let v_45 = i_44;
  let v_46 = v_45.x;
  let v_48 = i_47;
  let v_49 = v_48.x;
  let v_52 = b_0.m0;
  let v_54 = (v_46 >= v_52);
  if (v_54) {
  return;
  } else {
  }
  let v_59 = b_0.m1;
  let v_60 = (v_59 >> 5u);
  f_35 = bitcast<f32>(0u);
  f_32 = v_49;
  loop {
  let v_65 = f_32;
  let v_66 = (v_65 < v_60);
  if (!(v_66)) { break; }
  let v_68 = f_32;
  let v_69 = (v_46 * v_60);
  let v_70 = (v_69 + v_68);
  let v_71 = (v_70 * 2u);
  let v_74 = b_1[v_71];
  let v_75 = (v_71 + 1u);
  let v_77 = b_1[v_75];
  let v_78 = (v_68 * 8u);
  let v_79 = v_74.x;
  let v_80 = (v_78 + 0u);
  let v_83 = b_2[v_80];
  let v_85 = bitcast<i32>(v_79);
  let v_86 = extractBits(v_85, u32(0u), u32(8u));
  let v_87 = f32(v_86);
  let v_88 = bitcast<i32>(v_79);
  let v_89 = extractBits(v_88, u32(8u), u32(8u));
  let v_90 = f32(v_89);
  let v_91 = bitcast<i32>(v_79);
  let v_93 = extractBits(v_91, u32(16u), u32(8u));
  let v_94 = f32(v_93);
  let v_95 = bitcast<i32>(v_79);
  let v_97 = extractBits(v_95, u32(24u), u32(8u));
  let v_98 = f32(v_97);
  let v_99 = vec4<f32>(v_87, v_90, v_94, v_98);
  let v_100 = dot(v_99, v_83);
  let v_101 = v_74.y;
  let v_102 = (v_78 + 1u);
  let v_104 = b_2[v_102];
  let v_105 = bitcast<i32>(v_101);
  let v_106 = extractBits(v_105, u32(0u), u32(8u));
  let v_107 = f32(v_106);
  let v_108 = bitcast<i32>(v_101);
  let v_109 = extractBits(v_108, u32(8u), u32(8u));
  let v_110 = f32(v_109);
  let v_111 = bitcast<i32>(v_101);
  let v_112 = extractBits(v_111, u32(16u), u32(8u));
  let v_113 = f32(v_112);
  let v_114 = bitcast<i32>(v_101);
  let v_115 = extractBits(v_114, u32(24u), u32(8u));
  let v_116 = f32(v_115);
  let v_117 = vec4<f32>(v_107, v_110, v_113, v_116);
  let v_118 = dot(v_117, v_104);
  let v_119 = (v_100 + v_118);
  let v_120 = v_74.z;
  let v_121 = (v_78 + 2u);
  let v_123 = b_2[v_121];
  let v_124 = bitcast<i32>(v_120);
  let v_125 = extractBits(v_124, u32(0u), u32(8u));
  let v_126 = f32(v_125);
  let v_127 = bitcast<i32>(v_120);
  let v_128 = extractBits(v_127, u32(8u), u32(8u));
  let v_129 = f32(v_128);
  let v_130 = bitcast<i32>(v_120);
  let v_131 = extractBits(v_130, u32(16u), u32(8u));
  let v_132 = f32(v_131);
  let v_133 = bitcast<i32>(v_120);
  let v_134 = extractBits(v_133, u32(24u), u32(8u));
  let v_135 = f32(v_134);
  let v_136 = vec4<f32>(v_126, v_129, v_132, v_135);
  let v_137 = dot(v_136, v_123);
  let v_138 = v_74.w;
  let v_140 = (v_78 + 3u);
  let v_142 = b_2[v_140];
  let v_143 = bitcast<i32>(v_138);
  let v_144 = extractBits(v_143, u32(0u), u32(8u));
  let v_145 = f32(v_144);
  let v_146 = bitcast<i32>(v_138);
  let v_147 = extractBits(v_146, u32(8u), u32(8u));
  let v_148 = f32(v_147);
  let v_149 = bitcast<i32>(v_138);
  let v_150 = extractBits(v_149, u32(16u), u32(8u));
  let v_151 = f32(v_150);
  let v_152 = bitcast<i32>(v_138);
  let v_153 = extractBits(v_152, u32(24u), u32(8u));
  let v_154 = f32(v_153);
  let v_155 = vec4<f32>(v_145, v_148, v_151, v_154);
  let v_156 = dot(v_155, v_142);
  let v_157 = (v_137 + v_156);
  let v_158 = (v_119 + v_157);
  let v_159 = v_77.x;
  let v_161 = (v_78 + 4u);
  let v_163 = b_2[v_161];
  let v_164 = bitcast<i32>(v_159);
  let v_165 = extractBits(v_164, u32(0u), u32(8u));
  let v_166 = f32(v_165);
  let v_167 = bitcast<i32>(v_159);
  let v_168 = extractBits(v_167, u32(8u), u32(8u));
  let v_169 = f32(v_168);
  let v_170 = bitcast<i32>(v_159);
  let v_171 = extractBits(v_170, u32(16u), u32(8u));
  let v_172 = f32(v_171);
  let v_173 = bitcast<i32>(v_159);
  let v_174 = extractBits(v_173, u32(24u), u32(8u));
  let v_175 = f32(v_174);
  let v_176 = vec4<f32>(v_166, v_169, v_172, v_175);
  let v_177 = dot(v_176, v_163);
  let v_178 = v_77.y;
  let v_179 = (v_78 + 5u);
  let v_181 = b_2[v_179];
  let v_182 = bitcast<i32>(v_178);
  let v_183 = extractBits(v_182, u32(0u), u32(8u));
  let v_184 = f32(v_183);
  let v_185 = bitcast<i32>(v_178);
  let v_186 = extractBits(v_185, u32(8u), u32(8u));
  let v_187 = f32(v_186);
  let v_188 = bitcast<i32>(v_178);
  let v_189 = extractBits(v_188, u32(16u), u32(8u));
  let v_190 = f32(v_189);
  let v_191 = bitcast<i32>(v_178);
  let v_192 = extractBits(v_191, u32(24u), u32(8u));
  let v_193 = f32(v_192);
  let v_194 = vec4<f32>(v_184, v_187, v_190, v_193);
  let v_195 = dot(v_194, v_181);
  let v_196 = (v_177 + v_195);
  let v_197 = v_77.z;
  let v_199 = (v_78 + 6u);
  let v_201 = b_2[v_199];
  let v_202 = bitcast<i32>(v_197);
  let v_203 = extractBits(v_202, u32(0u), u32(8u));
  let v_204 = f32(v_203);
  let v_205 = bitcast<i32>(v_197);
  let v_206 = extractBits(v_205, u32(8u), u32(8u));
  let v_207 = f32(v_206);
  let v_208 = bitcast<i32>(v_197);
  let v_209 = extractBits(v_208, u32(16u), u32(8u));
  let v_210 = f32(v_209);
  let v_211 = bitcast<i32>(v_197);
  let v_212 = extractBits(v_211, u32(24u), u32(8u));
  let v_213 = f32(v_212);
  let v_214 = vec4<f32>(v_204, v_207, v_210, v_213);
  let v_215 = dot(v_214, v_201);
  let v_216 = v_77.w;
  let v_218 = (v_78 + 7u);
  let v_220 = b_2[v_218];
  let v_221 = bitcast<i32>(v_216);
  let v_222 = extractBits(v_221, u32(0u), u32(8u));
  let v_223 = f32(v_222);
  let v_224 = bitcast<i32>(v_216);
  let v_225 = extractBits(v_224, u32(8u), u32(8u));
  let v_226 = f32(v_225);
  let v_227 = bitcast<i32>(v_216);
  let v_228 = extractBits(v_227, u32(16u), u32(8u));
  let v_229 = f32(v_228);
  let v_230 = bitcast<i32>(v_216);
  let v_231 = extractBits(v_230, u32(24u), u32(8u));
  let v_232 = f32(v_231);
  let v_233 = vec4<f32>(v_223, v_226, v_229, v_232);
  let v_234 = dot(v_233, v_220);
  let v_235 = (v_215 + v_234);
  let v_236 = (v_196 + v_235);
  let v_239 = b_4[v_70];
  let v_240 = (v_158 + v_236);
  let v_241 = (v_239 * v_240);
  let v_242 = f_35;
  let v_243 = (v_242 + v_241);
  f_35 = v_243;
  continuing {
  let v_244 = f_32;
  let v_245 = (v_244 + 32u);
  f_32 = v_245;
  }
  }
  let v_248 = f_35;
  s_30[v_49] = v_248;
  workgroupBarrier();
  f_33 = 16u;
  loop {
  let v_254 = f_33;
  let v_255 = (v_254 > 0u);
  if (!(v_255)) { break; }
  let v_257 = f_33;
  let v_258 = (v_49 < v_257);
  if (v_258) {
  let v_263 = s_30[v_49];
  let v_264 = (v_49 + v_257);
  let v_266 = s_30[v_264];
  let v_268 = (v_263 + v_266);
  s_30[v_49] = v_268;
  } else {
  }
  workgroupBarrier();
  continuing {
  let v_269 = f_33;
  let v_270 = (v_269 >> 1u);
  f_33 = v_270;
  }
  }
  let v_271 = (v_49 == 0u);
  if (v_271) {
  let v_277 = s_30[0u];
  b_3[v_46] = v_277;
  } else {
  }
  return;
}
