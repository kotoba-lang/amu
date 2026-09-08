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

- 2026-09-06 03:50 JST tick 15 (JIT): quiet gate failed a 14th consecutive
  time — load1 3.7–7.2 on 10 CPUs (best of the series so far, but 15m avg
  still 16–20), iostat cpu idle 46–66% across two probes ~6 min apart,
  never near the required ≥90%. Host also showed the known instability
  (commands intermittently hanging past 60 s, background-run outputs not
  landing), so even beyond idle the window is not trustworthy for J-B.
  J-B measurement deferred, no compiler change, control unchanged at
  bench/runtime-comparison/jb_imod_control.c. Next tick unchanged: on a
  quiet host (idle ≥90%) run 4000000 iters × 24 alternations, ratio of
  medians, then add the third (non-inlined mulh) arm.

- 2026-09-06 07:05 JST tick 16 (JIT): quiet gate failed a 15th consecutive
  time — load1 27.8–70.4 on 10 CPUs across probes (06:53–06:59), iostat cpu
  idle 34–47% across ~28 samples, never ≥90% (host busy: several terminal
  probes timed out past 60–180 s before producing output). J-B measurement
  deferred, no compiler change, control unchanged at
  bench/runtime-comparison/jb_imod_control.c. Next tick unchanged: on a
  quiet host (idle ≥90%) run 4000000 iters × 24 alternations, ratio of
  medians, then add the third (non-inlined mulh) arm.

- 2026-09-06 07:53 JST tick 17 (JIT): quiet gate failed a 16th consecutive
  time — load1 33–69 on 10 CPUs (15m avg ~67, heavy host; this tick the host
  was so loaded that `uptime` foreground calls returned empty output and
  shell commands timed out at 60–300 s; probes succeeded only via
  redirect-to-file), iostat cpu idle 29–47% across ~65 samples over ~8 min,
  never ≥90%. J-B measurement deferred, no compiler change, control unchanged
  at bench/runtime-comparison/jb_imod_control.c. Next tick unchanged: on a
  quiet host (idle ≥90%) run 4000000 iters × 24 alternations, ratio of
  medians, then add the third (non-inlined mulh) arm.

- 2026-09-06 10:04 JST tick 18 (JIT): quiet gate failed a 17th consecutive
  time — load1 18.6-21.3 on 10 CPUs, iostat cpu idle 33-59% across two
  probes ~2 min apart (10:01, 10:03), never >=90%. J-B measurement deferred,
  no compiler change, control unchanged at
  bench/runtime-comparison/jb_imod_control.c. Next tick unchanged: on a
  quiet host (idle >=90%) run 4000000 iters x 24 alternations, ratio of
  medians, then add the third (non-inlined mulh) arm.

- 2026-09-06 11:13 JST tick 19 (JIT): quiet gate failed an 18th consecutive
  time — load1 25.6-26.1 on 10 CPUs (15m avg ~51, falling trend), iostat cpu
  idle 46-52% across 3 samples, never near the required >=90%. J-B
  measurement deferred, no compiler change, control unchanged at
  bench/runtime-comparison/jb_imod_control.c. Next tick unchanged: on a
  quiet host (idle >=90%) run 4000000 iters x 24 alternations, ratio of
  medians, then add the third (non-inlined mulh) arm.

- 2026-09-06 12:45 JST tick 20 (JIT): quiet gate failed a 19th consecutive
  time — 6 probes over ~27 min (12:11-12:38), load1 9.9-18.7 on 10 CPUs
  (15m avg 14-16, stable), iostat cpu idle 22-65%, never >=90% (best window
  12:17-12:23: idle 54-65%). J-B measurement deferred, no compiler change,
  control unchanged at bench/runtime-comparison/jb_imod_control.c. Note:
  terminal output was again intermittently empty this tick (uptime/ls
  returned nothing; probes succeeded via redirect-to-file) — the known host
  instability persists, so even the 65%-idle window is not trustworthy for
  the rerun. Next tick unchanged: on a quiet host (idle >=90%) run 4000000
  iters x 24 alternations, ratio of medians, then add the third
  (non-inlined mulh) arm.

