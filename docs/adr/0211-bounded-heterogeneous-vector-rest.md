# ADR 0211: bounded heterogeneous-vector rest

Status: accepted

## Context

Nested destructuring already preserves exact child descriptors, but `[head &
rest]` still lowered to homogeneous `vector-drop`. For a heterogeneous vector,
the suffix has a different descriptor, so accepting the old operation would
erase its types. This left an otherwise idiomatic Kotoba pattern rejected.

## Decision

The type-directed projection pass specializes `vector-drop` over a
heterogeneous receiver when its drop count is an in-range integer literal. It
slices the compile-time item descriptor and lowers the operation to a fresh
`hetero-vector-new` populated by exact `hetero-vector-at` projections. A
synthetic `let` binds the receiver once, preserving evaluation semantics.

The descriptor is bounded by the existing 32-item heterogeneous-vector limit.
Dropping exactly the vector length produces the valid empty descriptor
`[:vector []]`. Dynamic, negative, and out-of-range counts remain compile
errors. No backend primitive or runtime descriptor interpretation is added.

Closed vector literals infer an exact descriptor when every item is itself a
typed literal. All-i64 and all-f64 literals retain their homogeneous owned
representations; mixed scalars and nested closed vectors lower to a bounded
heterogeneous vector. Expressions whose descriptor is not statically evident
keep the prior i64-vector path and fail through ordinary type checking instead
of guessing. Thus `[1 [2 3] 4 5]` is sufficient source for the nested-rest
case; it does not require an authored `hetero-vector` descriptor.

The same type-directed branch selects `vector-f64-drop` for homogeneous
floating vectors; ordinary i64 vectors retain `vector-drop`.

Because a heterogeneous position is statically known to exist, its familiar
three-argument `nth` form also erases to the same exact projection after
checking that the unreachable default has the child type. This keeps generic
destructuring code source-compatible without adding runtime missingness.

## Evidence

`type-directed-access-test` executes non-empty and empty heterogeneous rest
bindings, checks exact suffix construction and primitive erasure, and verifies
literal/range rejection. The `:nested-let-destructuring` conformance case
executes the composed closed literal, nested pattern, typed-map default, and
heterogeneous rest surface with result `29` on KIR and Wasm. Existing KIR,
restricted ESM, and Wasm lowering remain unchanged because the rewrite emits
already-supported typed primitives.
