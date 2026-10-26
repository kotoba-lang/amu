# Kotoba/Amu performance proof v1

This directory is the claim gate for performance statements derived from the
Embench translated-port work.  It does not replace the historical reproduction
bundle in `../reproduce-20261015/`; it classifies that evidence and defines the
stronger packet required before a performance statement is used in branding,
community outreach, or sales.

## Current evidence classification

The corrected M104 bundle reports two complete Apple M4 cycles:

* the original cycle: Kotoba/C elapsed-time geometric mean `0.821298642657085`;
* a second Mac16,10 cycle: `0.7877703356`.

Both are valuable author-run, host-specific translated-port comparisons.  They
are not official Embench scores and do not establish that Kotoba is universally
faster than C.  The original M104 cycle used one selected sample per workload;
the second cycle was produced with the project's reproduction kit, not by an
independent organization.  Slower individual workloads remain part of the
result and must be shown.

The superseded M93 `0.7999` result is not admissible as a same-algorithm claim:
the later audit found substitution kernels and an asymmetric SHA instruction
path.  It remains historical evidence only.

## Files

* `claim-matrix.json` records the claims that are admitted, withheld, or kept in
  a separate evidence track.
* `protocol.json` is the preregistration contract for the next claim-grade run.
* `result-manifest.schema.json` defines the portable result bundle required from
  both project and external runners.
* `evidence-index.json` binds the current classification to repository paths and
  source revisions.
* `validate.py` validates all four control files using only Python's standard
  library.  It deliberately does not validate benchmark results that do not yet
  exist.
* `campaign.py` emits the immutable 760-position ABBA/BAAB schedule and checks
  record integrity, the full manifest schema, local artifact hashes, ordering,
  selection, and deterministic statistics. The platform timing driver must consume this
  schedule verbatim and retain every rejected retry. The schedule has 760
  positions; each may contain one to three raw attempts, and the first accepted
  attempt is selected without continuing to search for a faster sample.
* `native_build.py` prepares the current native route: it checks product/source
  pins, observes F1=F2=F3, builds the existing native KX64 runner with that same
  compiler, and attempts every original workload's `bench-verify 1` through
  source-locked `kx64-v1` builds. `native-entry.kotoba` supplies the fixed entry.
  All original declarations and function bodies are retained. Every refusal,
  failure and raw process log remains in the output.
* `verify_native_records.py` checks the retained native observations and process
  trace. It preserves the failed full-count result as part of the record.

Run the control-file gate from the repository root:

```sh
python3 bench/embench/proof-v1/validate.py
```

Expected output:

```text
PROOF_V1_CONTROL PASS
```

Create the timing schedule and verify a completed manifest with:

```sh
python3 bench/embench/proof-v1/campaign.py schedule --out schedule.json
python3 bench/embench/proof-v1/campaign.py verify result-manifest.json
```

`verify` currently prints `PROOF_V1_RECORDS PASS; QUALIFICATION REJECTED:
native-measurement-gate-pending` and exits **2** when records are internally
consistent. A claim-grade result cannot pass until the native measurement gate
is connected. Internal record consistency alone cannot establish selfhost
provenance, same-algorithm equivalence, runtime accounting, or executable
negative-control results. Pending controls must be recorded as `pending`.

The next measurement must use the current complete selfhost compiler and
loaderless native execution under `AGENTS.md`. The historical M104 C timing
loader is not an allowed implementation for that measurement. This Python
module stages and audits records; it grants no native controller verdict.

## Pre-timing clarification (2026-10-26)

No proof-v1 timing campaign has been run. The initial record verifier resampled
workload identities and did not check the full manifest. Before any timing,
the protocol now fixes the 19 workload identities and bootstraps the 10 paired
round ratios **within each workload**, using 10,000 replicates and seed 104.
Each replicate takes a median for each workload and the geometric mean over
all 19 medians. The percentile 95% interval describes repeat measurement
uncertainty on that fixed corpus, rather than variation across a hypothetical
workload population. Results from different hosts remain separate.

The normalization factors are pinned to `4 / multiplier` in the M104 workload
table; changing iteration counts requires a new preregistered measurement
profile before collecting timings. A selected observation must meet the one
second floor, all three 70% idle thresholds, and nominal thermal state. The
attempt array must follow schedule order, with contiguous CPU-only retries.
Rejected workloads retain an explicit per-workload row and produce no
aggregate or confidence interval.

Before any proof-v1 timing, the manifest also requires one explicit native
runtimeProfile with fixed resource bounds, the actual compiler artifact, and
image/build-record bindings covering all19 workloads exactly once. One shared
runner or separate packed images may be bound; mixing profiles within one
campaign is not allowed. Each referenced byte stream must be a verified
bundle artifact. The canonical build record must match the declared
target/format/profile/capacity and actual image size. Unknown profiles, silent
default widening, increased growth-row limits and mismatched host ISAs refuse.
These are record-integrity checks, not native compiler provenance or runtime
qualification; the native measurement gate remains pending and exits2.

