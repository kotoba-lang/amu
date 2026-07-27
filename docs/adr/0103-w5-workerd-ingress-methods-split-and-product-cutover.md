# ADR 0103: W5 family-3 product cutover — ingress methods split + toshokan handleIncoming

Status: accepted; intermediate product cutover evidence for murakumo-toshokan;
not fleet-wide cutover of every workerd app

## Decision

1. **Separate egress and ingress HTTP methods** in `host-profile`:
   - `:allowed-methods` — outbound `host.http.fetch` allowlist (unchanged)
   - `:ingress-methods` — optional inbound allowlist; **default**
     `GET HEAD POST PUT DELETE` when omitted
   - Generated worker `toIncoming` checks `ingressMethods`, not
     `allowedMethods` (ADR 0100 used the egress set and would block POST
     app routes when egress is GET-only)

2. **Product cutover (toshokan / murakumo-toshokan)**:
   - `toshokan.host.edn` adds `:max-request-bytes 65536` (required by ADR 0100)
   - `createApplication` exposes **`handleIncoming`** returning
     `{status, headers, body}` plain maps (workerd adapter path)
   - `fetch` becomes a thin adapter over `handleIncoming` so existing
     Request-based tests keep working
   - Health payload includes `"ingress": "handleIncoming"` as a cutover
     marker

## Evidence

- compiler host-profile-test: 3 tests / 40 assertions (default ingress
  methods include POST when egress is GET-only)
- toshokan `node workerd/application.test.mjs` green (fetch + handleIncoming)

## What this does NOT claim

- Live Cloudflare deploy of the cutover worker
- Guest `:http/accept`/`:http/reply` typed-cap-call inside the worker
- Other product services (kotobase, commitment-ledger) cut over

## Related

- ADR 0100 — workerd ingress adapter
- Migration plan family-3 product route cutover
