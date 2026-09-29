# Embench native qualification

> **Selfhost status.** The measured artifact below was produced with a
> GraalVM-built compiler, so under `docs/selfhost-priority.md` it is a
> *bootstrap-reference* result, not a selfhost result. Selfhost is the top
> priority for the Amu compiler: Embench numbers are published as selfhost
> only when taken with a compiler that Amu built, on a quiet host.

The reference is the current `embench/embench-iot` master at commit
`09c2ed8c3b7008c95d08b038de4a3f6dc103ed70` (2026-09-29). Its benchmark
sources and support directory are byte-identical to tag `embench-2.0rc2` for
the 19 workloads covered here.

Amu does not accept C source. This directory therefore measures translated
Kotoba programs and records their fidelity explicitly. The result is **not an
official Embench score**. Official speed and size scores require the upstream
C harness, prescribed scale factors, reference platform normalization, and
equivalent timed bodies.

## Coverage

| Workload | Native check/compile/run | Fidelity |
| --- | --- | --- |
| aha-mont64 | pass | full correctness translation |
| crc32 | pass | full correctness translation |
| depthconv | pass | full correctness translation |
| edn | pass | adapted DSP kernel |
| huffbench | pass | adapted Huffman kernel |
| matmult-int | pass | full correctness translation |
| md5sum | pass | full correctness translation |
| nettle-aes | pass | adapted AES arithmetic kernel |
| nettle-sha256 | pass | full correctness translation |
| nsichneu | pass | adapted Petri-net kernel |
| picojpeg | pass | adapted reconstruction/color kernel |
| qrduino | pass | adapted Reed-Solomon kernel |
| sglib-combined | pass | adapted container-semantics kernel |
| slre | pass | exact four-pattern recognizers, not general SLRE |
| statemate | pass | adapted statechart kernel |
| tarfind | pass | full correctness translation |
| ud | pass | full correctness translation |
| wikisort | pass | all nine inputs with a different stable-sort algorithm |
| xgboost | pass | full 400-tree/128-sample correctness translation |

“Full correctness translation” means the relevant upstream input and complete
expected output are checked for one benchmark-body iteration. It does not mean
that upstream repetition loops or timing boundaries are identical. “Adapted”
means a real algorithmic workload derived from that benchmark is executed but
the full upstream implementation is not translated. Adapted measurements are
compiler maturity evidence only.

## JavaScript-independent compiler gate

Build the standalone compiler with:

```sh
bin/build-native-image
```

The build uses Clojure and GraalVM Native Image as build tools. The resulting
Mach-O compiler has no Node.js, JavaScript, JVM, or Clojure runtime dependency.
The qualification runner gives the compiler an empty `PATH`, so it cannot
delegate checking, compilation, or extraction to `node`, `java`, `clojure`, or
another executable. The recorded `otool -L` output is also checked for Node/JVM
libraries.

Run all 19 ports and retain raw evidence with:

```sh
python3 bench/embench/run_native_qualification.py \
  --compiler /absolute/path/to/amu-native \
  --runner /absolute/path/to/kexe-benchmark \
  --upstream /absolute/path/to/embench-iot \
  --output /absolute/path/to/evidence
```

The output contains five raw check timings, five compile timings, five native
execution samples, source/KEXE/raw-code hashes and sizes, compiler and runner
hashes, target ISA, host details, upstream commit, dependency inspection, JSON,
and CSV. Every `test-*` export must return exactly `1`; otherwise the command
fails.

## Current measured artifact

The 2026-09-29 Apple M4 run used standalone compiler SHA-256
`59e3081256a116d3f50e864f44178bb35d38f5e07fd86420929c5ae13ad99ba0`
and upstream commit `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70`. All 19 ports passed under an
empty compiler `PATH`. The evidence directory is
`/Users/junkawasaki/Downloads/amu-embench-qualification-final2-20260929`.

The long XGBoost time reflects the current translated tree walker and native
runtime string-handle representation. It is a useful optimization target, not
an Embench runtime score.

## Licensing

Benchmark translations retain their upstream SPDX notice. They are compiler
test inputs and are not linked into the Apache-licensed Amu compiler. Relevant
license texts are in `licenses/`.
