struct S_7 { m0: u32, m1: u32, m2: u32, m3: u32, m4: u32, m5: u32, m6: u32, m7: u32, };
@group(0) @binding(0) var<storage, read> b_0: S_7;
@group(0) @binding(1) var<storage, read> b_1: array<u32>;
@group(0) @binding(2) var<storage, read> b_2: array<f32>;
@group(0) @binding(3) var<storage, read_write> b_3: array<f32>;
@group(0) @binding(4) var<storage, read> b_4: array<u32>;
var<workgroup> s_27: array<f32, 256>;
@compute @workgroup_size(64, 1, 1)
fn main(@builtin(workgroup_id) i_48: vec3<u32>, @builtin(local_invocation_id) i_54: vec3<u32>) {
  var f_31: array<f32, 4>;
  var f_32: array<f32, 4>;
  var f_34: u32;
  var f_35: u32;
  var f_36: u32;
  var f_37: u32;
  var f_41: vec4<i32>;
  var f_237: u32;
  var f_396: u32;
  var f_583: u32;
  var f_642: u32;
  var f_728: u32;
  var f_808: u32;
  var f_828: u32;
  var f_913: u32;
  var f_933: u32;
  var f_1043: u32;
  var f_1068: u32;
  let v_49 = i_48;
  let v_50 = v_49.x;
  let v_51 = (v_50 * 4u);
  let v_52 = i_48;
  let v_53 = v_52.y;
  let v_55 = i_54;
  let v_56 = v_55.x;
  let v_59 = b_4[v_53];
  f_37 = 0u;
  let v_61 = b_0.m4;
  let v_63 = (v_61 == 1u);
  if (v_63) {
  f_37 = v_53;
  let v_69 = b_0.m5;
  let v_70 = (v_69 > 1u);
  if (v_70) {
  let v_75 = b_0.m5;
  let v_76 = (v_53 / v_75);
  f_37 = v_76;
  } else {
  }
  } else {
  }
  let v_77 = f_37;
  let v_80 = b_0.m6;
  let v_81 = (v_77 + v_80);
  let v_83 = b_0.m0;
  let v_85 = b_0.m1;
  let v_88 = b_0.m2;
  let v_91 = b_0.m3;
  let v_94 = (v_88 == 7u);
  let v_95 = (v_94 || false);
  let v_96 = (v_88 == 6u);
  let v_97 = (v_96 || v_95);
  let v_98 = (v_88 == 3u);
  let v_99 = (v_98 || v_97);
  let v_100 = (v_88 == 1u);
  let v_101 = (v_100 || v_99);
  let v_102 = (v_88 == 2u);
  let v_103 = (v_102 || v_101);
  let v_105 = (v_88 == 8u);
  let v_106 = (v_105 || v_103);
  let v_108 = (v_85 + 255u);
  let v_109 = (v_108 / 256u);
  let v_110 = (v_85 / 256u);
  let v_111 = select(v_110, v_109, v_106);
  let v_112 = (v_88 == 7u);
  let v_114 = select(0u, 192u, v_112);
  let v_115 = (v_88 == 6u);
  let v_117 = select(v_114, 176u, v_115);
  let v_118 = (v_88 == 3u);
  let v_120 = select(v_117, 160u, v_118);
  let v_121 = (v_88 == 1u);
  let v_123 = select(v_120, 512u, v_121);
  let v_124 = (v_88 == 2u);
  let v_126 = select(v_123, 144u, v_124);
  let v_127 = (v_88 == 8u);
  let v_129 = select(v_126, 272u, v_127);
  let v_131 = (v_88 == 23u);
  let v_133 = select(v_129, 136u, v_131);
  let v_135 = (v_88 == 14u);
  let v_137 = select(v_133, 210u, v_135);
  let v_139 = (v_88 == 13u);
  let v_140 = select(v_137, 176u, v_139);
  let v_142 = (v_88 == 12u);
  let v_143 = select(v_140, 144u, v_142);
  let v_145 = (v_85 + 31u);
  let v_147 = (v_145 / 32u);
  let v_148 = (v_143 / 8u);
  let v_149 = (v_147 * v_148);
  let v_150 = (v_111 * v_143);
  let v_151 = select(v_150, v_149, v_106);
  let v_152 = (v_56 * 4u);
  f_34 = 0u;
  loop {
  let v_157 = f_34;
  let v_158 = (v_157 < 4u);
  if (!(v_158)) { break; }
  let v_160 = f_34;
  f_31[v_160] = bitcast<f32>(0u);
  f_32[v_160] = bitcast<f32>(0u);
  continuing {
  let v_164 = f_34;
  let v_165 = (v_164 + 1u);
  f_34 = v_165;
  }
  }
  let v_167 = min(v_51, v_83);
  let v_168 = (v_83 - v_167);
  let v_169 = min(4u, v_168);
  let v_170 = (v_53 < v_91);
  if (v_170) {
  f_35 = 0u;
  loop {
  let v_178 = f_35;
  let v_179 = (v_178 < v_111);
  if (!(v_179)) { break; }
  let v_181 = f_35;
  let v_182 = (v_181 * 256u);
  let v_183 = (v_182 + v_152);
  let v_184 = (v_183 >= v_85);
  if (v_184) {
  } else {
  }
  let v_188 = (v_81 * v_85);
  let v_189 = (v_181 * 256u);
  let v_190 = (v_188 + v_189);
  let v_191 = (v_190 + v_152);
  let v_195 = b_2[v_191];
  let v_196 = (v_191 + 1u);
  let v_198 = b_2[v_196];
  let v_199 = (v_191 + 2u);
  let v_201 = b_2[v_199];
  let v_202 = (v_191 + 3u);
  let v_204 = b_2[v_202];
  let v_205 = vec4<f32>(v_195, v_198, v_201, v_204);
  let v_206 = v_205.x;
  let v_207 = v_205.y;
  let v_208 = (v_206 + v_207);
  let v_209 = v_205.z;
  let v_210 = (v_208 + v_209);
  let v_211 = v_205.w;
  let v_212 = (v_210 + v_211);
  let v_213 = (v_59 * v_83);
  let v_214 = (v_213 + v_51);
  let v_215 = (v_214 * v_151);
  let v_216 = (v_181 * v_143);
  let v_217 = (v_215 + v_216);
  f_34 = 0u;
  loop {
  let v_222 = f_34;
  let v_223 = (v_222 < v_169);
  if (!(v_223)) { break; }
  let v_225 = f_34;
  let v_226 = (v_225 * v_151);
  let v_227 = (v_217 + v_226);
  let v_230 = (v_88 == 12u);
  let v_231 = (v_88 == 13u);
  let v_232 = (v_230 || v_231);
  if (v_232) {
  let v_236 = (v_152 / 32u);
  let v_238 = (v_236 < 4u);
  if (v_238) {
  let v_242 = (v_227 + 4u);
  let v_243 = (v_242 + v_236);
  let v_244 = (v_243 >> 2u);
  let v_246 = b_1[v_244];
  let v_247 = (v_243 & 3u);
  let v_248 = (v_247 * 8u);
  let v_249 = (v_246 >> v_248);
  let v_250 = (v_249 & 255u);
  let v_252 = (v_250 & 63u);
  f_237 = v_252;
  } else {
  let v_253 = (v_227 + 8u);
  let v_254 = (v_253 + v_236);
  let v_255 = (v_254 >> 2u);
  let v_257 = b_1[v_255];
  let v_258 = (v_254 & 3u);
  let v_259 = (v_258 * 8u);
  let v_260 = (v_257 >> v_259);
  let v_261 = (v_260 & 255u);
  let v_263 = (v_261 & 15u);
  let v_264 = (v_227 + v_236);
  let v_265 = (v_264 >> 2u);
  let v_267 = b_1[v_265];
  let v_268 = (v_264 & 3u);
  let v_269 = (v_268 * 8u);
  let v_270 = (v_267 >> v_269);
  let v_271 = (v_270 & 255u);
  let v_272 = (v_271 >> 6u);
  let v_273 = (v_272 << 4u);
  let v_274 = (v_263 | v_273);
  f_237 = v_274;
  }
  let v_275 = f_237;
  let v_276 = bitcast<i32>(v_275);
  let v_277 = f32(v_276);
  let v_278 = (v_88 == 12u);
  if (v_278) {
  let v_282 = (v_152 / 64u);
  let v_283 = (v_152 & 63u);
  let v_285 = (v_227 + 16u);
  let v_286 = (v_282 * 32u);
  let v_287 = (v_285 + v_286);
  let v_288 = (v_283 & 31u);
  let v_289 = (v_287 + v_288);
  let v_290 = (v_289 >> 2u);
  let v_292 = b_1[v_290];
  let v_293 = (v_283 >= 32u);
  let v_294 = select(0u, 4u, v_293);
  let v_295 = (v_292 >> v_294);
  let v_296 = (v_295 & 15u);
  let v_297 = bitcast<i32>(v_296);
  let v_298 = (8u + v_294);
  let v_299 = (v_292 >> v_298);
  let v_300 = (v_299 & 15u);
  let v_301 = bitcast<i32>(v_300);
  let v_302 = (16u + v_294);
  let v_303 = (v_292 >> v_302);
  let v_304 = (v_303 & 15u);
  let v_305 = bitcast<i32>(v_304);
  let v_307 = (24u + v_294);
  let v_308 = (v_292 >> v_307);
  let v_309 = (v_308 & 15u);
  let v_310 = bitcast<i32>(v_309);
  let v_311 = vec4<i32>(v_297, v_301, v_305, v_310);
  f_41 = v_311;
  } else {
  let v_312 = (v_152 / 64u);
  let v_313 = (v_152 & 63u);
  let v_314 = (v_313 & 31u);
  let v_315 = (v_313 >= 32u);
  let v_317 = (v_227 + 48u);
  let v_318 = (v_312 * 32u);
  let v_319 = (v_317 + v_318);
  let v_320 = (v_319 + v_314);
  let v_321 = (v_320 >> 2u);
  let v_323 = b_1[v_321];
  let v_324 = (v_227 + 16u);
  let v_325 = (v_324 + v_314);
  let v_326 = (v_325 >> 2u);
  let v_328 = b_1[v_326];
  let v_329 = select(0u, 4u, v_315);
  let v_330 = (2u * v_312);
  let v_331 = select(0u, 1u, v_315);
  let v_332 = (v_330 + v_331);
  let v_333 = (v_323 >> v_329);
  let v_334 = (v_333 & 15u);
  let v_335 = (v_328 >> v_332);
  let v_336 = (v_335 & 1u);
  let v_337 = (v_336 << 4u);
  let v_338 = (v_334 | v_337);
  let v_339 = bitcast<i32>(v_338);
  let v_340 = (8u + v_329);
  let v_341 = (v_323 >> v_340);
  let v_342 = (v_341 & 15u);
  let v_343 = (8u + v_332);
  let v_344 = (v_328 >> v_343);
  let v_345 = (v_344 & 1u);
  let v_346 = (v_345 << 4u);
  let v_347 = (v_342 | v_346);
  let v_348 = bitcast<i32>(v_347);
  let v_349 = (16u + v_329);
  let v_350 = (v_323 >> v_349);
  let v_351 = (v_350 & 15u);
  let v_352 = (16u + v_332);
  let v_353 = (v_328 >> v_352);
  let v_354 = (v_353 & 1u);
  let v_355 = (v_354 << 4u);
  let v_356 = (v_351 | v_355);
  let v_357 = bitcast<i32>(v_356);
  let v_358 = (24u + v_329);
  let v_359 = (v_323 >> v_358);
  let v_360 = (v_359 & 15u);
  let v_361 = (24u + v_332);
  let v_362 = (v_328 >> v_361);
  let v_363 = (v_362 & 1u);
  let v_364 = (v_363 << 4u);
  let v_365 = (v_360 | v_364);
  let v_366 = bitcast<i32>(v_365);
  let v_367 = vec4<i32>(v_339, v_348, v_357, v_366);
  f_41 = v_367;
  }
  let v_368 = (v_227 >> 2u);
  let v_370 = b_1[v_368];
  let v_372 = unpack2x16float(v_370);
  let v_373 = (v_227 & 2u);
  let v_374 = (v_373 != 0u);
  let v_375 = v_372.y;
  let v_376 = v_372.x;
  let v_377 = select(v_376, v_375, v_374);
  let v_378 = (v_377 * v_277);
  let v_379 = f_41;
  let v_380 = vec4<f32>(v_379);
  let v_381 = dot(v_380, v_205);
  let v_382 = (v_378 * v_381);
  let v_383 = f_31[v_225];
  let v_384 = (v_383 + v_382);
  f_31[v_225] = v_384;
  let v_385 = f_32[v_225];
  let v_386 = (v_227 + 2u);
  let v_387 = (v_386 >> 2u);
  let v_389 = b_1[v_387];
  let v_390 = unpack2x16float(v_389);
  let v_391 = (v_386 & 2u);
  let v_392 = (v_391 != 0u);
  let v_393 = v_390.y;
  let v_394 = v_390.x;
  let v_395 = select(v_394, v_393, v_392);
  let v_397 = (v_236 < 4u);
  if (v_397) {
  let v_401 = (v_227 + 8u);
  let v_402 = (v_401 + v_236);
  let v_403 = (v_402 >> 2u);
  let v_405 = b_1[v_403];
  let v_406 = (v_402 & 3u);
  let v_407 = (v_406 * 8u);
  let v_408 = (v_405 >> v_407);
  let v_409 = (v_408 & 255u);
  let v_410 = (v_409 & 63u);
  f_396 = v_410;
  } else {
  let v_411 = (v_227 + 8u);
  let v_412 = (v_411 + v_236);
  let v_413 = (v_412 >> 2u);
  let v_415 = b_1[v_413];
  let v_416 = (v_412 & 3u);
  let v_417 = (v_416 * 8u);
  let v_418 = (v_415 >> v_417);
  let v_419 = (v_418 & 255u);
  let v_420 = (v_419 >> 4u);
  let v_421 = (v_227 + 4u);
  let v_422 = (v_421 + v_236);
  let v_423 = (v_422 >> 2u);
  let v_425 = b_1[v_423];
  let v_426 = (v_422 & 3u);
  let v_427 = (v_426 * 8u);
  let v_428 = (v_425 >> v_427);
  let v_429 = (v_428 & 255u);
  let v_430 = (v_429 >> 6u);
  let v_431 = (v_430 << 4u);
  let v_432 = (v_420 | v_431);
  f_396 = v_432;
  }
  let v_433 = f_396;
  let v_434 = bitcast<i32>(v_433);
  let v_435 = f32(v_434);
  let v_436 = (v_395 * v_435);
  let v_437 = (v_436 * v_212);
  let v_438 = (v_385 + v_437);
  f_32[v_225] = v_438;
  } else {
  let v_439 = (v_88 == 23u);
  if (v_439) {
  let v_443 = (v_152 / 32u);
  let v_444 = (v_227 >> 2u);
  let v_446 = b_1[v_444];
  let v_447 = (v_446 >> 16u);
  let v_448 = (v_227 + 4u);
  let v_449 = (v_443 / 2u);
  let v_450 = (v_448 + v_449);
  let v_451 = (v_450 >> 2u);
  let v_453 = b_1[v_451];
  let v_454 = (v_450 & 3u);
  let v_455 = (v_454 * 8u);
  let v_456 = (v_453 >> v_455);
  let v_457 = (v_456 & 255u);
  let v_458 = (v_443 & 1u);
  let v_459 = (4u * v_458);
  let v_460 = (v_457 >> v_459);
  let v_461 = (v_460 & 15u);
  let v_462 = (2u * v_443);
  let v_463 = (v_447 >> v_462);
  let v_464 = (v_463 & 3u);
  let v_465 = (v_464 << 4u);
  let v_466 = (v_461 | v_465);
  let v_467 = bitcast<i32>(v_466);
  let v_469 = (v_467 - 32i);
  let v_470 = f32(v_469);
  let v_471 = (v_227 >> 2u);
  let v_473 = b_1[v_471];
  let v_474 = unpack2x16float(v_473);
  let v_475 = (v_227 & 2u);
  let v_476 = (v_475 != 0u);
  let v_477 = v_474.y;
  let v_478 = v_474.x;
  let v_479 = select(v_478, v_477, v_476);
  let v_480 = (v_479 * v_470);
  let v_481 = (v_152 / 32u);
  let v_482 = (v_152 & 31u);
  let v_483 = (v_482 >= 16u);
  let v_484 = (v_227 + 8u);
  let v_485 = (v_481 * 16u);
  let v_486 = (v_484 + v_485);
  let v_487 = (v_482 - 16u);
  let v_488 = select(v_482, v_487, v_483);
  let v_489 = (v_486 + v_488);
  let v_490 = (v_489 >> 2u);
  let v_492 = b_1[v_490];
  let v_493 = select(0u, 4u, v_483);
  let v_494 = (v_492 >> v_493);
  let v_495 = (v_494 & 15u);
  let v_496 = (v_495 < 4u);
  let v_498 = (v_495 < 8u);
  let v_500 = (v_495 < 12u);
  let v_503 = select(1901675829u, 639175937u, v_500);
  let v_504 = select(v_503, 4142587343u, v_498);
  let v_505 = select(v_504, 3215825025u, v_496);
  let v_506 = bitcast<i32>(v_505);
  let v_507 = (v_495 & 3u);
  let v_508 = (v_507 * 8u);
  let v_509 = bitcast<i32>(v_508);
  let v_511 = extractBits(v_506, u32(v_509), u32(8i));
  let v_512 = (8u + v_493);
  let v_513 = (v_492 >> v_512);
  let v_514 = (v_513 & 15u);
  let v_515 = (v_514 < 4u);
  let v_516 = (v_514 < 8u);
  let v_517 = (v_514 < 12u);
  let v_518 = select(1901675829u, 639175937u, v_517);
  let v_519 = select(v_518, 4142587343u, v_516);
  let v_520 = select(v_519, 3215825025u, v_515);
  let v_521 = bitcast<i32>(v_520);
  let v_522 = (v_514 & 3u);
  let v_523 = (v_522 * 8u);
  let v_524 = bitcast<i32>(v_523);
  let v_525 = extractBits(v_521, u32(v_524), u32(8i));
  let v_526 = (16u + v_493);
  let v_527 = (v_492 >> v_526);
  let v_528 = (v_527 & 15u);
  let v_529 = (v_528 < 4u);
  let v_530 = (v_528 < 8u);
  let v_531 = (v_528 < 12u);
  let v_532 = select(1901675829u, 639175937u, v_531);
  let v_533 = select(v_532, 4142587343u, v_530);
  let v_534 = select(v_533, 3215825025u, v_529);
  let v_535 = bitcast<i32>(v_534);
  let v_536 = (v_528 & 3u);
  let v_537 = (v_536 * 8u);
  let v_538 = bitcast<i32>(v_537);
  let v_539 = extractBits(v_535, u32(v_538), u32(8i));
  let v_540 = (24u + v_493);
  let v_541 = (v_492 >> v_540);
  let v_542 = (v_541 & 15u);
  let v_543 = (v_542 < 4u);
  let v_544 = (v_542 < 8u);
  let v_545 = (v_542 < 12u);
  let v_546 = select(1901675829u, 639175937u, v_545);
  let v_547 = select(v_546, 4142587343u, v_544);
  let v_548 = select(v_547, 3215825025u, v_543);
  let v_549 = bitcast<i32>(v_548);
  let v_550 = (v_542 & 3u);
  let v_551 = (v_550 * 8u);
  let v_552 = bitcast<i32>(v_551);
  let v_553 = extractBits(v_549, u32(v_552), u32(8i));
  let v_554 = vec4<i32>(v_511, v_525, v_539, v_553);
  let v_555 = vec4<f32>(v_554);
  let v_556 = dot(v_555, v_205);
  let v_557 = (v_480 * v_556);
  let v_558 = f_31[v_225];
  let v_559 = (v_558 + v_557);
  f_31[v_225] = v_559;
  } else {
  let v_560 = (v_88 == 8u);
  if (v_560) {
  let v_564 = (v_152 / 32u);
  let v_566 = (v_564 * 34u);
  let v_567 = (v_227 + v_566);
  let v_568 = (v_567 >> 2u);
  let v_570 = b_1[v_568];
  let v_571 = unpack2x16float(v_570);
  let v_572 = (v_567 & 2u);
  let v_573 = (v_572 != 0u);
  let v_574 = v_571.y;
  let v_575 = v_571.x;
  let v_576 = select(v_575, v_574, v_573);
  let v_577 = (v_152 / 32u);
  let v_578 = (v_577 * 34u);
  let v_579 = (v_227 + v_578);
  let v_580 = (v_579 + 2u);
  let v_581 = (v_152 & 31u);
  let v_582 = (v_580 + v_581);
  let v_584 = (v_582 >> 2u);
  let v_586 = b_1[v_584];
  let v_587 = (v_582 & 3u);
  let v_588 = (v_587 * 8u);
  f_583 = v_586;
  let v_589 = (v_588 != 0u);
  if (v_589) {
  let v_593 = (v_586 >> v_588);
  let v_594 = (v_582 >> 2u);
  let v_595 = (v_594 + 1u);
  let v_597 = b_1[v_595];
  let v_598 = (32u - v_588);
  let v_599 = (v_597 << v_598);
  let v_600 = (v_593 | v_599);
  f_583 = v_600;
  } else {
  }
  let v_601 = f_583;
  let v_602 = bitcast<i32>(v_601);
  let v_604 = extractBits(v_602, u32(0i), u32(8i));
  let v_605 = extractBits(v_602, u32(8i), u32(8i));
  let v_607 = extractBits(v_602, u32(16i), u32(8i));
  let v_609 = extractBits(v_602, u32(24i), u32(8i));
  let v_610 = vec4<i32>(v_604, v_605, v_607, v_609);
  let v_611 = vec4<f32>(v_610);
  let v_612 = dot(v_611, v_205);
  let v_613 = (v_576 * v_612);
  let v_614 = f_31[v_225];
  let v_615 = (v_614 + v_613);
  f_31[v_225] = v_615;
  } else {
  let v_616 = (v_88 == 2u);
  if (v_616) {
  let v_620 = (v_152 / 32u);
  let v_622 = (v_620 * 18u);
  let v_623 = (v_227 + v_622);
  let v_624 = (v_623 >> 2u);
  let v_626 = b_1[v_624];
  let v_627 = unpack2x16float(v_626);
  let v_628 = (v_623 & 2u);
  let v_629 = (v_628 != 0u);
  let v_630 = v_627.y;
  let v_631 = v_627.x;
  let v_632 = select(v_631, v_630, v_629);
  let v_633 = (v_152 & 31u);
  let v_634 = (v_633 >= 16u);
  let v_635 = select(0u, 4u, v_634);
  let v_636 = (v_152 / 32u);
  let v_637 = (v_636 * 18u);
  let v_638 = (v_227 + v_637);
  let v_639 = (v_638 + 2u);
  let v_640 = (v_633 & 15u);
  let v_641 = (v_639 + v_640);
  let v_643 = (v_641 >> 2u);
  let v_645 = b_1[v_643];
  let v_646 = (v_641 & 3u);
  let v_647 = (v_646 * 8u);
  f_642 = v_645;
  let v_648 = (v_647 != 0u);
  if (v_648) {
  let v_652 = (v_645 >> v_647);
  let v_653 = (v_641 >> 2u);
  let v_654 = (v_653 + 1u);
  let v_656 = b_1[v_654];
  let v_657 = (32u - v_647);
  let v_658 = (v_656 << v_657);
  let v_659 = (v_652 | v_658);
  f_642 = v_659;
  } else {
  }
  let v_660 = f_642;
  let v_661 = (v_660 >> v_635);
  let v_662 = (v_661 & 15u);
  let v_663 = bitcast<i32>(v_662);
  let v_664 = (8u + v_635);
  let v_665 = (v_660 >> v_664);
  let v_666 = (v_665 & 15u);
  let v_667 = bitcast<i32>(v_666);
  let v_668 = (16u + v_635);
  let v_669 = (v_660 >> v_668);
  let v_670 = (v_669 & 15u);
  let v_671 = bitcast<i32>(v_670);
  let v_672 = (24u + v_635);
  let v_673 = (v_660 >> v_672);
  let v_674 = (v_673 & 15u);
  let v_675 = bitcast<i32>(v_674);
  let v_676 = vec4<i32>(v_663, v_667, v_671, v_675);
  let v_677 = vec4<i32>(8i, 8i, 8i, 8i);
  let v_678 = (v_676 - v_677);
  let v_679 = vec4<f32>(v_678);
  let v_680 = dot(v_679, v_205);
  let v_681 = (v_632 * v_680);
  let v_682 = f_31[v_225];
  let v_683 = (v_682 + v_681);
  f_31[v_225] = v_683;
  } else {
  let v_684 = (v_88 == 1u);
  if (v_684) {
  let v_688 = (v_152 * 2u);
  let v_689 = (v_227 + v_688);
  let v_690 = (v_689 >> 2u);
  let v_692 = b_1[v_690];
  let v_693 = unpack2x16float(v_692);
  let v_694 = (v_690 + 1u);
  let v_696 = b_1[v_694];
  let v_697 = unpack2x16float(v_696);
  let v_698 = vec4<f32>(v_693, v_697);
  let v_699 = dot(v_698, v_205);
  let v_700 = f_31[v_225];
  let v_701 = (v_700 + v_699);
  f_31[v_225] = v_701;
  } else {
  let v_702 = (v_88 == 3u);
  if (v_702) {
  let v_706 = (v_152 / 32u);
  let v_708 = (v_706 * 20u);
  let v_709 = (v_227 + v_708);
  let v_710 = (v_709 >> 2u);
  let v_712 = b_1[v_710];
  let v_713 = unpack2x16float(v_712);
  let v_714 = (v_709 & 2u);
  let v_715 = (v_714 != 0u);
  let v_716 = v_713.y;
  let v_717 = v_713.x;
  let v_718 = select(v_717, v_716, v_715);
  let v_719 = (v_152 & 31u);
  let v_720 = (v_719 >= 16u);
  let v_721 = select(0u, 4u, v_720);
  let v_722 = (v_152 / 32u);
  let v_723 = (v_722 * 20u);
  let v_724 = (v_227 + v_723);
  let v_725 = (v_724 + 4u);
  let v_726 = (v_719 & 15u);
  let v_727 = (v_725 + v_726);
  let v_729 = (v_727 >> 2u);
  let v_731 = b_1[v_729];
  let v_732 = (v_727 & 3u);
  let v_733 = (v_732 * 8u);
  f_728 = v_731;
  let v_734 = (v_733 != 0u);
  if (v_734) {
  let v_738 = (v_731 >> v_733);
  let v_739 = (v_727 >> 2u);
  let v_740 = (v_739 + 1u);
  let v_742 = b_1[v_740];
  let v_743 = (32u - v_733);
  let v_744 = (v_742 << v_743);
  let v_745 = (v_738 | v_744);
  f_728 = v_745;
  } else {
  }
  let v_746 = f_728;
  let v_747 = (v_746 >> v_721);
  let v_748 = (v_747 & 15u);
  let v_749 = bitcast<i32>(v_748);
  let v_750 = (8u + v_721);
  let v_751 = (v_746 >> v_750);
  let v_752 = (v_751 & 15u);
  let v_753 = bitcast<i32>(v_752);
  let v_754 = (16u + v_721);
  let v_755 = (v_746 >> v_754);
  let v_756 = (v_755 & 15u);
  let v_757 = bitcast<i32>(v_756);
  let v_758 = (24u + v_721);
  let v_759 = (v_746 >> v_758);
  let v_760 = (v_759 & 15u);
  let v_761 = bitcast<i32>(v_760);
  let v_762 = vec4<i32>(v_749, v_753, v_757, v_761);
  let v_763 = vec4<f32>(v_762);
  let v_764 = dot(v_763, v_205);
  let v_765 = (v_718 * v_764);
  let v_766 = f_31[v_225];
  let v_767 = (v_766 + v_765);
  f_31[v_225] = v_767;
  let v_768 = f_32[v_225];
  let v_769 = (v_709 + 2u);
  let v_770 = (v_769 >> 2u);
  let v_772 = b_1[v_770];
  let v_773 = unpack2x16float(v_772);
  let v_774 = (v_769 & 2u);
  let v_775 = (v_774 != 0u);
  let v_776 = v_773.y;
  let v_777 = v_773.x;
  let v_778 = select(v_777, v_776, v_775);
  let v_779 = (v_778 * v_212);
  let v_780 = (v_768 - v_779);
  f_32[v_225] = v_780;
  } else {
  let v_781 = (v_88 == 6u);
  if (v_781) {
  let v_785 = (v_152 / 32u);
  let v_787 = (v_785 * 22u);
  let v_788 = (v_227 + v_787);
  let v_789 = (v_788 >> 2u);
  let v_791 = b_1[v_789];
  let v_792 = unpack2x16float(v_791);
  let v_793 = (v_788 & 2u);
  let v_794 = (v_793 != 0u);
  let v_795 = v_792.y;
  let v_796 = v_792.x;
  let v_797 = select(v_796, v_795, v_794);
  let v_798 = (v_152 & 31u);
  let v_799 = (v_798 >= 16u);
  let v_800 = select(0u, 4u, v_799);
  let v_801 = (v_152 / 32u);
  let v_802 = (v_801 * 22u);
  let v_803 = (v_227 + v_802);
  let v_804 = (v_803 + 2u);
  let v_805 = (v_804 + 4u);
  let v_806 = (v_798 & 15u);
  let v_807 = (v_805 + v_806);
  let v_809 = (v_807 >> 2u);
  let v_811 = b_1[v_809];
  let v_812 = (v_807 & 3u);
  let v_813 = (v_812 * 8u);
  f_808 = v_811;
  let v_814 = (v_813 != 0u);
  if (v_814) {
  let v_818 = (v_811 >> v_813);
  let v_819 = (v_807 >> 2u);
  let v_820 = (v_819 + 1u);
  let v_822 = b_1[v_820];
  let v_823 = (32u - v_813);
  let v_824 = (v_822 << v_823);
  let v_825 = (v_818 | v_824);
  f_808 = v_825;
  } else {
  }
  let v_826 = f_808;
  let v_827 = (v_803 + 2u);
  let v_829 = (v_827 >> 2u);
  let v_831 = b_1[v_829];
  let v_832 = (v_827 & 3u);
  let v_833 = (v_832 * 8u);
  f_828 = v_831;
  let v_834 = (v_833 != 0u);
  if (v_834) {
  let v_838 = (v_831 >> v_833);
  let v_839 = (v_827 >> 2u);
  let v_840 = (v_839 + 1u);
  let v_842 = b_1[v_840];
  let v_843 = (32u - v_833);
  let v_844 = (v_842 << v_843);
  let v_845 = (v_838 | v_844);
  f_828 = v_845;
  } else {
  }
  let v_846 = f_828;
  let v_847 = (v_846 >> v_798);
  let v_848 = (v_847 & 15u);
  let v_849 = (v_826 >> v_800);
  let v_850 = (v_849 & 15u);
  let v_851 = (v_848 & 1u);
  let v_852 = (v_851 << 4u);
  let v_853 = (v_850 | v_852);
  let v_854 = bitcast<i32>(v_853);
  let v_855 = (8u + v_800);
  let v_856 = (v_826 >> v_855);
  let v_857 = (v_856 & 15u);
  let v_858 = (v_848 >> 1u);
  let v_859 = (v_858 & 1u);
  let v_860 = (v_859 << 4u);
  let v_861 = (v_857 | v_860);
  let v_862 = bitcast<i32>(v_861);
  let v_863 = (16u + v_800);
  let v_864 = (v_826 >> v_863);
  let v_865 = (v_864 & 15u);
  let v_866 = (v_848 >> 2u);
  let v_867 = (v_866 & 1u);
  let v_868 = (v_867 << 4u);
  let v_869 = (v_865 | v_868);
  let v_870 = bitcast<i32>(v_869);
  let v_871 = (24u + v_800);
  let v_872 = (v_826 >> v_871);
  let v_873 = (v_872 & 15u);
  let v_874 = (v_848 >> 3u);
  let v_875 = (v_874 & 1u);
  let v_876 = (v_875 << 4u);
  let v_877 = (v_873 | v_876);
  let v_878 = bitcast<i32>(v_877);
  let v_879 = vec4<i32>(v_854, v_862, v_870, v_878);
  let v_880 = vec4<i32>(16i, 16i, 16i, 16i);
  let v_881 = (v_879 - v_880);
  let v_882 = vec4<f32>(v_881);
  let v_883 = dot(v_882, v_205);
  let v_884 = (v_797 * v_883);
  let v_885 = f_31[v_225];
  let v_886 = (v_885 + v_884);
  f_31[v_225] = v_886;
  } else {
  let v_887 = (v_88 == 7u);
  if (v_887) {
  let v_891 = (v_152 / 32u);
  let v_892 = (v_891 * 24u);
  let v_893 = (v_227 + v_892);
  let v_894 = (v_893 >> 2u);
  let v_896 = b_1[v_894];
  let v_897 = unpack2x16float(v_896);
  let v_898 = (v_893 & 2u);
  let v_899 = (v_898 != 0u);
  let v_900 = v_897.y;
  let v_901 = v_897.x;
  let v_902 = select(v_901, v_900, v_899);
  let v_903 = (v_152 & 31u);
  let v_904 = (v_903 >= 16u);
  let v_905 = select(0u, 4u, v_904);
  let v_906 = (v_152 / 32u);
  let v_907 = (v_906 * 24u);
  let v_908 = (v_227 + v_907);
  let v_909 = (v_908 + 4u);
  let v_910 = (v_909 + 4u);
  let v_911 = (v_903 & 15u);
  let v_912 = (v_910 + v_911);
  let v_914 = (v_912 >> 2u);
  let v_916 = b_1[v_914];
  let v_917 = (v_912 & 3u);
  let v_918 = (v_917 * 8u);
  f_913 = v_916;
  let v_919 = (v_918 != 0u);
  if (v_919) {
  let v_923 = (v_916 >> v_918);
  let v_924 = (v_912 >> 2u);
  let v_925 = (v_924 + 1u);
  let v_927 = b_1[v_925];
  let v_928 = (32u - v_918);
  let v_929 = (v_927 << v_928);
  let v_930 = (v_923 | v_929);
  f_913 = v_930;
  } else {
  }
  let v_931 = f_913;
  let v_932 = (v_908 + 4u);
  let v_934 = (v_932 >> 2u);
  let v_936 = b_1[v_934];
  let v_937 = (v_932 & 3u);
  let v_938 = (v_937 * 8u);
  f_933 = v_936;
  let v_939 = (v_938 != 0u);
  if (v_939) {
  let v_943 = (v_936 >> v_938);
  let v_944 = (v_932 >> 2u);
  let v_945 = (v_944 + 1u);
  let v_947 = b_1[v_945];
  let v_948 = (32u - v_938);
  let v_949 = (v_947 << v_948);
  let v_950 = (v_943 | v_949);
  f_933 = v_950;
  } else {
  }
  let v_951 = f_933;
  let v_952 = (v_951 >> v_903);
  let v_953 = (v_952 & 15u);
  let v_954 = (v_931 >> v_905);
  let v_955 = (v_954 & 15u);
  let v_956 = (v_953 & 1u);
  let v_957 = (v_956 << 4u);
  let v_958 = (v_955 | v_957);
  let v_959 = bitcast<i32>(v_958);
  let v_960 = (8u + v_905);
  let v_961 = (v_931 >> v_960);
  let v_962 = (v_961 & 15u);
  let v_963 = (v_953 >> 1u);
  let v_964 = (v_963 & 1u);
  let v_965 = (v_964 << 4u);
  let v_966 = (v_962 | v_965);
  let v_967 = bitcast<i32>(v_966);
  let v_968 = (16u + v_905);
  let v_969 = (v_931 >> v_968);
  let v_970 = (v_969 & 15u);
  let v_971 = (v_953 >> 2u);
  let v_972 = (v_971 & 1u);
  let v_973 = (v_972 << 4u);
  let v_974 = (v_970 | v_973);
  let v_975 = bitcast<i32>(v_974);
  let v_976 = (24u + v_905);
  let v_977 = (v_931 >> v_976);
  let v_978 = (v_977 & 15u);
  let v_979 = (v_953 >> 3u);
  let v_980 = (v_979 & 1u);
  let v_981 = (v_980 << 4u);
  let v_982 = (v_978 | v_981);
  let v_983 = bitcast<i32>(v_982);
  let v_984 = vec4<i32>(v_959, v_967, v_975, v_983);
  let v_985 = vec4<f32>(v_984);
  let v_986 = dot(v_985, v_205);
  let v_987 = (v_902 * v_986);
  let v_988 = f_31[v_225];
  let v_989 = (v_988 + v_987);
  f_31[v_225] = v_989;
  let v_990 = f_32[v_225];
  let v_991 = (v_893 + 2u);
  let v_992 = (v_991 >> 2u);
  let v_994 = b_1[v_992];
  let v_995 = unpack2x16float(v_994);
  let v_996 = (v_991 & 2u);
  let v_997 = (v_996 != 0u);
  let v_998 = v_995.y;
  let v_999 = v_995.x;
  let v_1000 = select(v_999, v_998, v_997);
  let v_1001 = (v_1000 * v_212);
  let v_1002 = (v_990 - v_1001);
  f_32[v_225] = v_1002;
  } else {
  let v_1003 = (v_227 + 192u);
  let v_1004 = (v_152 / 16u);
  let v_1005 = (v_1003 + v_1004);
  let v_1006 = (v_1005 >> 2u);
  let v_1008 = b_1[v_1006];
  let v_1009 = (v_1005 & 3u);
  let v_1010 = (v_1009 * 8u);
  let v_1011 = (v_1008 >> v_1010);
  let v_1012 = (v_1011 & 255u);
  let v_1014 = (v_1012 >= 128u);
  let v_1015 = bitcast<i32>(v_1012);
  let v_1017 = (v_1015 - 256i);
  let v_1018 = bitcast<i32>(v_1012);
  let v_1019 = select(v_1018, v_1017, v_1014);
  let v_1021 = (v_227 + 208u);
  let v_1022 = (v_1021 >> 2u);
  let v_1024 = b_1[v_1022];
  let v_1025 = unpack2x16float(v_1024);
  let v_1026 = (v_1021 & 2u);
  let v_1027 = (v_1026 != 0u);
  let v_1028 = v_1025.y;
  let v_1029 = v_1025.x;
  let v_1030 = select(v_1029, v_1028, v_1027);
  let v_1031 = f32(v_1019);
  let v_1032 = (v_1030 * v_1031);
  let v_1033 = (v_152 / 128u);
  let v_1035 = (v_152 & 127u);
  let v_1036 = (v_1035 & 31u);
  let v_1037 = (v_1033 * 64u);
  let v_1038 = (v_227 + v_1037);
  let v_1039 = (v_227 + 128u);
  let v_1040 = (v_1033 * 32u);
  let v_1041 = (v_1039 + v_1040);
  let v_1042 = (v_1041 + v_1036);
  let v_1044 = (v_1042 >> 2u);
  let v_1046 = b_1[v_1044];
  let v_1047 = (v_1042 & 3u);
  let v_1048 = (v_1047 * 8u);
  f_1043 = v_1046;
  let v_1049 = (v_1048 != 0u);
  if (v_1049) {
  let v_1053 = (v_1046 >> v_1048);
  let v_1054 = (v_1042 >> 2u);
  let v_1055 = (v_1054 + 1u);
  let v_1057 = b_1[v_1055];
  let v_1058 = (32u - v_1048);
  let v_1059 = (v_1057 << v_1058);
  let v_1060 = (v_1053 | v_1059);
  f_1043 = v_1060;
  } else {
  }
  let v_1061 = f_1043;
  let v_1062 = (v_1035 / 32u);
  let v_1063 = (v_1062 & 1u);
  let v_1064 = (v_1063 == 1u);
  let v_1065 = select(0u, 32u, v_1064);
  let v_1066 = (v_1038 + v_1065);
  let v_1067 = (v_1066 + v_1036);
  let v_1069 = (v_1067 >> 2u);
  let v_1071 = b_1[v_1069];
  let v_1072 = (v_1067 & 3u);
  let v_1073 = (v_1072 * 8u);
  f_1068 = v_1071;
  let v_1074 = (v_1073 != 0u);
  if (v_1074) {
  let v_1078 = (v_1071 >> v_1073);
  let v_1079 = (v_1067 >> 2u);
  let v_1080 = (v_1079 + 1u);
  let v_1082 = b_1[v_1080];
  let v_1083 = (32u - v_1073);
  let v_1084 = (v_1082 << v_1083);
  let v_1085 = (v_1078 | v_1084);
  f_1068 = v_1085;
  } else {
  }
  let v_1086 = f_1068;
  let v_1087 = (v_1062 >= 2u);
  let v_1088 = select(0u, 4u, v_1087);
  let v_1089 = (v_1062 * 2u);
  let v_1090 = (v_1086 >> v_1088);
  let v_1091 = (v_1090 & 15u);
  let v_1092 = (v_1061 >> v_1089);
  let v_1093 = (v_1092 & 3u);
  let v_1094 = (v_1093 << 4u);
  let v_1095 = (v_1091 | v_1094);
  let v_1096 = bitcast<i32>(v_1095);
  let v_1097 = (v_1096 - 32i);
  let v_1098 = (8u + v_1088);
  let v_1099 = (v_1086 >> v_1098);
  let v_1100 = (v_1099 & 15u);
  let v_1101 = (8u + v_1089);
  let v_1102 = (v_1061 >> v_1101);
  let v_1103 = (v_1102 & 3u);
  let v_1104 = (v_1103 << 4u);
  let v_1105 = (v_1100 | v_1104);
  let v_1106 = bitcast<i32>(v_1105);
  let v_1107 = (v_1106 - 32i);
  let v_1108 = (16u + v_1088);
  let v_1109 = (v_1086 >> v_1108);
  let v_1110 = (v_1109 & 15u);
  let v_1111 = (16u + v_1089);
  let v_1112 = (v_1061 >> v_1111);
  let v_1113 = (v_1112 & 3u);
  let v_1114 = (v_1113 << 4u);
  let v_1115 = (v_1110 | v_1114);
  let v_1116 = bitcast<i32>(v_1115);
  let v_1117 = (v_1116 - 32i);
  let v_1118 = (24u + v_1088);
  let v_1119 = (v_1086 >> v_1118);
  let v_1120 = (v_1119 & 15u);
  let v_1121 = (24u + v_1089);
  let v_1122 = (v_1061 >> v_1121);
  let v_1123 = (v_1122 & 3u);
  let v_1124 = (v_1123 << 4u);
  let v_1125 = (v_1120 | v_1124);
  let v_1126 = bitcast<i32>(v_1125);
  let v_1127 = (v_1126 - 32i);
  let v_1128 = vec4<i32>(v_1097, v_1107, v_1117, v_1127);
  let v_1129 = vec4<f32>(v_1128);
  let v_1130 = dot(v_1129, v_205);
  let v_1131 = (v_1032 * v_1130);
  let v_1132 = f_31[v_225];
  let v_1133 = (v_1132 + v_1131);
  f_31[v_225] = v_1133;
  }
  }
  }
  }
  }
  }
  }
  }
  continuing {
  let v_1134 = f_34;
  let v_1135 = (v_1134 + 1u);
  f_34 = v_1135;
  }
  }
  continuing {
  let v_1136 = f_35;
  let v_1137 = (v_1136 + 1u);
  f_35 = v_1137;
  }
  }
  } else {
  }
  f_34 = 0u;
  loop {
  let v_1142 = f_34;
  let v_1143 = (v_1142 < 4u);
  if (!(v_1143)) { break; }
  let v_1145 = f_34;
  let v_1146 = (v_1145 * 64u);
  let v_1147 = (v_1146 + v_56);
  let v_1151 = f_31[v_1145];
  let v_1153 = f_32[v_1145];
  let v_1154 = (v_1151 - v_1153);
  s_27[v_1147] = v_1154;
  continuing {
  let v_1155 = f_34;
  let v_1156 = (v_1155 + 1u);
  f_34 = v_1156;
  }
  }
  workgroupBarrier();
  f_36 = 32u;
  loop {
  let v_1162 = f_36;
  let v_1163 = (v_1162 > 0u);
  if (!(v_1163)) { break; }
  let v_1165 = f_36;
  let v_1166 = (v_56 < v_1165);
  if (v_1166) {
  f_34 = 0u;
  loop {
  let v_1174 = f_34;
  let v_1175 = (v_1174 < 4u);
  if (!(v_1175)) { break; }
  let v_1177 = f_34;
  let v_1178 = (v_1177 * 64u);
  let v_1179 = (v_1178 + v_56);
  let v_1182 = s_27[v_1179];
  let v_1183 = (v_1179 + v_1165);
  let v_1185 = s_27[v_1183];
  let v_1186 = (v_1182 + v_1185);
  s_27[v_1179] = v_1186;
  continuing {
  let v_1187 = f_34;
  let v_1188 = (v_1187 + 1u);
  f_34 = v_1188;
  }
  }
  } else {
  }
  workgroupBarrier();
  continuing {
  let v_1189 = f_36;
  let v_1190 = (v_1189 >> 1u);
  f_36 = v_1190;
  }
  }
  let v_1191 = (v_56 < v_169);
  let v_1192 = (v_53 < v_91);
  let v_1193 = (v_1191 && v_1192);
  if (v_1193) {
  let v_1197 = (v_53 * v_83);
  let v_1198 = (v_1197 + v_51);
  let v_1199 = (v_1198 + v_56);
  let v_1201 = (v_56 * 64u);
  let v_1203 = s_27[v_1201];
  b_3[v_1199] = v_1203;
  } else {
  }
  return;
}
