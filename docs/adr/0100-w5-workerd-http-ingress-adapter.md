# ADR 0100: W5 family-3 fourth slice — workerd HTTP ingress adapter

Status: accepted; intermediate workerd bridge evidence, not production
Cloudflare cutover of product routes and not accept/reply Component wiring

## Decision

Wire family-3 ingress bounds into the generated Cloudflare workerd adapter
(`kotoba.compiler.host-profile/emit-worker`):

1. Profile `:http` gains required **`:max-request-bytes`** (1–16MiB).
2. Generated worker maps inbound `Request` → bounded plain
   `{method, path, headers, body}` (`toIncoming`):
   - method must be in `allowedMethods` (`capability-denied:http-ingress`)
   - path UTF-8 length ∈ [1, 4096] (kit path bound)
   - headers folded lowercase, max 32 unique names
   - body bounded by `maxRequestBytes`
3. Prefer **`application.handleIncoming(incoming, ctx)`** when present;
   map reply `{status, headers?, body?}` → `Response` (`fromReply`) with
   status ∈ [100,599] and response body ≤ `maxResponseBytes`.
4. Legacy **`application.fetch(request, ctx)`** remains for apps that have
   not adopted the ingress shape.

This does **not** install ambient listen sockets and does **not** claim that
the guest uses `:http/accept` / `:http/reply` typed-cap-call inside the
worker yet — it is the host-side Request/Response boundary that matches
http-ingress-v1 field bounds so product adapters can migrate gradually.

## Evidence

- `host_profile.clj` emit path + profile schema
- `host_profile_test.clj` — generation strings + unbounded request rejection
  (3 tests / 37 assertions)

## What this does NOT claim

- Product murakumo/kotobase routes cut over to handleIncoming
- Guest accept/reply capability providers installed in workerd
- Multi-inflight concurrent fetch orchestration inside the worker
- WASI incoming-handler

## Related

- ADR 0097–0099 — reference dual-runtime / wasm / multi-inflight
- Migration plan W5 family 3 next: workerd adapter
