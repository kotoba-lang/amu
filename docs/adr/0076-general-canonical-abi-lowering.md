# ADR 0076: replace shape-enumerated Canonical ABI lowering with a compositional, type-derived one

**Status**: proposed
**Date**: 2026-07-25
**Depends on**: ADR 0075 (component target, declared budgets, admission request)

## Context

ADR 0075 exposed `wasm-component-kotoba-v1` as a compile target and made fuel a
declared budget. It also recorded the limitation this ADR exists to remove.

`component-core` lowers a Kotoba program to the Canonical ABI by **recognizing
program shapes**, not by deriving lowering from types. Today that is roughly 25
shape recognizers (`scalar-record-identity-function?`,
`variant-capability-call`, `string-field-record-schema`, …) feeding 16
hand-written WAT generators (`scalar-record-wat`, `variant-capability-wat`,
`scalar-record-projection-wat`, …), selected by `assert-supported!`.

Each supported program is a case someone wrote by hand. Two consequences follow,
and they are the same root cause:

1. **Capability imports work only in four shapes.**
   `component-artifact/assert-qualified-slice!` rejects any program that has WIT
   imports unless the lowering is one of `:scalar-capability-call`,
   `:record-capability-call`, `:variant-capability-call`, or
   `:different-variant-capability-call` — all of which additionally require
   exactly one function and one export. A multi-function program that uses even
   one capability is refused. (The general `:scalar` lowering does admit many
   functions; the restriction is imports, not arity.)

2. **Typed collections cannot cross the boundary.** In the core module they are
   host objects behind `externref` (`0x6f`), and the Canonical ABI has no
   `externref`. `component-wit` already emits `list<s64>` for `:vector-i64`, so
   the WIT side promises a representation the core side cannot produce.

Root ADR-2607254500 scopes an Ethereum execution client whose every module is
multi-function, capability-using, and built on `u256` limb vectors and a
1024-deep EVM stack. It cannot compile under either restriction. It is the
forcing case, not the only one: any real application hits both immediately.

## Decision

Replace shape recognition with a **compositional lowering derived from the
type**, implementing the Canonical ABI as specified rather than per-program.

### 1. Flattening and spill

Each component-level type flattens to a sequence of core types by the spec's
rules. Apply the spec limits: `MAX_FLAT_PARAMS = 16`, `MAX_FLAT_RESULTS = 1`.
When a signature exceeds a limit, pass/return a single `i32` pointer to a
linear-memory area instead of the flattened sequence. This is mechanical and
type-directed; no shape is privileged.

### 2. Memory layout

Implement `size`/`alignment` for every representable type and lay values out
accordingly:

- **record** — fields in declaration order, each at its own alignment, struct
  size rounded up to the max field alignment.
- **variant** (and `option`/`result`, which are variants) — discriminant in the
  smallest integer type that holds the case count, payload placed at the max
  payload alignment.
- **list\<T\>** — `(ptr, len)` pair; elements contiguous at `T`'s alignment.
- **string** — `(ptr, len)` with UTF-8 encoding, matching the `--encoding utf8`
  already passed to `wasm-tools component embed`.

### 3. realloc and post-return

Export a single general `cm32p2_realloc` and wire `post-return` for lifted
functions that return owned memory. The existing bump arenas
(`bounded-bump-realloc-wat`) already do this per shape; generalize to one
implementation with an explicit bound, so the allocation limit stays declared
and auditable rather than reappearing in each generated shape.

### 4. Typed collections: marshal at the boundary, do not add resources

Two options were considered for `externref`-backed typed collections:

- **(a) Marshal at the boundary.** At lift/lower, materialize the host
  collection into linear memory as a Canonical `list<T>`, and rebuild it on the
  way in. The core module keeps its existing `externref` representation
  internally.
- **(b) Resource types.** Give the guest an opaque handle and keep the
  collection host-side.

**Choose (a).** A vector of integers is a *value*, and the Canonical ABI already
has `list<T>` for exactly that; `component-wit` has been emitting `list<s64>`
on that assumption. Resources exist for handles with lifecycle and identity
(a connection, a file, a signing key) — modelling `u256` limbs as a resource
would put allocation and ownership of ordinary values in the host and give every
arithmetic step a host round-trip. Option (b) remains correct for genuinely
host-owned things and should be used when a capability provider needs one.

**Longer-term direction (not this ADR):** the marshalling in (a) exists only
because typed collections are host objects in the first place. Representing them
in linear memory throughout the backend removes the impedance mismatch and the
per-call copy. That is a larger change to the typed backend and should be its
own ADR; (a) is chosen here because it unblocks real programs without
destabilizing the existing representation.

### 5. Keep the allowlist as a fallback, and shrink it

`assert-supported!` stays, but inverts: the compositional lowering is tried
first, and the enumerated shapes remain only where a hand-written WAT is still
demonstrably better or where the general path is not yet proven. Each retained
shape needs a comment saying why. When the list reaches zero, delete it.

Rejection remains **fail-closed**: an unrepresentable type is rejected with a
diagnostic naming the type, never silently approximated.

## Acceptance

This ADR is done when all of the following hold, verified — not asserted:

1. A **multi-function program with capability imports** compiles to a validated
   component. `wasm-tools validate --features all` passes and `wasmtime` runs it.
2. A function taking and returning `list<s64>` round-trips a non-trivial vector
   through the component boundary with the values intact.
3. A signature exceeding `MAX_FLAT_PARAMS` compiles and runs correctly, proving
   the spill path rather than only the flat path.
4. Differential test: for every shape still in the allowlist, the compositional
   lowering and the hand-written WAT produce the same observable results.
5. The existing component tests (`component-wit`, `component-artifact`,
   `component-composition`, `component-admission`) still pass unchanged.

Acceptance criterion 4 is the one that matters most: it is what makes deleting a
hand-written shape safe rather than hopeful.

## Consequences

- The compiler can compile a general Kotoba application to a component, which is
  the precondition for every application in root ADR-2607252500's architecture,
  including the Ethereum client of ADR-2607254500.
- The lowering becomes reviewable as one implementation of a published
  specification instead of 16 bespoke generators.
- Adding a type to the language stops requiring a new WAT generator.
- Risk: a general lowering that is subtly wrong is worse than a narrow one that
  is right, because it fails on programs nobody hand-checked. Criterion 4 exists
  to bound that risk; until it holds for a shape, that shape keeps its
  hand-written path.
