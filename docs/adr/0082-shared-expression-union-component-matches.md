# ADR 0082: Shared-expression structural union Component matches

Status: accepted

## Context

ADR 0080 added direct predicates and fallback projections, but exhaustive
`match-option` and `match-result` remained rejected. Adding a second WAT
expression compiler inside `component-core` would duplicate arithmetic,
comparison, `if`, `let`, call, and fuel semantics already owned by the binary
Wasm backend.

## Decision

Admit exhaustive matches whose option/result payloads and final result are
`i64`; any additional function parameters must also be `i64`.

`component-core` performs only an adapter transformation:

1. replace the structural union parameter with a Canonical `i32`
   discriminant and joined `i64` payload;
2. unsigned-extend the discriminant into the ordinary emitter's i64 value
   domain;
3. range-check it against the two valid cases before dispatch;
4. bind the payload to the source branch binder through an ordinary `let`;
5. hand both original branch expressions to the existing binary Wasm
   expression emitter.

The backend gains a narrowly scoped `core-param-types` override so the
synthetic scalar function can receive the Canonical i32 discriminant while all
ordinary Kotoba values remain i64. It also gains the internal
`i64-extend-i32-u` bridge instruction used by this adapter. Normal compilation
does not supply the override and is byte-for-byte on its previous path.

The transformed function is emitted as KIR v3 intentionally: its only values
are native i64 scalars and the one explicitly typed core i32 adapter parameter,
so it needs no `kotoba:typed` imports. Component packaging still embeds the WIT
derived from the original checked KIR, not the synthetic adapter KIR.

Fresh adapter locals are selected deterministically against source parameter
names. Branch binders remain lexical `let` bindings, so nested shadowing is
handled by the ordinary emitter rather than textual symbol substitution.

## Security properties

- discriminants are unsigned-extended and checked before branch dispatch;
  negative i32 bit patterns become large positive i64 values and trap;
- exactly one branch executes, preserving lazy failure and effects;
- malformed hand-built KIR branch counts or non-symbol binders fail admission;
- the standard module-private fuel global charges the match function;
- no ambient import or typed host heap is introduced.

## Evidence

`.kotoba` option and result programs compile through `compile-component`.
Their branches use multiplication, addition, subtraction, outer parameters,
and lexical binders. `none`, `some`, `ok`, and `err` executions in the pinned
real Wasmtime engine match `ir/execute`.

A lazy fixture puts division-by-zero exclusively in the `some` branch:
`none` returns normally and `some` traps. Direct core invocation with
discriminant `2` traps before dispatch. The artifact reports
`:fuel-enforcement :module-global`.

## Remaining gaps

- f32/f64/bool payload and result matches through a host-free typed scalar
  expression emitter;
- nested option/result, record, string, and list payloads;
- match expressions in multi-function Component modules;
- general aggregate computation and ownership/linearity analysis.
