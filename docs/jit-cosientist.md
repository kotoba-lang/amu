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
| J-B | Runtime constant-divisor specialization of the shared `imod` (ADR 0289 residual, ~165 sdiv/call) recovers ≥5% | open — **hand-patch run, unqualified** | 2026-09-03: C control `/tmp/jb-imod` (saved as `bench/runtime-comparison/jb_imod_control.c`), serial chain `acc = imod(acc*31+v[i], M)`, arm A opaque divisor (real `sdiv`, disassembly-verified) vs arm B constant divisor (smulh+asr), both checksum-agreeing. Three runs at load1 16–27 (10 CPUs): saving **−7.8% / +3.8% / −4.7%** — sign flips between runs. Host never met the quiet gate (≥1 idle CPU); perfgate would fail closed. Verdict: **measurement under-qualified, hypothesis neither killed nor confirmed.** The ratio bound suggests the sdiv→mulh term alone is ≲5% of element cost *under load*, but quiet-host numbers are required (expected sdiv latency ~10 cycles on the serial chain could make the real saving much larger than any run above shows). Next: rerun when idle ≥ 9/10 CPUs, 4000000 iters × 24 alternations, ratio of medians. 2026-09-03 tick 2 (JIT): rerun attempted, host again failed the quiet gate (load 16–20 on 10 CPUs, iostat idle 0–4%) — measurement deferred, still neither killed nor confirmed. 2026-09-03 tick 3 (JIT): rerun again deferred — host load 23–28 on 10 CPUs, idle 0–1.6% (two probes 90s apart); third consecutive busy tick. Control remains at bench/runtime-comparison/jb_imod_control.c; measurement is next tick's first action when quiet gate passes. 2026-09-03 tick 4 (JIT): quiet gate failed a 4th consecutive time (load 13–21 on 10 CPUs, top idle 0–1.7%, two probes 2 min apart) — J-B measurement again deferred, no compiler change made. 2026-09-04 10:42 JST tick 5 (JIT): quiet gate failed a 5th consecutive time — load1 31–34 on 10 CPUs, iostat idle 0–1.7% (20 samples), no idle CPU. Control unchanged; measurement is next tick's first action when idle ≥9/10. 2026-09-04 11:43 JST tick 6 (JIT): quiet gate failed a 6th consecutive time — load1 43.6–45.8 on 10 CPUs, iostat idle 0–25% (5 samples, 0% on best). Measurement deferred. Control unchanged. 2026-09-04 12:14 JST tick 7 (JIT): quiet gate failed a 7th consecutive time — load1 14.5–17.9 on 10 CPUs, iostat idle 0–8% (10 samples). Measurement deferred, no compiler change, control unchanged. 2026-09-04 12:48 JST tick 8 (JIT): quiet gate failed an 8th consecutive time — load1 11.6–14.3 on 10 CPUs (falling trend), iostat cpu idle 6–18% across 10 samples, never ≥90%. J-B measurement deferred, no compiler change, control unchanged at bench/runtime-comparison/jb_imod_control.c. Next: on a quiet host run 4000000 iters × 24 alternations, ratio of medians, then add the third (non-inlined mulh) arm to separate lever 1 from lever 2. 2026-09-04 13:24 JST tick 9 (JIT): quiet gate failed a 9th consecutive time — load1 12.3–16.5 on 10 CPUs, iostat cpu idle 2–14% across 10 samples. J-B measurement deferred, no compiler change, control unchanged. Next tick unchanged.

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

- 2026-09-09 20:50 JST tick 15 (JIT): quiet gate failed a 14th consecutive
  time — load1 16.4–49.9 on 10 CPUs (uptime 19.46/49.91/70.09 at 20:50,
  falling to ~17–25 through the tick), iostat cpu idle 0–43% across ~55
  samples, never >=90%. J-B measurement deferred, no compiler change,
  control unchanged at bench/runtime-comparison/jb_imod_control.c.
  Note: terminal commands over ~60s were killed/timed out this tick, so
  even if the gate opened, the 4000000-iter x 24-alternation run would need
  a background session. Next tick unchanged: quiet host -> ratio of medians,
  then third (non-inlined mulh) arm.

