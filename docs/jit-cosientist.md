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
| J-B | Runtime constant-divisor specialization of the shared `imod` (ADR 0289 residual, ~165 sdiv/call) recovers ≥5% | open — **hand-patch run, unqualified** | 2026-09-03: C control `/tmp/jb-imod` (saved as `bench/runtime-comparison/jb_imod_control.c`), serial chain `acc = imod(acc*31+v[i], M)`, arm A opaque divisor (real `sdiv`, disassembly-verified) vs arm B constant divisor (smulh+asr), both checksum-agreeing. Three runs at load1 16–27 (10 CPUs): saving **−7.8% / +3.8% / −4.7%** — sign flips between runs. Host never met the quiet gate (≥1 idle CPU); perfgate would fail closed. Verdict: **measurement under-qualified, hypothesis neither killed nor confirmed.** The ratio bound suggests the sdiv→mulh term alone is ≲5% of element cost *under load*, but quiet-host numbers are required (expected sdiv latency ~10 cycles on the serial chain could make the real saving much larger than any run above shows). Next: rerun when idle ≥ 9/10 CPUs, 4000000 iters × 24 alternations, ratio of medians. 2026-09-03 tick 2 (JIT): rerun attempted, host again failed the quiet gate (load 16–20 on 10 CPUs, iostat idle 0–4%) — measurement deferred, still neither killed nor confirmed. 2026-09-03 tick 3 (JIT): rerun again deferred — host load 23–28 on 10 CPUs, idle 0–1.6% (two probes 90s apart); third consecutive busy tick. Control remains at bench/runtime-comparison/jb_imod_control.c; measurement is next tick's first action when quiet gate passes. 2026-09-03 tick 4 (JIT): quiet gate failed a 4th consecutive time (load 13–21 on 10 CPUs, top idle 0–1.7%, two probes 2 min apart) — J-B measurement again deferred, no compiler change made. 2026-09-04 10:42 JST tick 5 (JIT): quiet gate failed a 5th consecutive time — load1 31–34 on 10 CPUs, iostat idle 0–1.7% (20 samples), no idle CPU. Control unchanged; measurement is next tick's first action when idle ≥9/10. 2026-09-04 11:43 JST tick 6 (JIT): quiet gate failed a 6th consecutive time — load1 43.6–45.8 on 10 CPUs, iostat idle 0–25% (5 samples, 0% on consecutive probes). J-B measurement again deferred, no compiler change; awaiting idle ≥9/10. 2026-09-04 12:58 JST tick 7 (falsify): quiet gate failed a 7th time — load1 40.3–44.9 on 10 CPUs, iostat idle 0–7% (10 samples, two probes 3 min apart); J-B measurement deferred again, no compiler change. Awaiting the idle ≥9/10 rerun; J-C blocked behind it. 2026-09-05 08:39 JST tick 7 (falsify): quiet gate failed again - load1 57.91 / 5m 53.61 / 15m 56.51 (up 1:22, 10 CPUs); no measurement attempted, no compiler change. J-B remains confirmed-diagnostic (14 consecutive positive windows) but unqualified, awaiting the idle>=9/10 rerun; J-C blocked behind it. 2026-09-05 09:14 JST tick 8 (JIT): quiet gate failed again — load1 49.7–54.2 on 10 CPUs, iostat cpu idle 22–54% across 5 samples, no idle CPU, probes ~6 min apart. J-B measurement again deferred, no compiler change. Control unchanged at bench/runtime-comparison/jb_imod_control.c; next tick's first action is the idle>=9/10 rerun (4000000 iters × 24 alternations, ratio of medians), then J-C. (2026-09-05 09:55 JST tick 9 JIT: quiet gate failed again — load1 19.2 at 09:42, 22.5 at 09:52, top idle 39–44% but no idle CPU, java ~186% CPU; measurement deferred. Source-inspection result, no quiet host needed: J-B premise re-verified on origin tree — bench/runtime-comparison/kernel_collections.kotoba defines imod as a user function with the divisor a runtime parameter, so constant-divisor specialization requires inlining+constant-fold (AOT) or runtime callee specialization (JIT). ADR 0289 ranks inlining small user functions ABOVE constant-divisor strength reduction; the J-B hand-patch arm (const divisor, inlined by the C compiler) therefore measures levers 1+2 combined and the lever-2-only saving may be smaller than the +6.2–7.8% diagnostic runs suggest. No compiler change. Next: on quiet host add a third arm (non-inlined mulh shape) to separate lever 1 from lever 2.)

## Tick log (falsify — appended evidence notes)

- 2026-09-05 11:15 JST tick 9 (JIT): quiet gate failed an 8th consecutive time
  — load1 16.4–23.5 on 10 CPUs (falling trend through the tick), iostat cpu
  idle 65–79% across probes ~3 min apart, below the required ≥90%.
  J-B measurement again deferred, no compiler change, control unchanged at
  `bench/runtime-comparison/jb_imod_control.c`. Next: on a quiet host add the
  third (non-inlined mulh) arm to separate lever 1 from lever 2.

- 2026-09-05 12:20 JST tick 10 (JIT): quiet gate failed a 9th consecutive
  time — load1 21.0–21.7 on 10 CPUs, iostat cpu idle 50–73% (3 samples),
  below the required ≥90%. Top consumers: hermes gateway, WindowServer, and
  a stray `git merge` in /tmp/gp-pr495. J-B measurement again deferred, no
  compiler change, control unchanged at `bench/runtime-comparison/jb_imod_control.c`.
  Note: working tree has unrelated uncommitted changes (atomic_output.clj +
  13 test files) from another role — left untouched per cowork discipline.

## Policy note (standing)

Any JIT-form claim needs a warmup/steady-state measurement-boundary decision in
`perfgate` — changes go through an ADR draft; **no sealed claim before human
approval**. Current verdicts above are diagnostics, not claims.
