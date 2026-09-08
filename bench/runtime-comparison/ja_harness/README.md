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

## Next estimator candidate (not yet built)

JFR method sampling (bundled with the JDK, no new deps): long chicory loop
runs, then `jfr print` exclusive share of
`com.dylibso.chicory.runtime.InterpreterMachine.execute`. That measures
dispatch-loop self-time directly instead of perturbing it with a listener.

## Files

| file | role |
|---|---|
| JaOrderFlip.java | arm-order control for the wall-diff estimator (falsified it) |
| JaOpHistogram.java | per-call executed-opcode histogram, kernel export (counting only) |
| JaLoopHistogram.java | per-iteration executed-opcode histogram, bench loop (counting only) |
| JaFixedVsSlope.java | instr-count-vs-wall OLS slope/intercept estimator (load-unstable) |
| JaModuleShape.java | exports/import count of the fixture |

No sealed claim; diagnostics only until perfgate + human-approved warmup
policy (see docs/jit-cosientist.md policy note).
