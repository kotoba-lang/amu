# ADR 0125: W5 deepen — true multi-chunk get-stream (chunk-queue)

Status: accepted; intermediate dual-runtime evidence for discrete multi-chunk
yields on object + http get-stream; not guest poll/read ops, not progressive
live push while reading, not linear Component v0.3 handles

## Decision

### 1. Runtime primitives (`kotoba.kir.value`, kotoba-kir#15)

- `make-chunk-queue-bytes-stream` — stream whose `stream-read!` yields **one
  producer chunk per call** without pre-joining into a single payload
- `make-ready-bytes-task-from-chunk-queue` / `task-fulfill-chunk-queue!`
- Producer chunks are atomic: a single chunk larger than the caller's
  `max-bytes` fails closed (contrast ADR 0123 join path, which allows
  max-bytes splits of the concatenated payload)

### 2. Provider transport reply shapes (provider#19)

`:object/get-stream` (id 14) and `:http/get-stream` (id 13) transports may return:

| reply | result |
|---|---|
| host `:bytes` or `{:bytes ...}` | ready task (ADR 0121/0122) |
| `{:pending true}` | pending task; host later `task-fulfill!` |
| `{:chunks [bytes…]}` | ready task over **concatenated** payload (ADR 0123) |
| `{:chunk-queue [bytes…]}` | ready task with **true multi-chunk** stream (this ADR) |

Bounds and allowlist/origin checks are unchanged.

### Evidence

- kotoba-kir#15 — chunk-queue helpers + 5 tests (suite 39/194)
- provider#19 — object/http `as-bytes-task!` accept `:chunk-queue`
- compiler object/http provider tests: discrete two-chunk yield
- nbb object/http providers: +1 case each (9+9)
- Pin kotoba-kir → `9de0d22061133a592c7b41e83d3db7bd2078f4cc`
- Pin provider → `6eddff42babc31db2227ce53c62da505e040ee61`

## What this does NOT claim

- Guest-language poll/read/fulfill ops (host-side only)
- Progressive live push (`stream-enqueue!`) while a consumer is reading
- Live HTTPS / object-store stream transport (mock transports in this slice)
- Linear Component v0.3 handle ABI / `:wasm-aot`

## Related

- ADR 0123 — join-before-ready multi-chunk (`:chunks`)
- ADR 0121–0122 — object/http get-stream ready-task dual-runtime
- ADR 0124 — nbb dual-runtime for ready/pending/joined multi-chunk
- Migration plan: true async multi-chunk producers
