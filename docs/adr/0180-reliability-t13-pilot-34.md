# ADR 0180: T1.3 pilot expand 31→34 (vector-mut, map-dissoc, quot/bit-not)

- Status: Accepted
- Date: 2026-07-29
- WBS: T1.3 / T4.4 / T4.5

## Decision

Grow pure-product dual-backend pilot with already-admitted surface:

| Case | Expect | Notes |
|---|---|---|
| `vector-mut-kit` | 108 | assoc + drop + get-fallback |
| `typed-map-dissoc-kit` | 1 | dissoc then count |
| `quot-bitnot-kit` | 18 | `quot` + `bit-not` |

Pilot **31 → 34**.

## Not claimed

- map/filter/reduce transforms
- string-split → collection

## Evidence

- `clojure -M:conformance` 34/34 + goldens
