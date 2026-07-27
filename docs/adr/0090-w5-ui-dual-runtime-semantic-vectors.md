# ADR 0090: W5 family-5 first slice — UI dual-runtime semantic vectors + cljs i64 revisions

Status: accepted; intermediate W5 family-5 evidence (reference + cljs), not
family exit and not DOM reconciliation wasm packaging

## Decision

Start **Delivery 5 / W5 host capability qualification** family 5
(**UI commit/event and DOM reconciliation**) with `ui-v1` dual-runtime
semantic vectors on `:clj` and nbb `:cljs`, and close the revision i64 defect:

`base-revision`, view `revision`, `node-count`, event `revision`, and
`after-revision` are `:i64` ABI fields. On `:cljs` the canonical
representation is JS `bigint`. Plain `inc`/`=`/`<=` against numbers failed
typed-cap-call results and revision matching. Fixed in `provider.ui`.

## Evidence

- `test/kotoba/compiler/ui_provider_test.clj` — declarative commit/events,
  stale revision, node/typed-set limit, missing-grant denial
- `test/nbb/ui-provider.cljs` — same four vectors on cljs with bigint
  revisions
- provider#6 — cljs i64 revisions
- No DOM host objects cross the boundary (ADR 0072 log/ui no-transport)

## What this does NOT claim

- `:wasm-aot` / ui-provider-wat
- Real browser DOM reconciliation (W4 document path is separate)
- Full family-5 exit

## Related

- ADR 0072 — log/ui no-transport
- ADR 0088/0089 — dual-runtime pattern for state/storage
- Migration plan W5 item 5
