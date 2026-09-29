# ADR 0354 — Language semantics are target-independent; wasm32 is one build target

- Date: 2026-09-29
- Status: Accepted (owner decision, 2026-09-29).
- Amends: ADR 0162 (the 8-part `string-join` cap), and every note in this
  repository that treats "lowers on wasm32" or "works on every backend" as a
  condition of admitting a language feature.
- Related: `docs/selfhost-priority.md`, `docs/architecture.md` ("one compiler,
  multiple verified backends"), `lang/surface-status.edn` in
  `kotoba-lang/kotoba-lang` (per-head backend status).

## Context

The Amu compiler is a native compiler. wasm32 (`wasm32-browser`,
`wasm32-wasi`) is one of several targets it emits, next to the native
AArch64 / x86_64 targets, KIR, and the JS route. In practice several design
decisions were made as if wasm32 were the definition of the language:

- ADR 0162 capped `string-join` at 8 parts and rejected `string-split`
  because a collection return "needs" a wasm intrinsic, so the feature was
  built only from what wasm32 already lowered.
- Notes such as "desugar to existing wasm-safe ops preferred", "works on every
  backend that already has `string-concat`", and "lowers on wasm32" appear as
  the acceptance test for a stdlib or frontend feature.

The cost is measured. The selfhost scoreboard
(`docs/selfhost-priority.md`) is dominated by walls where the compiler's own
sources need something ordinary — a runtime-length collection of strings, a
`join` over a computed sequence, `split` — that the language does not offer
because it could not be expressed with wasm32-era primitives. The 8-part cap
was not a safety bound; it was the size of an unrolled expansion.

## Decision

1. **The language is defined by its semantics, not by its narrowest backend.**
   A feature is admitted when its typed semantics, effects, resource bounds and
   capability requirements are specified and a reference implementation (the
   KIR interpreter) agrees with them. It is not required to lower on wasm32,
   nor on any single target, first.

2. **A target that cannot yet lower an admitted feature refuses it by name.**
   The refusal is a target refusal (exit 65), reported with the feature and the
   target, and recorded in `lang/surface-status.edn` as backend status for that
   head. The feature is not removed, capped, or rewritten into something
   weaker to make the narrowest target pass. This is the existing rule for
   features that do not reach every backend (`guest-grammar.edn`,
   `:backend-note`), promoted from an exception to the design.

3. **No backend has a veto over the language.** wasm32 gets the same standing
   as every other target: it implements what it can, refuses the rest by name,
   and gains features as its lowering is written. Native targets are the
   reference for what the compiler is for (selfhost); a feature the native
   compiler needs to build itself is not deferred for lack of a wasm32 lowering.

4. **Limits are stated as limits with a reason.** A cap is kept only when it
   bounds a resource or protects an invariant (for example
   `max-expression-nodes`, `max-lowered-nodes`, admission size). A cap that only
   records what one backend could do at the time is removed. ADR 0162's
   8-part `string-join` cap is removed by this ADR.

5. **Portable oracles stay.** Semantic vectors that run on more than one
   target remain the way a feature's meaning is pinned down; a target that
   runs them must agree. A target that does not run them yet is listed as not
   implemented in the surface status, not treated as a failure of the feature.

6. **What does not change.** The shared safety pipeline still precedes every
   backend and no backend may weaken the source subset, inferred effects,
   resource bounds or capability requirements (`docs/architecture.md`). Fail
   closed remains the default; nothing here adds a JVM, GraalVM or Node
   fallback.

## Consequences

- Selfhost work is no longer gated on wasm32 lowerings. Runtime-length string
  collections (and `join` / `split` over them) are designed against the
  native targets and the KIR interpreter; wasm32 follows.
- Every new frontend feature ADR states, per target, one of: lowers,
  refused by name (with reason), or not yet implemented. "Works on every
  backend" is no longer an acceptance criterion; it is a status.
- Existing text that says stdlib ops should "desugar to existing wasm-safe
  ops" is read as a preference for reuse, not a requirement.
- `wasm32-browser` and `wasm32-wasi` builds may refuse more programs than
  native builds until their lowerings catch up. That is expected and visible
  in the surface status, not hidden by narrowing the language.
