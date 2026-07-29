# ADR 0186: T1.3/T4.5 reduce-named + pair/list + string-length (46→49)

- Status: Accepted
- Date: 2026-07-29
- WBS: T1.3 / T4.5 / T4.2

## Decision

1. **Named binary reduce (T4.5):** `(reduce named-fn init coll)` admits an
   arity-2 module `defn` (same fail-closed model as named map/filter).
2. **Pair/list pilot (T1.3):** `pair` / `cons` / `first` / `empty?` dual-green.
3. **String length/concat pilot (T1.3/T4.2):** `string-length` (alias) +
   `string-concat` dual-green (split→collection still deferred).

Pilot **46 → 49** (`reduce-named-kit` 22, `pair-list-kit` 15,
`string-length-concat-kit` 7).

## Evidence

- Unit tests + dual-backend conformance goldens
