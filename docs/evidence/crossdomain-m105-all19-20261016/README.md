# M105 selfhost compiler: 19-workload reach and exactness

Status: **G1=G2=G3 FIXED POINT; 19/19 WORKLOADS EXACT; EXPLORATORY TIMING ONLY**.

This checks the combined M105 seed compiler after reciprocal division, MSub
fusion, and the four-wide xgboost early-stop candidate. It establishes that
the generated compiler remains a native selfhost fixed point and that its
changes preserve all 19 pinned M104 workload results, fuel values, and arena
counters. The timing below is a loaded-host diagnostic, not qualified evidence.

## Compiler provenance

The build used the adopted native bootstrap and the seed unity at source
commit `6103f5cf661252c2031af20778e0a30ca24b7eb2`. No JVM, Node, GraalVM, or C
compiler fallback built the compiler. Stage A matched the adopted image. G1,
G2, and G3 all produced native image
`b10e381344a1f5a8b82cac981c0011bd20ecbcc4b48dd5f5dce97364c74e8a00`.

The build recompiled all 19 official translated ports with G2. Their source,
KSEED, native image, and export hashes are in `images.json`; the selfhost
chain and exact source pins are in `compiler-chain.json` and
`build-inputs.json`.

## Exactness and changed images

`exactness.json` records a full pass at the pinned M104 run counts for all 19
workloads. Each candidate image matched the expected result, benchmark fuel,
verify fuel, and 17 arena counters. Seven generated images differ from the
M104 pins: `matmult-int`, `nsichneu`, `picojpeg`, `qrduino`, `sglib-combined`,
`slre`, and `xgboost`. The other 12 images are byte-identical. The changed
images are evidence that the compiler edits reach multiple workloads, not
evidence that they improve their speed.

## Same-source exploratory timing

To separate compiler-generation changes from the earlier M104 comparison, the
verified M105 baseline compiler (source commit `9892fc06`, image
`6b158aa8…add2eb`) and the current M105 compiler both compiled the same pinned
19 port sources. The baseline passed the pinned result, fuel, and arena checks
for all 19 workloads. Five historically C-favored domains were then measured
on an M1 Max against the recorded Apple clang 21 `-O2` binaries: four
alternating baseline/C/candidate pairs per domain, with exactness checked on
every Kotoba run.

| workload | current / baseline median (range of 4 pairs) | current / C median normalized ratio |
|---|---:|---:|
| xgboost | 1.133 (0.804–1.342) | 1.039 |
| picojpeg | 1.060 (0.971–1.134) | 0.975 |
| slre | 0.953 (0.897–1.132) | 1.093 |
| qrduino | 1.123 (0.893–1.427) | 1.025 |
| sglib-combined | 0.889 (0.798–1.151) | 1.153 |

The normalized C ratio is `(4/m_w) * Kotoba / C`; below 1 favors the Kotoba
image. The candidate/baseline ratios are mixed and highly variable. Raw idle
during these runs ranged from 10% to 59%, below the protocol's 70% gate, so
this table cannot establish a speed result. The combined candidate also
contains several compiler changes; it does not isolate reciprocal lowering,
MSub fusion, or the xgboost change. Full samples and host readings are in
`same-source-exploratory-timing.json`; compiler and exactness provenance are in
`m105-baseline-build.json` and `m105-baseline-exactness.json`. The earlier
`exploratory-timing.json` used M104 images as its baseline and is only a
cross-generation diagnostic.

The M104 M4 report previously showed C ahead on xgboost (1.515 Kotoba/C),
picojpeg (1.446), slre (1.194), qrduino (1.177), and sglib-combined (1.087).
Those ratios rank follow-up work; they are not results for these M105 images.

## Reproduction

From the repository root on Apple silicon, using fresh output directories:

```sh
python3 bench/embench/reproduce-20261015/b_build.py \
  --out <new-empty-dir> \
  --round docs/evidence/crossdomain-m105-all19-20261016/candidate-round.json \
  --record <record-dir> \
  --skip-bootstrap-check

python3 bench/embench/reproduce-20261015/c_exactness.py \
  --round rounds/sa-m104-20261015.json \
  --images <new-empty-dir>/step4-images \
  --out <another-new-empty-dir>

python3 docs/evidence/crossdomain-m105-all19-20261016/compile-m105-baseline-current-ports.py \
  --loader <new-empty-dir>/host/kexe-loader \
  --out <new-baseline-dir>

python3 bench/embench/reproduce-20261015/c_exactness.py \
  --round rounds/sa-m104-20261015.json \
  --images <new-baseline-dir> \
  --out <another-new-empty-dir>
```

The current and baseline build and exactness reports are retained here.
Exactness runtimes are diagnostic only and must not be treated as benchmark
measurements. Timing samples are exploratory only and do not pass the quiet-host
qualification gate.
