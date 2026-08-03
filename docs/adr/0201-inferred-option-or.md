# ADR 0201: Inferred `option-or`

Status: accepted

## Context

Kotoba's generic Option ABI deliberately keeps its payload descriptor in the
lowered `option-value-of` operation. Repeating that descriptor at every source
fallback site is representation ceremony, especially for nested document and
typed-map access. The repository inventory measured 121 authored
`option-value-of` calls but only two `some->` calls.

## Decision

Admit `(option-or option fallback)` as type-directed frontend sugar. After
ordinary desugaring and signature inference, the frontend infers the Option
type and rewrites the form to the existing
`(option-value-of [:option T] option fallback)` representation. A second result
inference pass covers unannotated functions whose body uses the sugar.

The rewrite accepts Option values obtained from typed locals, constructors,
record fields, let bindings, and function results. Non-Option inputs and
fallback payload mismatches fail closed with source metadata preserved.

`if-some`, `when-some`, `some->`, and `some->>` remain the preferred forms when
control flow is the intent. `option-or` is specifically the total
value-with-default operation.

## Consequences

No KIR, ABI, evaluator, codec, capability, or backend operation is added.
Every downstream stage continues to see only `option-value-of`. JVM and NBB
tests cover constructor, document, local, function-result, inferred-return,
and rejection cases.
