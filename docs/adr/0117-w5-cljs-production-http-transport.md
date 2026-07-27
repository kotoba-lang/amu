# ADR 0117: W5 deepen — production `:cljs`/nbb HTTP transport via spawnSync hops

Status: accepted; production `:cljs` transport for `:http/post` on Node/nbb;
DNS-rebinding TOCTOU and connect/hop timeout split remain remaining gaps

## Decision

Close the ADR 0066 explicit `:cljs` gap for `provider.http-transport/production-transport`.

### Synchronous contract on a Promise-based host

Every reference provider transport in this repo is `(fn [request] -> reply)`
with no promise/callback machinery in `kotoba.compiler.reference-runtime`.
Node's `fetch`/`http.request` are async. This ADR keeps that contract by
running **each hop** in a child `node` process via `child_process.spawnSync`
(the monorepo's existing blocking-subprocess pattern for conformance
launchers). Parent cljs blocks until the hop child exits.

### Parity with ADR 0066 `:clj`

- Redirects never auto-followed; cljs owns the loop
- Every hop re-validates canonical origin ∈ host `allowed-origins`
- First-hop refusal → typed `:http/destination-blocked`; subsequent hop
  decline → return prior 3xx as ordinary ok
- Destination-IP block: IP literals pure-checked; hostnames via child
  `dns.lookup` (best-effort; not full rebinding defense)
- Bounded body (65536) and headers (32) folding; restricted hop headers dropped
- `truncate-to-byte-limit` made portable for shared use

### Evidence

- provider#12 — `:cljs` implementation in `provider.http-transport`
- `test/nbb/http-transport.cljs` — destination-literal, constructor, allow-list
  refuse, local echo POST through typed provider, outside-redirect decline
- Pin `io.github.kotoba-lang/provider` → `393a02a3d0cb84f065d13905f67814376adcff67`

## What this does NOT claim

- Full DNS-rebinding closure (TOCTOU same as `:clj`)
- Separate HttpClient connect-timeout vs per-hop timeout on cljs
- Production cljs LLM or storage transports
- Browser host (Node/nbb only; no XHR path)

## Related

- ADR 0066 — `:clj` production HTTP transport
- ADR 0073 — cljs production clock (simpler pure sources)
- Migration plan: production cljs transports
