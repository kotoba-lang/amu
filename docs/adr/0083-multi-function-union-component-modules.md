# ADR 0083: Multi-function structural-union Component modules

Status: accepted

## Context

ADR 0082 compiled exhaustive scalar option/result matches through the shared
binary expression emitter, but its adapter immediately emitted one standalone
core module. WIT generation and the binary backend already supported multiple
exports, so the remaining single-function restriction was an adapter
composition problem rather than a Component Model limitation.

## Decision

Split structural-union lowering into two phases:

1. transform each match function into a host-free scalar adapter function,
   recording its Canonical core parameter types and the bool payload positions
   that must be validated only after case dispatch;
2. collect all transformed match functions and ordinary Canonical scalar
   helpers/exports into one KIR v4 core module and emit it once.

The module may contain multiple exports or a single export with private scalar
helpers. Every function must either have a qualified structural-union match
plan or use only `i64`, `f32`, `f64`, and `bool`; a host-backed value anywhere
still rejects the entire host-free adapter module.

Per-function bool validation exclusions are keyed by function identity. A
joined i32 payload in one match therefore cannot disable entry validation for
an ordinary bool parameter at the same numeric index in another function.

All functions share the binary backend's one private monotonic fuel global.
Internal calls consume fuel normally; exports cannot replenish it.

WIT generation also rejects export-name or per-function parameter-name
collisions after canonical identifier normalization. This prevents two checked
KIR identities from silently becoming one WIT name when a module has several
exports.

## Security properties

- every discriminant and selected bool payload retains ADR 0082 validation;
- inactive joined payloads remain uninterpreted per function;
- adapter validation exemptions cannot leak across function boundaries;
- all exports share one non-exported fuel authority;
- no ambient WASI or typed host import is introduced;
- WIT identifier collisions fail before embedding or componentization.

## Evidence

One `.kotoba` module exports an `option<i64>` match, a heterogeneous
`result<bool,f32>` match, and an ordinary bool function, and contains a private
i64 helper. One generated Component executes every export in pinned Wasmtime
and matches `ir/execute`.

Direct core calls prove:

- fuel 1 traps on match-to-helper execution while fuel 2 succeeds;
- joined bits accepted by the active f32 case trap in the active bool case;
- an unrelated export's malformed ordinary bool parameter still traps.

Hand-built KIR fixtures prove colliding normalized export and parameter names
are rejected.

## Remaining gaps

- flat record payload identity for structural option/result is implemented by
  `kotoba-component` commit `3230520`, including active-case bool and bounded
  string/keyword validation;
- finite nested record and bare bounded string/keyword payload identity is
  implemented by `kotoba-component` commit `ed8e4b3`, with recursive
  active-case leaf validation;
- bounded `list<s64>` and `list<f64>` payload identity is implemented by
  `kotoba-wasm` commit `7e2bc34` and `kotoba-component` commits `3b99139` /
  `ceecdc5`: the shared public vector layouts drive selected-case count,
  alignment, overflow, and arena-range validation; the admitted input buffer
  remains borrowed until canonical post-return resets the arena;
- nested option/result payload identity is implemented by `kotoba-component`
  commit `fed370c`; every inner discriminant is range checked and only its
  selected payload recursively validates/stores;
- nested/indirect list item types and non-identity aggregate branch
  computation;
- general aggregate ownership and linearity analysis beyond this bounded
  identity/borrowed-result slice;
- general compositional lowering for mixtures of aggregate match functions and
  capability imports.
