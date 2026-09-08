# ADR 0345 — J-B lever matrix at full gate: inlining +18.03% qualified, divisor fold qualifies only standalone and regresses −5.97% on top of it

- Date: 2026-09-08 (amu-jit tick 28)
- Status: Accepted (evidence record; no compiler change, no policy change, no sealed claim)
- Chain: extends ADR 0335 / 0338 / 0339 (busy-host sign series), ADR 0341
  (measurement placement: fleet node, busy-CPU gate), ADR 0344 (host-qualified
  2-arm + first 4-arm matrix on levi). This ADR adds the FIRST perfgate-
  qualified verdicts on the JIT axis and closes the J-B attribution question.

## What was missing before

ADR 0344's 4-arm matrix (levi) reported the arm means but no perfgate
verdict per pair; the JIT ledger (docs/jit-cosientist.md ticks 22–23) had the
lever split only as busy-host sign diagnostics, with an explicit caveat that
the C-vs-D ordering was not stable across ticks. No JIT-axis measurement had
ever carried a `perfgate.core/qualify` verdict at the fleet quiet gate
(busy-CPU fraction ≤ 0.10, ADR 0282 criterion).

## Measurement (benjamin, 2026-09-08 13:25–13:37 JST run window = 04:25–04:37 UTC)

- Fixture: `bench/runtime-comparison/jb_imod_control_4arms.c`, sha256
  `a025ed9ba133d5a4c2c435c7c299ab56142444da2bcbf850cb032a22a8e3c108`
  (verified on-node after scp; untouched since tick 22).
- Build: Apple clang 17 (clang-1700.6.4.2) `-std=c11 -O3 -Wall -Wextra`
  (`-Werror` omitted only for the fixture's two pre-existing unused-`q`
  warnings; arms re-verified by disassembly on-node: A `bl`→`imod_opaque`
  (sdiv), B `bl`→`imod_const` (smulh+asr), C inline sdiv / 0 `bl`,
  D inline smulh+asr / 0 sdiv).
- 12 process-cold runs of `./jb4_t28 4000000 24`; each printed
  median-of-24-alternations ns/elem is ONE perfgate sample; 4-arm checksum
  agreement (764266) held every run.
- Gate: busy-CPU fraction PRE 0.045 / POST 0.049 (3-rep bracket same day
  0.044/0.044/0.078/0.045), load1 ~2.0 on 10 cores, 0 users. Meets ADR 0282.

## perfgate.core/qualify verdicts (default-v1 policy, machine
darwin-arm64-benjamin `:measured`; route:
`bench/runtime-comparison/jb_qualify.clj`, run on-node)

| pair | meaning | improvement | separated? | verdict |
|---|---|---|---|---|
| A→B | lever 1: constant-divisor fold, helper call kept | **+13.11%** | yes (gap 0.4676 vs summed-stdev 0.0008) | **QUALIFIED** |
| A→C | lever 2: helper-call INLINING, sdiv kept | **+18.03%** | yes (gap 0.6432 vs 0.0019) | **QUALIFIED** |
| A→D | both | +13.14% | yes (gap 0.4687 vs 0.0040) | **QUALIFIED** |
| B→D | marginal inlining on top of const arm | +0.03% | no (:not-separated-from-noise) | NOT qualified |
| C→D | marginal const fold on top of inlined arm | **−5.97%** | yes — as a REGRESSION | NOT qualified |

Relative stdevs 0.0001–0.0012 (policy ceiling 0.10). Cross-host check against
ADR 0344 Evidence 2 (levi): all five deltas agree within 0.1pp.

## Decision

1. The tick-22/23 falsification of J-B's causal story is **confirmed at
   qualified quality**: on the serial `imod` chain the saving attributed to
   "runtime constant-divisor specialization" is the removal of the
   **helper call**, and once the call is gone the divisor fold adds nothing
   (B→D ≈ noise) and on top of the inlined shape actively regresses
   (C→D −5.97%, separated). The two levers are substitutes on this shape,
   not complements.
2. The ladder's next hand-patch/implementation lever is **J-B2: imod helper
   inlining at the call site in kotoba-native emission** (candidate for
   amu-rank to rank; the ≥5% bar is cleared twice over by the A→C delta with
   spread separation at the proxy level). The divisor-specialization route
   (kotoba-mir const-divisor lowering) is demoted: it qualifies only where
   an out-of-line call remains, which the inlining lever removes anyway.
3. The 25-tick workstation quiet-gate streak is formally irrelevant to this
   axis: per ADR 0341 the measurements now run on fleet nodes under the
   busy-CPU criterion. The tick 23 "structural ceiling" flag is retired.

## What this verdict is NOT

- Not a claim about amu/kotoba-native output: arms A–D are hand-written C
  controls bounding the mechanism, exactly as in 0335–0344. The compiler
  change remains unimplemented and unqualified.
- Not a JIT-form sealed claim: the warmup/steady-state policy note in
  docs/jit-cosientist.md stands — any JIT-shaped claim needs its own policy
  ADR with human approval first. This ADR changes no policy.
- No claim artifact is emitted (g/claim was not called on these pairs; the
  qualification records above live in
  `bench/runtime-comparison/jb_imod_4arm_benjamin_t28.edn` as an evidence
  file, diagnostics-grade by the standing rule until perfgate + approval).

## Consequences / next

- amu-rank: rewrite J-B status (mechanism attribution falsified —
  confirmed-qualified) and promote J-B2 (imod inlining) into the population.
- amu-jit next tick: move the J-A JFR cross-attribution run to benjamin as
  well (SampleVersion=2 method-vs-stack on a quiet node); leaf-share
  stability, not the wall share, is the open J-A question.
- J-B2 implementation, when ranked: correctness first — inlining the guard
  must preserve signed-modulo semantics for divisor 1 / −1 / powers of two /
  INT64_MIN-over-−1 and negative dividends, fail-closed to the call outside
  the proven window (same boundary list as 0341 §3).
