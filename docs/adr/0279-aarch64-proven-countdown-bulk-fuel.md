# ADR 0279: AArch64 proven countdown bulk fuel

## Decision

Pin kotoba-mir `7f248d57` transitively through kotoba-native `1bcac520`.
For AArch64 only, an exact, closed, pure, non-trapping self-recursive countdown
may precharge its complete `counter + 1` fuel cost at entry and omit charging
on its one direct hot recur edge. Insufficient fuel stores zero before trapping,
so success consumes exactly the same fuel as ordinary edge charging and failure
cannot expose partial effects.

Admission is deliberately fail-closed twice. MIR proves one direct decrement by
one, one base return, one body, and one self tail, with no calls, capabilities,
memory, nested or multiple recurrence, unsafe arithmetic, or data-dependent
exit. After register allocation, native enables the transform only when the
allocated function still has exactly one direct `:mc/recur`, exactly one
`:mc/reentry`, and no self public tail-call. Any failed proof keeps the complete
ordinary instrumentation vector.

Negative counters enter a separately encoded cold body with ordinary entry and
recur charging. Its recur returns to its own charged reentry even after signed
wrap, so `Long/MIN_VALUE` cannot escape into the uncharged positive hot edge.
x86-64 and every non-AArch64 target are unchanged.

## Semantic and structural evidence

The merged MIR proof passes 78 JVM tests / 1,258 assertions. The merged native
implementation passes 196 JVM tests / 2,356 assertions. Its structural corpus
covers calls, data exits, unsafe division, nested and multiple sites, the cold
negative duplicate, unchanged x86 instrumentation, a fifth-argument counter in
`x4`, and a five-argument/30-live-value allocation that lowers through the
public entry and therefore retains ordinary charging.

The Amu W^X loader executes exact zero, counter-one, exact-full, insufficient,
negative, minimum-i64, and maximum-i64 boundaries. In particular, minimum-i64
with initial fuel one and two traps with remaining zero; a fifth-argument
counter succeeds with its exact two units; and the high-pressure public-tail
fallback succeeds for `n=2` with exactly `n+1` fuel. The full JVM suite passes
151 namespaces, 1,154 tests / 8,519 assertions. The NBB project, locked
classpath, wasm32 cross-runtime, runtime-batch exact-fuel, and JDK-free native
W^X checks pass.

## Claim boundary

This decision establishes fuel equivalence, fail-closed fallback, and removal
of recurring fuel memory traffic only for the admitted shape. A clean sealed
fair-batch run passed the host-load gate (`load1` 6.199, limit 7.5) and consumed
exactly 100,002 fuel units per Amu sample. The sealed prepared-bundle digest is
`d82f2c53fd9490edd957ac426e5403e4f8416d3f8a5e9a281425182ead155d90`.
Its median was 5.24 ns/iteration; the optional Rust comparator measured
3.88416 ns/iteration, making Amu 1.349x slower on this fixture. Perfgate was not
run, so this is host-load-qualified diagnostic evidence, not a qualified
performance claim. It is evidence against a fastest claim, not evidence of a
speedup or Rust/LLVM parity. Rust and LLVM remain optional comparators, not
build or runtime dependencies.

> **Superseded in part by ADR 0281 (2026-08-29).** The `1.349x` ratio in
> this section is withdrawn: re-measured on a host-load-qualified run, both
> arms of this fixture carry a relative standard deviation near 0.47, which
> `perfgate.core/qualify` refuses as `:too-noisy`. The fuel-equivalence and
> fail-closed claims above are untouched.
