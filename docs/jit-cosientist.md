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

  **UPDATE 2026-09-04 20:2x JST, tick 7 (JIT): tick-1 premise falsified.**
  `orgs/kotoba-lang/kotoba/deps.edn:107-108` pins `com.dylibso.chicory/wasm`
  + `runtime` 1.7.5, and `kotoba/test/kotoba/wasm_exec_test.clj` (595 lines)
  executes emitted kotoba wasm modules through Chicory (including kgraph
  host-import effects). The tick-1 repo-wide search that concluded
  "no chicory anywhere" was incomplete — the hit it found was in
  `kotoba-lang-security-hardening/lang/value-codec.edn:376` and the real
  dependency lives in the `kotoba` repo. J-A is therefore **actionable**:
  a chicory-host dispatch-share measurement can be built on
  `kotoba.wasm-exec/run-main` + the runtime-comparison kernel fixtures.
  Not measured this tick: host failed the quiet gate (load1 23–34 on
  10 CPUs, iostat idle 0–11%, persistent JVM/bb fleet processes, 7th
  consecutive busy tick) — a JVM-based chicory bench under load would be
  unqualified anyway.

## Population

| ID | hypothesis | status | evidence |
|---|---|---|---|
| J-A | Chicory interpreter dispatch dominates the wasm hot-loop cost; measure its share as the JIT premise | **not actionable here** — no chicory host in the org; this workstation's wasm path is V8 (tiered), so the share would measure V8 tiering, not interpreter dispatch | 2026-09-03: search + runner source inspection. Needs an environment decision before any measurement can mean "interpreter dispatch". 2026-09-04 20:2x JST tick 7 (JIT) evidence: **tick-1 premise falsified** — `orgs/kotoba-lang/kotoba/deps.edn:107-108` pins `com.dylibso.chicory/wasm`+`runtime` 1.7.5 and `kotoba/test/kotoba/wasm_exec_test.clj` (595 lines) runs emitted kotoba wasm through Chicory (incl. kgraph host-import effects); the tick-1 search missed the `kotoba` repo dependency. Status cell intentionally left to rank; a chicory-host dispatch-share measurement IS buildable here (`kotoba.wasm-exec/run-main` + runtime-comparison kernel fixtures). Harness not built this tick; host failed quiet gate (load1 23–34/10 CPUs, idle 0–11%, 7th consecutive busy tick). 2026-09-04 21:2x–22:0x JST tick 8 (JIT): quiet gate failed an 8th consecutive time (load1 21.7–33.2 on 10 CPUs, iostat idle 0–1%, probes 90–120s apart) — **no qualified verdict possible this tick; all numbers below are loaded-host diagnostics, labeled as such.** (1) **J-A harness built and smoke-run** (`bench/runtime-comparison/ja_chicory_probe.clj` + `ja_persist_kernel.clj` + precompiled `ja_kernel_wasm.edn`, 764-byte wasm of `kernel.kotoba`, JVM route like the existing wasm_exec_test suite — not a Q9 route). Loaded-host numbers, n=200: instantiation 257–590 ms; per-`kernel`-call cost through chicory ≈ **660–1285 µs/call**, essentially flat vs call count (calls=1: 744 µs; calls=500: 660–1285 µs) → the interpreter per-call cost, not the Clojure host-bridge, dominates. Native/V8 reference: kernel ≈13 ns/call (runtime-comparison) → chicory interpreter is ~5 orders of magnitude slower per call under load. Quiet-host rerun (J-A verdict + dispatch-share decomposition) is next tick's first action when idle ≥9/10. (2) **J-B loaded-host rerun, unqualified, sign still flips**: `/tmp/jb_imod 200000 40` at load1 32–33 → saving **+15.2% / −26.3% / −1.0%** (40-alternation medians, checksums agree). J-B remains neither killed nor confirmed. |
| J-B | Runtime constant-divisor specialization of the shared `imod` (ADR 0289 residual, ~165 sdiv/call) recovers ≥5% | open — **hand-patch run, unqualified** | 2026-09-03: C control `/tmp/jb-imod` (saved as `bench/runtime-comparison/jb_imod_control.c`), serial chain `acc = imod(acc*31+v[i], M)`, arm A opaque divisor (real `sdiv`, disassembly-verified) vs arm B constant divisor (smulh+asr), both checksum-agreeing. Three runs at load1 16–27 (10 CPUs): saving **−7.8% / +3.8% / −4.7%** — sign flips between runs. Host never met the quiet gate (≥1 idle CPU); perfgate would fail closed. Verdict: **measurement under-qualified, hypothesis neither killed nor confirmed.** The ratio bound suggests the sdiv→mulh term alone is ≲5% of element cost *under load*, but quiet-host numbers are required (expected sdiv latency ~10 cycles on the serial chain could make the real saving much larger than any run above shows). Next: rerun when idle ≥ 9/10 CPUs, 4000000 iters × 24 alternations, ratio of medians. 2026-09-03 tick 2 (JIT): rerun attempted, host again failed the quiet gate (load 16–20 on 10 CPUs, iostat idle 0–4%) — measurement deferred, still neither killed nor confirmed. 2026-09-03 tick 3 (JIT): rerun again deferred — host load 23–28 on 10 CPUs, idle 0–1.6% (two probes 90s apart); third consecutive busy tick. Control remains at bench/runtime-comparison/jb_imod_control.c; measurement is next tick's first action when quiet gate passes. 2026-09-03 tick 4 (JIT): quiet gate failed a 4th consecutive time (load 13–21 on 10 CPUs, top idle 0–1.7%, two probes 2 min apart) — J-B measurement again deferred, no compiler change made. 2026-09-04 10:42 JST tick 5 (JIT): quiet gate failed a 5th consecutive time — load1 31–34 on 10 CPUs, iostat idle 0–1.7% (20 samples), no idle CPU. Control unchanged; measurement is next tick's first action when idle ≥9/10. 2026-09-04 11:43 JST tick 6 (JIT): quiet gate failed a 6th consecutive time — load1 43.6–45.8 on 10 CPUs, iostat idle 0–25% (5 samples, 0% on 4/5), no idle CPU. J-B measurement again deferred; control unchanged, no compiler change made. 2026-09-04 20:2x JST tick 7 (JIT): quiet gate failed a 7th consecutive time — load1 23.1–34.6 on 10 CPUs, iostat idle 0–11% across probes 4 min apart; persistent fleet JVM (PID 2666, up since 08:52) and bb agents are the load. J-B still deferred; nothing killed, nothing confirmed. |
| J-C | wasm host crossings (H-Y1: 2.03/element, ADR 0285) are removable by JIT-side inlining | open — not started | AOT lowering lever (widen `structured-loop-body?`) may precede any JIT work; do not start until J-B has a quiet-host verdict. |

## Policy note (standing)

Any JIT-form claim needs a warmup/steady-state measurement-boundary decision in
`perfgate` — changes go through an ADR draft; **no sealed claim before human
approval**. Current verdicts above are diagnostics, not claims.
