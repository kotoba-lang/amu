# NOTES -- the cross-day replication of the :simdgroup-reduce ANCHOR cell (W = 256, shape 1)

## What row this is

The record's own "Honest LEFT" named cross-day replication as a sanctioned
row: "Cross-day replication of any cell needs a later-day run (a cron tick
on another day), not more same-day sessions." This is that later-day run,
ONE cell: the anchor (W = 256, n = 1,000,003, shape 1), whose original
record is docs/evidence/gpu-simdgroup-reduce-m1max-20261023 (measured
2026-10-23). This replication ran 2026-10-24 on the same host (Apple M1
Max, reported simdgroup size 32) through the same conforming native-Metal
channel (ADR-0360 question (1)'s decision, the emitters' own bytes), the
byte-identical protocol (6 fresh processes, 20 interleaved AB/BA pairs per
operator per run, 2 warmup submits per arm discarded, verified read-back).

Driver (named verbatim, never paraphrased):

    python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 6
      --workgroup 256 --elements 1000003 --variant simdgroup-reduce
      --out docs/evidence/gpu-simdgroup-reduce-m1max-crossday-20261024/w256
      --compare-historical docs/evidence/gpu-simdgroup-reduce-m1max-20261023/summary.md

The emitted shaders are byte-identical to the anchor record's (`diff -r`
empty, checked this tick). The classpath resolution is the driver's named
route 2 (`AMU_KBB_TEST_CLASSPATH`, the same `kbb -Spath -M:test` closure
the retired deps.edn resolved -- the merge 7b8f6488 removed deps.edn from
every current tree root; the compile-log names the fallback route, never
silent).

## FINDING (real measurement, this host, this tick)

- This cell's own verdict (claim protocol rule 2): **REGIME-INVARIANT
  FASTER** -- 18/18 per-run ratios below 1.0, every observed regime
  one-sided; paired median ratios 0.790/0.800/0.801 for :sum/:max/:min.
- The historical anchor (2026-10-23) recorded 0.790/0.800/0.799.
- The rule-3 regime-matched comparison against that record (the driver's
  --compare-historical auto-wiring): sign -- **"reproduces in sign
  strictly"** at every operator (all 6 per-run ratios hold the historical
  sign at each operator); magnitude -- reproduces within 0.000 (:sum) and
  0.002 (:min), and "magnitude splits by clock regime" for :max (mixed
  strata draws: the max strata match, within-stratum delta 0.000 at both
  matched strata pairs). The claim names the split and attributes it to
  session mixing -- never "failed to reproduce".
- Read-back: 36 verify lines, ok=1 on every one; :max/:min bit-exact vs
  the reference and between arms; :sum 1.58e-05 vs the reference and
  3.05e-05 between arms (regrouping).
- Rule 1 this run: one level for :sum, three for :max, four for :min;
  cross-operator level identity REFUTED (12/15 run pairs) -- the regime
  structure differs from the anchor's day-of-run structure (the fast clock
  level appears in :max/:min runs), which is exactly why the comparison is
  published regime-matched and not as raw-median agreement.

## What this slice does NOT license

- No `:measured?` flag moves: this replication re-measures an ALREADY
  flipped cell (the anchor was flipped 2026-10-23). No selection answer
  changes and no workgroup row (ADR-0355/0358) is touched.
- The shape-2 W = 512 cell stays measured-but-REFUSED (REGIME-SCOPED);
  this run says nothing about it -- replication of a REFUSED cell is its
  own decision, not a way to re-run a refusal.
- Shapes beyond the two measured ones (1,000,003 and 2^20) stay UNMEASURED
  at every cell; the other five W cells stay same-day-only until their own
  later-day runs.
- This is a REPLICATION record, not a new flip cell: the flip contract's
  cell set and the record's basis text are unchanged by this commit ("this
  tick changed no code namespace"). Naming this record in the flip note /
  basis evidence lists is its own later slice.

## Gate (this tick changed no code namespace)

- Scoped GPU gate (the 8 GPU-owned test namespaces), run this tick after
  the measurement: "Ran 101 tests containing 9624 assertions. 0 failures,
  0 errors." (scoped: 101 tests, 9624 passed, 0 failed, 0 errors).
- Full run-tests.cljk: RED AT BASE, re-run this tick (real transcript:
  aborts at namespace load with "Could not find namespace: kotoba.form",
  the W3 port path, outside this diff -- documented red at base in ADR 0362
  and every prior tick record). No green full suite is claimed.

## Honest LEFT (the real remainder after this row)

- Cross-day replication of the other five W cells (shape 1: W = 32, 64,
  128, 512, 1024 -- each its own later-day MEASUREMENT row) and of the
  shape-2 cells (each needs a day later than 2026-10-24).
- The shape-2 W = 512 REGIME-SCOPED refusal stands; resolving it is a
  protocol decision, not a re-run.
- Naming this replication record in accelerator-variants' flip note and
  basis evidence lists (a docstring slice, with the scoped gate).
- The regime-robust magnitude claim protocol (PROPOSED, decided nowhere)
  and the blocked/absent-hardware rows stay exactly as prior records left
  them.
