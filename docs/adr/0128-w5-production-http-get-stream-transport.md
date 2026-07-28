# ADR 0128: W5 deepen — production HTTP get-stream transport

Status: accepted; intermediate production evidence for live HTTPS GET as
`:http/get-stream` transport on clj + cljs/nbb; not object-store live
transport and not Component v0.3 linear handle packaging

## Decision

### 1. `provider.http-transport/production-get-stream-transport`

Same security floor as `production-transport` (ADR 0066 / 0117):

- required closed `allowed-origins` (canonical HTTPS)
- never auto-follow redirects outside that set
- best-effort private/loopback destination-IP block
- bounded body (`http/max-pull-bytes` = 65536)

Method is **GET** (no request body). Request schema has no timeout field;
default hop timeout is `default-get-stream-timeout-ms` (30000), overridable
via constructor `:timeout-ms`.

### 2. Reply shape for get-stream provider

Success → `{:bytes <host :bytes>}` (ready-task path in `as-bytes-task!`).

First-hop destination refusal → **throw** (redacted by
`invoke-get-stream-transport` into generic transport failure). Network/IO
exceptions likewise propagate to that catch.

### 3. Dual runtime

| host | hop |
|---|---|
| `:clj` | `HttpClient` GET + `ofInputStream` + `read-bounded-bytes` |
| `:cljs`/nbb | `spawnSync` GET hop script; body as base64 → `Uint8Array` |

### Evidence

- provider#21 — implementation
- compiler http_transport_test: GET ready-task, in-allow-list redirect, outside refuse
- nbb http-transport: constructor + first-hop throw cases
- Pin provider → `d19177767888777a781c3b463ad29f48241b014f`
- Suite: 637 tests / 5664 assertions green

## What this does NOT claim

- Live object-store get-stream transport
- Status/headers surface on get-stream (body bytes only)
- Guest-language progressive drain of live open streams
- Component v0.3 linear ABI packaging of get-stream poll/read

## Related

- ADR 0066 / 0117 — production HTTP POST transport
- ADR 0122 — http/get-stream dual-runtime ready-task
- Migration plan: live stream transport
