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
- 2026-09-20 18:55 JST tick 32 (JIT): quiet gate failed a 27th consecutive
time - probe 1 at 18:48:27 JST: load1 14.14 (5m 12.29), iostat cpu idle
45-60 percent (3 samples); probe 2 at 18:51:09 (~3 min later): load1
RISING to 16.57 (5m 14.75), idle 45-61 percent. Never >=90 percent.
Under-qualified J-B diagnostic run as ticks 27/30 did (control
bench/runtime-comparison/jb_imod_control.c UNCHANGED, md5
baf8905aad3892ce5fe58a9d8f7ecb6e, 3266 bytes; rebuilt clang -O2 -arch
arm64): ONE full run 4000000 iters x 24 alternations, finished 18:53:14
JST - opaque(sdiv) 5.697 ns/elem vs const(mulh) 5.360, ratio 1.063,
saving +5.9 percent, checksum 764266 agreeing all arms. Sign consistent
5/5 across the last 5 under-qualified runs (ticks 27/30/32: 6.6/8.8/7.1,
6.6, 5.9) - magnitude band 5.9-8.8 percent, still far from ADR 0341's
quiet-host 13.1. Disassembly re-verified: _imod_opaque emits sdiv
0x9ac10c08 (guarded SDIV), _imod_const emits smulh+asr; whole binary has
exactly 1 sdiv (opaque arm) and 3 smulh. J-B stays not-killed/not-
confirmed (under-qualified). Third (inlined-mulh) arm NOT added this
tick - the patch attempt failed on an exact-string match (hidden
whitespace suspected, not diagnosed), control left byte-identical rather
than risk an unverified edit. No compiler change, no policy change, no
sealed claim. Next tick: (a) quiet host -> full run + third arm; (b) if
host stays busy, fix the third-arm patch (check line endings via od) and
rerun, then the tick-27 emit-verification hand-patch.

- 2026-09-21 12:46 JST tick 33 (JIT): quiet gate failed a 28th consecutive
  time - probe 1 at 12:46:13 JST: load1 107.33 (5m 83.50, 15m 70.87) on 10
  CPUs, iostat cpu idle 46/58/51 percent (3 samples, ~3 s apart), never
  >=90 percent; host busier than any recent tick (worst load1 since tick
  11). Control re-verified byte-identical: md5
  baf8905aad3892ce5fe58a9d8f7ecb6e (matches tick 32, 3266 bytes).
  Line-ending diagnosis from tick 32's failed third-arm patch: `od -c` +
  `file` confirm pure LF (0x0a) endings, ASCII text - the failure was NOT
  CRLF; root cause remains the exact-string match itself (not further
  diagnosed this tick). Backup copy of the control taken to scratch + /tmp
  (tick-33 backup; existence unverified - terminal stdout was empty this
  tick). J-B measurement deferred, no compiler change, no policy change, no
  sealed claim. Next tick: (a) quiet host -> full run + third arm; (b) if
  busy, add the third (non-inlined mulh) arm with a verified patch (file is
  confirmed LF/ASCII, so an exact-string from read_file content should
  match - suspect the earlier old_string differed in content, not
  whitespace), then the tick-27 emit-verification hand-patch.
- 2026-09-21 18:43 JST tick 34 (JIT): quiet gate failed a 29th consecutive
  time - load1 31.2-35.5 on 10 CPUs (uptime 35.49/30.33/31.70 at 18:43,
  iostat 31.20/32.46), cpu idle 42-46 percent across 2 samples, never
  >=90 percent. Branch (b) of the tick-33 plan executed: third
  (inlined-mulh) arm patch attempted in-repo against
  bench/runtime-comparison/jb_imod_control.c - FAILED on exact match again
  (8-line header anchor AND a 2-line anchor both rejected by the patch
  tool). Control re-verified byte-identical AFTER the failed patches:
  md5 baf8905aad3892ce5fe58a9d8f7ecb6e (matches ticks 32/33, 3266 bytes)
  - file untouched. Root-cause check this tick: jb_imod_control.c is
  confirmed 100% LF/ASCII with SPACE-indented comments (grep for tab:
  0 matches; od -c of lines 5-7 shows space runs, no tab) and stayed
  byte-identical after both failed patch attempts. The patch tool
  simply failed to match this exact content (ticks 32-34), unexplained -
  treat the patch tool as unreliable for these files. This doc is
  space-indented on its recent entry continuation lines as well
  (grep for tab: 0 matches), yet the same exact-match failure
  occurred on it too. This entry was appended via file-redirected
  shell cat, not the patch tool. Pre-tick-34 backup of the control
  /tmp/jb_imod_control.pre-tick34.c. Read path: foreground stdout empty
  again; file-redirected probes land (unchanged since tick 18). No J-B
  diagnostic measurement this tick (host busy; budget used on the patch
  diagnosis). J-B stays open, not-killed/not-confirmed; no compiler
  change, no policy change, no sealed claim. Next tick: add the third
  (inlined-mulh) arm C with write_file (full-file rewrite, SPACE-
  indented, matching the existing file), verify md5 changed, then on a quiet host run 4000000 iters x
  24 alternations for A/B/C (lever 1 = A vs B, lever 2 = B vs C), ratio
  of medians.

