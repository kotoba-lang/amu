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
* `campaign.py` emits the immutable 760-position ABBA/BAAB schedule and verifies
  a completed result manifest, including deterministic statistics and a
  tamper-evident bundle hash. The platform timing driver must consume this
  schedule verbatim and retain every rejected retry. The schedule has 760
  positions; each may contain one to three raw attempts, and the first accepted
  attempt is selected without continuing to search for a faster sample.

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
