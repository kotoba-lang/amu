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

### 4a. Correction (2026-07-25): option (a) is not implementable

Decision 4 above is wrong, and it is worth stating plainly because acting on it
would cost a substantial implementation effort before failing.

**Marshalling a host collection at the boundary requires calling the host to
read it** -- `vector-count`, `vector-at-i64` and friends, which live in the
`kotoba:typed` intrinsic module. **A component cannot import those.** Every core
import of a component must resolve against its WIT world, and `kotoba:typed` is
not a WIT interface; it is a host intrinsic table. Inside a component there is no
host to call, so the marshalling code option (a) calls for cannot be written.

The evidence was already in this repository. Every one of the sixteen
hand-written WAT generators in `component-core` imports **only**
`cm32p2|kotoba:application/<interface>@1` -- WIT-bound capabilities. Not one
imports `kotoba:typed` or `kotoba:heap`. Instead they contain 23
`i64.store`/`i32.store` sites: they **construct their records, variants and
strings directly in linear memory**, because that is the only thing that works.
Read as sixteen ad-hoc shapes, they obscured the fact that they were already
demonstrating the correct representation.

So the work is not a marshalling layer over the existing host-object
collections. It is a **linear-memory representation** for them in the component
profile -- what the paragraph above filed as the longer-term direction, promoted
here to the actual plan. Option (b), resource types, stays rejected for value
types for the reason already given; this correction does not revive it.

The prerequisites are concrete and currently absent: `emit-component-core`
declares `(section 5 [1 0 0])` -- a **zero-page** memory -- and a
`cm32p2_realloc` whose entire body is `i32.const 0`, a stub. Both are correct
for a scalar-only signature and useless for anything else. A real bounded bump
allocator already exists in WAT form (`bounded-bump-realloc-wat`: alignment,
capacity trapping, old-content preservation) and is what to port into the binary
emitter first.

**Revised order for acceptance criterion 2.**

1. A non-zero memory and a real bump `cm32p2_realloc` in the binary emitter,
   ported from `bounded-bump-realloc-wat`. Self-contained and independently
   testable. **Done 2026-07-25**: one page, bump pointer as global 1 based at 8,
   verified by `wasm-tools validate`, by the printed instruction sequence
   matching the WAT, and by executing the allocator under `wasmtime`. ADR 0077
   revises the page count upward.
2. A linear-memory representation for `:vector-i64` in the component profile.
   This deserves its own ADR: it changes how a typed collection is represented,
   not just how one crosses a boundary. **Written: ADR 0077.** Its finding is
   that the deciding constraint is not layout but allocation -- collections are
   persistent (`ir/eval-expr`'s `vector-conj` is `(conj items item)`) and the
   arena never frees, so building a 16384-item vector by repeated `conj` would
   allocate 1.0 GiB. ADR 0077 admits single-shot construction now and defers
   `conj` chains to a linearity analysis.
3. The Canonical `list<T>` layout (ptr/len pair, return area for the
   `MAX_FLAT_RESULTS = 1` spill) on top of it.

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
   **Done (increment 1, 2026-07-25)** for scalar capability calls:
   `component-core/scalar-capability-imports` derives a per-capability typed core
   import from the KIR and the WIT contract, so shape no longer matters. The four
   hand-written `*-capability-call` shapes stay ahead of it in
   `assert-supported!`, so existing artifacts are byte-identical.
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
