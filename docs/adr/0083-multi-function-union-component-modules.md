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
- finite record payload match computation is implemented by
  `kotoba-component` commits `7b50152` / `a6991f9`: sealed record binders are
  eliminated through typed `record-get` paths into selected joined-flat
  scalar slots, and all selected bool leaves validate even if unread. The
  compiler test starts at `.kotoba` source and executes the packaged
  Component;
- source schemas may now reference distinct nominal record roots while each
  referenced descriptor retains its own identity. Inline descriptors naming a
  closed schema must exactly match it before ref/descriptor type compatibility
  is admitted; the `.kotoba` Component test exercises a nested record through
  that path;
- selected string/keyword record leaves now support `string-byte-length`
  through `kotoba-wasm` commit `b6de0dc` and `kotoba-component` commit
  `fe9a70c`: the Canonical pointer/length pair is bounded against its
  descriptor and actual core memory, selected unread leaves validate, and
  inactive slots remain lazy;
- selected `list<s64>`/`list<f64>` record leaves now support their matching
  count operation through `kotoba-wasm` commit `db5b04f` and
  `kotoba-component` commit `0911651`: pointer alignment, item bounds,
  unsigned byte-size/range overflow, and actual memory size are checked;
  selected unread leaves validate and inactive slots remain lazy;
- selected scalar list elements may now be read with `vector-at`/
  `vector-f64-at` through `kotoba-wasm` commit `9550a08` and
  `kotoba-component` commit `058ff9a`; the same list checks run before an
  unsigned index check and aligned scalar load;
- fallback reads with `vector-get`/`vector-f64-get` are implemented by
  `kotoba-wasm` commit `0eb2cf9` and `kotoba-component` commit `ea2bc06`;
  malformed selected lists still trap before index fallback selection;
- aggregate match branches returning `list<s64>`/`list<f64>` are implemented
  by `kotoba-component` commits `de5af55` / `a5cc925` and compiler commit
  `b91b429`: a selected payload list, another vector parameter, or a bounded
  literal may feed copy-on-write drop/assoc/conj; every result uses a fresh
  Canonical buffer and result area, selected aggregate leaves validate,
  inactive joined slots stay lazy, and post-return permits repeated calls in
  one core instance without arena growth;
- nested/indirect list item types remain fail-closed pending recursive
  per-element validation and an ownership plan;
- linear reuse for repeated internal collection construction remains separate
  from the now-implemented bounded export-result ownership contract;
- scalar named capabilities now compose with aggregate match functions through
  `kotoba-wasm` commit `7359448` and `kotoba-component` commit `a5804c0`.
  The shared match emitter receives the exact WIT import table, generic
  canonical capability fallback is rejected, and a `.kotoba` option match is
  executed through a closed application-plus-provider Component;
- an `option<list<s64>>` or `option<list<f64>>` selected payload may now be reconstructed, passed to
  a named capability with the same request/result descriptor, and immediately
  matched through the shared module. `kotoba-wasm` commit `ab8dde1` keeps the
  maximum bounded request and result live in one arena; `kotoba-component`
  commits `6e4759b` / `efaf53f` bind the caller-allocated standard32 result without a
  generic host ABI. The evidence starts at `.kotoba`, composes an identity
  provider, and executes the closed Component in Wasmtime;
- other aggregate request/result descriptors and less constrained branch
  shapes remain fail-closed pending explicit shared Canonical codec admission.
- symmetric `result<list<T>, list<T>>` now uses the shared match module for
  both `ok` and `err` request branches. `kotoba-wasm` commit `ed5ce4f` checks
  the returned case and active list; `kotoba-component` commit `ac3156c`
  admits only the exact typed shape. Source E2E covers s64 and f64 lists.
- bounded string/keyword leaves now reuse the indirect `(pointer,length)`
  codec in option and symmetric result matches. `kotoba-wasm` commit
  `aaecaa4` separates payload alignment from union result alignment, and
  `kotoba-component` commit `4c6a617` validates both. `.kotoba` E2E covers
  string; keyword remains covered at typed KIR because source
  `string-byte-length` intentionally accepts only `:string`.
