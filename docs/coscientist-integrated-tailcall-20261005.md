# Tail-call improvement in the source-rebuilt unified Amu image

The verified direct scalar tail-call compiler is now included in a unified
Amu candidate with native `check`, `compile` and `refactor`. Three generations
recompile the frontend and launcher objects from source. All 162 objects,
containers, native code and executable commands are byte-identical across
generations. Each frontend contains 117 source-recompiled objects.

The executable is 6,010,104 bytes, SHA-256
`6420b1b3ee3d1a308e24677a2d2f6840d5866d93e65c8d68fe16c763eab4d6e2`.
The compiler seed is pinned to
`6a7e2df066f82ee330e34175e8cc65b272788b25ccccb797952a377f8f3625bc`.
No stage-0, Node, nbb or JVM compiler is used to produce these generations.

`rebuild.sh` now accepts an explicitly hash-pinned candidate seed and supplies
it to both frontend and launcher compilation. The default r6m record stays
unchanged. Missing and incorrect candidate hash pins are refused before any
compilation. The first attempt failed because the copied source farm was
outside wire 35's read scope; `front.sh` now includes that exact input root.
The failed log remains in the evidence. Snapshot twin provenance is reported
by content hashes, because a copied input snapshot has no Git metadata.
These are build configuration changes, with no applicable mechanical Amu
refactor rule.

All 19 canonical benchmark sources pass `check` and compile through the new
unified image. Their native code is byte-identical to the separately validated
raw-seed candidate. That earlier proof includes exact fuel comparisons,
bounds checks, 2,873 Statemate state observations and 792 AArch64 fixture
runs. The unified candidate's corpus validation preserves the prior results:

| Validation | Result |
|---|---|
| check, 391 sources | 358 same accepts, 33 same refusals |
| compile, 391 sources | 300 behavior-same; 27 Amu-only accepts; 12 Amu-only refusals; 3 differing accepted outputs; 49 shared refusals |
| exports, 890 runs | 875 same, 15 existing differences, 0 timeouts, 1 missing export |

Stage-0 is used only as a test reference in this comparison. These results
preserve existing limitations, rather than claiming full corpus equivalence.

Whole-suite timing is run on zebulun with the same pinned C artifacts,
runner, canonical sources and fixed 30-triple policy as the baseline.
Every workload is also compiled and extracted by the transferred unified
Amu on zebulun, and its code hash checked against the validated candidate.
All 19 experiments completed, each with 30 accepted triples and relative
standard deviation below 10% in all arms. Raw rejected attempts remain in
the timing archive. The concurrent baseline/C geometric time ratio is
11.1314 and candidate/C is 10.3885: a 1.0715x geometric speedup (6.67%
less time). None of the 19 candidates reaches C time. Three workloads meet
the predeclared 5% and combined-standard-deviation improvement criteria:

| Workload | Old / candidate speedup | Candidate / C time | Improvement criterion |
|---|---:|---:|---|
| aha-mont64 | 0.990 | 1.997 | not established |
| crc32 | 0.994 | 2.298 | not established |
| depthconv | 0.984 | 3.575 | not established |
| edn | 1.007 | 15.741 | not established |
| huffbench | 0.998 | 7.376 | not established |
| matmult-int | 0.993 | 24.449 | not established |
| md5sum | 1.055 | 6.588 | PASS |
| nettle-aes | 1.029 | 17.986 | not established |
| nettle-sha256 | 1.038 | 14.638 | not established |
| nsichneu | 1.656 | 8.943 | PASS |
| picojpeg | 1.045 | 31.298 | not established |
| qrduino | 1.000 | 12.503 | not established |
| sglib-combined | 1.015 | 7.683 | not established |
| slre | 0.991 | 7.579 | not established |
| statemate | 1.969 | 39.632 | PASS |
| tarfind | 0.992 | 19.935 | not established |
| ud | 0.998 | 12.796 | not established |
| wikisort | 1.027 | 16.553 | not established |
| xgboost | 0.978 | 7.491 | not established |


The candidate has not replaced `bin/amu`. Full own-source 100% qualification
and official Embench scores remain unclaimed. These measurements use a
custom native whole-call adapter and estimated background CPU activity.

[Evidence](evidence/coscientist-integrated-tailcall-20261005/summary.json)
contains source-input hashes, three-generation hashes, per-port parity and
corpus results. The selfbuild and parity archives retain detailed logs.
[Timing summary](evidence/coscientist-integrated-tailcall-20261005/timing-summary.json)
and its archive include all accepted and rejected rows, remote compilation
logs and candidate manifests. The earlier standalone Statemate 2.056x result
is a separate run; the whole-suite concurrent result here is 1.969x.
The largest remaining ratio is Statemate 39.632x, followed by Picojpeg
31.298x and Matmult-int 24.449x.
