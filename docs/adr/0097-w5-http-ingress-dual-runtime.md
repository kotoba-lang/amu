# ADR 0097: W5 family-3 first slice — HTTP ingress accept/reply dual-runtime

Status: accepted; intermediate family-3 evidence (reference + cljs), not
listen-in-wasm and not Cloudflare Worker cutover

## Decision

Start **HTTP ingress and lifecycle** (W5 family 3) with a host-inject /
guest-poll lifecycle on ids **17** (`:http/accept`) and **18**
(`:http/reply`):

- Host owns listen/socket; `enqueue!` injects a bounded incoming request
- Guest `accept` returns `option` of `{method, path, headers, body}`
- Guest `reply` returns a bool after validating status ∈ [100,599]
- v1 is single-inflight (queue depth 1; accept must pair with reply)

No ambient listen. Wire names land in abi import table; Component inventory
gains `http-ingress` interface. Not typed v0.3 grant-request cases.

Status uses canonical i64 (bigint on cljs).

## Evidence

- `provider.http-ingress` (provider#10)
- abi#17 + kotoba-component#54 inventory
- `test/kotoba/compiler/http_ingress_provider_test.clj`
- `test/nbb/http-ingress-provider.cljs`

## What this does NOT claim

- Production workerd/Cloudflare Worker entry cutover
- Multi-request concurrency / streaming bodies
- `:wasm-aot` ingress provider packaging
- WASI incoming-handler binding

## Related

- ADR 0026 — HTTP egress kit (complement)
- Migration plan W5 item 3
