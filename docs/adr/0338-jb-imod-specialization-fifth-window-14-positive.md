# ADR 0338 — J-B imod specialization: fifth window, 14 consecutive positive runs (still diagnostic-only)

- Date: 2026-09-05 06:10 JST (amu-jit tick 13)
- Status: Accepted (evidence record; no claim, no policy change)

## Context

J-B (runtime constant-divisor specialization of the shared `imod`, ADR 0289
residual ~165 sdiv/call) has an ABBA-interleaved C proxy control
(`bench/runtime-comparison/jb_imod_control.c`) measuring opaque-sdiv vs
constant-divisor (smulh+asr) on the serial chain
`acc = imod(acc*31 + v[i], M)`.

## Evidence (tick 13, fifth window)

Host: 10 CPUs, load1 4.1–6.7, top idle 77.5% — majority-idle, **full quiet
gate (idle ≥ 9/10) again NOT met**. 4000000 iters × 24 alternations, 3 runs:

| run | opaque (sdiv) ns/elem | const (mulh) ns/elem | ratio | saving |
|-----|----------------------|----------------------|-------|--------|
| 1   | 5.101                | 4.715                | 1.082 | +7.6%  |
| 2   | 5.094                | 4.698                | 1.084 | +7.8%  |
| 3   | 5.060                | 4.741                | 1.067 | +6.3%  |

Checksums agree (764266) in all runs. **14 consecutive positive runs across
five windows; effect 6–8%, stable in sign and magnitude.**

## Decision

- No compiler change. No perfgate policy change. Diagnostic only.
- The C-proxy kill attempt has now failed 14 times; J-B survives every
  proxy-level falsification attempt.
- The next lever is unchanged and now overdue: real runtime specialization in
  kotoba-native measured via bench/runtime-comparison + perfgate.core/qualify
  on a fully quiet host.

## Consequences

JIT-form end-to-end claims still require the warmup/steady-state boundary ADR
(draft pending human approval); nothing here is a sealed claim.
