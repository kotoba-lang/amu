# ADR 0075: `wasm-component-kotoba-v1` as a compile target, declared fuel/memory budgets, and the compiler's admission request

**Status**: accepted
**Date**: 2026-07-25

## Context

[ADR-2607252500](https://github.com/com-junkawasaki/root/blob/main/90-docs/adr/2607252500-kotoba-wasm-component-first-execution-boundary.edn)
makes a Wasm Component the primary Kotoba application artifact and assigns
roles: the language owns effect/type semantics, **the compiler owns the WIT and
the component artifact**, and `kototama` owns admission, linking, composition
and runtime.

`kototama/component-platform.edn` already encodes the runtime half of that
contract: target `:wasm-component-kotoba-v1`, WASI `0.3.0`,
`:required-budgets [:fuel :memory-pages]` for the `:sync` profile, and an
admission envelope whose key set
`kototama.component-platform/validate-world!` checks exactly.

The compiler half was partially present. `component-core`/`component-artifact`
could already lift a qualified slice into a validated component binary via the
pinned `wasm-tools` toolchain, and `component-wit` emitted the WIT package. But:

1. There was no `wasm-component-kotoba-v1` **target profile**, and no CLI route
   to it — `compile-component` existed only as an API function.
2. The core module's fuel global was the fixed constant `512`
   (`(global (mut i64) (i64.const 512))`), so a component could not declare the
   budget its own platform contract requires as a per-component value.
3. Nothing emitted the admission envelope kototama validates.

## Decision

### 1. `wasm-component-kotoba-v1` is a real target, routed explicitly

`target/profiles` gains the profile (`:execution :component`,
`:wasi-version "0.3.0"`, `:ambient-wasi false`). The target keyword is
character-identical to `component-platform.edn`'s `:target`, so an artifact
compiled here and an envelope validated there cannot silently disagree.

`compile-source*` **rejects** component targets with a diagnostic naming
`compile-component`. A component is a core module lifted through the Canonical
ABI, not one more backend output; letting it fall through to the wasm32 backend
would emit a bare core module under a component target name — valid-looking and
wrong.

The CLI accepts `--target component` and writes three files together: the
binary, the `.wit` world it was lifted against, and the `.admission.edn`
request. An artifact should not circulate without the interface and the bounds
it claims.

### 2. Fuel is a declared budget, not a codegen constant

`backend.wasm/emit` accepts `:fuel`. The value is SLEB128-encoded into the
module's fuel global. **The enforcement mechanism is unchanged** — charge one
unit per call, trap at zero, no guest replenishment. Only the initial value
moved from a literal in the emitter to a caller-supplied budget.

`default-fuel` is 512, so every existing core-wasm caller is byte-identical to
before; a test asserts that supplying no `:fuel`, `{}`, and `{:fuel 512}` all
produce the same bytes. Non-integer, non-positive, and over-ceiling budgets are
rejected rather than silently defaulted: a budget that cannot be enforced must
not look like one that can.

`component-core/fuel-enforcement` reports `:module-global` or `:host-only`.
The shape-specific WAT paths (see "Known limitation") have no fuel global at
all, so for those the declared budget is host-enforced only. The envelope says
which, because a declared budget that reads as guest-enforced when it is not is
worse than no budget.

### 3. The compiler emits an admission *request*, not an envelope

`component-admission/request` emits eight of the ten envelope keys. It
deliberately omits two:

- **`:grants`** is the authority decision. `component-platform.edn` fixes
  `:authority {:imports :declared-and-granted-only}`, and ADR-2607252500 places
  grant policy in the aiueos control plane with a native micro-TCB
  independently re-verifying it. A compiler that emitted its own grants would
  be asserting the very property the admission check exists to test.
- **`:provider-bindings`** is a composition decision. `component-composition`
  resolves it against real provider artifacts and the contract requires the
  binding be `:exact`.

`component-admission/complete` composes the full ten-key envelope from a
request plus those two, and re-checks import/grant and import/binding
correspondence locally so a malformed envelope fails here rather than at the
runtime boundary.

Identities are real CIDv1 (`0x01 0x55 0x12 0x20` + sha2-256, multibase base32),
verified in test against the published empty-block CID
`bafkreihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku`.
**When no package lock is supplied, `:identity` is omitted** and
`:identity-inputs-missing` names what is absent. kototama's `cid-looking?` gate
only checks the multibase prefix, so a fabricated CID would pass it while
binding the component to a supply chain nobody verified. Refusing to emit is
the honest failure.

## Known limitation (not addressed here)

Canonical ABI lowering in `component-core` is **enumerated per program shape**,
not derived from types: roughly 25 shape recognizers feeding 16 hand-written
WAT generators (`scalar-record-wat`, `variant-capability-wat`, …).

Two consequences, which are the same root cause:

- **Capability imports work only in the four single-function
  `*-capability-call` shapes.** `component-artifact/assert-qualified-slice!`
  rejects any program that has WIT imports under a different lowering, so a
  multi-function program that uses even one capability is refused. (The
  general `:scalar` lowering does support many functions — the restriction is
  imports, not arity.)
- **Typed collections cannot cross the boundary.** They are host objects behind
  `externref` (`0x6f`) in the core module, and the Canonical ABI has no
  `externref`. `component-wit` already maps `:vector-i64` to `list<s64>`, so
  the WIT side anticipates a representation the core side cannot yet provide.

Generalizing this means a compositional Canonical ABI lowering derived from the
type: flattening, the 16-param/1-result spill to linear memory, realloc and
post-return wiring, utf8 string encoding, and record/variant/option/result/list
layout with correct alignment. That subsumes most of the 16 bespoke generators
and is the prerequisite for any real application — including the Ethereum
execution client scoped in root ADR-2607254500. It is deliberately **not**
attempted in this ADR; it needs its own design, and doing it badly would be
worse than the current honest fail-closed allowlist.

## Consequences

- `kotoba compile --target component` produces a validated component, its WIT
  world, and its admission request.
- A component's declared fuel budget and the budget compiled into its module
  are the same number, or the artifact says they are not.
- Core-wasm output is unchanged byte-for-byte when no budget is declared.
- The compiler still cannot compile a general Kotoba application to a
  component. That gap is now stated in one place instead of being discovered
  per shape.
