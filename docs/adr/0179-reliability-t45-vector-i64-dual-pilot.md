# ADR 0179: T4.5 vector-i64 pure-product dual-backend pilot

- Status: Accepted
- Date: 2026-07-29
- WBS: T4.5 / T1.3

## Decision

Land pure-product dual-backend pilot `:vector-i64-kit`:

- `vector-i64` constructor → `vector-new`
- `vector-count` / `vector-at` / `vector-conj`
- Expect `27` (3 + 20 + 4)

Requires kotoba-wasm#37 (body ops seal `:vector-i64` without export signature).

Pilot **30 → 31**.

## Not claimed

- Bounded map/filter/reduce collection transforms (T4.5 residual)
- Hetero-vector dual-backend pilot

## Evidence

- `clojure -M:conformance` dual-green + goldens
