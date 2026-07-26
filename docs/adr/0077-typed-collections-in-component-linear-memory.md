# ADR 0077: representing typed collections in a component's linear memory

**Status**: accepted
**Date**: 2026-07-25
**Depends on**: ADR 0076 (general Canonical ABI lowering), in particular section 4a
**Blocks**: ADR 0076 acceptance criterion 2 (`list<s64>` round-trip); root
ADR-2607254600 D5/D6 (crypto and storage providers); root ADR-2607254500
(Ethereum execution client) from Phase 1 onward

## Context

ADR 0076 section 4a established that a component cannot import
`kotoba:typed`/`kotoba:heap`: every core import must resolve against the WIT
world, and those are host intrinsic tables, not WIT interfaces. Inside a
component there is no host to call. Anything that is not a bare scalar
therefore has to live in the module's own linear memory — which is exactly what
all sixteen hand-written WAT shapes already do.

ADR 0076 4a step 1 landed the prerequisite: a component module now declares a
real page of memory and a real bounded bump `cm32p2_realloc`, ported from
`bounded-bump-realloc-wat` and verified by execution.

Step 2 is this ADR: **how is a `:vector-i64` represented in that memory?** It is
separated out because it does not change how a value crosses a boundary — it
changes how a typed collection is represented at all.

## The constraint that decides the design

Two measured facts about the existing semantics:

1. **Collections are persistent.** `ir/eval-expr`'s `vector-conj` is
   `(conj items item)` on a Clojure vector: it returns a new value and leaves
   the old one intact. Every backend must agree with this interpreter — it is
   the oracle the tests compare against.
2. **They are bounded.** `value/vector-item-limit` is 16384 items.

Combine persistence with a bump allocator that never frees, and building a
vector by repeated `conj` allocates `1 + 2 + … + n` element slots:

| n | slots | bytes allocated |
|---|---|---|
| 64 | 2 080 | 16 KiB |
| 256 | 32 896 | 257 KiB |
| 1 024 | 524 800 | 4.0 MiB |
| 16 384 (the limit) | 134 225 920 | **1.0 GiB** |

A single maximum-size vector is 128 KiB of live data — already two pages, where
step 1 declared one. Building it by `conj` touches a gigabyte of arena that is
never reclaimed. **Copy-on-write persistence on a non-reclaiming bump allocator
is not a viable general representation.** This is the whole problem; a layout
choice that ignores it will look fine on a four-element fixture and fall over on
the first real workload.

For the driving case, the numbers split sharply. A `u256` is 4 limbs — free
under any scheme. The EVM stack is 1024 deep and EVM memory grows into the
megabytes — hopeless under naive copy-on-write.

## Options

**(A) Keep copy-on-write; lower the bound in the component profile.**
Admit vectors up to some small `n` (say 64) and reject larger ones at compile
time. Correct, tiny, and enough for `u256`. Useless for the EVM stack, and it
splits the language's own limit across profiles — a program that compiles for
the wasm host would stop compiling as a component, with no principled reason a
reader could predict.

**(B) Linearity/escape analysis: mutate in place when the old value is dead.**
The standard functional-language answer. When the compiler can prove the input
of a `conj` is not reachable afterwards (the overwhelmingly common
accumulate-in-a-loop shape), reuse the buffer and grow amortised, giving O(1)
`conj`. Fall back to copying when it cannot. Preserves the semantics exactly —
the observable behaviour is identical, only the allocation is not. Costs a real
analysis pass, and its performance is a cliff: a program that accidentally keeps
an alias silently drops back to O(n²).

**(C) Reference counting or a real allocator with `free`.**
Makes copying cheap to avoid dynamically rather than statically. More machinery
than the whole rest of the component path, and reference counting has to be
threaded through every op that touches a collection.

**(D) Restrict the component boundary to collections that are not built by
`conj` chains** — literals, or the result of a single bounded construction —
and reject the rest.
Narrow but honest, and it is the direct analogue of what the sixteen
hand-written shapes already do: they build a record or a variant in memory once
and hand out a pointer. Nothing in `list<s64>` round-tripping actually requires
`conj`.

