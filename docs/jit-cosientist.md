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
| J-B | Runtime constant-divisor specialization of the shared `imod` (ADR 0289 residual, ~165 sdiv/call) recovers ≥5% | open — **hand-patch run, unqualified** | 2026-09-03: C control `/tmp/jb-imod` (saved as `bench/runtime-comparison/jb_imod_control.c`), serial chain `acc = imod(acc*31+v[i], M)`, arm A opaque divisor (real `sdiv`, disassembly-verified) vs arm B constant divisor (smulh+asr), both checksum-agreeing. Three runs at load1 16–27 (10 CPUs): saving **−7.8% / +3.8% / −4.7%** — sign flips between runs. Host never met the quiet gate (≥1 idle CPU); perfgate would fail closed. Verdict: **measurement under-qualified, hypothesis neither killed nor confirmed.** The ratio bound suggests the sdiv→mulh term alone is ≲5% of element cost *under load*, but quiet-host numbers are required (expected sdiv latency ~10 cycles on the serial chain could make the real saving much larger than any run above shows). Next: rerun when idle ≥ 9/10 CPUs, 4000000 iters × 24 alternations, ratio of medians. 2026-09-03 tick 2 (JIT): rerun attempted, host again failed the quiet gate (load 16–20 on 10 CPUs, iostat idle 0–4%) — measurement deferred, still neither killed nor confirmed. 2026-09-03 tick 3 (JIT): rerun again deferred — host load 23–28 on 10 CPUs, idle 0–1.6% (two probes 90s apart); third consecutive busy tick. Control remains at bench/runtime-comparison/jb_imod_control.c; measurement is next tick's first action when quiet gate passes. 2026-09-03 tick 4 (JIT): quiet gate failed a 4th consecutive time (load 13–21 on 10 CPUs, top idle 0–1.7%, two probes 2 min apart) — J-B measurement again deferred, no compiler change made. 2026-09-04 10:42 JST tick 5 (JIT): quiet gate failed a 5th consecutive time — load1 31–34 on 10 CPUs, iostat idle 0–1.7% (20 samples), no idle CPU. Control unchanged; measurement is next tick's first action when idle ≥9/10. 2026-09-04 11:43 JST tick 6 (JIT): quiet gate failed a 6th consecutive time — load1 43.6–45.8 on 10 CPUs, iostat idle 0–25% (5 samples, 0% on the busiest probes) — J-B measurement deferred again, no compiler change, control unchanged. (Tick 7 and tick 8 recorded in the tick log below.) |

## Tick log (falsify — appended evidence notes)

- 2026-09-05 11:15 JST tick 9 (JIT): quiet gate failed an 8th consecutive time
  — load1 16.4–23.5 on 10 CPUs (falling trend through the tick), iostat cpu
  idle 65–79% across probes ~3 min apart, below the required ≥90%.
  J-B measurement again deferred, no compiler change, control unchanged at
  `bench/runtime-comparison/jb_imod_control.c`. Next: on a quiet host add the
  third (non-inlined mulh) arm to separate lever 1 from lever 2.
- 2026-09-05 19:55 JST tick 10 (JIT): quiet gate failed a 9th consecutive time
  — 15 iostat probes over ~70 min, cpu idle 0–51% (never ≥90%), load1
  18.8–70.2 on 10 CPUs, late-tick spike to 70. J-B measurement deferred,
  no compiler change, control unchanged. Next tick unchanged from tick 9.
- 2026-09-05 21:27 JST tick 11 (JIT): quiet gate failed a 10th consecutive
  time — load1 83–132 on 10 CPUs across probes (21:11, 21:13, 21:18, 21:20,
  21:27; iostat cpu idle 22–43% at 21:16, never near the required ≥90%).
  J-B measurement deferred again, no compiler change, control unchanged at
  `bench/runtime-comparison/jb_imod_control.c`. Next tick unchanged: on a
  quiet host run 4000000 iters × 24 alternations, ratio of medians, then
  add the third (non-inlined mulh) arm to separate lever 1 from lever 2.

- 2026-09-05 22:25 JST tick 12 (JIT): quiet gate failed an 11th consecutive
  time — 20 iostat samples: cpu idle 36–60% (never ≥90%), load1 17.3–32.6 on
  10 CPUs (slowly falling through the tick; heavy host also slowed terminal
  commands to multi-second latency). J-B measurement deferred, no compiler
  change, control unchanged at bench/runtime-comparison/jb_imod_control.c.
  Next tick unchanged: on a quiet host (idle ≥90%) run 4000000 iters × 24
  alternations, ratio of medians, then add the third (non-inlined mulh) arm
  to separate lever 1 from lever 2.

## Policy note (standing)

Any JIT-form claim needs a warmup/steady-state measurement-boundary decision in
`perfgate` — changes go through an ADR draft; **no sealed claim before human
approval**. Current verdicts above are diagnostics, not claims.

## Tick log (appended)

- 2026-09-05 23:21 JST tick 13 (JIT): quiet gate failed a 12th consecutive
  time — load1 6.7–12.6 on 10 CPUs (best of the 13 ticks so far but still
  not quiet), iostat cpu idle 43–72% across probes (23:12, 23:19–23:20),
  never ≥90%. Additional finding: terminal sessions on this host are being
  killed mid-run (~10–240 s), so long probe loops and the J-B measurement
  cannot complete in one session even if the gate opens; the J-B rerun needs
  (a) idle ≥90% and (b) probes surviving >5 min. J-B deferred, no compiler
  change, control unchanged at bench/runtime-comparison/jb_imod_control.c.
  Next tick unchanged: on a quiet host run 4000000 iters × 24 alternations,
  ratio of medians, then add the third (non-inlined mulh) arm.

- 2026-09-05 23:52 JST tick 14 (JIT): quiet gate failed a 13th consecutive
  time — load1 12.6-27.5 on 10 CPUs across probes (23:43, 23:46, 23:49,
  23:52; a late spike to 27.5), iostat cpu idle 10-55%, never >=90%.
  J-B measurement deferred, no compiler change, control unchanged at
  bench/runtime-comparison/jb_imod_control.c. Cross-check: ADR 0335/0338
  (amu-rank ticks) record the same J-B C proxy with 14 consecutive positive
  runs (+6.2..+7.8%, five windows); consistent with ours, still diagnostic
  only (full quiet gate never met there either). Next tick unchanged; ADR
  0335 step 2 (real kotoba-native lowering specialization + perfgate on a
  fully quiet host) is now the overdue lever and belongs to the AOT axis.
