# ADR 0175: T1.3 pilot expand — if-some, string-byte-length, control sugar, bitops

- Status: Accepted
- Date: 2026-07-29
- WBS: T1.3 (progressive dual-backend matrix)

## Decision

Grow the pure-product dual-backend pilot **23 → 28** with surface already
admitted and executable on KIR + wasm32-kotoba-v1:

| Case | Expect | Notes |
|---|---|---|
| `if-some-kit` | 10 | T4.3: `option-some-of` / `option-none-of` + `if-some` |
| `string-byte-length-kit` | 4 | T4.2 surface (byte length + char length) |
| `when-cond-kit` | 21 | `when` + `cond` + `if-let` |
| `case-kit` | 20 | `case` |
| `bitops-kit` | 10 | `bit-and` / `bit-or` / `bit-xor` |

Also align `cli_test` structured diagnostic code with T3.1
(`:kotoba.error/subset-reject`).

## Not claimed

- Full kotoba-lang conformance matrix (collections still gated)
- `string-split` (still deferred)
- Typed-map pure pilot
- Zero-charge `recur`

## Evidence

- `clojure -M:conformance` 28/28
- `clojure -M:conformance --check-golden`
