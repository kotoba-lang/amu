# ADR 0194: T8.3 typed-set-nth frontend (guest set fold)

- Status: Accepted
- Date: 2026-08-01
- Depends: kotoba-kir ADR 0024; kotoba-wasm set-nth emit

## Decision

Admit `(typed-set-nth type set index) → item` in the frontend (desugar,
validate, typecheck). Enables pure packages to fold set members into EDN
vectors (full headers encode residual after provider ADR 0231).

## Evidence

- compile-source + KIR execute AcceptHost + EDN vector fold
