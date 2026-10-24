# NOTES -- the cross-day replication of the W = 512 (shape 1) :simdgroup-reduce cell

## What row this is, and its eligibility

The record's own "Honest LEFT" named this row: "Cross-day replication of
the other five W cells (shape 1: W = 32, 64, 128, 512, 1024 -- each its
own later-day MEASUREMENT row)", with eligibility per cell's OWN session
date (the resweep record's correction: "cross-day eligibility is per
cell's OWN session date, not the directory's date suffix"). W = 512 is
the ONE such cell whose original session is a 2026-10-23 session (commit
2026-10-23 23:22, docs/evidence/gpu-simdgroup-reduce-m1max-wsweep-20261023/w512)
and is therefore runnable as a cross-day replication on 2026-10-24. This
run is 2026-10-24 09:20 JST, the same host (Apple M1 Max, reported
simdgroup size 32), the same conforming native-Metal channel (ADR-0360
question (1)'s decision, the emitters' own bytes), the byte-identical
protocol (6 fresh processes, 20 interleaved AB/BA pairs per operator per
run, 2 warmup submits per arm discarded, verified read-back). This is
the record's first cross-day replication at a cell other than the
W = 256 anchor (the anchor's is the sibling record
gpu-simdgroup-reduce-m1max-crossday-20261024/w256).

Driver (named verbatim, never paraphrased):

    python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 6
      --workgroup 512 --elements 1000003 --variant simdgroup-reduce
      --out docs/evidence/gpu-simdgroup-reduce-m1max-crossday-20261024/w512
      --compare-historical docs/evidence/gpu-simdgroup-reduce-m1max-wsweep-20261023/w512/summary.md

The emitted shaders are byte-identical to the wsweep cell's (`diff -r`
empty, checked this tick). Classpath: the driver's named route 2
(`AMU_KBB_TEST_CLASSPATH`; route 1 `kbb -Spath -M:test` fails at the tree
root, exit "no deps.edn" -- the merge 7b8f6488 retired deps.edn; the
compile-log names the fallback, never silent).

## FINDING (real measurement, this host, this tick)

- This session's own verdict (claim protocol rule 2): **REGIME-INVARIANT
  FASTER** -- 18/18 per-run ratios below 1.0, every observed regime
  one-sided; paired median ratios 0.814/0.824/0.824 for :sum/:max/:min.
- The historical cell (2026-10-23 23:22) recorded 0.815/0.823/0.824
  (also 18/18 REGIME-INVARIANT FASTER).
- The rule-3 regime-matched comparison (the driver's --compare-historical
  auto-wiring): sign -- **"reproduces in sign strictly"** at every
  operator; magnitude -- "magnitude reproduces within 0.001" for :sum and
  **"magnitude splits by clock regime"** for :max/:min (mixed strata
  draws) -- but at the MATCHED strata the within-stratum deltas are
  0.000-0.004 (max: 0.001; min: 0.004/0.000; sum: 0.000). The claim names
  the split and attributes it to session mixing -- never "failed to
  reproduce".
- THE FINDING: at W = 512 the :simdgroup-reduce speedup over :baseline
  reproduces CROSS-DAY in sign strictly (18/18 both days, every operator)
  and in within-stratum magnitude to within 0.004, while the day's regime
  MIX is not cross-day stable (this day's :max/:min runs draw the fast
  clock levels in runs 5/6; the historical draw was mixed differently).
  That is the measured, per-cell form of the record's position: sign is
  the cross-day-stable claim at this cell; magnitude phrases stay
  regime-scoped and strata-matched.
- Read-back: 36 verify lines, ok=1 on every one (ok=0: 0); :max/:min
  bit-exact vs the reference and between arms (24/24 lines); :sum
  max_abs_vs_ref 1.63e-05 / max_abs_vs_other 3.05e-05 (regrouping).
- Rule 1 this run: one level for :sum, three for :max, three for :min;
  cross-operator level identity REFUTED (9/15 run pairs) -- again a
  different regime structure from the historical day's, which is exactly
  why the comparison is published regime-matched.

## What this slice does NOT license

- No `:measured?` flag moves: this replication re-measures an ALREADY
  flipped cell (W = 512 flipped with the wsweep). No selection answer
  changes and no workgroup row (ADR-0355/0358) is touched.
- The other cross-day rows stay UNMEASURED: W = 32/64/128 (shape 1) and
  every shape-2 cell need 2026-10-25+ (their own sessions ran
  2026-10-24); W = 1024 is midnight-straddling and needs 2026-10-25+
  unless its own run-log shows a 2026-10-23 run.
- The shape-2 W = 512 cell stays measured-but-REFUSED (REGIME-SCOPED);
  this run says nothing about it -- replication of a REFUSED cell is its
  own decision, not a way to re-run a refusal.
- Shapes beyond the two measured ones (1,000,003 and 2^20) stay UNMEASURED
  at every cell.
- This is a REPLICATION record: naming it in accelerator-variants' flip
  note / basis evidence lists is its own later slice (the anchor's naming
  was likewise its own slice, commit 9e393ccd).
- The regime-robust magnitude claim protocol (PROPOSED, decided nowhere)
  and the blocked/absent-hardware rows stay exactly as prior records left
  them.

## Gate (this tick changed no code namespace)

- Scoped GPU gate (the 8 GPU-owned test namespaces, scratch runner
  gpu_scoped_gate.cljk, not in the repo), run this tick after the
  measurement: "Ran 101 tests containing 9632 assertions. 0 failures,
  0 errors." (scoped: 101 tests, 9632 passed, 0 failed, 0 errors).
- Full run-tests.cljk: RED AT BASE, re-run this tick (real transcript:
  aborts at namespace load with "Could not find namespace: kotoba.form",
  the W3 port path, outside this diff -- documented red at base in ADR
  0362 and every prior tick record). No green full suite is claimed.

## Honest LEFT (the real remainder after this row)

- The cross-day replication rows that are not yet eligible: W = 32/64/128
  (shape 1, each runnable 2026-10-25), W = 1024 (midnight-straddling;
  2026-10-25+ unless its own run-log shows a 2026-10-23 run), and the
  shape-2 cells (each needs a day later than 2026-10-24).
- The shape-2 W = 512 REGIME-SCOPED refusal stands; resolving it is a
  protocol decision, not a re-run.
- Naming this replication record in accelerator-variants' flip note and
  basis evidence lists (a docstring slice, with the scoped gate).
- The regime-robust magnitude claim protocol (PROPOSED, decided nowhere)
  and the blocked/absent-hardware rows stay exactly as prior records left
  them.
