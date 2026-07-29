# ADR 0187: T4.5 2-source map + list/control pilots (49→52)

- Status: Accepted
- Date: 2026-07-29
- WBS: T4.5 / T1.3

## Decision

1. **2-source `map` (T4.5 residual):** admit `(map f a b)` for vector-i64 sources
   with **shortest-collection** termination. `f` is `(fn [x y] expr)` or a named
   arity-2 module `defn`. 3+ sources remain deferred (param budget).
2. **List rest pilot (T1.3):** `second` / `rest` dual-green on pair-chains.
3. **Control pilot (T1.3):** `when-let` + `u64-shift-right` + `false` + `<=`/`>=`.
   Nested `do` is not yet wasm-typed-qualified (solo body `do` works).

Pilot **49 → 52** (`multi-map-kit` 53, `list-rest-kit` 7, `when-let-u64-kit` 14).

## Evidence

- Unit tests + dual-backend conformance goldens
