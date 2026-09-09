# ADR 0346: J-A leaf attribution is regime-stable on a quiet host — the busy-host flip was the artifact

- Status: accepted (diagnostic evidence record; no sealed claim)
- Date: 2026-09-09 (amu-jit tick 31, backfill-sealing ticks 29–30)
- Stage: Measured-quiet (fleet node benjamin; ADR 0282/0341 busy-CPU gate MET:
  PRE samples 0.038–0.041, POST 0.043–0.054, all ≤ 0.10 on 10 cores, load1
  1.4–3.6 across the 10:06–10:29 JST run/probe window)

## Decision

Tick 27 recorded a JFR leaf profile that FLIPPED between two busy-host reps
(MStack.push 71.4% → 0%; StackFrame.doControlTransfer ~0 → 68.8%) and ruled
that "leaf-share cannot be quoted from ANY number of busy-host reps." This
ADR records the quiet-gate continuation (ticks 29–31, chicory 1.7.5, fixture
kernel.kotoba.wasm sha256 5be27a87...cb30ac91, checksum 110550153 every rep;
13 JFR reps / 10249 stack samples total = 7 default-tiering (tick 29 x5 @60 s
+ tick 31 CTRL x2 @40 s) + 6 tiering-ablation (tick 30 noInline x2, c1only
x2; tick 31 c2only x2)):

1. **On a quiet host the dominant leaf is stable.**
   `InterpreterMachine.numberOfParams` holds 75.27–80.54% of leaf samples
   across all 7 default-tiering quiet reps AND the 2
   `-XX:TieredStopAtLevel=4` (C2-only) reps. `StackFrame.<init>` 7.6–12.9%
   on-stack. The tick-27 flip between `MStack.push` and `doControlTransfer`
   NEVER appears as a dominant leaf in any quiet rep: that flapping was a
   load/tier artifact, not the mechanism.
2. **The inclusive shares reproduce**: on-stack `InterpreterMachine.call`
   98.0–99.4%, `eval` 80.8–85.8% — same as the busy reps. Only the leaf
   attribution needed the quiet gate, exactly as predicted.
3. **Tick-27 caveat (a) (inlined code piles onto a leaf name) is CONFIRMED
   by ablation**: with `-XX:-Inline` the profile genuinely changes shape
   (eval leaf 20.8–22.9%, MethodHandle ctor machinery ~15–21% on-stack,
   numberOfParams vanishes from the leaf top) AND wall slows ~3.7x
   (2677–2812 vs 686–756 ns/call). So the default-run `numberOfParams` leaf
   carries the inlined per-instruction operand-stack/type machinery inside
   the `IF` dispatch path — stable in NAME, mixed in CONTENT.
4. **J-A's lever answer** (diagnostic, not a claim): in a chicory-class
   interpreter the hot term is the per-instruction `IF`/`numberOfParams` +
   operand-type machinery (~75–81% leaf share, C1 tier suppresses its leaf
   name to ~0 while the same work moves to `BLOCK`/on-stack frames), NOT
   the dispatch loop as a standalone (`eval` exclusive leaf 3.0–5.1% at
   default tiering) and NOT the arithmetic opcode handlers (never dominant
   in any rep, busy or quiet). "Opcode dispatch dominates" as stated in J-A
   is FALSIFIED as an attribution; "the interpreter machine dominates"
   (≈99% on-stack) is trivially true and restated.
5. **Cross-host correction of record**: quiet, identical-fixture, same-host
   (benjamin): chicory default 685.5–755.8 ns/call (median 744.2) vs V8
   28.6–29.3 ns/call (median 29.0) → **~25–26x**, replacing both the
   withdrawn "~100x" (tick 24, per-call rebuild accounting) and the
   busy-host "~6–10x" (tick 27).

## Method branch notes

- `jdk.MethodSample` records ZERO events on benjamin's OpenJDK 26.0.1 (all
  13 reps), and `FlightRecorderOptions=SampleVersion=2` is rejected there —
  the tick-27 cross-attribution route is impossible on this host. The
  tiering ABLATION (ticks 30–31) achieved the attribution split instead,
  without perf counters. Perf counters stay as the fallback if a future
  question needs exact self-time.
- This tick also fixed a NaN bug in the newly written gate probe
  (`c.times.system` → node's field is `.sys`); the post-window bracket used
  the fixed version (sealed at bench/runtime-comparison/ja_harness/
  gate_probe.js).

## Consequences

- J-A evidence now reaches "which part is the lever" at quiet-host quality
  (status rewrite belongs to amu-rank). The JIT-side lever candidate in a
  chicory-class host is per-instruction signature/type machinery
  specialisation (numberOfParams/IF operand path), analogous in SHAPE to
  J-B2's finding (helper-call/operand machinery, not the arithmetic).
- Sealed artifacts (bench/runtime-comparison/): ja_jfr_benjamin_t29.log
  (sha256 c05d0d46...), ja_v8_benjamin_t29.log (5c7fb016...),
  ja_jfr_ablate_benjamin_t30.log (3022c85e...),
  ja_jfr_regime_benjamin_t31.log (a0e45239...), harness source
  JaJfrDispatchShareV2FIX.java (de105441...).
- NO compiler change, NO sealed claim. JIT warmup/steady-state policy note
  unchanged: shares here are diagnostics; any JIT-form claim still requires
  the perfgate boundary ADR with human approval first.
