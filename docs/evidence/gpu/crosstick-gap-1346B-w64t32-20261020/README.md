# crosstick-gap-1346B-w64t32-20261020 — cross-tick sign probe at a 21m39s gap (ticks 20261020-1403 + this tick, JUN-58): flip-cell transition INCONCLUSIVE (analyzer FLIP=YES VOIDED: batch B non-unanimous −/−/+, 0/6 IQR-clean at record load 17.7–50.0); anchor sign-unanimous −/−/− both batches (FLIP=no by sign); the transition does NOT count — series stays "one flip in twenty-five"

## The finding this tick

**The 26th transition attempt is INCONCLUSIVE and does not advance the
series count.** The flip cell w64t32's analyzer verdict is FLIP=YES
(batch A +/+/+, batch B −/−/+) but it is **voided** on the chain's rule:
batch B is **non-unanimous (−/−/+)** and **0/3 IQR-clean** — every one of
the six batch-B runs is IQR-dirty (anchor 0.2853 / 0.0951 / 0.1893, flip
cell 0.2339 / 0.0620 / 0.1478, all > the 0.05 rule) at the chain's
**record loads** (load1 17.74–50.02 vs batch A's 5.39–7.50). The magnitudes
are unusable (no IQR-clean survivors in any batch-B cell). The anchor
w64t31 reads **−/−/− in both batches** — FLIP=no by sign — but its batch-B
side is equally noise-labeled. Series: **25 counted transitions, one flip
in twenty-five** (unchanged from tick 1346 / PR #1416).

| cell | batch A (Oct 20 13:50:59–13:52:07, tick 1346 / PR #1416) | batch B (Oct 20 14:13:46–14:51:49, ticks 1403 + this) | cross-batch |
|------|------|------|------|
| w64t31 (anchor) | mean(3) **−11,973.0**, signs **−/−/−** (2/3 IQR-clean) | mean(3) **−95,639.3**, signs **−/−/−** (0/3 IQR-clean) | FLIP=**no by sign** (both sign-unanimous; noise-labeled) |
| w64t32 (flip cell) | mean(3) **+5,176.8**, signs **+/+/+** (3/3 IQR-clean) | mean(3) **−233,747.1**, signs **−/−/+** (0/3 IQR-clean) | analyzer FLIP=**YES — VOIDED** (non-unanimous + 0/3 clean) → INCONCLUSIVE |

ns/dispatch, variant-chunked minus baseline-chunked. All 12 runs `RESULT
verified=true` (machine-checked), runner exit 0 on every retained run.
Batch-B per-run: anchor run1 −207,679.7 (iqr 0.2853, load1 23.22), run2
−65,359.4 (0.0951, 35.56), run3 −13,878.9 (0.1893, 49.13); flip cell run1
−409,745.1 (0.2339, 18.28), run2 −366,550.8 (0.0620, 17.74), run3
+75,054.7 (0.1478, 50.02). All batch-B `vs-1.0` verdicts
`indistinguishable-at-this-noise`. **Gap series now** (voided entries in
parentheses): 6m52s within-session / 11m34s / 12m32s / 12m52s / 13m34s /
13m50s / 13m51s / 14m51s / 14m59s / (15m21s tick 1132, voided) / 16m20s /
24m33s / 25m36s / (27m27s tick 1201, voided) / 27m27s / 29m21s / 30m9s /
30m14s / **21m39s (this tick, VOIDED)** / 70m26s / 124m20s / 318m29s.

## What this bounds, honestly

- **CROSS-TICK / CROSS-SESSION datum; VOIDED for the sign question at the
  flip cell.** Gap and session restart remain confounded; the flip cell's
  sign break (−/−/+) is recorded as observed but carries no adjudication
  weight — a voided transition is not a flip. The count stays at one flip
  in twenty-five.
- **Load confound is at its chain maximum.** Batch B ran under host load1
  17.74–50.02 (including 35.56 / 49.13 / 50.02 during pairs 2–3) — the
  heaviest loads any batch has run at; batch A ran at 5.39–7.50. The
  #1396 noise-attribution hypothesis reads **supporting-direction** here
  (quality collapsed exactly as load spiked) but this datum does not
  adjudicate it: load, session restart and the three failed attempts are
  all confounded together. The load source is UNATTRIBUTED.
- **Protocol deviations, all recorded: (1)** three failed attempts before
  the six retained runs — `attempt1-run-B-1-w64t31-failed-SIGALRM.log`
  (14:07, load 12.84, guest SIGALRM trap),
  `attempt1-run-B-1-w64t32-interrupted-by-harness.log` (14:16, truncated
  after TOOLCHAIN, 3 lines),
  `attempt2-run-B-2-w64t32-interrupted-truncated.log` (14:26, truncated
  after TOOLCHAIN, 3 lines),
  `attempt3-run-B-2-w64t32-failed-VK_ERROR_DEVICE_LOST.log` (14:37–14:45,
  guest exit 120 trap + `vkWaitForFences … VK_ERROR_DEVICE_LOST` — the
  chain's first device-lost failure); **(2)** batch B straddles two cron
  ticks (pair 1 in tick 1403, pairs 2–3 resuming in this tick after the
  sweep was truncated mid-run) and is **not internally adjacent** (pair 1
  14:13:46/14:21:16 vs pairs 2–3 14:46:49–14:51:49). Retained runs all
  passed the `verified=true` gate on the pinned probe.
- No value here is a workgroup-default value; every number is measured on
  this host (Apple M1 Max / MoltenVK 1.3.357; `INFO
  Apple M1 Max|1.3.357|1024|1 aarch64-macos` in every retained log) at
  lanes 2,095,104. Nothing flips `:measured?` in
  `kotoba.compiler.accelerator-targets` — `:arm` / `:unknown` rows stay
  provisional (`:measured? false`).

## Protocol and base note

**Probe identity: the chain's pinned bytes, sha256 `3696ca0d…`** (full:
`3696ca0db0e28c5b41fa5c8551df2ae1302deb190e91722408117a06077ef652`), run as
`scripts/gpu-subgroup-reduce-chunksweep-pinned-3696ca0d.cljk`,
shasum-guarded by `run-sweep.sh.txt` before every run. Every retained log
self-printed `fixture=subgroup-reduce-w64-sum.emitted.glsl
sha256=a25a6931…` (full: `a25a69317b5c5a956279ccc37a5089adb489104a28ed89460b8928889b096254`,
12/12 machine-checked).

**Chain inputs at this base (the PR #1393 staging rule — executed).** Base
is origin/main `005d48fb`; `sh scripts/gpu-sign-chain-stage-fixtures.sh.txt`
was run from this worktree root before dispatch, restoring the chain's
pinned pre-fix fixture bytes (all four sha256 re-verified this tick: w32
`0cf6c406…`, w64 `a25a6931…`, w128 `c7931718…`, w256 `087107f9…`). After
dispatch the tracked fixtures were restored (`git checkout --
test/fixtures/gpu/`) so this diff stays evidence-only.

**Base note.** Batch A ran on `005d48fb` (tick 1346's worktree); batch B
ran on `005d48fb` (tick 1403's worktree, both cron ticks) — base delta
**empty**.

**Gap provenance.** 13:52:07 (batch A end) → 14:13:46 (batch B start) =
**21m39s**, carrying no documented amu-gpu GPU dispatch (tick 1346's
post-dispatch work; tick 1403's pre-dispatch work). The batch-B
interruptions (14:21–14:46) coincide with sharply rising host load
(15.1 → 50.0); other sessions' GPU/CPU traffic is **not ruled out**.

**Analyzer carry.** `analyze-1403.py` carried from `analyze-1346.py` —
diff machine-checked to exactly five changed line-pairs (carry-source
line, two-line batch attribution pair, output-filename pair in docstring
and code); parsing, noise rule and gap label untouched. `run-sweep.sh.txt`
body below `set -e` byte-identical to tick 1346's except `EV=`
(machine-verified). Batch-A copies sha256-machine-checked byte-identical
to tick 1346's batch-B logs.

## States

- implemented (code + test): nothing in src/test this tick — evidence-only
  diff. **Gate not run** (nothing to gate). Suite base state carried from
  PR #1388's exact-base run (16F/15–17E, red set outside every amu-gpu
  diff, not green) — not re-measured this tick.
- measured (this document + logs): the 21m39s cross-tick datum above
  (signs, loads, IQRs, the three failure logs) — transition INCONCLUSIVE,
  not counted.
- UNMEASURED: the flip RATE; all batch-B magnitudes (0 IQR-clean
  survivors); the #1396 load-noise attribution (still unadjudicated);
  probe-idle gap across all sessions; the `:arm` / `:unknown` workgroup
  rows (`:measured? false` stays false).

## Files

- `run-A-*.log` — byte-identical copies of tick 1346's batch-B logs (PR
  #1416), sha256 machine-checked: `e06da337…` `a0f4a4c5…` `e5defc0c…`
  (w64t31 pairs 1–3), `16d5dad5…` `12f16021…` `8330dfe1…` (w64t32 pairs
  1–3).
- `run-B-*.log` — the six retained runs (exit 0, `RESULT verified=true`),
  sha256: `acddb3a9…` `7791e7f2…` `035373ed…` (w64t31 pairs 1–3),
  `8201a81a…` `d06b83a8…` `a94e82f9…` (w64t32 pairs 1–3).
- `attempt1-*.log` / `attempt2-*.log` / `attempt3-*.log` — the four
  failed/interrupted attempts (bytes preserved, renamed only).
- `run-sweep.sh.txt`, `analyze-1403.py` / `analyze-1403.txt` — carried probe
  driver and analyzer output.
