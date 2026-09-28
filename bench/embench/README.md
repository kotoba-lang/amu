# Embench correctness qualification

The reference is `embench/embench-iot` tag `embench-2.0rc2`, commit
`0be80d44227d73c732a0de596d6b00b59fdf805e`. The upstream C suite has 19
workloads. Kotoba needs a separately reviewed translation of each workload;
Amu does not accept C input. Keep the upstream and translated sources, input
generation, expected output, and licenses together in the qualification
record. Do not label a translated workload as an official Embench score.

| Workload | Kotoba native correctness | Remaining qualification |
| --- | --- | --- |
| aha-mont64 | passed for Montgomery and reference modular results | timed-loop parity |
| crc32 | passed for one seeded 1024-byte run | timed-loop parity |
| depthconv | unverified | port and compare full output |
| edn | unverified | port and compare full output |
| huffbench | unverified | port and compare full output |
| matmult-int | passed for all 400 output cells | timed-loop parity |
| md5sum | passed for all four MD5 state words | timed-loop parity |
| nettle-aes | unverified | port and compare full output |
| nettle-sha256 | passed for all 32 digest bytes | timed-loop parity |
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

As of 2026-09-29, seven correctness ports are in `ports/`, with their original
license notices and the relevant license texts in `licenses/`. These benchmark
programs are separate from the Apache-licensed compiler and are compiled as
test inputs; they are not linked into Amu. `tarfind` includes a GPL-licensed
BEEBS random generator adaptation, while its upstream benchmark body is MIT.
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
The `md5sum` port checks all four state words after hashing the upstream
1000-byte message. The expected words were independently computed from the
message with a second MD5 implementation; their XOR is Embench's `0x33f673b4`.
The `aha-mont64` port reproduces unsigned 64-bit multiplication, remainder,
extended GCD, and Montgomery multiplication. Both calculation paths agree
with an independent modular exponentiation result for the upstream inputs.
The `nettle-sha256` port checks all eight 32-bit state words, corresponding to
the upstream 32-byte digest of its 56-byte input. `evidence/native-20260929-apple-m4.json`
records the source and compiled artifact hashes for all seven native passes.

The frontend used here includes kotoba-sema PR #89, pinned in `deps.edn`.
It fixes dependent loops that capture a vector returned by an earlier loop.
The small regression compiled through Amu's native AArch64 route and returned
`2` under the native KEXE loader. This repository's pin must be revisited
when that PR lands on kotoba-sema main.

**Compiler-host boundary:** `bin/amu` is currently a Node.js launcher and
the compiler runs as ClojureScript under nbb. The seven passes prove native
AArch64 **output execution**, not JS-independent compilation. A requirement
that the compiler itself run without JS remains unqualified. No Embench
performance or compiler-host-independence claim may cite this evidence as a
pass for that requirement.

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
   Record the compiler host separately from the generated target; `--jvm-free`
   does not mean JS-free.
4. Only after correctness, align the benchmark loop, warmup, scale factor,
   hardware, compiler options, timing boundary, and code-size metric before
   reporting performance. Repeat samples and retain the raw results.

The native benchmark runner `bench/runtime-comparison/kexe-benchmark.c` now
initializes the ABI v9 pair and vector arena pointers. Before that change,
native code using inline vector operations could crash in the runner even
though the compiler output was valid.
