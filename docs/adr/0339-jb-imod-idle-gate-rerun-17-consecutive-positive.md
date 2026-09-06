# ADR 0339 — J-B imod specialization: idle-gate rerun lands, 17 consecutive positive runs (still diagnostic-only)

- Date: 2026-09-06 09:30 JST (amu-falsify cron)
- Status: Accepted (evidence record; no claim, no policy change)

## Context

The J-B population note demanded an idle≥9/10 sustained-window rerun of
`bench/runtime-comparison/jb_imod_control.c` (constant-divisor imod strength
reduction, ADR 0289 residual). Six+ prior ticks were busy-refused. This tick
load fell through the window (09:22 vm.loadavg 8.16 → 09:23 6.60; during runs
load1 4.1–5.3 across 9×5s samples, 9/9 < 7.5). Binary preflighted at
/private/tmp/jb_imod_control_preflight (staged 04:08, unchanged source).

## Evidence (idle-gate rerun, amu-falsify)

ABBA-interleaved, checksum-agreeing (arms agree 764266). Warmup (not counted):
3×40 alternations @200k iters = +6.7/+5.4/+6.9% at load1 ~11 (borderline).

Policy-compliant runs (24 alternations × 4,000,000 iters), 3 independent runs:

| run | opaque (sdiv) ns/elem | const (mulh) ns/elem | ratio | saving |
|-----|----------------------|----------------------|-------|--------|
| 1   | 5.085                | 4.714                | 1.079 | +7.3%  |
| 2   | 5.147                | 4.785                | 1.076 | +7.0%  |
| 3   | 5.156                | 4.824                | 1.069 | +6.4%  |

All ≥ the 5% bar, spread tight (range 0.9pp), sign consistent. Combined with
ADR 0335 (+6.2/+7.0/+6.7) and ADR 0338 (+7.6/+7.8/+6.3): **17 consecutive
positive checksum-agreeing runs across six windows; effect 5.4–7.8%, stable.**

## Decision

- No compiler change. No perfgate policy change. Diagnostic only.
- J-B survives every proxy-level falsification attempt; the proxy kill path is
  exhausted. Status remains confirmed-diagnostic/unqualified — qualification
  still requires real runtime specialization in kotoba-native measured through
  perfgate.core/qualify, which is amu-bench/compiler territory, not falsify.
- This entry supplies the idle-gate rerun numbers the population note asked for.

## Consequences

Next falsify ladder step unchanged: H-Z3 quiet-host hand-patch A/B, then H-C2
timed A/B (static-confirmed 61/61).
