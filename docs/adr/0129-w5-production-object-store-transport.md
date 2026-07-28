# ADR 0129: W5 deepen — production object-store transport

Status: accepted; intermediate production evidence for host-configured
object-store get-stream / put-block / CAS on clj + cljs/nbb; not ambient
filesystem blob root and not Component v0.3 linear packaging

## Decision

### 1. `provider.object-transport/production-transport`

Same “no ambient authority” floor as storage-transport (ADR 0071):

- required closed host `:endpoint` (or `KOTOBA_OBJECT_ENDPOINT`)
- fixed path (default `/object/v1/transact`); guest data only in JSON body
- optional bearer `:api-key` / `KOTOBA_OBJECT_API_KEY`
- bounded response body; bytes on the wire as `bytes_base64`

| operation | success reply to provider |
|---|---|
| `:get-stream` | `{:bytes <host :bytes>}` |
| `:put-block` | `true` / `false` |
| `:compare-and-set-ref` | `true` / `false` |

Missing get-stream, non-2xx, and malformed wire **throw** (redacted by
`provider.object/invoke-transport`). Network/IO exceptions propagate
similarly.

### 2. Dual runtime

| host | hop |
|---|---|
| `:clj` | `HttpClient` POST JSON |
| `:cljs`/nbb | `spawnSync` Node POST hop |

### Evidence

- provider#22 — `object_transport.cljc` + load/unit tests
- compiler object_transport_test: put→get-stream round-trip, CAS win/lose, missing fail-closed
- Pin provider → `322b05b095cdfe71ba6f3b497fab1553414f676b`

## What this does NOT claim

- A repo-wide well-known object backend (endpoint is always host-configured)
- Ambient local-disk object store
- Progressive open-stream live push over the wire
- Component v0.3 linear handle packaging of get-stream

## Related

- ADR 0071 / 0119 — production storage transport pattern
- ADR 0121–0128 — get-stream dual-runtime + HTTP live transport
- Migration plan: object-store live transport
