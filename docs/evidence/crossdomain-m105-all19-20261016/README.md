# M105 selfhost compiler: 19-workload reach and exactness

Status: **G1=G2=G3 FIXED POINT; 19/19 WORKLOADS EXACT; FOUR M4 FULL-SUITE CAMPAIGNS PASSED THE TIMING GATES**.

This checks the combined M105 seed compiler after reciprocal division, MSub
fusion, and the four-wide xgboost early-stop candidate. It establishes that
the generated compiler remains a native selfhost fixed point and that its
changes preserve all 19 pinned M104 workload results, fuel values, and arena
counters. The earlier M1 timing below is a loaded-host diagnostic. A separate
M4 ABBA follow-up is recorded in
[`m105-abba-m4-20261016`](../m105-abba-m4-20261016/README.md).

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

## M4 full-suite repeatability follow-up

Two more full 19-workload campaigns were run in ABBA order against the two
M105 compiler image sets. Together with the previous baseline and candidate
campaigns, this gives two accepted full-suite runs per compiler arm. The
geometric mean of the two baseline round results is 0.75939; the candidate is
0.78965. The normalized candidate/baseline ratio is 1.03984, but the raw
results show timing drift: 14 native images are byte-identical across arms,
yet their candidate-period Kotoba elapsed times are 3.1% slower on average.
The shared C binaries are 2.0% faster during the candidate period. The 4.0%
normalized difference therefore cannot be attributed to the compiler change.

Only five images differ. Their Kotoba elapsed-time geometric mean is 0.99337
for candidate/baseline; xgboost improves, while the other changed workloads
are near parity or slightly slower. See the linked ABBA record for all per-run
raw samples, accepted CPU gates, exact ratios, and the common C build receipt.
These results remain translated-port measurements, not an official Embench
score or a SPEC result.

## Isolated selfhost compiler variants

Three pinned selfhost compiler variants were built from G1=G2=G3 fixed points:
reciprocal division (`08e88db9`), MSub fusion (`1d7c4712`), and the combined
current candidate with four-wide xgboost early stop (`6103f5cf`). The reciprocal
and MSub artifacts are separate compiler variants, not successive source
commits. Each recompiled the same 19 port sources and passed the pinned M104
result, fuel, arena, and image-table exactness checks.

| Variant | Fixed-point native image | Images changed from M105 baseline |
|---|---|---|
| Baseline (`9892fc06`) | `6b158aa8…add2eb` | — |
| Reciprocal division (`08e88db9`) | `40696a8a…541fa55` | `matmult-int`, `nsichneu` |
| MSub fusion (`1d7c4712`) | `854fad33…502258a3b` | `matmult-int`, `nsichneu`, `qrduino`, `sglib-combined`, `xgboost` |
| Combined current candidate (`6103f5cf`) | `b10e3813…74e8a00` | `matmult-int`, `nsichneu`, `qrduino`, `sglib-combined`, `xgboost` |

These are byte-level image changes, not performance claims. `compile-fixedpoint-ports.py`
verifies source-unity and fixed-point hashes before compiling; the compiler
variant directories retain image tables and 19/19 exactness reports.

## Qualified M4 timing of the isolated variants

Each variant was measured twice on the same Apple M4 Mac mini with the same
Apple clang 17 C build (`3e7ba67f…b17d53dd`). Every run accepted all 19 Kotoba
and 19 C workloads under the CPU gate. The measurements were collected in
reciprocal R1, MSub R1, MSub R2, reciprocal R2 order.

| Run | Variant | Kotoba/C geometric mean | Kotoba-faster workloads |
|---|---|---:|---:|
| R1 | Reciprocal | 0.78357 | 12/19 |
| R2 | Reciprocal | 0.78124 | 12/19 |
| MSub R1 | MSub | 0.76588 | 14/19 |
| MSub R2 | MSub | 0.73809 | 14/19 |

The raw campaign scores make MSub look faster, but the byte-identical workload
controls shifted by a similar amount. Relative to the M105 baseline campaigns,
the changed-image group divided by the same-image control shift is 1.01072 for
the reciprocal variant and 1.00038 for MSub. These control-adjusted results do
not establish a speedup from either compiler change. Two campaigns per variant
also do not resolve small effects. This analysis uses the verified M105
baseline ABBA per-workload ratios and is descriptive, not a significance test.

`variant-timing-m4/raw/` preserves all four reports, raw per-workload attempts,
and CPU-gate samples. Reproduce the validation and summary from the repository
root with:

```sh
python3 docs/evidence/crossdomain-m105-all19-20261016/variant-timing-m4/analyze-variant-timing.py
```

The generated analysis and all values remain translated-port measurements, not
an official Embench score or a SPEC result.

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

python3 bench/embench/reproduce-20261015/tools/fetch_upstream.py \
  --dest <pinned-upstream-dir>

python3 bench/embench/reproduce-20261015/d_timing.py \
  --upstream <pinned-upstream-dir> \
  --round docs/evidence/crossdomain-m105-all19-20261016/baseline-timing-round.json \
  --images <new-baseline-dir> \
  --out <new-baseline-timing-dir>

python3 bench/embench/reproduce-20261015/d_timing.py \
  --upstream <pinned-upstream-dir> \
  --round docs/evidence/crossdomain-m105-all19-20261016/candidate-timing-round.json \
  --images <new-empty-dir>/step4-images \
  --out <new-candidate-timing-dir>
```

The current and baseline build and exactness reports are retained here.
Exactness runtimes are diagnostic only and must not be treated as benchmark
measurements. The two timing round files pin each image set and the expected
accounting. `d_timing.py` applies the raw-idle and background-idle gates and
emits a geometric mean only when all 19 workloads are accepted in both arms.