- 2026-09-17 (JIT tick 16): quiet gate failed a 15th consecutive time -
load1 14.5-25.1 on 10 CPUs (falling through the tick; vm.loadavg
25.08/19.10/17.61 at probe start), iostat cpu idle 1-31 percent across
~62 samples over ~5 min, never >=90 percent. J-B measurement deferred,
no compiler change, control unchanged at
bench/runtime-comparison/jb_imod_control.c. Terminal-note: this tick the
terminal backend returned empty stdout for foreground commands (exit 0,
no output) and hung >3 min on trivial commands; only file-redirected
background commands produced data (/tmp/jit-probe.txt, /tmp/jit-iostat.txt).
Next tick unchanged: on a quiet host (idle >=90 percent) run 4000000 iters
x 24 alternations, ratio of medians, then add the third (non-inlined
mulh) arm.

- 2026-09-17 (JIT tick 17): quiet gate COULD NOT BE MEASURED — the terminal
  backend again returned empty stdout (exit 0, no output) for `date`/`uptime`
  foreground probes and for a file-redirected probe (/tmp/jit-tick17-load.txt;
  cat and stat both empty), so no load or idle number was obtainable this
  tick, and the run budget ran out before an alternative read path completed.
  Per the no-fabrication rule no verdict is recorded: J-B stays open, neither
  killed nor confirmed, gate status = unmeasured (not "failed"). No compiler
  change, control unchanged at bench/runtime-comparison/jb_imod_control.c.
  Next tick unchanged: first action = obtain a load/idle reading by any
  surviving path (if the terminal stays dead, record gate=unmeasured again);
  on a quiet host (idle >=90 percent) run 4000000 iters x 24 alternations,
  ratio of medians, then add the third (non-inlined mulh) arm.


- 2026-09-17 18:56 JST tick 18 (JIT): read path restored — terminal stdout is
  still empty but file-redirected commands land. Quiet gate failed a 16th
  consecutive time — load1 12.9–14.7 on 10 CPUs (load avg 9.53/9.25/10.25 at
  18:48 rising to 14.74/16.02/13.47 at 18:54), iostat cpu idle 16–31 percent
  across 6 samples, never >=90 percent. J-B measurement deferred, no compiler
  change, control unchanged at bench/runtime-comparison/jb_imod_control.c.
  Measurement pipeline is otherwise ready (redirected file I/O works); next
  tick: if idle >=90 percent, run 4000000 iters x 24 alternations via a
  file-redirected background session, ratio of medians, then add the third
  (non-inlined mulh) arm.

- 2026-09-18 15:05 JST tick 19 (JIT): quiet gate failed a 17th consecutive
  time — load1 13.2–15.1 on 10 CPUs (vm.loadavg 13.22/14.24/15.12 then
  14.93/14.31/14.99 across two probes ~3 min apart), iostat cpu idle 0–29
  percent across 10 samples, never >=90 percent. J-B measurement deferred,
  no compiler change, control unchanged at
  bench/runtime-comparison/jb_imod_control.c. Terminal-note: terminal
  stdout again empty for foreground commands; file-redirected commands
  land (pipeline unchanged from tick 18). Next tick unchanged: if idle
  >=90 percent, run 4000000 iters x 24 alternations via file-redirected
  background session, ratio of medians, then add the third (non-inlined
  mulh) arm.

- 2026-09-18 06:52 JST tick 20 (JIT): quiet gate failed an 18th consecutive
time - probe 1 at 06:43: load1 13.98 (5m 13.47), iostat cpu idle 8-29
percent (5 samples). Probe 2 at 06:46 (3 min later): load1 RISING to
28.42/18.30/14.94, idle 0-29 percent. Never >=90 percent; host getting
busier through the tick. J-B measurement deferred, no compiler change,
control unchanged at bench/runtime-comparison/jb_imod_control.c. Next
tick unchanged: if idle >=90 percent, run 4000000 iters x 24 alternations
via file-redirected background session, ratio of medians, then add the
third (non-inlined mulh) arm.

- 2026-09-18 12:47 JST tick 21 (JIT): quiet gate failed a 19th consecutive
  time — load1 13.0-15.5 on 10 CPUs (probes 12:42, 12:43, 12:46 JST),
  iostat cpu idle 0-29 percent across 9 samples over two probes ~4 min
  apart, never >=90 percent. Read path still degraded: raw terminal stdout
  empty; file-redirected probes land. J-B measurement deferred, no compiler
  change, control unchanged at bench/runtime-comparison/jb_imod_control.c.
  Next tick unchanged: if idle >=90 percent, run 4000000 iters x 24
  alternations via file-redirected background session, ratio of medians,
  then add the third (non-inlined mulh) arm.

