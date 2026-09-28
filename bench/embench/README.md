# Embench correctness qualification

The reference is `embench/embench-iot` tag `embench-2.0rc2`, commit
`0be80d44227d73c732a0de596d6b00b59fdf805e`. The upstream C suite has 19
workloads. Kotoba needs a separately reviewed translation of each workload;
Amu does not accept C input. Keep the upstream and translated sources, input
generation, expected output, and licenses together in the qualification
record. Do not label a translated workload as an official Embench score.

| Workload | Kotoba native correctness | Remaining qualification |
| --- | --- | --- |
| aha-mont64 | unverified | port and compare full output |
| crc32 | passed for one seeded 1024-byte run | timed-loop parity |
| depthconv | unverified | port and compare full output |
| edn | unverified | port and compare full output |
| huffbench | unverified | port and compare full output |
| matmult-int | passed for all 400 output cells | timed-loop parity |
| md5sum | unverified | port and compare full output |
| nettle-aes | unverified | port and compare full output |
| nettle-sha256 | unverified | port and compare full output |
| nsichneu | unverified | port and compare full output |
| picojpeg | unverified | port and compare full output |
| qrduino | unverified | port and compare full output |
| sglib-combined | unverified | port and compare full output |
| slre | unverified | port and compare full output |
| statemate | unverified | port and compare full output |
| tarfind | passed for generated filename bytes and five searches | timed-loop parity |
| ud | passed for all 20 result values | timed-loop parity |
| wikisort | unverified | port and compare full output |
| xgboost | unverified | port and compare full output |

As of 2026-09-29, the four correctness ports live outside this Apache-licensed
repository because they adapt upstream benchmark code with its own license.
Their results are correctness probes, not representative performance samples:
the timing boundaries and repetition loops differ from the C suite. The
`crc32` port compiles and returns the upstream expected `11433` on native
AArch64. The `matmult-int` port checks all 400 cells and the `ud` port checks
all 20 solution values on native AArch64. `amu test` is not the acceptance
gate for this suite: it invokes JS and Wasm targets, and the requested
qualification is through Amu's native compiler.
The `tarfind` port checks all generated filename bytes against a fingerprint
from the upstream BEEBS random generator and checks each of five first-match
positions. It represents one C benchmark iteration, without the TAR header's
unused fields or the full timing loop.

## Qualification gate for each workload

1. Pin the upstream source revision and translated source hash, including
   support-library routines used by the workload.
2. Match the benchmark input, seed, integer width and overflow behavior,
   memory contents, and complete expected output. A matching checksum alone
   is insufficient where the upstream verifier checks individual values.
3. Compile through `bin/amu check PORT.kotoba --jvm-free` and
   `bin/amu compile PORT.kotoba --target aarch64-macos --jvm-free`.
   Execute the native export and assert the expected result. Do not count
   `amu test` as evidence of native correctness; it exercises other targets.
4. Only after correctness, align the benchmark loop, warmup, scale factor,
   hardware, compiler options, timing boundary, and code-size metric before
   reporting performance. Repeat samples and retain the raw results.

The native benchmark runner `bench/runtime-comparison/kexe-benchmark.c` now
initializes the ABI v9 pair and vector arena pointers. Before that change,
native code using inline vector operations could crash in the runner even
though the compiler output was valid.
