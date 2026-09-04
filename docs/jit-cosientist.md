# JIT/tiering cosientist — hypothesis population

Status ledger for the JIT/tiering axis. Independent of
`docs/codegen-cosientist.md` (AOT axis); same discipline: falsify first,
quiet gate, `perfgate.core/qualify` is the only judge, no fabricated numbers.
Appended only; population rows are owned by rank, evidence by falsify.

## Environment note (measured 2026-09-03, tick 1)

- No Chicory (or any JVM wasm interpreter) exists anywhere in
  `orgs/kotoba-lang` (repo-wide search: 1 unrelated hit). On this workstation
  kotoba wasm executes under Node/V8 (`bench/runtime-comparison/wasm-runner.mjs`
  → `runtime/browser-host.mjs` → `WebAssembly.instantiate`), i.e. already
  tiered-JIT wasm, not an interpreter. Any "interpreter dispatch share"
  hypothesis needs a chicory-host environment that is not present here.

## Population

| ID | hypothesis | status | evidence |
|---|---|---|---|
| J-A | Chicory interpreter dispatch dominates the wasm hot-loop cost; measure its share as the JIT premise | **not actionable here** — no chicory host in the org; this workstation's wasm path is V8 (tiered), so the share would measure V8 tiering, not interpreter dispatch | 2026-09-03: search + runner source inspection. Needs an environment decision before any measurement can mean "interpreter dispatch". |
| J-B | Runtime constant-divisor specialization of the shared `imod` (ADR 0289 residual, ~165 sdiv/call) recovers ≥5% | open — **hand-patch run, unqualified** | 2026-09-03: C control `/tmp/jb-imod` (saved as `bench/runtime-comparison/jb_imod_control.c`), serial chain `acc = imod(acc*31+v[i], M)`, arm A opaque divisor (real `sdiv`, disassembly-verified) vs arm B constant divisor (smulh+asr), both checksum-agreeing. Three runs at load1 16–27 (10 CPUs): saving **−7.8% / +3.8% / −4.7%** — sign flips between runs. Host never met the quiet gate (≥1 idle CPU); perfgate would fail closed. Verdict: **measurement under-qualified, hypothesis neither killed nor confirmed.** The ratio bound suggests the sdiv→mulh term alone is ≲5% of element cost *under load*, but quiet-host numbers are required (expected sdiv latency ~10 cycles on the serial chain could make the real saving much larger than any run above shows). Next: rerun when idle ≥ 9/10 CPUs, 4000000 iters × 24 alternations, ratio of medians. 2026-09-03 tick 2 (JIT): rerun attempted, host again failed the quiet gate (load 16–20 on 10 CPUs, iostat idle 0–4%) — measurement deferred, still neither killed nor confirmed. 2026-09-03 tick 3 (JIT): rerun again deferred — host load 23–28 on 10 CPUs, idle 0–1.6% (two probes 90s apart); third consecutive busy tick. Control remains at bench/runtime-comparison/jb_imod_control.c; measurement is next tick's first action when quiet gate passes. 2026-09-03 tick 4 (JIT): quiet gate failed a 4th consecutive time (load 13–21 on 10 CPUs, top idle 0–1.7%, two probes 2 min apart) — J-B measurement again deferred, no compiler change made. 2026-09-04 10:42 JST tick 5 (JIT): quiet gate failed a 5th consecutive time — load1 31–34 on 10 CPUs, iostat idle 0–1.7% (20 samples), no idle CPU. Control unchanged; measurement is next tick's first action when idle ≥9/10. 2026-09-04 11:43 JST tick 6 (JIT): quiet gate failed a 6th consecutive time — load1 43.6–45.8 on 10 CPUs, iostat idle 0–25% (5 samples, 0% on 4/5), no idle CPU. J-B measurement again deferred; control unchanged, no compiler change made. 2026-09-04 13:05 JST tick 7 (JIT): quiet gate failed a 7th consecutive time (load1 53–75 on 10 CPUs, idle 0.3–1.4% during runs; external load: Chrome renderer 99%, java, WindowServer — no stray jb processes). Rather than defer again, ran the measurement as a **loaded-host diagnostic only** (per tick-1 precedent, ADR 0289 style: ratios only, never a qualify input). Hand-patch `/tmp/jb-imod/jb_imod.c`, 4,000,000 iters × 24 ABBA alternations, checksums agree (764266). Three runs: saving **−0.5% / +4.5% / −0.7%** (median ns/elem 12.94 vs 13.00; 31.50 vs 30.09; 34.29 vs 34.54) — sign still flips, magnitude ≤4.5% even under heavy load. Interim read: the sdiv→mulh saving on this residual chain is unlikely to reach 5% alone; a quiet-host confirmatory run is still required before recording it as killed (do not record killed on loaded-host data alone). |
| J-C | wasm host crossings (H-Y1: 2.03/element, ADR 0285) are removable by JIT-side inlining | open — not started | AOT lowering lever (widen `structured-loop-body?`) may precede any JIT work; do not start until J-B has a quiet-host verdict. |

## Policy note (standing)

Any JIT-form claim needs a warmup/steady-state measurement-boundary decision in
`perfgate` — changes go through an ADR draft; **no sealed claim before human
approval**. Current verdicts above are diagnostics, not claims.
