# ADR 0131: W5 deepen — http get-stream synthetic wasm packaging

Status: accepted; intermediate Component packaging evidence for
`:http/get-stream` as url+headers → i64 byte-count aggregate; not linear
bytes-task/stream resource table and not `:wasm-aot :implemented`

## Decision

### 1. Packaging shape (intermediate)

| field | packaging admission |
|---|---|
| request | record `url: string`, `headers: set header{name keyword, value string}` |
| result | `:i64` fixed body length **2** (stand-in for poll+read of `"ok"`) |

Bounds: non-empty URL, `https://` prefix, no `#` fragment, header count ≤ 32.

Linear kit result `[:task [:stream :bytes]]` remains the dual-runtime /
typed-v0.3 **consumer** path (ADR 0122–0127, `:stream-byte-count-call`).
This synthetic **provider** mirrors object get-stream packaging (ADR 0130).

### 2. API

- `kotoba.component.core/http-get-stream-provider-wat`
- `kotoba.component.composition/package-http-get-stream-provider`

No ambient network. No task/stream resource table in the core module.

### 3. Multi-step Wasmtime

Driver performs two gets with empty headers; closed composition returns **4**
(2+2).

### Evidence

- kotoba-component#72 — packaging + multi-step (suite 97/666)
- Pin kotoba-component → `00881137167f373f65e58310955fb4b3f1a47419`

## What this does NOT claim

- Linear Component v0.3 `bytes-task` / `bytes-stream` resource ABI in the provider
- `:wasm-aot :implemented` on http get-stream
- Live HTTPS inside the synthetic module (ADR 0128 is the production transport)

## Related

- ADR 0130 — object get-stream packaging intermediate
- ADR 0092 / 0087 — http post packaging
- ADR 0122–0128 — dual-runtime + production GET transport
- Migration plan: HTTP get-stream packaging
