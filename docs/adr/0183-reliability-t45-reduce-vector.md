# ADR 0183: T4.5 bounded `reduce` over vector-i64 (41→42)

- Status: Accepted
- Date: 2026-07-29
- WBS: T4.5 / T1.3

## Decision

Admit surface `reduce` for **vector-i64** collections only, desugaring to a
zero-charge `loop`/`recur` over `vector-count` / `vector-at`:

| Form | Meaning |
|---|---|
| `(reduce + init coll)` | Binary arithmetic op as reducer (`+ - * bit-and bit-or bit-xor`) |
| `(reduce (fn [acc x] expr) init coll)` | Single-expr anonymous reducer |

Empty vector returns `init`. Pair-chain / map / filter sugar still gated.

Pilot **41 → 42** (`reduce-vector-kit` expect 72).

## Evidence

- `reduce-vector-test` + dual-backend conformance
