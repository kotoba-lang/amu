# ADR 0086: W5 family-2 first slice — HTTP egress dual-runtime semantic vectors + cljs i64 fix

Status: accepted; intermediate W5 family-2 evidence (reference + cljs dual-runtime
with mock transport), not family exit and not production cljs transport

## Decision

Start **Delivery 5 / W5 host capability qualification** family 2
(**HTTP egress**, `:http/post`) by recording dual-runtime semantic vectors on
the reference path (`:clj` via `clojure -M:test`, `:cljs` via nbb) and closing
the i64 defect that blocked honest cljs results:

`timeout-ms` (request) and `status` (ok response) are `:i64` ABI fields. On
`:cljs` the canonical representation is JS `bigint` (same rule ADR 0073 /
provider#2 applied to clock/log). Plain numbers failed range checks when mixed
with bigint and would fail `typed-cap-call` result validation for status.
The fix lives in `kotoba-lang/provider` (`provider.http`): normalize timeout
bounds and status through `cljs-i64`, pass a host `Number` timeout into the
transport callback.

Production **cljs** HTTP transport remains intentionally unimplemented
(`provider.http-transport` cljs branch throws). This slice uses a **mock**
host transport on both runtimes for boundary semantics — the same pattern
as the original clj `http_provider_test` suite.

## Evidence

- `test/kotoba/compiler/http_provider_test.clj` — existing vectors + missing-grant denial
- `test/nbb/http-provider.cljs` — post ok, origin/timeout fail-closed, typed transport
  error, redacted exception, denial on cljs
- provider#3 — http cljs i64 timeout/status fix
- `npm run test-nbb-http-provider` — 5 cases / 0 failed

## What this does NOT claim

- Production cljs/nbb HTTP transport (still throws; JVM transport ADR 0066 only)
- `:wasm-aot` / component provider for http-v1 (pending)
- Live network integration on cljs
- Full W5 family-2 exit (timeout/quota/cancellation matrices on every target,
  wasm/browser/workerd providers)

## Related

- ADR 0066 — production HTTP transport (JVM)
- ADR 0079 / 0084 / 0085 — W5 family-1 slices
- Migration plan W5 item 2 — HTTP egress
