# ADR 0194: T8.3 typed-set-nth frontend + host (guest set fold)

- Status: Accepted
- Date: 2026-08-01
- Depends: kotoba-kir ADR 0024 (`4213cc7a`); kotoba-wasm set-nth emit (`0ec47a66`)

## Context

ADR 0231 pure kit-shaped request records hold
`[:headers [:set [:ref header]]]` but EDN encode could only emit **headers-n**
without indexing set items. KIR landed `(typed-set-nth type set index)`;
wasm emit landed `set-nth-{i64,ref}` imports. Compiler frontend + browser-host
still rejected the form / import.

## Decision

1. Admit `typed-set-nth` in frontend ops, desugar, validate, and type-infer
   (result = set item type; index `:i64`).
2. Pin kotoba-kir → `4213cc7a`, kotoba-wasm → `0ec47a66`.
3. browser-host: allowlist + implement `set-nth-i64` / `set-nth-ref` over the
   sorted item vector (OOB → invalid-typed-operation).
4. Guest fold for EDN uses a **recursive helper** (string `loop` type residual
   is separate).

Honesty:

- Bound ≤32 items; OOB traps.
- Does **not** flip ops `:wasm-aot :implemented` (W4 recursive nested EDN open).

## Evidence

- `typed-set-nth-test`: simple nth + fold EDN shape `["Accept" "Host"]`
- Live browser-host import of set-nth packages

## Related

- T8.3; provider ADR 0231 follow-up (full headers EDN fold)
- kotoba-kir ADR 0024; kotoba-wasm PR #47
