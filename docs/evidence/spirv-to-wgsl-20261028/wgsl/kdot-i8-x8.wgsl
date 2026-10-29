requires packed_4x8_integer_dot_product;
struct S_7 { m0: u32, m1: u32, m2: u32, m3: u32, m4: u32, m5: u32, m6: u32, m7: u32, };
@group(0) @binding(0) var<storage, read> b_0: S_7;
@group(0) @binding(1) var<storage, read> b_1: array<u32>;
@group(0) @binding(2) var<storage, read> b_2: array<u32>;
@group(0) @binding(3) var<storage, read_write> b_3: array<f32>;
@group(0) @binding(4) var<storage, read> b_4: array<u32>;
@group(0) @binding(5) var<storage, read> b_5: array<f32>;
var<workgroup> s_30: array<f32, 1024>;
@compute @workgroup_size(256, 1, 1)
fn main(@builtin(workgroup_id) i_50: vec3<u32>, @builtin(local_invocation_id) i_56: vec3<u32>) {
  var f_34: array<f32, 4>;
  var f_35: array<f32, 4>;
  var f_37: u32;
  var f_38: u32;
  var f_39: u32;
  var f_40: u32;
  var f_41: u32;
  var f_42: u32;
  var f_223: u32;
  var f_391: u32;
  var f_663: u32;
  var f_689: u32;
  var f_740: u32;
  var f_771: u32;
  var f_898: u32;
  var f_924: u32;
  var f_962: u32;
  var f_988: u32;
  let v_51 = i_50;
  let v_52 = v_51.x;
  let v_53 = (v_52 * 4u);
  let v_54 = i_50;
  let v_55 = v_54.y;
  let v_57 = i_56;
  let v_58 = v_57.x;
  let v_61 = b_4[v_55];
  f_40 = 0u;
  let v_63 = b_0.m4;
  let v_65 = (v_63 == 1u);
  if (v_65) {
  f_40 = v_55;
  let v_71 = b_0.m5;
  let v_72 = (v_71 > 1u);
  if (v_72) {
  let v_77 = b_0.m5;
  let v_78 = (v_55 / v_77);
  f_40 = v_78;
  } else {
  }
  } else {
  }
  let v_79 = f_40;
  let v_82 = b_0.m6;
  let v_83 = (v_79 + v_82);
  let v_85 = b_0.m0;
  let v_87 = b_0.m1;
  let v_90 = b_0.m2;
  let v_93 = b_0.m3;
  let v_94 = (v_90 == 8u);
  let v_95 = (v_90 == 2u);
  let v_96 = (v_94 || v_95);
  let v_97 = (v_90 == 1u);
  let v_98 = (v_96 || v_97);
  let v_100 = (v_87 + 255u);
  let v_101 = (v_100 / 256u);
  let v_102 = (v_87 / 256u);
  let v_103 = select(v_102, v_101, v_98);
  let v_104 = (v_90 == 1u);
  let v_106 = select(0u, 512u, v_104);
  let v_107 = (v_90 == 2u);
  let v_109 = select(v_106, 144u, v_107);
  let v_110 = (v_90 == 8u);
  let v_112 = select(v_109, 272u, v_110);
  let v_114 = (v_90 == 23u);
  let v_116 = select(v_112, 136u, v_114);
  let v_118 = (v_90 == 14u);
  let v_120 = select(v_116, 210u, v_118);
  let v_122 = (v_90 == 13u);
  let v_124 = select(v_120, 176u, v_122);
  let v_126 = (v_90 == 12u);
  let v_127 = select(v_124, 144u, v_126);
  let v_129 = (v_87 + 31u);
  let v_131 = (v_129 / 32u);
  let v_132 = (v_127 / 8u);
  let v_133 = (v_131 * v_132);
  let v_134 = (v_103 * v_127);
  let v_135 = select(v_134, v_133, v_98);
  let v_136 = (v_58 >> 5u);
  let v_137 = (v_58 & 31u);
  let v_138 = (v_137 * 8u);
  f_37 = 0u;
  loop {
  let v_143 = f_37;
  let v_144 = (v_143 < 4u);
  if (!(v_144)) { break; }
  let v_146 = f_37;
  f_34[v_146] = bitcast<f32>(0u);
  f_35[v_146] = bitcast<f32>(0u);
  continuing {
  let v_150 = f_37;
  let v_151 = (v_150 + 1u);
  f_37 = v_151;
  }
  }
  let v_153 = min(v_53, v_85);
  let v_154 = (v_85 - v_153);
  let v_155 = min(4u, v_154);
  let v_156 = (v_55 < v_93);
  if (v_156) {
  f_38 = v_136;
  loop {
  let v_164 = f_38;
  let v_165 = (v_164 < v_103);
  if (!(v_165)) { break; }
  let v_167 = f_38;
  let v_168 = (v_167 * 256u);
  let v_169 = (v_168 + v_138);
  let v_170 = (v_169 < v_87);
  if (v_170) {
  let v_174 = (v_83 * v_87);
  let v_175 = (v_167 * 256u);
  let v_176 = (v_174 + v_175);
  let v_177 = (v_176 + v_138);
  let v_178 = (v_177 >> 2u);
  let v_180 = b_2[v_178];
  let v_182 = bitcast<i32>(v_180);
  let v_183 = (v_177 >> 2u);
  let v_184 = (v_183 + 1u);
  let v_186 = b_2[v_184];
  let v_187 = bitcast<i32>(v_186);
  let v_188 = (v_177 >> 5u);
  let v_191 = b_5[v_188];
  let v_193 = dot4I8Packed(u32(16843009i), u32(v_182));
  let v_194 = dot4I8Packed(u32(16843009i), u32(v_187));
  let v_195 = (v_193 + v_194);
  let v_196 = f32(v_195);
  let v_197 = (v_196 * v_191);
  let v_198 = (v_61 * v_85);
  let v_199 = (v_198 + v_53);
  let v_200 = (v_199 * v_135);
  let v_201 = (v_167 * v_127);
  let v_202 = (v_200 + v_201);
  f_37 = 0u;
  loop {
  let v_207 = f_37;
  let v_208 = (v_207 < v_155);
  if (!(v_208)) { break; }
  let v_210 = f_37;
  let v_211 = (v_210 * v_135);
  let v_212 = (v_202 + v_211);
  let v_215 = (v_138 + 4u);
  let v_216 = (v_90 == 12u);
  let v_217 = (v_90 == 13u);
  let v_218 = (v_216 || v_217);
  if (v_218) {
  let v_222 = (v_138 / 32u);
  let v_224 = (v_222 < 4u);
  if (v_224) {
  let v_228 = (v_212 + 4u);
  let v_229 = (v_228 + v_222);
  let v_230 = (v_229 >> 2u);
  let v_232 = b_1[v_230];
  let v_233 = (v_229 & 3u);
  let v_234 = (v_233 * 8u);
  let v_235 = (v_232 >> v_234);
  let v_236 = (v_235 & 255u);
  let v_238 = (v_236 & 63u);
  f_223 = v_238;
  } else {
  let v_239 = (v_212 + 8u);
  let v_240 = (v_239 + v_222);
  let v_241 = (v_240 >> 2u);
  let v_243 = b_1[v_241];
  let v_244 = (v_240 & 3u);
  let v_245 = (v_244 * 8u);
  let v_246 = (v_243 >> v_245);
  let v_247 = (v_246 & 255u);
  let v_249 = (v_247 & 15u);
  let v_250 = (v_212 + v_222);
  let v_251 = (v_250 >> 2u);
  let v_253 = b_1[v_251];
  let v_254 = (v_250 & 3u);
  let v_255 = (v_254 * 8u);
  let v_256 = (v_253 >> v_255);
  let v_257 = (v_256 & 255u);
  let v_258 = (v_257 >> 6u);
  let v_259 = (v_258 << 4u);
  let v_260 = (v_249 | v_259);
  f_223 = v_260;
  }
  let v_261 = f_223;
  let v_262 = bitcast<i32>(v_261);
  let v_263 = f32(v_262);
  let v_264 = (v_90 == 12u);
  if (v_264) {
  let v_269 = (v_138 / 64u);
  let v_270 = (v_138 & 63u);
  let v_272 = (v_212 + 16u);
  let v_273 = (v_269 * 32u);
  let v_274 = (v_272 + v_273);
  let v_275 = (v_270 & 31u);
  let v_276 = (v_274 + v_275);
  let v_277 = (v_276 >> 2u);
  let v_279 = b_1[v_277];
  let v_280 = (v_270 >= 32u);
  let v_281 = (v_279 >> 4u);
  let v_282 = select(v_279, v_281, v_280);
  let v_284 = (v_282 & 252645135u);
  f_41 = v_284;
  } else {
  let v_285 = (v_138 / 64u);
  let v_286 = (v_138 & 63u);
  let v_287 = (v_286 & 31u);
  let v_288 = (v_286 >= 32u);
  let v_290 = (v_212 + 48u);
  let v_291 = (v_285 * 32u);
  let v_292 = (v_290 + v_291);
  let v_293 = (v_292 + v_287);
  let v_294 = (v_293 >> 2u);
  let v_296 = b_1[v_294];
  let v_297 = (v_212 + 16u);
  let v_298 = (v_297 + v_287);
  let v_299 = (v_298 >> 2u);
  let v_301 = b_1[v_299];
  let v_302 = (2u * v_285);
  let v_303 = select(0u, 1u, v_288);
  let v_304 = (v_302 + v_303);
  let v_305 = (v_296 >> 4u);
  let v_306 = select(v_296, v_305, v_288);
  let v_307 = (v_306 & 252645135u);
  let v_308 = (v_301 >> v_304);
  let v_310 = (v_308 & 16843009u);
  let v_311 = (v_310 << 4u);
  let v_312 = (v_307 | v_311);
  f_41 = v_312;
  }
  let v_313 = (v_90 == 12u);
  if (v_313) {
  let v_317 = (v_215 / 64u);
  let v_318 = (v_215 & 63u);
  let v_319 = (v_212 + 16u);
  let v_320 = (v_317 * 32u);
  let v_321 = (v_319 + v_320);
  let v_322 = (v_318 & 31u);
  let v_323 = (v_321 + v_322);
  let v_324 = (v_323 >> 2u);
  let v_326 = b_1[v_324];
  let v_327 = (v_318 >= 32u);
  let v_328 = (v_326 >> 4u);
  let v_329 = select(v_326, v_328, v_327);
  let v_330 = (v_329 & 252645135u);
  f_42 = v_330;
  } else {
  let v_331 = (v_215 / 64u);
  let v_332 = (v_215 & 63u);
  let v_333 = (v_332 & 31u);
  let v_334 = (v_332 >= 32u);
  let v_335 = (v_212 + 48u);
  let v_336 = (v_331 * 32u);
  let v_337 = (v_335 + v_336);
  let v_338 = (v_337 + v_333);
  let v_339 = (v_338 >> 2u);
  let v_341 = b_1[v_339];
  let v_342 = (v_212 + 16u);
  let v_343 = (v_342 + v_333);
  let v_344 = (v_343 >> 2u);
  let v_346 = b_1[v_344];
  let v_347 = (2u * v_331);
  let v_348 = select(0u, 1u, v_334);
  let v_349 = (v_347 + v_348);
  let v_350 = (v_341 >> 4u);
  let v_351 = select(v_341, v_350, v_334);
  let v_352 = (v_351 & 252645135u);
  let v_353 = (v_346 >> v_349);
  let v_354 = (v_353 & 16843009u);
  let v_355 = (v_354 << 4u);
  let v_356 = (v_352 | v_355);
  f_42 = v_356;
  }
  let v_357 = (v_212 >> 2u);
  let v_359 = b_1[v_357];
  let v_361 = unpack2x16float(v_359);
  let v_362 = (v_212 & 2u);
  let v_363 = (v_362 != 0u);
  let v_364 = v_361.y;
  let v_365 = v_361.x;
  let v_366 = select(v_365, v_364, v_363);
  let v_367 = (v_366 * v_263);
  let v_368 = (v_367 * v_191);
  let v_369 = f_41;
  let v_370 = bitcast<i32>(v_369);
  let v_371 = f_42;
  let v_372 = bitcast<i32>(v_371);
  let v_373 = dot4I8Packed(u32(v_370), u32(v_182));
  let v_374 = dot4I8Packed(u32(v_372), u32(v_187));
  let v_375 = (v_373 + v_374);
  let v_376 = f32(v_375);
  let v_377 = (v_368 * v_376);
  let v_378 = f_34[v_210];
  let v_379 = (v_378 + v_377);
  f_34[v_210] = v_379;
  let v_380 = f_35[v_210];
  let v_381 = (v_212 + 2u);
  let v_382 = (v_381 >> 2u);
  let v_384 = b_1[v_382];
  let v_385 = unpack2x16float(v_384);
  let v_386 = (v_381 & 2u);
  let v_387 = (v_386 != 0u);
  let v_388 = v_385.y;
  let v_389 = v_385.x;
  let v_390 = select(v_389, v_388, v_387);
  let v_392 = (v_222 < 4u);
  if (v_392) {
  let v_396 = (v_212 + 8u);
  let v_397 = (v_396 + v_222);
  let v_398 = (v_397 >> 2u);
  let v_400 = b_1[v_398];
  let v_401 = (v_397 & 3u);
  let v_402 = (v_401 * 8u);
  let v_403 = (v_400 >> v_402);
  let v_404 = (v_403 & 255u);
  let v_405 = (v_404 & 63u);
  f_391 = v_405;
  } else {
  let v_406 = (v_212 + 8u);
  let v_407 = (v_406 + v_222);
  let v_408 = (v_407 >> 2u);
  let v_410 = b_1[v_408];
  let v_411 = (v_407 & 3u);
  let v_412 = (v_411 * 8u);
  let v_413 = (v_410 >> v_412);
  let v_414 = (v_413 & 255u);
  let v_415 = (v_414 >> 4u);
  let v_416 = (v_212 + 4u);
  let v_417 = (v_416 + v_222);
  let v_418 = (v_417 >> 2u);
  let v_420 = b_1[v_418];
  let v_421 = (v_417 & 3u);
  let v_422 = (v_421 * 8u);
  let v_423 = (v_420 >> v_422);
  let v_424 = (v_423 & 255u);
  let v_425 = (v_424 >> 6u);
  let v_426 = (v_425 << 4u);
  let v_427 = (v_415 | v_426);
  f_391 = v_427;
  }
  let v_428 = f_391;
  let v_429 = bitcast<i32>(v_428);
  let v_430 = f32(v_429);
  let v_431 = (v_390 * v_430);
  let v_432 = (v_431 * v_197);
  let v_433 = (v_380 + v_432);
  f_35[v_210] = v_433;
  } else {
  let v_434 = (v_90 == 23u);
  if (v_434) {
  let v_438 = (v_138 / 32u);
  let v_439 = (v_138 & 31u);
  let v_440 = (v_439 >= 16u);
  let v_441 = (v_212 + 8u);
  let v_442 = (v_438 * 16u);
  let v_443 = (v_441 + v_442);
  let v_444 = (v_439 - 16u);
  let v_445 = select(v_439, v_444, v_440);
  let v_446 = (v_443 + v_445);
  let v_447 = (v_446 >> 2u);
  let v_449 = b_1[v_447];
  let v_450 = (v_439 - 12u);
  let v_451 = (v_439 + 4u);
  let v_452 = select(v_451, v_450, v_440);
  let v_453 = (v_443 + v_452);
  let v_454 = (v_453 >> 2u);
  let v_456 = b_1[v_454];
  let v_457 = (v_449 >> 4u);
  let v_458 = select(v_449, v_457, v_440);
  let v_459 = (v_458 & 252645135u);
  let v_461 = (v_459 & 15u);
  let v_462 = (v_461 < 4u);
  let v_464 = (v_461 < 8u);
  let v_466 = (v_461 < 12u);
  let v_469 = select(1901675829u, 639175937u, v_466);
  let v_470 = select(v_469, 4142587343u, v_464);
  let v_471 = select(v_470, 3215825025u, v_462);
  let v_472 = bitcast<i32>(v_471);
  let v_473 = (v_461 & 3u);
  let v_474 = (v_473 * 8u);
  let v_475 = bitcast<i32>(v_474);
  let v_477 = extractBits(v_472, u32(v_475), u32(8i));
  let v_478 = (v_477 & 255i);
  let v_479 = (v_459 >> 8u);
  let v_480 = (v_479 & 15u);
  let v_481 = (v_480 < 4u);
  let v_482 = (v_480 < 8u);
  let v_483 = (v_480 < 12u);
  let v_484 = select(1901675829u, 639175937u, v_483);
  let v_485 = select(v_484, 4142587343u, v_482);
  let v_486 = select(v_485, 3215825025u, v_481);
  let v_487 = bitcast<i32>(v_486);
  let v_488 = (v_480 & 3u);
  let v_489 = (v_488 * 8u);
  let v_490 = bitcast<i32>(v_489);
  let v_491 = extractBits(v_487, u32(v_490), u32(8i));
  let v_492 = (v_491 & 255i);
  let v_493 = (v_492 << u32(8i));
  let v_494 = (v_459 >> 16u);
  let v_495 = (v_494 & 15u);
  let v_496 = (v_495 < 4u);
  let v_497 = (v_495 < 8u);
  let v_498 = (v_495 < 12u);
  let v_499 = select(1901675829u, 639175937u, v_498);
  let v_500 = select(v_499, 4142587343u, v_497);
  let v_501 = select(v_500, 3215825025u, v_496);
  let v_502 = bitcast<i32>(v_501);
  let v_503 = (v_495 & 3u);
  let v_504 = (v_503 * 8u);
  let v_505 = bitcast<i32>(v_504);
  let v_506 = extractBits(v_502, u32(v_505), u32(8i));
  let v_507 = (v_506 & 255i);
  let v_509 = (v_507 << u32(16i));
  let v_511 = (v_459 >> 24u);
  let v_512 = (v_511 & 15u);
  let v_513 = (v_512 < 4u);
  let v_514 = (v_512 < 8u);
  let v_515 = (v_512 < 12u);
  let v_516 = select(1901675829u, 639175937u, v_515);
  let v_517 = select(v_516, 4142587343u, v_514);
  let v_518 = select(v_517, 3215825025u, v_513);
  let v_519 = bitcast<i32>(v_518);
  let v_520 = (v_512 & 3u);
  let v_521 = (v_520 * 8u);
  let v_522 = bitcast<i32>(v_521);
  let v_523 = extractBits(v_519, u32(v_522), u32(8i));
  let v_524 = (v_523 & 255i);
  let v_526 = (v_524 << u32(24i));
  let v_527 = (v_478 | v_493);
  let v_528 = (v_527 | v_509);
  let v_529 = (v_528 | v_526);
  let v_530 = (v_456 >> 4u);
  let v_531 = select(v_456, v_530, v_440);
  let v_532 = (v_531 & 252645135u);
  let v_533 = (v_532 & 15u);
  let v_534 = (v_533 < 4u);
  let v_535 = (v_533 < 8u);
  let v_536 = (v_533 < 12u);
  let v_537 = select(1901675829u, 639175937u, v_536);
  let v_538 = select(v_537, 4142587343u, v_535);
  let v_539 = select(v_538, 3215825025u, v_534);
  let v_540 = bitcast<i32>(v_539);
  let v_541 = (v_533 & 3u);
  let v_542 = (v_541 * 8u);
  let v_543 = bitcast<i32>(v_542);
  let v_544 = extractBits(v_540, u32(v_543), u32(8i));
  let v_545 = (v_544 & 255i);
  let v_546 = (v_532 >> 8u);
  let v_547 = (v_546 & 15u);
  let v_548 = (v_547 < 4u);
  let v_549 = (v_547 < 8u);
  let v_550 = (v_547 < 12u);
  let v_551 = select(1901675829u, 639175937u, v_550);
  let v_552 = select(v_551, 4142587343u, v_549);
  let v_553 = select(v_552, 3215825025u, v_548);
  let v_554 = bitcast<i32>(v_553);
  let v_555 = (v_547 & 3u);
  let v_556 = (v_555 * 8u);
  let v_557 = bitcast<i32>(v_556);
  let v_558 = extractBits(v_554, u32(v_557), u32(8i));
  let v_559 = (v_558 & 255i);
  let v_560 = (v_559 << u32(8i));
  let v_561 = (v_532 >> 16u);
  let v_562 = (v_561 & 15u);
  let v_563 = (v_562 < 4u);
  let v_564 = (v_562 < 8u);
  let v_565 = (v_562 < 12u);
  let v_566 = select(1901675829u, 639175937u, v_565);
  let v_567 = select(v_566, 4142587343u, v_564);
  let v_568 = select(v_567, 3215825025u, v_563);
  let v_569 = bitcast<i32>(v_568);
  let v_570 = (v_562 & 3u);
  let v_571 = (v_570 * 8u);
  let v_572 = bitcast<i32>(v_571);
  let v_573 = extractBits(v_569, u32(v_572), u32(8i));
  let v_574 = (v_573 & 255i);
  let v_575 = (v_574 << u32(16i));
  let v_576 = (v_532 >> 24u);
  let v_577 = (v_576 & 15u);
  let v_578 = (v_577 < 4u);
  let v_579 = (v_577 < 8u);
  let v_580 = (v_577 < 12u);
  let v_581 = select(1901675829u, 639175937u, v_580);
  let v_582 = select(v_581, 4142587343u, v_579);
  let v_583 = select(v_582, 3215825025u, v_578);
  let v_584 = bitcast<i32>(v_583);
  let v_585 = (v_577 & 3u);
  let v_586 = (v_585 * 8u);
  let v_587 = bitcast<i32>(v_586);
  let v_588 = extractBits(v_584, u32(v_587), u32(8i));
  let v_589 = (v_588 & 255i);
  let v_590 = (v_589 << u32(24i));
  let v_591 = (v_545 | v_560);
  let v_592 = (v_591 | v_575);
  let v_593 = (v_592 | v_590);
  let v_594 = (v_212 >> 2u);
  let v_596 = b_1[v_594];
  let v_597 = (v_596 >> 16u);
  let v_598 = (v_212 + 4u);
  let v_599 = (v_438 / 2u);
  let v_600 = (v_598 + v_599);
  let v_601 = (v_600 >> 2u);
  let v_603 = b_1[v_601];
  let v_604 = (v_600 & 3u);
  let v_605 = (v_604 * 8u);
  let v_606 = (v_603 >> v_605);
  let v_607 = (v_606 & 255u);
  let v_608 = (v_438 & 1u);
  let v_609 = (4u * v_608);
  let v_610 = (v_607 >> v_609);
  let v_611 = (v_610 & 15u);
  let v_612 = (2u * v_438);
  let v_613 = (v_597 >> v_612);
  let v_614 = (v_613 & 3u);
  let v_615 = (v_614 << 4u);
  let v_616 = (v_611 | v_615);
  let v_617 = bitcast<i32>(v_616);
  let v_619 = (v_617 - 32i);
  let v_620 = f32(v_619);
  let v_621 = (v_212 >> 2u);
  let v_623 = b_1[v_621];
  let v_624 = unpack2x16float(v_623);
  let v_625 = (v_212 & 2u);
  let v_626 = (v_625 != 0u);
  let v_627 = v_624.y;
  let v_628 = v_624.x;
  let v_629 = select(v_628, v_627, v_626);
  let v_630 = (v_629 * v_620);
  let v_631 = (v_630 * v_191);
  let v_632 = dot4I8Packed(u32(v_529), u32(v_182));
  let v_633 = dot4I8Packed(u32(v_593), u32(v_187));
  let v_634 = (v_632 + v_633);
  let v_635 = f32(v_634);
  let v_636 = (v_631 * v_635);
  let v_637 = f_34[v_210];
  let v_638 = (v_637 + v_636);
  f_34[v_210] = v_638;
  } else {
  let v_639 = (v_90 == 8u);
  if (v_639) {
  let v_643 = (v_138 / 32u);
  let v_645 = (v_643 * 34u);
  let v_646 = (v_212 + v_645);
  let v_647 = (v_646 >> 2u);
  let v_649 = b_1[v_647];
  let v_650 = unpack2x16float(v_649);
  let v_651 = (v_646 & 2u);
  let v_652 = (v_651 != 0u);
  let v_653 = v_650.y;
  let v_654 = v_650.x;
  let v_655 = select(v_654, v_653, v_652);
  let v_656 = (v_655 * v_191);
  let v_657 = (v_138 / 32u);
  let v_658 = (v_657 * 34u);
  let v_659 = (v_212 + v_658);
  let v_660 = (v_659 + 2u);
  let v_661 = (v_138 & 31u);
  let v_662 = (v_660 + v_661);
  let v_664 = (v_662 >> 2u);
  let v_666 = b_1[v_664];
  let v_667 = (v_662 & 3u);
  let v_668 = (v_667 * 8u);
  f_663 = v_666;
  let v_669 = (v_668 != 0u);
  if (v_669) {
  let v_673 = (v_666 >> v_668);
  let v_674 = (v_662 >> 2u);
  let v_675 = (v_674 + 1u);
  let v_677 = b_1[v_675];
  let v_678 = (32u - v_668);
  let v_679 = (v_677 << v_678);
  let v_680 = (v_673 | v_679);
  f_663 = v_680;
  } else {
  }
  let v_681 = f_663;
  let v_682 = bitcast<i32>(v_681);
  let v_683 = (v_215 / 32u);
  let v_684 = (v_683 * 34u);
  let v_685 = (v_212 + v_684);
  let v_686 = (v_685 + 2u);
  let v_687 = (v_215 & 31u);
  let v_688 = (v_686 + v_687);
  let v_690 = (v_688 >> 2u);
  let v_692 = b_1[v_690];
  let v_693 = (v_688 & 3u);
  let v_694 = (v_693 * 8u);
  f_689 = v_692;
  let v_695 = (v_694 != 0u);
  if (v_695) {
  let v_699 = (v_692 >> v_694);
  let v_700 = (v_688 >> 2u);
  let v_701 = (v_700 + 1u);
  let v_703 = b_1[v_701];
  let v_704 = (32u - v_694);
  let v_705 = (v_703 << v_704);
  let v_706 = (v_699 | v_705);
  f_689 = v_706;
  } else {
  }
  let v_707 = f_689;
  let v_708 = bitcast<i32>(v_707);
  let v_709 = dot4I8Packed(u32(v_682), u32(v_182));
  let v_710 = dot4I8Packed(u32(v_708), u32(v_187));
  let v_711 = (v_709 + v_710);
  let v_712 = f32(v_711);
  let v_713 = (v_656 * v_712);
  let v_714 = f_34[v_210];
  let v_715 = (v_714 + v_713);
  f_34[v_210] = v_715;
  } else {
  let v_716 = (v_90 == 2u);
  if (v_716) {
  let v_720 = (v_138 / 32u);
  let v_722 = (v_720 * 18u);
  let v_723 = (v_212 + v_722);
  let v_724 = (v_723 >> 2u);
  let v_726 = b_1[v_724];
  let v_727 = unpack2x16float(v_726);
  let v_728 = (v_723 & 2u);
  let v_729 = (v_728 != 0u);
  let v_730 = v_727.y;
  let v_731 = v_727.x;
  let v_732 = select(v_731, v_730, v_729);
  let v_733 = (v_138 & 31u);
  let v_734 = (v_138 / 32u);
  let v_735 = (v_734 * 18u);
  let v_736 = (v_212 + v_735);
  let v_737 = (v_736 + 2u);
  let v_738 = (v_733 & 15u);
  let v_739 = (v_737 + v_738);
  let v_741 = (v_739 >> 2u);
  let v_743 = b_1[v_741];
  let v_744 = (v_739 & 3u);
  let v_745 = (v_744 * 8u);
  f_740 = v_743;
  let v_746 = (v_745 != 0u);
  if (v_746) {
  let v_750 = (v_743 >> v_745);
  let v_751 = (v_739 >> 2u);
  let v_752 = (v_751 + 1u);
  let v_754 = b_1[v_752];
  let v_755 = (32u - v_745);
  let v_756 = (v_754 << v_755);
  let v_757 = (v_750 | v_756);
  f_740 = v_757;
  } else {
  }
  let v_758 = f_740;
  let v_759 = (v_733 >= 16u);
  let v_760 = (v_758 >> 4u);
  let v_761 = select(v_758, v_760, v_759);
  let v_762 = (v_761 & 252645135u);
  let v_763 = bitcast<i32>(v_762);
  let v_764 = (v_215 & 31u);
  let v_765 = (v_215 / 32u);
  let v_766 = (v_765 * 18u);
  let v_767 = (v_212 + v_766);
  let v_768 = (v_767 + 2u);
  let v_769 = (v_764 & 15u);
  let v_770 = (v_768 + v_769);
  let v_772 = (v_770 >> 2u);
  let v_774 = b_1[v_772];
  let v_775 = (v_770 & 3u);
  let v_776 = (v_775 * 8u);
  f_771 = v_774;
  let v_777 = (v_776 != 0u);
  if (v_777) {
  let v_781 = (v_774 >> v_776);
  let v_782 = (v_770 >> 2u);
  let v_783 = (v_782 + 1u);
  let v_785 = b_1[v_783];
  let v_786 = (32u - v_776);
  let v_787 = (v_785 << v_786);
  let v_788 = (v_781 | v_787);
  f_771 = v_788;
  } else {
  }
  let v_789 = f_771;
  let v_790 = (v_764 >= 16u);
  let v_791 = (v_789 >> 4u);
  let v_792 = select(v_789, v_791, v_790);
  let v_793 = (v_792 & 252645135u);
  let v_794 = bitcast<i32>(v_793);
  let v_795 = dot4I8Packed(u32(v_763), u32(v_182));
  let v_796 = dot4I8Packed(u32(v_794), u32(v_187));
  let v_797 = (v_795 + v_796);
  let v_798 = f32(v_797);
  let v_799 = (v_191 * v_798);
  let v_801 = (bitcast<f32>(1090519040u) * v_197);
  let v_802 = (v_799 - v_801);
  let v_803 = (v_732 * v_802);
  let v_804 = f_34[v_210];
  let v_805 = (v_804 + v_803);
  f_34[v_210] = v_805;
  } else {
  let v_806 = (v_90 == 1u);
  if (v_806) {
  let v_810 = (v_138 * 2u);
  let v_811 = (v_212 + v_810);
  let v_812 = (v_811 >> 2u);
  let v_815 = b_1[v_812];
  let v_816 = unpack2x16float(v_815);
  let v_817 = (v_812 + 1u);
  let v_819 = b_1[v_817];
  let v_820 = unpack2x16float(v_819);
  let v_821 = vec4<f32>(v_816, v_820);
  let v_823 = extractBits(v_182, u32(0i), u32(8i));
  let v_824 = f32(v_823);
  let v_825 = extractBits(v_182, u32(8i), u32(8i));
  let v_826 = f32(v_825);
  let v_827 = extractBits(v_182, u32(16i), u32(8i));
  let v_828 = f32(v_827);
  let v_829 = extractBits(v_182, u32(24i), u32(8i));
  let v_830 = f32(v_829);
  let v_831 = vec4<f32>(v_824, v_826, v_828, v_830);
  let v_832 = dot(v_821, v_831);
  let v_833 = (v_215 * 2u);
  let v_834 = (v_212 + v_833);
  let v_835 = (v_834 >> 2u);
  let v_837 = b_1[v_835];
  let v_838 = unpack2x16float(v_837);
  let v_839 = (v_835 + 1u);
  let v_841 = b_1[v_839];
  let v_842 = unpack2x16float(v_841);
  let v_843 = vec4<f32>(v_838, v_842);
  let v_844 = extractBits(v_187, u32(0i), u32(8i));
  let v_845 = f32(v_844);
  let v_846 = extractBits(v_187, u32(8i), u32(8i));
  let v_847 = f32(v_846);
  let v_848 = extractBits(v_187, u32(16i), u32(8i));
  let v_849 = f32(v_848);
  let v_850 = extractBits(v_187, u32(24i), u32(8i));
  let v_851 = f32(v_850);
  let v_852 = vec4<f32>(v_845, v_847, v_849, v_851);
  let v_853 = dot(v_843, v_852);
  let v_854 = (v_832 + v_853);
  let v_855 = (v_191 * v_854);
  let v_856 = f_34[v_210];
  let v_857 = (v_856 + v_855);
  f_34[v_210] = v_857;
  } else {
  let v_859 = (v_212 + 192u);
  let v_860 = (v_138 / 16u);
  let v_861 = (v_859 + v_860);
  let v_862 = (v_861 >> 2u);
  let v_864 = b_1[v_862];
  let v_865 = (v_861 & 3u);
  let v_866 = (v_865 * 8u);
  let v_867 = (v_864 >> v_866);
  let v_868 = (v_867 & 255u);
  let v_870 = (v_868 >= 128u);
  let v_871 = bitcast<i32>(v_868);
  let v_873 = (v_871 - 256i);
  let v_874 = bitcast<i32>(v_868);
  let v_875 = select(v_874, v_873, v_870);
  let v_877 = (v_212 + 208u);
  let v_878 = (v_877 >> 2u);
  let v_880 = b_1[v_878];
  let v_881 = unpack2x16float(v_880);
  let v_882 = (v_877 & 2u);
  let v_883 = (v_882 != 0u);
  let v_884 = v_881.y;
  let v_885 = v_881.x;
  let v_886 = select(v_885, v_884, v_883);
  let v_887 = f32(v_875);
  let v_888 = (v_886 * v_887);
  let v_889 = (v_138 / 128u);
  let v_891 = (v_138 & 127u);
  let v_892 = (v_891 & 31u);
  let v_893 = (v_891 / 32u);
  let v_894 = (v_212 + 128u);
  let v_895 = (v_889 * 32u);
  let v_896 = (v_894 + v_895);
  let v_897 = (v_896 + v_892);
  let v_899 = (v_897 >> 2u);
  let v_901 = b_1[v_899];
  let v_902 = (v_897 & 3u);
  let v_903 = (v_902 * 8u);
  f_898 = v_901;
  let v_904 = (v_903 != 0u);
  if (v_904) {
  let v_908 = (v_901 >> v_903);
  let v_909 = (v_897 >> 2u);
  let v_910 = (v_909 + 1u);
  let v_912 = b_1[v_910];
  let v_913 = (32u - v_903);
  let v_914 = (v_912 << v_913);
  let v_915 = (v_908 | v_914);
  f_898 = v_915;
  } else {
  }
  let v_916 = f_898;
  let v_917 = (v_889 * 64u);
  let v_918 = (v_212 + v_917);
  let v_919 = (v_893 & 1u);
  let v_920 = (v_919 == 1u);
  let v_921 = select(0u, 32u, v_920);
  let v_922 = (v_918 + v_921);
  let v_923 = (v_922 + v_892);
  let v_925 = (v_923 >> 2u);
  let v_927 = b_1[v_925];
  let v_928 = (v_923 & 3u);
  let v_929 = (v_928 * 8u);
  f_924 = v_927;
  let v_930 = (v_929 != 0u);
  if (v_930) {
  let v_934 = (v_927 >> v_929);
  let v_935 = (v_923 >> 2u);
  let v_936 = (v_935 + 1u);
  let v_938 = b_1[v_936];
  let v_939 = (32u - v_929);
  let v_940 = (v_938 << v_939);
  let v_941 = (v_934 | v_940);
  f_924 = v_941;
  } else {
  }
  let v_942 = f_924;
  let v_943 = (v_893 >= 2u);
  let v_944 = (v_942 >> 4u);
  let v_945 = select(v_942, v_944, v_943);
  let v_946 = (v_945 & 252645135u);
  let v_947 = (v_893 * 2u);
  let v_948 = (v_916 >> v_947);
  let v_950 = (v_948 & 50529027u);
  let v_951 = (v_950 << 4u);
  let v_952 = (v_946 | v_951);
  let v_953 = bitcast<i32>(v_952);
  let v_954 = (v_215 / 128u);
  let v_955 = (v_215 & 127u);
  let v_956 = (v_955 & 31u);
  let v_957 = (v_955 / 32u);
  let v_958 = (v_212 + 128u);
  let v_959 = (v_954 * 32u);
  let v_960 = (v_958 + v_959);
  let v_961 = (v_960 + v_956);
  let v_963 = (v_961 >> 2u);
  let v_965 = b_1[v_963];
  let v_966 = (v_961 & 3u);
  let v_967 = (v_966 * 8u);
  f_962 = v_965;
  let v_968 = (v_967 != 0u);
  if (v_968) {
  let v_972 = (v_965 >> v_967);
  let v_973 = (v_961 >> 2u);
  let v_974 = (v_973 + 1u);
  let v_976 = b_1[v_974];
  let v_977 = (32u - v_967);
  let v_978 = (v_976 << v_977);
  let v_979 = (v_972 | v_978);
  f_962 = v_979;
  } else {
  }
  let v_980 = f_962;
  let v_981 = (v_954 * 64u);
  let v_982 = (v_212 + v_981);
  let v_983 = (v_957 & 1u);
  let v_984 = (v_983 == 1u);
  let v_985 = select(0u, 32u, v_984);
  let v_986 = (v_982 + v_985);
  let v_987 = (v_986 + v_956);
  let v_989 = (v_987 >> 2u);
  let v_991 = b_1[v_989];
  let v_992 = (v_987 & 3u);
  let v_993 = (v_992 * 8u);
  f_988 = v_991;
  let v_994 = (v_993 != 0u);
  if (v_994) {
  let v_998 = (v_991 >> v_993);
  let v_999 = (v_987 >> 2u);
  let v_1000 = (v_999 + 1u);
  let v_1002 = b_1[v_1000];
  let v_1003 = (32u - v_993);
  let v_1004 = (v_1002 << v_1003);
  let v_1005 = (v_998 | v_1004);
  f_988 = v_1005;
  } else {
  }
  let v_1006 = f_988;
  let v_1007 = (v_957 >= 2u);
  let v_1008 = (v_1006 >> 4u);
  let v_1009 = select(v_1006, v_1008, v_1007);
  let v_1010 = (v_1009 & 252645135u);
  let v_1011 = (v_957 * 2u);
  let v_1012 = (v_980 >> v_1011);
  let v_1013 = (v_1012 & 50529027u);
  let v_1014 = (v_1013 << 4u);
  let v_1015 = (v_1010 | v_1014);
  let v_1016 = bitcast<i32>(v_1015);
  let v_1017 = dot4I8Packed(u32(v_953), u32(v_182));
  let v_1018 = dot4I8Packed(u32(v_1016), u32(v_187));
  let v_1019 = (v_1017 + v_1018);
  let v_1020 = f32(v_1019);
  let v_1021 = (v_191 * v_1020);
  let v_1023 = (bitcast<f32>(1107296256u) * v_197);
  let v_1024 = (v_1021 - v_1023);
  let v_1025 = (v_888 * v_1024);
  let v_1026 = f_34[v_210];
  let v_1027 = (v_1026 + v_1025);
  f_34[v_210] = v_1027;
  }
  }
  }
  }
  }
  continuing {
  let v_1028 = f_37;
  let v_1029 = (v_1028 + 1u);
  f_37 = v_1029;
  }
  }
  } else {
  }
  continuing {
  let v_1030 = f_38;
  let v_1031 = (v_1030 + 8u);
  f_38 = v_1031;
  }
  }
  } else {
  }
  f_37 = 0u;
  loop {
  let v_1036 = f_37;
  let v_1037 = (v_1036 < 4u);
  if (!(v_1037)) { break; }
  let v_1039 = f_37;
  let v_1040 = (v_1039 * 256u);
  let v_1041 = (v_1040 + v_58);
  let v_1045 = f_34[v_1039];
  let v_1047 = f_35[v_1039];
  let v_1048 = (v_1045 - v_1047);
  s_30[v_1041] = v_1048;
  continuing {
  let v_1049 = f_37;
  let v_1050 = (v_1049 + 1u);
  f_37 = v_1050;
  }
  }
  workgroupBarrier();
  f_39 = 128u;
  loop {
  let v_1056 = f_39;
  let v_1057 = (v_1056 > 0u);
  if (!(v_1057)) { break; }
  let v_1059 = f_39;
  let v_1060 = (v_58 < v_1059);
  if (v_1060) {
  f_37 = 0u;
  loop {
  let v_1068 = f_37;
  let v_1069 = (v_1068 < 4u);
  if (!(v_1069)) { break; }
  let v_1071 = f_37;
  let v_1072 = (v_1071 * 256u);
  let v_1073 = (v_1072 + v_58);
  let v_1076 = s_30[v_1073];
  let v_1077 = (v_1073 + v_1059);
  let v_1079 = s_30[v_1077];
  let v_1080 = (v_1076 + v_1079);
  s_30[v_1073] = v_1080;
  continuing {
  let v_1081 = f_37;
  let v_1082 = (v_1081 + 1u);
  f_37 = v_1082;
  }
  }
  } else {
  }
  workgroupBarrier();
  continuing {
  let v_1083 = f_39;
  let v_1084 = (v_1083 >> 1u);
  f_39 = v_1084;
  }
  }
  let v_1085 = (v_58 < v_155);
  let v_1086 = (v_55 < v_93);
  let v_1087 = (v_1085 && v_1086);
  if (v_1087) {
  let v_1091 = (v_55 * v_85);
  let v_1092 = (v_1091 + v_53);
  let v_1093 = (v_1092 + v_58);
  let v_1095 = (v_58 * 256u);
  let v_1097 = s_30[v_1095];
  b_3[v_1093] = v_1097;
  } else {
  }
  return;
}
