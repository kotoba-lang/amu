# ADR 0121: W5 deepen — get-stream dual-runtime ready-task (reference path)

Status: accepted; intermediate dual-runtime evidence for `:object/get-stream`
on the reference path; not linear Component v0.3 handles and not pending→ready
scheduling

## Decision

### 1. Runtime types (`kotoba.kir.value`)

- `[:stream :bytes]` — host affine stream handle (payload + offset/cancel atom)
- `[:task [:stream :bytes]]` — host affine task (`:pending` | `:ready` | `:cancelled`)

Helpers: `make-ready-bytes-task`, `task-poll`, `stream-read!`, cancel.

### 2. Provider (`provider.object`)

`get-stream-provider` (id 14): binding allowlist + non-empty key → transport
`{:operation :get-stream :binding :key}` → wrap `{:bytes ...}` as **ready**
bytes-task. `create-providers` → `{14 15 16}`.

### Evidence

- kotoba-kir#13 — 4 tests / 20 assertions
- provider#16 — get-stream provider
- compiler object-provider-test: get-stream poll/read + denial/redaction
- nbb object-provider: write path still 5/5 with allow {14 15 16}
- Pin kotoba-kir → `1404d643ba0b9dbc92cfeffec5eb2a75a7d2d257`
- Pin provider → `eb9042d876f13db7ba463adb67e921e89ebc9c49`

## What this does NOT claim

- Guest-language poll/read ops
- Pending→ready async scheduling / multi-chunk producers
- `:http/get-stream` dual-runtime
- Linear Component v0.3 handle ABI / `:wasm-aot`

## Related

- ADR 0095 / 0120 — write path + runtime `:bytes`
- Migration plan: get-stream dual-runtime
