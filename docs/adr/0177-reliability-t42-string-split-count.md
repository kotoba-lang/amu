# ADR 0177: T4.2 `string-split-count` dual-backend

- Status: Accepted
- Date: 2026-07-29
- WBS: T4.2 / T1.3

## Decision

Ship **bounded** `string-split-count` (segment count) as the optional T4.2
split surface:

| Op | Arity | Result |
|---|---|---|
| `string-split-count` | 2 (haystack, sep) | i64 segment count |

Empty separator rejects. Full `string-split` → collection still deferred.

Pins: kotoba-kir (ADR 0022) + kotoba-wasm (ADR 0034). Pilot **29→30**.

## Evidence

- `:string-split-count-kit` expect 7 (3+1+3)
- `clojure -M:conformance` dual-green