- 2026-09-22 00:58 JST tick 35 (JIT): quiet gate failed a 30th consecutive
  time - probe at 00:43:16 JST: load1 32.78 on 10 CPUs (5m 42.97, 15m
  48.49, falling trend), iostat cpu idle 37-46 percent (3 samples ~2 s
  apart), never >=90 percent. Tick-34 branch (a) executed: the third
  (inlined-mulh) arm C was ADDED to the control file via write_file
  full-file rewrite (the patch-tool exact-match failures of ticks 32-34
  sidestepped) - md5 baf8905aad3892ce5fe58a9d8f7ecb6e (ticks 32/33) ->
  5fe2c47a1c3e2d4268bc65dc0d3779d9 (3266 -> 4695 bytes), pre-tick-35
  backup at /tmp/jb_imod_control.pre-tick35.c; rebuilt clean (clang -O2
  -arch arm64 -> /tmp/jb_imod_tick35, empty build output). The arm C
  mechanism: imod_const_inl is the same constant-divisor body WITHOUT
  noinline, so clang -O2 inlines it into arm_inl's loop body - lever 1
  = A vs B (sdiv->mulh swap, call boundary kept), lever 2 = B vs C
  (same strength-reduced body, call boundary removed). Under-qualified
  J-B diagnostic run (4000000 iters x 24 alternations, A/B/C interleaved)
  STARTED as background session proc_c554016d61f8 ->
  /tmp/jb_imod_tick35_out.txt; tick budget exhausted before completion:
  status = STARTED, UNDER-QUALIFIED, IN-MEASUREMENT - NO NUMBERS THIS
  TICK (per the no-fabrication rule, nothing recorded until the output
  file is read). Disassembly verification of the C arm (expect: no bl,
  smulh present inside arm_inl loop body) pending in background ->
  /tmp/jb_imod_tick35_disasm.txt. No compiler change, no policy change,
  no sealed claim. Next tick first actions: (1) read
  /tmp/jb_imod_tick35_out.txt (or poll session proc_c554016d61f8 if still
  running), record A/B/C medians + lever1 A/B + lever2 B/C + checksum
  agreement; (2) verify C-arm disassembly; (3) then the tick-27
  emit-verification hand-patch (constant-divisor kernel -> expect
 smulh+asr instead of the 0x9ac10c00 guarded SDIV in emitted aarch64).

 - 2026-09-23 06:43 JST tick 39 (JIT): quiet gate failed a 33rd consecutive
 time - probe at 06:43 JST: load1 11.04 (5m 10.81, 15m 9.57) on 10 CPUs,
 iostat cpu idle 46/61/70 percent (3 samples ~2 s apart), never >=90
 percent. J-B measurement deferred (host busy); control unchanged at
 bench/runtime-comparison/jb_imod_control.c (no writes this tick).
 Branch (b) advanced - static emit-verification targets re-located and
 READ this tick (no quiet gate needed):
 (1) kotoba-native/src/kotoba/native/machine_ir.cljk:
     signed-division-magic def at line 2954; a64-quotient-constant def at
     line 6243 - on magic success emits smulh 0x9b407c00 + asr/add
     (lines 6250-6286), on failure falls back to a64-quotient (guarded
     SDIV, sdiv 0x9ac00c00 body at line 6236, 18-insn cbz/cmp/divide
     sequence). MIR dispatch: :aarch64/quotient-constant (line 7222,
     reads :mir/divisor) vs :aarch64/quotient (line 7219, register
     divisor). signed-division-magic call sites: 3553 (x86), 6245 (a64),
     8254 (nil? guard), 8709 (mir/divisor).
 (2) Candidate kernels located: bench/runtime-comparison/kernel_strings.kotoba
     (line 4: (defn imod [x :i64 m :i64] :i64; scan loop calls imod with
     constant 1000003) and kernel_collections.kotoba (imod with constants
     1000003/16/8).
 Falsification expectation to verify next tick: if constant divisors
 ALREADY flow through the :aarch64/quotient-constant path at MIR level
 (site 8709 reads :mir/divisor), the J-C "connect" lever reduces to
 whether the inliner/const-prop propagates the call-site constant into
 :mir/divisor BEFORE encoding; the disasm test is: compile kernel_strings
 (jvm-free, aarch64) and count sdiv 0x9ac10c00 occurrences - expect 0 in
 the imod body if the lever is present, 1 if it is not. No compiler
 change, no policy change, no sealed claim. Next tick: run that disasm
 test; if sdiv present, trace where :mir/divisor is (or is not) populated
 for inlined constant calls.

- 2026-09-22 06:45 JST tick 36 (JIT): tick-35 background measurement COMPLETED and
  read back from /tmp/jb_imod_tick35_out.txt (written 2026-09-22 00:53 JST) - the
  A/B/C three-arm J-B diagnostic, 4000000 iters x 24 alternations, checksum
  764266 agreeing all arms: A opaque(sdiv) 5.240 ns/elem, B const-call(mulh)
  4.902, C const-inline(mulh) 4.890. lever1 A/B ratio 1.069 = saving +6.5%
  (inside the established busy-host 5.9-8.8 band, sign now consistent 6/6 across
  ticks 27/30/32/35). lever2 B/C ratio 1.002 = saving +0.2%: the call boundary is
  NOT a meaningful cost; essentially the whole J-B effect is the sdiv->mulh
  strength reduction itself. C-arm disassembly verified (/tmp/jb_imod_tick35_
  disasm.txt): _arm_inl body contains smulh (0x9b497d8d) in-loop and no bl to
  imod; binary still has exactly 1 sdiv (opaque arm) + 3 smulh. Consequence for
  J-C: inlining alone (without constant propagation to a64-quotient-constant)
  buys ~nothing - the emit-path lever is the constant propagation, not the
  call removal. All results UNDER-QUALIFIED (run host idle never >=90%), so
  J-B remains not-killed/not-confirmed, no sealed claim. Tick-36 quiet gate
  failed a 31st consecutive time - load1 22.36 (5m 29.30, 15m 32.92) on 10
  CPUs at 06:43, iostat cpu idle 46-58 percent (3 samples), never >=90
  percent. No compiler change, no policy change, no sealed claim. Next tick:
  (a) if idle >=90 percent, rerun the three-arm run on a quiet host for a
  qualified lever1/lever2 pair; (b) otherwise the tick-27 emit-verification
  hand-patch (constant-divisor kernel -> expect smulh+asr instead of the
  0x9ac10c00 guarded SDIV in emitted aarch64).

- 2026-09-23 00:43 JST tick 38 (JIT): quiet gate failed a 32nd consecutive
  time - probe at 00:43 JST: load1 22.07 (5m 19.20, 15m 17.74) on 10 CPUs,
  iostat cpu idle 45/55/62 percent (3 samples ~2 s apart), never >=90
  percent. J-B measurement deferred, no compiler change, no policy change,
  no sealed claim. Control re-verified: bench/runtime-comparison/
  jb_imod_control.c = 4695 bytes, three-arm state (A opaque-sdiv / B
  const-call mulh / C const-inline mulh) matching the tick-35 write_file
  rewrite; /tmp/jb_imod_control.pre-tick35.c is the 3266-byte two-arm
  original. Emit-verification hand-patch targets located for next tick:
  kotoba-native/src/kotoba/native/machine_ir.cljk (signed-division-magic
  ~line 2954, a64-quotient-constant ~line 6243 per tick 27) and
  kotoba-native/src/kotoba/native/aarch64.cljk (guarded SDIV body,
  0x9ac10c00). Read path: foreground stdout empty; file-redirected
  commands land; grouped compound commands blocked by the security
  scanner (separate redirected commands work, same as ticks 23/24).
  Next tick: (a) quiet host (idle >=90 percent) -> three-arm run, ratio of
  medians; (b) otherwise the static emit-verification hand-patch on a
  constant-divisor kernel (no quiet gate needed): expect emitted aarch64
  to switch from the 0x9ac10c00 guarded SDIV body to the smulh+asr form
  when the divisor is constant post-inline.
