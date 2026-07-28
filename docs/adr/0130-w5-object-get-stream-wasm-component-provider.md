# ADR 0130: W5 deepen — object get-stream synthetic wasm packaging

Status: accepted; intermediate Component packaging evidence for
`:object/get-stream` as binding+key → i64 byte-count aggregate; not linear
bytes-task/stream resource table and not `:wasm-aot :implemented`

## Decision

### 1. Packaging shape (intermediate)

| field | packaging admission |
|---|---|
| request | record `binding: keyword`, `key: string` |
| result | `:i64` fixed body length **2** (stand-in for poll+read of `"ok"`) |

Linear kit result `[:task [:stream :bytes]]` remains the dual-runtime /
typed-v0.3 **consumer** path (ADR 0121–0127, `:stream-byte-count-call`).
This synthetic **provider** deliberately uses the same intermediate
simplification pattern as object-write packaging admitting kit `:bytes` as
host `:string` (ADR 0095/0096).

### 2. API

- `kotoba.component.core/object-get-stream-provider-wat`
- `kotoba.component.composition/package-object-get-stream-provider`

Bounds-check non-empty binding and key; always return `i64.const 2`. No
ambient object store. No task/stream resource table in the core module.

### 3. Multi-step Wasmtime

Driver performs two get-stream calls; closed composition returns **4**
(2+2).

### Evidence

- kotoba-component#71 — packaging + multi-step (suite 93/652)
- Pin kotoba-component → `0748651212c177d150eb646a180199aed6cb504c`

## What this does NOT claim

- Linear Component v0.3 `bytes-task` / `bytes-stream` resource ABI in the provider
- HTTP get-stream packaging (follow-up)
- `:wasm-aot :implemented` on stream-object get-stream
- Live object-store inside the synthetic module (ADR 0129 is the production transport)

## Related

- ADR 0096 — object-write packaging intermediate
- ADR 0121–0127 — dual-runtime + guest poll/read
- ADR 0129 — production object-store transport
- Migration plan: Component v0.3 packaging of get-stream poll/read