- 2026-09-07 10:55 JST tick 21 (JIT): quiet gate failed a 20th consecutive
  time — load1 25.5-92.8 on 10 CPUs across probes (10:42-10:54, rising
  through the tick), iostat cpu idle 25-61% across ~34 samples in two
  windows (10:43-10:44, 10:47-10:52), never >=90%. Diagnostic partial J-B
  runs completed anyway to keep the control alive: 400000 iters x 24
  alternations twice (10:53, 10:54), saving +6.9% then +2.1% (21.7/20.2 and
  14.1/13.8 ns/elem; both checksum-agreeing, arm-A sdiv disassembly-verified).
  Magnitude swings ~3x between runs under load — NOT qualify-eligible, no
  perfgate verdict, hypothesis neither killed nor confirmed. Sign pattern
  consistent with ADR 0335/0338 (all-positive there, +6.2..+7.8%) but load
  numbers cannot bound the effect. J-B deferred; no compiler change; control
  unchanged at bench/runtime-comparison/jb_imod_control.c (rebuilt clean from
  source this tick, BUILD_OK). Next tick unchanged: on a quiet host (idle
  >=90%) run 4000000 iters x 24 alternations, ratio of medians, then add the
  third (non-inlined mulh) arm.

- 2026-09-07 11:55 JST tick 22 (JIT): **lever-split done - J-B's mechanism
  attribution falsified (measurement itself still under-qualified).** Quiet
  gate failed a 21st consecutive time (probe 11:42: load1 33.9-35.9, iostat
  cpu idle 7-28% over 12 samples; 11:54 during runs: load1 20.0-21.7), so
  numbers below are sign-only diagnostics, NOT qualify-eligible and no
  perfgate verdict. Built the planned third arm as a 4-arm control
  `bench/runtime-comparison/jb_imod_control_4arms.c` (sealed 2-arm control
  untouched; disassembly-verified shapes: imod_opaque = sdiv, imod_const =
  smulh+asr, arm_opaque_inl = inline sdiv with 0 bl, arm_const_inl = inline
  smulh+asr with 0 sdiv). 3 runs at load1 ~20-22, 400000 iters x 12 rotated
  alternations, 4-arm checksum agreement (764266) every run:
  lever1 A->B (constant divisor only) +9.5/+14.8/+11.6%;
  lever2 A->C (inlining only, sdiv KEPT) +21.3/+26.9/+22.4%;
  both A->D +9.8/+16.0/+11.6%.
  Decisive pattern, repeated 3/3: B ~= D (marginal lever2 on the const arm
  -0.0/+0.3/+1.3% ~ noise) and D < C (adding the constant-divisor fold ON
  TOP of inlining makes it 12-16% SLOWER).
  Reading: on this latency-bound serial chain the dominant term is the
  helper CALL, not the sdiv; once the call is inlined, divisor
  specialization contributes nothing measurable (the mulh+asr guard shape
  even costs slightly more than the volatile-modulo fast path). The saving
  attributed to J-B ("runtime constant-divisor specialization recovers
  >=5%") is not attributable to that mechanism: the same A->B delta is
  reachable without divisor specialization at all (just inline imod), and
  the bigger prize (2-3x lever1) is inlining itself. J-B's A-vs-B number
  remains reproducible (= the sealed control, consistent with ADR
  0335/0338/0339 +6.2..+7.8% idle windows) but its causal story is dead at
  the proxy level.
  Consequence for the ladder: the next hand-patch/implementation lever
  should be **imod helper inlining at the call site** (J-B2 candidate for
  amu-rank to rank; rule-5 composition: inlining subsumes where the 5%
  actually lives), with divisor specialization demoted to
  "same-delta-by-a-different-mechanism". No compiler change, no sealed
  claim, perfgate untouched; status rewrite belongs to amu-rank.
  Next tick: on a quiet host (idle >=90%) re-run the 4-arm at 4000000 x 24,
  ratio of medians, separated spreads, to put numbers on lever2.


- 2026-09-07 13:06 JST tick 23 (JIT): **planned full-size 4-arm rerun
  COMPLETED (4000000 x 24, ratio of medians), but the quiet gate failed a
  22nd consecutive time — load1 24.9 at 12:52, 21.1–21.9 across the run
  window (13:04–13:06), iostat cpu idle 32–67%, never >=90%. Numbers below
  are diagnostics, NOT qualify-eligible, no perfgate verdict.**
  Rebuilt /tmp/jb4 from the untouched tick-22 control
  (jb_imod_control_4arms.c sha256 a025ed9b...e3c108); disassembly
  re-verified this tick: arm_opaque/arm_const = bl to imod_opaque (sdiv) /
  imod_const (smulh+asr); arm_opaque_inl = inline sdiv+msub, 0 bl;
  arm_const_inl = inline smulh+asr+msub+csel, 0 sdiv. Single run
  13:04:13–13:06:00, 4-arm checksum agreement (764266) on every
  alternation; medians A 5.521 / B 4.978 / C 4.362 / D 4.962 ns/elem.
  lever1 (A->B) +9.8% | lever2 (A->C) +21.0% | both (A->D) +10.1% |
  B->D (marginal lever2 on const) +0.3% | C->D (marginal lever1 on inl)
  -13.7%.
  Reading: at full size the tick-22 attribution holds — lever2 (helper-call
  inlining) is ~2.1x lever1 (constant-divisor fold); B ~= D, and C beats
  both B and D, i.e. the same A->B saving is reachable without divisor
  specialization at all. J-B's mechanism attribution stays FALSIFIED;
  J-B2 (imod helper inlining at the call site) stays the candidate for
  amu-rank to rank. CAVEAT on the C-vs-D gap: its sign/magnitude is NOT
  stable across ticks (tick 22 small-size marginal lever1 on inl:
  -0.0/+0.3/+1.3%; tick 23 full-size: -13.7%, single run) — under-load
  ordering of C vs D cannot be quoted as an effect size, only the robust
  C > B > A / D ~= B pattern is.
  Structural ceiling note: 22 consecutive busy ticks over ~45 h (never
  >=90% idle, best observed ~67%) plus recurring terminal-output loss mean
  the full quiet-gate separated-spread rerun may be unachievable on this
  host under the current gate. Flagged for an environment decision (same
  class as the J-A note); does not block sign-level diagnostics.
  No compiler change, no sealed claim, perfgate untouched, controls
  unchanged (2-arm sealed control + tick-22 4-arm control).
  Next tick: quiet-gate probe first; if open, re-run 4000000 x 24 twice to
  test whether lever2's +21% separates (median ratio + spread).

- 2026-09-08 09:00 JST tick 24 (JIT): **J-A premise REVISED — the "not
  actionable here" environment finding is superseded.** The tick-1 note said
  no Chicory host exists in the org; that holds for the repo (deps.edn has no
  chicory coord) but the jars ARE on this workstation:
  ~/.m2/repository/com/dylibso/chicory/{wasm,runtime}/1.7.5 (+1.4.0),
  pure-JVM interpreter, zero non-test transitive deps. Functional smoke
  built and run this tick (javac + java -cp against the sealed
  bench/runtime-comparison/kernel.kotoba.wasm, sha256 5be27a87...cb30ac91,
  imports=[] so no host fakes needed):
  chicory kernel(100) -> 110550153 == V8 kernel(100n) -> 110550153
  (CHICORY_HOST_FUNCTIONAL_CHECKSUM_OK), and the fuel/trap model matches
  (calls_until_trap = 512 on BOTH hosts). J-A is therefore actionable on
  this box without any environment decision; the tick-1 blocker was
  search-scope (repo-only), not infrastructure.
  Rough order-of-magnitude probe (slope ns/call vs n; host load1 132->18
  DURING the run, quiet gate failed a 23rd consecutive time — iostat idle
  16-54% at 08:42, 23-79% at 08:59; never a full >=90% window, so NOT
  qualify-eligible): chicory n=0/50/200 medians 27.5/26.1/29.8 us/call
  under the load-130 regime; n=800 point 1.7 us/call measured after load
  fell — magnitude unstable across the tick, do NOT quote as effect size.
  V8 same-fixture medians 208-375 ns/call, flat in n (call-overhead-
  dominated). The only load-robust statement: interpreter per-call cost is
  ~2-3 orders of magnitude above V8's on identical checksum-agreeing output
  — far outside the observed ~2x load noise. An interpreter-dispatch-
  dominated regime exists and is measurable here.
  Harness note for a real J-A share measurement: fuel is module-private so
  a fresh Instance is required per call (same rule as the sealed V8
  runner's max-calls-per-instance calibration); Parser.parse+Instance.build
  cost must sit outside the timed region; dispatch share needs in-loop op
  counting (ExecutionListener exists in runtime-1.7.5.jar), not wall slope.
  No compiler change, no sealed claim, perfgate untouched, controls
  unchanged (2-arm sealed + 4-arm a025ed9b...). J-B rerun stays deferred.
  Suggested for amu-rank: J-A status rewrite (not-actionable -> open).
  Next tick: quiet-gate probe first; if open run J-B 4-arm 4000000 x 24
  twice; if busy, build the chicory ExecutionListener dispatch-share
  harness so it is ready for the first quiet window.
