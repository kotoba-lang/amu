# ADR 0182: T4.5 inc/dec desugar + vector-sum loop pilot (38→41)

- Status: Accepted
- Date: 2026-07-29
- WBS: T4.5 / T1.3

## Decision

1. **`inc` / `dec`** desugar to `(+ x 1)` / `(- x 1)` in frontend (stdlib sugar;
   dual-backend via existing arithmetic).
2. **`vector-sum-kit`**: reduce over `vector-i64` with zero-charge `loop`/`recur`
   (explicit author pattern until map/filter/reduce sugar is admitted).
3. **`shift-right-kit`**: `i64-shift-right` dual-backend.

Pilot **38 → 41**.

## Not claimed

- First-class `map` / `filter` / `reduce` sugar (still subset-reject)
- string-split → collection

## Evidence

- `clojure -M:conformance` 41/41 + goldens
