# ADR 0088: W5 family-4 first slice — state dual-runtime semantic vectors + cljs i64 versions

Status: accepted; intermediate W5 family-4 evidence (reference + cljs), not
family exit (wasm packaging for state already exists under ADR 0060/0061)

## Decision

Start **Delivery 5 / W5 host capability qualification** family 4
(**state and storage**) with `state-v1` dual-runtime semantic vectors on
`:clj` and nbb `:cljs`, and close the version-counter i64 defect:

Entry `:version` is an `:i64` ABI field. On `:cljs` the canonical
representation is JS `bigint` (same rule as clock/log/http). Plain `inc`
produced numbers that fail `typed-cap-call` result validation. Fixed in
`provider.state` (kotoba-lang/provider).

## Evidence

- `test/kotoba/compiler/state_provider_test.clj` — round-trip, isolation,
  capacity typed error, missing-grant denial
- `test/nbb/state-provider.cljs` — same four vectors on cljs with bigint
  versions
- provider#4 — cljs i64 version counters
- State wasm packaging already landed (ADR 0060/0061 `state-provider-wat`)

## What this does NOT claim

- Storage dual-runtime (next within family 4)
- Full family-4 exit (timeout/quota/cancellation matrices; storage cljs
  transport)
- Change to `:wasm-aot` flags (state remains pending at kit level despite
  real WAT — same honesty bar as prior ADRs)

## Related

- ADR 0060/0061/0067 — state wasm provider
- ADR 0079/0086 — dual-runtime pattern for log/clock/http
- Migration plan W5 item 4
