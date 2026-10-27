# load-manip-20261020 — the pre-registered load-MANIPULATION experiment: dispatched and completed, but INCONCLUSIVE-DOSE (JUN-58, parent JUN-55)

## The finding this tick

**The manipulated-comparison experiment that the corpus analysis asked for
was designed, pre-registered, dispatched and completed — 8/8 runs verified —
but it is INCONCLUSIVE-DOSE: the manipulation check failed on the arm-I side,
so per the pre-registered rules no outcome pattern is read as evidence, and
the causal direction (load → noise) stays UNMEASURED.**

The failure mode is itself the finding: **the host's NATURAL load rose through
the pre-registered arm-I threshold (load1 <= 16) during the idle arm**, so the
two arms' doses overlap from below. Arm-I run-start load1 = 15.70 / 17.91 /
17.66 / 20.88 — three of four above 16 — while arm L (12 CPU burners) reached
load1 45.87–78.39. A blocked I-then-L design on a host carrying substantial
background load cannot guarantee a low-load arm; a future attempt needs either
a quieter window, a matched-load design, or a dose threshold chosen from the
observed idle floor (which must be re-registered BEFORE dispatch, not after).

## What ran (all numbers from the committed logs through the committed analyzer)

- **Design:** exactly the pre-registered one (`analyze-manip.py` docstring,
  rules fixed before the first dispatched run). Arms I = natural load
  (pairs 1-2), L = 12 CPU-burner processes started 15:42:46, >=120 s burn-in
  (verified: load1 24.61 at start, 78.39 at burn-in end), killed 15:56 after
  the last L run. Cells w64t31 (anchor) / w64t32 (flip cell), lanes 2,095,104,
  cell order rotated t31,t32 / t32,t31 / t31,t32 / t32,t31. Blocked order
  I then L (fixed order confounds dose with time drift — a recorded confound).
- **Retention:** 8/8 runs `RESULT verified=true`, no failed or truncated
  attempts (every slot succeeded on attempt 1). Dispatch window 15:37–15:56
  JST, Oct 20.
- **Manipulation check (pre-registered, threshold 16):** arm I load1
  [15.7, 17.91, 20.88, 17.66] → **DOSE-VALID=False** →
  **INCONCLUSIVE-DOSE**. Per the pre-registered interpretation rules this
  adjudicates NOTHING, and the descriptive numbers below are recorded for
  completeness only.
- **Descriptive only (NOT evidence):** flip cell w64t32 iqr I [0.2093,
  0.0568] vs L [0.0913, 0.4543] — no clean run in either arm (0/4 cells-pooled
  are chain-clean, iqr<=0.05). Pooled exact Mann-Whitney U = 8.0 = chance,
  p = 1.0. Spearman rho(load1, iqr) = +0.07, exact p = 0.88 (n=8). Signs:
  gap<0 in all 8 runs (observational only; this is NOT a cross-tick sign
  probe — the transition series is untouched at one flip in twenty-five).

## What this bounds, honestly

- **Nothing about the causal direction.** The dose check failed, so this
  experiment cannot say whether load causes noise. The corpus association
  (load-noise-attribution-20261020, rho +0.27 over 196 runs) stands as
  observational and unattributed as before.
- **What it DOES bound:** at the doses actually observed (I 15.7–20.9,
  L 45.9–78.4), n=2 per cell per arm, no clean/dirty separation appeared in
  either direction — but since the arms' doses were not separated as
  registered, this bound is weak and is not claimed.
- One host (Apple M1 Max / MoltenVK 1.3.357), pinned probe sha256 3696ca0d…,
  chain's pre-fix fixtures staged and sha256-verified before dispatch.

## States

- implemented (code + test): nothing in src/test — evidence-only diff
  (analyzer + dispatch script + 8 logs + this README). **Gate not run**
  (nothing to gate); suite base state carried from PR #1388's exact-base run
  (16F/15–17E, red set outside every amu-gpu diff, not green), not
  re-measured this tick.
- measured: the 8 run logs and the dose-check outcome; every number comes
  from the logs through `analyze-manip.py`.
- UNMEASURED (unchanged): the causal direction load→noise; the load SOURCE;
  the flip rate; the `:arm` / `:unknown` workgroup rows (`:measured? false`
  stays false — nothing here touches `kotoba.compiler.accelerator-targets`).

## Files

- `analyze-manip.py` — the PRE-REGISTERED analyzer, sha256
  `2dfae5ecca3ffac1dae960a12fac6c9dc901c6443689c7100bea9db4867b15f4`
  (rules fixed before the first dispatched run).
- `analyze-manip.txt` — its output, sha256
  `8570bb9937c7f5a2fe199232c66893c3e867a1eec6be1b6216c0c3d3b45a1a4f`.
- `run-manip.sh.txt` — the dispatch script (arms, burners, order, idempotence,
  attempt preservation), sha256
  `cdb92fa06ece7f5ce3510e4803d3c7a12c5169be3310564611c2477c7b3ccc39`.
- `run-{1..4}-{w64t31,w64t32}.log` — the 8 verified runs.
- `burner-pids.txt` — the 12 burner PIDs (all killed at teardown).
