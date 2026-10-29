# Embench native qualification

For the corrected same-algorithm speed comparison, see the [Embench reproduction package](reproduce-20261015/README.md).
Its M104 record is an Embench-derived translated-port comparison, not an official score; the earlier M93 figure is retained
only as historical evidence after the kernel audit.

For the evidence level, claims that may or may not be made, and the
preregistered protocol required before performance-led outreach, see
[Kotoba/Amu performance proof v1](proof-v1/README.md).  The proof-v1 gate
requires repeated paired measurements and external result bundles; it does not
retroactively promote the one-sample M104 cycles to independent or official
results.

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

## Selfhost compiler gate

Use canonical Kotoba source and a compiler built and rebuilt by Amu selfhost,
including the native build, packaging and execution closure required by
[the current contract](../../docs/selfhost-priority.md). Do not require
CLJK/CLJC/CLJS, NBB, KBB, Clojure, Java/JVM, GraalVM, Node or a C
compiler/loader/runtime. Missing native benchmark orchestration is a blocker,
not permission to use a hosted compiler or C loader.

The old GraalVM builder and its Python staging helper are removed. Their
standalone Mach-O output did not establish Amu self-reconstruction. Retain
the recorded corpus, benchmark inputs and historical evidence; port required
orchestration to Kotoba before recording new selfhost qualification. Record
compiler generations, source/lock pins, output and runner hashes, process
traces, results and named refusals on a quiet host.

## Historical measured artifact (not current selfhost qualification)

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
