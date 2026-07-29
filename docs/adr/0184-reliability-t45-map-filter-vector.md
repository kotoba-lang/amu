# ADR 0184: T4.5 bounded `map`/`filter` over vector-i64 (42→43)

- Status: Accepted
- Date: 2026-07-29
- WBS: T4.5 / T1.3

## Decision

Admit surface `map` and `filter` for **vector-i64** collections only, desugaring
to zero-charge `loop`/`recur` over `vector-count` / `vector-at` / `vector-conj`.
Loop helpers may return **`:vector-i64`** (not only `:i64`) via
`*loop-result-type*`.

| Form | Meaning |
|---|---|
| `(map (fn [x] expr) coll)` | Map each element; build new vector |
| `(map inc coll)` / `(map dec coll)` | Unary sugar |
| `(filter (fn [x] pred) coll)` | Keep elements where pred is true in `if` |

Empty source returns empty vector. Multi-source `map`, named HOF refs, and
pair-chain collections remain gated.

Pilot **42 → 43** (`map-filter-vector-kit` expect 30 =
`(+ 12 (+ 9 9))`).

## Evidence

- `map-filter-vector-test` + dual-backend conformance
- Loop result-type override + preserve declared helper `:result` in
  `resolve-loop-helper-param-types`
