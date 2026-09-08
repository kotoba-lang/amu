# J-A harnesses (chicory interpreter dispatch share)

Built and validated on 2026-09-08 (amu-jit tick 25). Host jars:
`~/.m2/repository/com/dylibso/chicory/{wasm,runtime}/1.7.5/*.jar` (pure-JVM
interpreter). Fixture: `../kernel.kotoba.wasm` (sealed, sha256
5be27a87...cb30ac91, imports=0, exports: kernel(0), bench(1),
__kotoba_loop_1(2), main(3)).

Build/run (AGENTS.md Q9 rule: these are diagnostics, NOT a Q9 compiler route —
they run on bare `java` deliberately because J-A measures a JVM interpreter):

    CJ=$HOME/.m2/repository/com/dylibso/chicory/wasm/1.7.5/wasm-1.7.5.jar:\
$HOME/.m2/repository/com/dylibso/chicory/runtime/1.7.5/runtime-1.7.5.jar
    javac -cp "$CJ" JaOrderFlip.java
    java  -cp "$CJ:." JaOrderFlip ../kernel.kotoba.wasm 200 40 12 true

## Status of the estimators (tick 25 findings, all sign-level, quiet gate NOT met)

- **Wall-diff (ExecutionListener) estimator: FALSIFIED as a dispatch-share
  bound.** `withUnsafeExecutionListener` runs on the SAME
  `InterpreterMachine` class as bare, yet the empty-listener arm measures
  FASTER than bare, and the sign follows arm ORDER, not the listener
  (`JaOrderFlip`: listener-first → listener +5.2%; bare-first → listener
  −33.0%; `JaDispatchShare`/`JaMachineCheck` reproduce the negative "cost").
  A wall delta that flips sign with alternation order cannot bound any
  mechanism share. Do NOT build J-A numbers on bare-vs-listener wall diffs.
- **Counting estimators: load-robust, keep.** `JaOpHistogram` /
  `JaLoopHistogram` give exact per-call executed-opcode histograms
  (kernel(200) = 120 instructions, flat in n; bench loop = 128
  instructions/iteration). This is the ground-truth denominator for any
  future share estimate.
- **Slope estimator (`JaFixedVsSlope`): not stable under load.** OLS of
  per-call median vs executed-instruction count gave slope 454 ns/instr with
  a NEGATIVE intercept (run 1) and 200 ns/instr with +133 us intercept
  (run 2) at load1 8–32. r=64 points jump regimes (fuel or tiering). Needs
  the quiet gate before its numbers mean anything, and possibly a fixed-r
  range.

## JFR sampling estimator (`JaJfrDispatchShare`): BUILT + VALIDATED (ticks 26–27)

Passive stack sampling (`jdk.ExecutionSample`, 10 ms) over a long chicory
loop; reports leaf (exclusive) / on-stack (inclusive) shares of
`InterpreterMachine.*` plus a top-20 profile — no per-instruction listener
perturbation. Two bugs found and fixed by the tick-27 smoke runs:

1. Cached `ExportFunction`s exhaust the sealed per-instance fuel:
   `calls_until_trap=512` on one `Instance` (measured tick 27, matching the
   V8 runner's calibration); a fresh `Instance.builder(mod).build()` gets a
   fresh 512. The harness now keeps a pool of 8 slots, rebuilding each
   instance every 256 uses (~62–214 ns/call amortised, visible as its own
   JFR leaf if it ever matters).
2. `jdk.MethodSample` alone records ZERO samples on Temurin 21.0.1 aarch64
   (per-method CPU sampling needs
   `-XX:FlightRecorderOptions=SampleVersion=2`); the estimator therefore
   uses `jdk.ExecutionSample` (thread stack sampling, no extra flags).

First working run (busy host, load1 16–20, 409 samples, diagnostics only):
on-stack `InterpreterMachine.call` = 99.0% and `eval` = 83.6%, but the
dominant LEAF is `MStack.push` 71.4% — operand-stack push machinery, NOT
the dispatch loop itself (`eval` leaf 4.7%); `InterpreterMachine.execute`
never appears as a frame in chicory 1.7.5. Quote-worthy share numbers need
a quiet-gate run plus a SampleVersion=2 method-sampling cross-attribution
(to rule out inlined-push-site pile-on on the `MStack.push` leaf name).
See docs/jit-cosientist.md tick 27.

Run: `java -cp "$CJ:." JaJfrDispatchShare ../kernel.kotoba.wasm 100 200 5 20`
(args: wasm, kernel-n, inner-iters, warmup_s, record_s).

## Files

| file | role |
|---|---|
| JaOrderFlip.java | arm-order control for the wall-diff estimator (falsified it) |
| JaOpHistogram.java | per-call executed-opcode histogram, kernel export (counting only) |
| JaLoopHistogram.java | per-iteration executed-opcode histogram, bench loop (counting only) |
| JaFixedVsSlope.java | instr-count-vs-wall OLS slope/intercept estimator (load-unstable) |
| JaModuleShape.java | exports/import count of the fixture |
| JaJfrDispatchShare.java | JFR stack-sampling dispatch-share estimator (validated tick 27) |

No sealed claim; diagnostics only until perfgate + human-approved warmup
policy (see docs/jit-cosientist.md policy note).
