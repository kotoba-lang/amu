# NOTES -- the W = 32 :simdgroup-reduce cell re-swept (same-day second session -- NOT cross-day)

## What row this is, and why it is NOT the cross-day row

The tick set out to take the cross-day replication row the w256 anchor
record's "Honest LEFT" named for W = 32 ("Cross-day replication of the
other five W cells (shape 1: W = 32, 64, 128, 512, 1024 -- each its own
later-day MEASUREMENT row)"). The eligibility check killed that framing
for this cell before publication: the W = 32 original session ran
**2026-10-24** (its commit 5c8508e5 is 2026-10-24 02:39 JST, and the
W = 32 flip record docs/evidence/gpu/simdgroup-reduce-flip-w32-20261024.txt
states the wsweep measurement was "taken earlier the same day"), and this
run is 2026-10-24 09:01 JST -- the SAME calendar day. The record's own
protocol excludes it: "Cross-day replication of any cell needs a later-day
run (a cron tick on another day), **not more same-day sessions**." So this
is a same-day second session, filed exactly as the :subgroup-reduce family
filed the same situation (docs/evidence/gpu-subgroup-reduce-m1max-resweep-20261023:
"Same-day replication across sessions -- NOT cross-day, and it does not
claim temporal stability beyond this day"). W = 32's cross-day replication
row stays UNMEASURED and becomes runnable on 2026-10-25.

Record-integrity note (named, not hidden): an earlier same-day session
this tick (~09:00 JST) was run into a mis-named out path
(gpu-simdgroup-reduce-m1max-crossday-20261024/w32) before the eligibility
check. Because the driver's summary embeds the run-time --out path in its
rule-3 auto-wiring text, that directory was DELETED unrecorded and the
measurement re-run under this correct name. Nothing from the deleted
session is cited anywhere; every number below is the re-run's (the
recorded session). No repository record was rewritten -- the deleted
session was never committed.

## What ran (real hardware, real emitted bytes)

Driver (named verbatim, never paraphrased):

    python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 6
      --workgroup 32 --elements 1000003 --variant simdgroup-reduce
      --out docs/evidence/gpu-simdgroup-reduce-m1max-resweep-20261024/w32
      --compare-historical docs/evidence/gpu-simdgroup-reduce-m1max-wsweep-20261023/w32/summary.md

Ran 2026-10-24 09:01 JST, same host (Apple M1 Max, reported simdgroup
size 32), same conforming native-Metal channel (ADR-0360 question (1)'s
decision, the emitters' own bytes), the byte-identical protocol of the
wsweep cell (6 fresh processes, 20 interleaved AB/BA pairs per operator
per run, 2 warmup submits per arm discarded, verified read-back). The
emitted shaders are byte-identical to the wsweep cell's (`diff -r` empty,
checked this tick). Classpath: the driver's named route 2
(`AMU_KBB_TEST_CLASSPATH`; route 1 `kbb -Spath -M:test` re-probed this
tick and fails at the tree root, exit 66 "no deps.edn" -- the merge
7b8f6488 retired deps.edn; the compile-log names the fallback, never
silent).

## FINDING (real measurement, this host, this tick)

- This session's own verdict (claim protocol rule 2): **REGIME-INVARIANT
  FASTER** -- 18/18 per-run ratios below 1.0, every observed regime
  one-sided; paired median ratios 0.636/0.691/0.731 for :sum/:max/:min.
- The wsweep session (the same day, 02:39 JST) recorded
  0.657/0.658/0.650 (also 18/18 REGIME-INVARIANT FASTER).
- The rule-3 regime-matched comparison (the driver's --compare-historical
  auto-wiring): sign -- **"reproduces in sign strictly"** at every
  operator; magnitude -- "magnitude reproduces within 0.021" for :sum and
  **"magnitude splits by clock regime"** for :max/:min (mixed strata
  draws; within-stratum deltas 0.016 (:max), 0.006-0.099 (:min), 0.014
  (:sum)).
- THE FINDING: at W = 32 the sign is stable across same-day sessions
  (18/18 in both sessions) while the magnitude and the regime structure
  are not -- raw paired medians moved 0.021 (:sum) / 0.033 (:max) /
  0.081 (:min) within one calendar day, and the cross-operator level
  identity flipped from HOLDS (wsweep: 0/15 divergent run pairs) to
  REFUTED (this session: 12/15). This is the measured, per-cell form of
  the record's claim that same-day sessions cannot carry cross-day or
  magnitude claims: even the sign-stable cell's magnitude phrases are
  regime-scoped within a day. It also corrects the w256 record's "Honest
  LEFT" grouping: cross-day eligibility is per cell's OWN session date,
  not the directory's date suffix (the wsweep directory says 20261023 but
  w32/w64/w128/w1024 sessions ran 2026-10-24; only W = 512 (commit
  2026-10-23 23:22) is clearly a 2026-10-23 session, and W = 1024's
  commit (2026-10-24 00:05) straddles midnight).
- Read-back: 36 verify lines, ok=1 on every one; :max/:min bit-exact vs
  the reference and between arms; :sum max_abs_vs_ref 2.15e-06 (baseline)
  / 1.43e-06 (variant), max_abs_vs_other 1.91e-06 (regrouping).

## What this slice does NOT license

- This is NOT a cross-day replication: no cross-day row advances,
  including W = 32's own (runnable 2026-10-25).
- No `:measured?` flag moves (this re-measures an ALREADY flipped cell);
  no selection answer changes; no workgroup row (ADR-0355/0358) moves.
- kotoba.compiler.accelerator-variants' cross-day scoping ("measured at
  exactly ONE cell (the W = 256 anchor)") stays TRUE and untouched -- a
  same-day re-session is not a cross-day replication.
- The shape-2 W = 512 cell stays measured-but-REFUSED (REGIME-SCOPED);
  this run says nothing about it, and no re-run revisits a refusal.
- Shapes beyond the two measured ones (1,000,003 and 2^20) stay UNMEASURED
  at every cell.
- Whether same-day re-session records are named in the flip note / basis
  evidence lists at all is a decision this tick does not make; if made,
  the naming is its own slice.

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

- The cross-day replication rows, now with per-cell eligibility: W = 512
  (shape 1) is the ONE cell whose original session is 2026-10-23 and is
  runnable as a cross-day replication on 2026-10-24; W = 32/64/128 and
  the shape-2 cells need 2026-10-25+, and W = 1024 is midnight-straddling
  (treat as needing 2026-10-25+ unless its own run-log shows a 2026-10-23
  run).
- The shape-2 W = 512 REGIME-SCOPED refusal stands; resolving it is a
  protocol decision, not a re-run.
- The regime-robust magnitude claim protocol (PROPOSED, decided nowhere)
  and the blocked/absent-hardware rows stay exactly as prior records left
  them.