Run synthetic verifier tests with:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s bench/embench/proof-v1 -p test_campaign.py
```

These tests check the record verifier. They do not constitute the seven
protocol negative controls against actual benchmark binaries.

## Native preparation

On an actual native Linux x86_64 host with this checkout, run:

```sh
python3 bench/embench/proof-v1/native_build.py --out /absolute/path/to/new-observation-directory
python3 bench/embench/proof-v1/native_build.py --iteration-profile m104-counts --out /absolute/path/to/another-new-directory
```

The directory must not exist. The script uses only the pinned native compiler
and its native runner for workload execution. Child `PATH` is `/nonexistent`;
compiler grants cover explicit source/output files and workload grants are
empty. The current `static` CLI rejects source-locked project builds, so this
preparation uses its supported locked `kx64-v1` route throughout.

A successful one-body result is a correctness prerequisite. It does not
establish correctness at the registered full iteration counts, separate
benchmark/verify fuel and arena accounting, process-trace qualification,
quiet-host timing, C comparator equivalence, or a performance score. All of
those remain required before the pending native measurement gate can admit
any result as claim-grade.

The second command executes each workload's original registered M104 count.
It retains the same fixed 30-second diagnostic wall budget per execution and
a one-trillion-unit fuel budget; these are recorded through the pinned
preparation source. A wall-budget refusal says that the probe did not complete
within that bound. It does not establish an incorrect output or a C comparison.
The native runtime's named arena refusal is recorded separately. Neither
probe grants a proof-v1 aggregate. The complete native observations are in
[`docs/evidence/embench-native-preparation-20261026/`](../../../docs/evidence/embench-native-preparation-20261026/).

Those preparation commands retain the original diagnostic route, not the new
split-accounting measurement host. Its earlier capacity/wall/fuel failures
remain [historical native diagnosis evidence](../../../docs/evidence/embench-native-diagnosis-20261026/README.md),
not current measurement-host results.

## Merged ARM measurement host and retained-record audit

The explicit `large-vectors-v1` runtime profile merged in PR1602. The separate
closed measurement host merged in [PR1606](https://github.com/kotoba-lang/amu/pull/1606)
at `9fea26ca5282a982ed1fc0c533a706fde0fcc114`. Its exact-head native workflow
[40287198642](https://github.com/kotoba-lang/amu/actions/runs/40287198642)
and post-merge main workflow
[40290414642](https://github.com/kotoba-lang/amu/actions/runs/40290414642)
completed successfully. The [measurement evidence](../../../docs/evidence/native-benchmark-host-20261026/README.md)
retains earlier failures as well as final original-count19/19, separate fuel,
both17-field arena snapshots, 8 factory/17 runtime refusals and13 actually
built/executed semantic mutants. The native host owns its ordered/accounting
guards. Python does not own that verdict.

Both actual ISA compilers produced identical ARM host/payload bytes, and the
host ran natively on ARM. This is **not** an x86 measurement-host execution;
that host remains KOTOBA-152. Compiler qualification, host execution, retained
record integrity and comparative campaign qualification are separate facts.

After obtaining the `native-benchmark-arm-evidence` artifact from the pinned
run, audit its retained `benchmark-arm/host` directory locally:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 bench/embench/proof-v1/audit_measurement_records.py /absolute/path/to/benchmark-arm/host
```

This read-only command makes no network request, launches no compiler or
benchmark, and emits no timings or score. Exit0 means only that all19 retained
raw records and25 refusal records are consistent with the reviewed byte
graph, original source/count pins and independent accounting reference.
It checks raw stream digests, strict native receipts, invocation counts and
source/host/payload identity instead of trusting stored success booleans.
`sourceGraphCurrent` explicitly reports whether that reviewed graph still
matches the checkout. `observerSourceCurrent` distinguishes the earlier
reviewed observer snapshot from the current observer; neither silently
inherits qualification from the other. A consistent historical record need
not match a later checkout. Unknown byte graphs require a new reviewed anchor.

These are unsigned process observations, not binary replay, signed execution
proof or an independent rerun. The command always emits `campaignReady=false`,
`performanceQualified=false` and `nativeVerdictAuthority=false`. Its fixture
and tamper tests are record-integrity tests, not the seven actual-binary
protocol controls. `campaign.py verify` still exits2 with the pending native
campaign gate: same-host C builds/equivalence, host admission, all760 scheduled
positions, paired statistics, and actual protocol controls remain open.
No counts, timing floors, resource limits or promotion rules changed.

The bundle hash is SHA-256 over canonical compact JSON with a trailing newline
and `bundleSha256` replaced by 64 zeroes. This makes the seal independently
recomputable without a circular hash definition.

## Promotion ladder

1. `historical-author-run`: retained and reproducible, but not a current public
   headline.
2. `claim-grade-author-run`: passes `protocol.json`, including repetitions,
   correctness, quiet-host admission, complete results, uncertainty, and
   negative controls.
3. `independently-rerun`: at least two external result bundles validate against
   the same schema and protocol.
4. `upstream-reviewed`: the methodology and result format have an explicit
   upstream disposition.
5. `officially-published`: only when the named benchmark organization says so.

Marketing may use a bounded performance headline only from level 3 or higher.
Each statement must still name the workload family, comparator, host class,
compiler flags, revisions, and result.  A level does not automatically promote
another track, such as Murakumo inference.

## External-run boundary

An external runner receives the public reproduction kit and protocol, not a
preselected result.  Failed qualification, slower results, unsupported hosts,
and protocol deviations are retained.  Support may explain the documented
procedure but must not tune a runner's machine or discard a valid unfavorable
run after seeing its result.