- 2026-09-18 18:49 JST tick 22 (JIT): quiet gate failed a 20th consecutive
time - load1 11.1-18.3 on 10 CPUs (probe 18:49:12 JST, 20 iostat samples),
cpu idle 49-84 percent across samples, never >=90 percent; load mild but
not quiet. Read path: foreground terminal stdout still empty;
file-redirected background commands land. J-B measurement deferred, no
compiler change, control unchanged at
bench/runtime-comparison/jb_imod_control.c. Next tick unchanged: if idle
>=90 percent, run 4000000 iters x 24 alternations via file-redirected
background session, ratio of medians, then add the third (non-inlined
mulh) arm.

- 2026-09-19 00:47 JST tick 23 (JIT): quiet gate failed a 21st consecutive
time - probe 1 at 00:43:51 JST: load1 11.66 (5m 16.83), iostat cpu idle
47-55 percent (6 samples). Probe 2 at 00:47:23 JST (~3.5 min later):
load1 RISING to 36.0/23.2/24.6, idle 46-49 percent. Never >=90 percent;
host getting busier through the tick. Read path this tick: file-redirected
foreground probes land (grouped-compound commands are now blocked by the
security scanner; separate redirected commands work). J-B measurement
deferred, no compiler change, control unchanged at
bench/runtime-comparison/jb_imod_control.c. Next tick unchanged: if idle
>=90 percent, run 4000000 iters x 24 alternations via file-redirected
background session, ratio of medians, then add the third (non-inlined
mulh) arm.

- 2026-09-19 06:47 JST tick 24 (JIT): quiet gate failed a 22nd consecutive
  time - probe 1 at 06:43:08 JST: load1 28.21 (5m 32.27, 15m 34.67).
  Probe 2 at 06:45 (~2 min later): load1 29.54/30.53/33.51, iostat cpu
  idle 44-53 percent across 3 samples. Never >=90 percent; host flat-busy
  (load ~29-30 on 10 CPUs across both probes, not falling). Read path
  healthy this tick (foreground probes returned; long iostat loops time
  out >30 s - use short "-c 3" probes). J-B measurement deferred, no
  compiler change, control unchanged at
  bench/runtime-comparison/jb_imod_control.c. Next tick unchanged: if idle
  >=90 percent, run 4000000 iters x 24 alternations via file-redirected
  background session, ratio of medians, then add the third (non-inlined
  mulh) arm.

- 2026-09-19 12:48 JST tick 25 (JIT): quiet gate failed a 23rd consecutive
  time - probe 1 at 12:42 JST: load1 43.89 (5m 33.67), iostat cpu idle
  46-55 percent (3 samples). Probe 2 at 12:45 (~3 min later): load1 FALLING
  to 18.26 (5m 28.88), idle 40-51 percent. Never >=90 percent; load falling
  falling through the tick but far from quiet. J-B measurement deferred, no
  compiler change, control unchanged at bench/runtime-comparison/jb_imod_control.c.
  Next tick unchanged: if idle >=90 percent, run 4000000 iters x 24
  alternations via file-redirected background session, ratio of medians,
  then add the third (non-inlined mulh) arm.

- 2026-09-19 18:47 JST tick 26 (JIT): quiet gate failed a 24th consecutive
  time - probe 1 at 18:42 JST: load1 15.27 (5m 22.49, 15m 29.87), iostat cpu
  idle 32-46 percent (3 samples). Probe 2 at 18:45 (~3 min later): load1
  FALLING to 11.63 (5m 18.38), idle 36-46 percent. Never >=90 percent;
  load trending down but far from quiet. Read path healthy (foreground
  probes returned; short "iostat -c 3" works). J-B measurement deferred,
  no compiler change, control unchanged at bench/runtime-comparison/
  jb_imod_control.c. Next tick unchanged: if idle >=90 percent, run
  4000000 iters x 24 alternations via file-redirected background session,
  ratio of medians, then add the third (non-inlined mulh) arm.

