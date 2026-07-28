# ADR 0176: T4.4 typed-map pure-product dual-backend pilot

- Status: Accepted
- Date: 2026-07-29
- WBS: T4.4 / T1.3

## Decision

Land pure-product dual-backend pilot case `typed-map-kit` for bounded
`[:map :i64 :i64]`:

- `typed-map-new` / `typed-map-assoc` / `typed-map-count`
- `typed-map-get` + `if-some` (some + none paths)
- `typed-map-contains` (via `if`)
- `typed-map-equal`

Pilot count **28 → 29**. Expect `28`.

This closes the “typed-map pure pilot deferred” gap recorded in the record
cookbook (T4.4 partial → dual-green evidence).

## Not claimed

- Keyword keys / heterogeneous value maps as pure-product default
- Public product host `call-record` already separate (T5.2 partial)
- Full collection transform dual-backend (T4.5 ops still gated)

## Evidence

- `clojure -M:conformance` includes `:typed-map-kit`
- `--check-golden` digests updated