## Decision

**Do (D) now and (B) next; do not do (A).**

1. **Represent a `:vector-i64` as a pointer to `{len: i32}` followed by `len`
   contiguous `i64` elements**, allocated once through `cm32p2_realloc` with
   alignment 8. This is the Canonical ABI's own `list<s64>` layout plus a length
   header, so lifting to `(ptr, len)` at the boundary is a projection rather
   than a conversion.

2. **Admit, in the component profile, only vector values whose construction the
   compiler can see is single-shot**: a literal, or a bounded construction whose
   result is not derived from another live vector. Reject a `conj` chain with a
   diagnostic that names the operation and points at this ADR — fail closed, the
   same way every other unsupported shape already fails. This unblocks ADR 0076
   acceptance criterion 2 and the `u256` layer of ADR-2607254500 without
   pretending to support the EVM stack.

3. **Do not lower `vector-item-limit` for the component profile.** A vector that
   fits is admitted whatever its length; what is restricted is how it may be
   *built*, which is a property the compiler can explain, unlike an arbitrary
   smaller ceiling. The arena must therefore be sized for the largest admitted
   vector rather than left at step 1's single page: raise
   `component-memory-pages` to cover `vector-item-limit` (128 KiB = 2 pages) plus
   headroom for the ABI's own string-copy allocations, and keep
   `component-arena-capacity` in lockstep so an over-large value traps instead of
   running off the memory.

4. **(B) is the sequel, and the EVM stack is its acceptance test.** Linearity
   analysis is what turns the restriction in (2) from a permanent ceiling into
   an optimisation boundary. It should not be attempted in the same change:
   layout and analysis fail differently, and debugging them together is how a
   wrong layout gets blamed on the analysis.

(A) is rejected outright: a per-profile item limit makes the same source
compile or not depending on the target for a reason no reader can derive from
the program. (C) is deferred, not rejected — if (B)'s cliff proves too sharp in
practice, reference counting is the honest next step, but adopting it before
measuring would be building machinery against a guess.

## Consequences

- `list<s64>` can cross a component boundary, closing ADR 0076 acceptance
  criterion 2 and unblocking the crypto and storage providers of
  ADR-2607254600 D5/D6, whose requests and results are byte sequences.
- The `u256` and RLP layers of ADR-2607254500 Phase 0 become expressible as
  component exports, not merely as internal computation.
- A `conj` chain is rejected in the component profile until (B) lands. That is a
  real restriction and it must be stated in the diagnostic, not discovered.
- The typed backend gains a second representation for `:vector-i64`, selected by
  profile. This is duplication and it is a cost: the two must agree with
  `ir/execute`, which is the oracle. Every op admitted for the component profile
  needs a test asserting both representations produce the same observable
  result, in the same spirit as ADR 0076's acceptance criterion 4.

## Acceptance

1. A function returning a single-shot `:vector-i64` compiles to a validated
   component; `wasmtime` reads back the same elements that went in.
2. A signature taking `list<s64>` and returning `list<s64>` round-trips a
   non-trivial vector with the values and length intact.
3. A `conj` chain is rejected with a diagnostic naming the operation and this
   ADR — verified as a rejection, not merely documented.
4. For every admitted vector operation, the component representation and
   `ir/execute` agree on the observable result.
5. A vector at `vector-item-limit` either fits the declared arena or traps
   cleanly; it must not write past the declared memory.

## Implemented boundary

The first executable slice implements two single-shot forms:

- a `:vector-i64` literal is allocated once as `{len: i32, padding: i32,
  elements: len * i64}` and returned as the Canonical `(elements-ptr, len)`
  pair;
- an identity export validates and aliases the Canonical input buffer without
  copying it. Since the old value is not retained or mutated, this preserves
  the same observable semantics without creating a second maximum-sized
  allocation.

Both forms execute as standard Components on Wasmtime. Empty, non-trivial, and
16,384-item boundary vectors round-trip; a core call above that bound traps.
`vector-conj` remains rejected with an ADR-specific diagnostic until the
linearity analysis selected by this decision is implemented.
