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

Use the Canonical ABI's contiguous `list<s64>`/`list<float64>` representation
at the public Component boundary. Borrowed inputs are always validated for
item count, alignment, unsigned range overflow, and arena bounds. Any operation
that returns a list owns a fresh guest allocation and writes a standard
pointer/count result area; canonical post-return resets transient storage.

`vector-drop`, `vector-assoc`, and `vector-conj` therefore use bounded
copy-on-write at an export boundary. This is semantically identical to the
interpreter's persistent vectors and prevents a result from mutating or
aliasing its input. It is deliberately distinct from repeated internal vector
construction: linearity/escape analysis remains the required optimization for
long-lived loops such as an EVM stack.

The same ownership rule applies when an `option`/`result` match returns a list.
A branch may source its result from the selected payload's scalar-item list,
another vector parameter, or a bounded literal, and may apply one matching
drop/assoc/conj transform. The selected union case validates every bool,
string, and list leaf even if the branch does not read it; inactive joined
payload slots stay uninterpreted. Both branches converge on the same fresh
allocation and result-area convention.

Do not lower `vector-item-limit` for the component profile. The fixed arena is
sized for the language limit plus ABI headroom, and exhaustion traps before an
out-of-range write. More general nested item types remain fail-closed until
they have recursive per-element validation and a corresponding ownership
plan.

## Consequences

- `list<s64>` and `list<float64>` can cross a Component boundary as parameters,
  literals, identities, top-level transforms, and aggregate match results.
- Borrowed input buffers are never mutated by an owned-result operation.
- Export-boundary transforms are O(n) by design. This does not claim that a
  repeated internal `conj` loop is efficient; that still needs linear reuse or
  a reclaiming allocator.
- The Component backend and `ir/execute` remain two representations of the
  same persistent-vector semantics, so source-level vertical tests must cover
  every newly admitted form.

## Acceptance

1. Non-empty and maximum-bound scalar-item lists round-trip through a standard
   Component; over-bound or malformed core inputs trap.
2. i64 and f64 drop/assoc/conj results equal the language oracle, do not mutate
   their inputs, and do not alias them.
3. Option/result branches can return a selected payload list, another vector
   parameter, or a literal through the same owned-result ABI.
4. Selected aggregate leaves are validated and inactive joined slots remain
   lazy.
5. Repeated calls in one core instance succeed after post-return without
   unbounded arena growth.

All five conditions are executable. Component tests cover direct KIR and
20,000 repeated core calls; compiler tests cover the full
`.kotoba -> KIR -> core Wasm -> Component -> Wasmtime` path.
