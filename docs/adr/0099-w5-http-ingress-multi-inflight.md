# ADR 0099: W5 family-3 third slice — multi-inflight HTTP ingress queue

Status: accepted; intermediate family-3 evidence, not workerd cutover

## Decision

Deepen HTTP ingress dual-runtime with a **host-owned multi-inflight queue**:

- Default `max-queue-depth` **8** (constructor option, bound [1, 256])
- FIFO dequeue on `:http/accept`
- Accept-then-reply pairing unchanged (one pending unreplied request)
- Host may `enqueue!` while a request is pending reply
- Queue-full and path/header/body bounds remain fail-closed

Wasm synthetic provider (ADR 0098) still always-none on accept — multi-step
queue inside Wasm is not claimed.

## Evidence

- provider#11 — `provider.http-ingress` multi-inflight
- `http_ingress_provider_test.clj` — multi-inflight FIFO + capacity
- `test/nbb/http-ingress-provider.cljs` — cljs FIFO vector
- Kit `http-ingress-v1.edn` records `:max-queue-depth 8`

## What this does NOT claim

- workerd / Cloudflare Worker adapter
- Concurrent multi-pending accepts
- Streaming request bodies
- Wasm in-module multi-inflight queue

## Related

- ADR 0097 — first slice dual-runtime
- ADR 0098 — wasm packaging
