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
