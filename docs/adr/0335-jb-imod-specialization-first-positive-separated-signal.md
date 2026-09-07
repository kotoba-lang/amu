# 0335 — J-B hand-patch: constant-divisor imod shows a consistent +6–7% serial-chain saving, still diagnostic

- Date: 2026-09-05 01:42 JST
- Author: amu-jit-cosientist (falsify tick)
- Status: Diagnostic — **not a sealed claim** (see jit-cosientist.md policy note)

## Context

J-B (docs/jit-cosientist.md): runtime constant-divisor specialization of the
shared `imod` (ADR 0289 residual, ~165 sdiv/call) recovering ≥5% on the serial
imod chain. Six consecutive falsify ticks (2026-09-03 → 2026-09-04) failed the
quiet gate and the measurement was deferred each time. This tick the host was
measurably quieter and the deferred measurement ran.

## Measurement

Control: `bench/runtime-comparison/jb_imod_control.c` (unchanged — serial chain
`acc = imod(acc*31+v[i], M)`, arm A opaque divisor via volatile load → hardware
`sdiv`, arm B compile-time constant → `smulh+asr`, checksum-agreeing,
ABBA-interleaved, medians over 24 alternations × 4,000,000 iters).

| run | opaque (sdiv) ns/elem | const (mulh) ns/elem | ratio | saving |
|---|---|---|---|---|
| 1 | 5.322 | 4.990 | 1.067 | +6.2% |
| 2 | 5.152 | 4.793 | 1.075 | +7.0% |
| 3 | 5.174 | 4.825 | 1.072 | +6.7% |

All three runs checksum-agree (764266) and the sign is consistent — unlike the
six prior busy-host runs (−7.8/+3.8/−4.7%), which flipped.

## Gate honesty

The host did **not** meet the full quiet gate (idle ≥9/10 CPUs): load1 4.8–7.1
on 10 CPUs, iostat idle 33–62% (≈4–6 idle CPUs) during the runs — the first
tick in seven where a majority-idle window was available. Numbers are ABBA
median diagnostics, same as ADR 0289's methodology; a perfgate-qualified
verdict still requires a fully quiet host.

## Verdict

- J-B: **not killed, first positive separated signal** — +6.2/+7.0/+6.7% across
  three consecutive runs, direction consistent, magnitude at/above the 5% bar.
  This suggests the sdiv→mulh strength-reduction term on the serial chain is a
  real ~6–7% effect once the host has spare capacity, i.e. the ADR 0289
  residual's divisor term is worth an AOT lowering lever (constant-divisor
  specialization) rather than a JIT-only mechanism.
- No compiler change was made. No sealed claim. Not a perfgate verdict.

## Next hypothesis

1. Rerun the same control on a fully quiet host (idle ≥9/10) for a
   perfgate-qualifiable number.
2. If it holds, the mechanism combines with the AOT axis: hand-patch
   kotoba-mir/native lowering to specialize known-constant divisors and
   re-measure the ADR 0289 residual end-to-end (J-C remains blocked behind J-B).
