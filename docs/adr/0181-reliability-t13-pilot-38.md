# ADR 0181: T1.3 pilot expand 34→38 (pred, when-ext, if-some-string, shift)

- Status: Accepted
- Date: 2026-07-29
- WBS: T1.3 / T4.3

## Decision

| Case | Expect | Notes |
|---|---|---|
| `pred-kit` | 4 | zero?/pos?/neg?/not= |
| `when-ext-kit` | 10 | when-not + when-some |
| `if-some-string-kit` | 2 | if-some on `[:option :string]` |
| `shift-kit` | 8 | i64-shift-left |

Pilot **34 → 38**.

## Not claimed

- map/filter/reduce dual-backend (still admission-gated)
- string-split → collection

## Evidence

- `clojure -M:conformance` 38/38 + goldens
