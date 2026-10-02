# Seed stage-0 repair (2026-10-02)

Stage-0 is BOOTSTRAP-REFERENCE (JVM-built GraalVM native image of the amu CLI), `build/native-image/amu-native`.

## Causes found (measured)
1. "internal compiler error" on 12 of 19 ports in `compile`: `build-native.sh` ran the tracing agent over `check` only, so the
   native image lacked reflection entries the compile path uses. Fix: the script now traces `check`, `compile` and
   `extract-native` over the 19 ports (their test-* symbols), the T3 `:bytes` cap-call programs, the seed unity, a >64-bit
   literal probe. (The JVM compiled all of them except slre, below.)
2. `slre`: `hex-of-bytes` in kotoba-native `machine_ir.cljk` used `(.toString (int b) 16)`, an instance call Integer does not have
   (JVM only; fixed in kotoba-native 018f2bc with a regression test in `code_point_literal_test.cljk`; 3 tests fail on the old
   code, 6/6 pass on the new).
3. T3 (computed `:bytes` argument to the wire-35 cap call): not a frontend bug. The old image was built before osaho e77ffff;
   the rebuilt image links it. `seed/tests/t3/t3_copy.kotoba` compiles, extracts and runs byte-exact (cmp identical).
4. GraalVM 21 writes `reflect-config.json`, not `reachability-metadata.json`; the script's post-processing now handles both.
   `SKIP_TRACE=1` reuses an existing `agent-cfg` (the trace over compile took about 1 h on a load-80 Mac; the image 39 min).

## Result
- Image sha256 d2cb84f6e7934a638ae928342e13e96a34d13aa66a3f0170fb91cabf3c5e68e2 (128872136 bytes), GraalVM jdk-21.0.12+7.1,
  classpath /private/tmp/t23/cp.txt. Previous image kept as `amu-native.prev-0024` (sha 53e906f1...).
- `run_native_qualification.py --samples 1` (empty PATH): 19/19 ports compile, extract and return 1.
- Seed: unit tests 01-mem 02-io 10-lex 11-read 30-lower 41-a64gen 42-layout 50-out PASS; `scripts/seed/build.sh 0`: unity 4678
  lines compiles, seed-0.bin 139661 bytes; `io_bytes_check.sh` PASS on stage-0 (n=1, 256, 100000).
