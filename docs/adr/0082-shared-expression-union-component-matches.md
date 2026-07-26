# ADR 0082: Shared-expression structural union Component matches

Status: accepted

## Context

ADR 0080 added direct predicates and fallback projections, but exhaustive
`match-option` and `match-result` remained rejected. Adding a second WAT
expression compiler inside `component-core` would duplicate arithmetic,
comparison, `if`, `let`, call, and fuel semantics already owned by the binary
Wasm backend.

## Decision

Admit exhaustive matches whose option/result payloads, final result, and
additional parameters are Canonical scalars (`i64`, `f32`, `f64`, or `bool`).
The two payloads of a result may differ.

`component-core` performs only an adapter transformation:

1. replace the structural union parameter with a Canonical `i32`
   discriminant and joined native scalar payload;
2. unsigned-extend the discriminant into the emitter's i64 value
   domain;
3. range-check it against the two valid cases before dispatch;
4. decode the joined payload into the selected case's scalar type using the
   same authoritative coercion classification as the general variant codec;
5. bind the decoded payload to the source branch binder through an ordinary
   `let`;
6. hand both original branch expressions to the existing binary Wasm
   expression emitter.

Joined `i32/f32` slots stay i32. Every other heterogeneous pair joins to i64.
The adapter renders the Component Model coercions as native binary Wasm
`wrap`/`reinterpret` instructions; no numeric conversion or NaN
canonicalization is substituted for bit reinterpretation.

The backend has a narrowly scoped `core-param-types` override so the synthetic
function receives the Canonical i32 discriminant and native payload types. It
also has an explicit `component-canonical-scalars?` mode: the shared typed
expression emitter keeps `i64`, `f32`, and `f64` native and represents
Canonical `bool` as checked `i32`, rather than the ordinary KIR v4 host
`externref`. Normal compilation does not select this mode and retains its
existing ABI.

The transformed function is emitted as a host-free scalar KIR v4 adapter so
float arithmetic, conversion, comparison, `if`, `let`, and calls reuse the
existing typed expression implementation. The mode suppresses typed host
imports only after Component admission has proved every value is one of the
four native Canonical scalars. Component packaging still embeds the WIT
derived from the original checked KIR, not the synthetic adapter KIR.

Fresh adapter locals are selected deterministically against source parameter
names. Branch binders remain lexical `let` bindings, so nested shadowing is
handled by the ordinary emitter rather than textual symbol substitution.

## Security properties

- discriminants are unsigned-extended and checked before branch dispatch;
  negative i32 bit patterns become large positive i64 values and trap;
- exactly one branch executes, preserving lazy failure and effects;
- malformed hand-built KIR branch counts or non-symbol binders fail admission;
- bool parameters and selected bool payloads are checked for canonical 0/1,
  while an inactive joined payload is not interpreted;
- joined bits are decoded only after discriminant validation, so one case
  cannot impose its type validation on another case's active payload;
- the standard module-private fuel global charges the match function;
- no ambient import or typed host heap is introduced.

## Evidence

`.kotoba` option and result programs compile through `compile-component`.
Their branches exercise i64, f64, f32, and bool operations, outer parameters,
and lexical binders. `none`, `some`, `ok`, and `err` executions in the pinned
real Wasmtime engine match `ir/execute`, and the artifacts have no host import.

A lazy fixture puts division-by-zero exclusively in the `some` branch:
`none` returns normally and `some` traps. Direct core invocation with
discriminant `2` traps before dispatch. The artifact reports
`:fuel-enforcement :module-global`. Direct bool-core calls prove an invalid
active payload traps, the same bits in an inactive option payload are ignored,
and an invalid ordinary bool argument traps at entry.

All twelve ordered heterogeneous pairs of `i64`, `f32`, `f64`, and `bool`
execute both `ok` and `err` through a real Component in Wasmtime and match
`ir/execute`. Negative float fixtures prove sign-bit reinterpretation rather
than numeric conversion. Direct `result<bool,f32>` and `result<f32,bool>` core
calls prove the joined i32 slot is bool-validated only in the bool case.

ADR 0083 generalizes this adapter into multi-function and multi-export modules
without changing the match semantics recorded here.

## Remaining gaps

- nested option/result, record, string, and list payloads;
- general aggregate computation and ownership/linearity analysis.