- 2026-09-20 00:55 JST tick 27 (JIT): quiet gate failed a 25th consecutive
  time - load1 20.36-20.77 on 10 CPUs (00:43 probe), iostat cpu idle 42-45
  percent (3 samples), never >=90 percent. But the deferred J-B measurement
  ran as an under-qualified diagnostic: rebuilt
  bench/runtime-comparison/jb_imod_control.c unchanged (clang -O2 -arch
  arm64), 3 runs at 4000000 iters x 24 alternations - saving +6.6/+8.8/+7.1
  percent (opaque 5.254/5.844/6.249 ns/elem vs const 4.906/5.332/5.803;
  ratio 1.071/1.096/1.077), checksum 764266 agreeing all runs, sign
  consistent 3/3, magnitude inside ADR 0335's busy-host 6-7 percent band,
  far from ADR 0341's quiet-host 13.1. J-B stays not-killed/not-confirmed
  (under-qualified). New static fact for J-C: the strength-reduction lever
  is ALREADY IMPLEMENTED in kotoba-native machine_ir.cljk -
  signed-division-magic (exact Granlund-Montgomery reciprocal, ~line 2954)
  and a64-quotient-constant (smulh+asr emission, ~line 6243) - but the imod
  path still emits the opaque guarded SDIV (aarch64.cljk signed-division,
  0x9ac10c00) because the divisor is not constant at the call site
  (ADR 0289). J-C's mechanism is "connect it": inline small user functions
  so the divisor constant-propagates to a64-quotient-constant (the const+
  inline composition ADR 0344 ranked). No compiler change, no policy change,
  no sealed claim. Next tick: hand-patch a kernel whose imod divisor is
  constant post-inline, verify the emitted aarch64 switches from the
  18-insn guarded-SDIV body to the smulh+asr form, measure end-to-end on a
  quiet host.
- 2026-09-20 06:43 JST tick 30 (JIT): quiet gate first probe was the closest-ever
  to quiet (load1 11.45/11.73 on 10 CPUs falling through two probes, iostat cpu
  idle best 77 percent at first probe third sample; never >=90 percent; probe 2
  3 min later already rising load1 16.3/17.2, idle 47/59/49). Under-qualified
  diagnostic J-B run executed as tick 27 did: rebuilt bench/runtime-comparison/
  jb_imod_control.c unchanged (clang -O2 -arch arm64), ONE full run 4000000
  iters x 24 alternations via background session — opaque(sdiv) 5.126 ns/elem
  vs const(mulh) 4.789, ratio 1.070, saving +6.6 percent, checksum 764266
  agreeing all arms (single run; sign consistent with tick 27 three same-sign
  6.6/8.8/7.1 window). Still diagnostic, ADR 0341 quiet-host 13.1 untested.
  No compiler change, no policy change, no sealed claim. Next tick: on the
  closest-to-quiet host ADD third (non-inlined mulh) arm separating lever 1
  (sdiv->mulh) from lever 2 (const-inline composition), rerun ratio of medians,
  then hand-patch machine_ir-a64-quotient-constant: verify emitted arm64
  switches 0x9ac10c00 18-insn guarded-SDIV body -> smulh+asr form, end-to-end
  quiet-host.

- 2026-09-20 12:50 JST tick 31 (JIT): quiet gate failed a 26th consecutive
  time - probe 1 at 12:42:54 JST: load1 20.93 (5m 21.47), iostat cpu idle
  22-46 percent (3 samples). Probe 2 at 12:46 (~3.5 min later): load1 RISING
  to 34.60/27.61/28.75, idle 0-46 percent. Never >=90 percent; host getting
  busier through the tick. J-B measurement deferred, no compiler change, no
  policy change, no sealed claim, control unchanged at
  bench/runtime-comparison/jb_imod_control.c. Terminal-note: stdout empty
  for foreground commands this tick; file-redirected probes land (read path
  same as ticks 18-30). Next tick unchanged: if idle >=90 percent, run
  4000000 iters x 24 alternations via file-redirected background session
  (ratio of medians), add the third (non-inlined mulh) arm, then do the
  tick-27 emit-verification hand-patch (constant-divisor kernel -> expect
  smulh+asr instead of 0x9ac10c00 guarded SDIV).
