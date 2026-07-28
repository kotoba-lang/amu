# ADR 0162: Reliability T4.2 string kit — bounded `string-join`

- Status: Accepted
- Date: 2026-07-28
- WBS: T4.2

## Context

T4.2 asks for a string kit: length, from-i64, join (bounded), split (optional).
Length (`string-length` / `string-byte-length`) and `string-from-i64` already
ship (PVA v1). Join was missing; split remains optional.

## Decision

1. Add surface op **`string-join`**:
   - `(string-join sep)` → `""`
   - `(string-join sep a)` → `a`
   - `(string-join sep a b …)` → nested `string-concat` with `sep` between parts
2. **Bound:** at most **8** parts after the separator (reject otherwise).
3. Implement as **frontend desugar** only (same pattern as `string-from-i64`) so
   every backend that already has `string-concat` works without new wasm
   intrinsics.
4. **`string-split` deferred** (optional in WBS); needs bounded collection return.

## Evidence

- `frontend.cljc` desugar + defensive typing
- `string_operation_test.clj` KIR + js + wasm32 dual checks

## Related

- T4.1 stdlib freeze, T4.3 option guide
- PVA v1 string-from-i64 helpers
