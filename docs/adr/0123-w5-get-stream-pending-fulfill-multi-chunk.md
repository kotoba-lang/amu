# ADR 0123: W5 deepen — get-stream pending→ready + multi-chunk

Status: accepted; intermediate reference-path evidence for pending tasks and
multi-chunk join on object + http get-stream; not guest poll/read ops, not
true async multi-chunk producers, not linear Component v0.3 handles

## Decision

### 1. Runtime primitives (`kotoba.kir.value`, kotoba-kir#14)

- `task-fulfill!` — transition a host `:pending` bytes-task to `:ready` with a
  stream over a payload (same task id; fail-closed if not pending)
- `concat-bytes` (public) + `make-bytes-stream-from-chunks` — ordered chunk join
  into one affine stream (first multi-chunk slice = single linear payload after
  join)

### 2. Provider transport reply shapes (provider#18)

`:object/get-stream` (id 14) and `:http/get-stream` (id 13) transports may return:

| reply | result |
|---|---|
| host `:bytes` or `{:bytes ...}` | ready task (ADR 0121/0122) |
| `{:pending true}` | pending task; host later `value/task-fulfill!` |
| `{:chunks [bytes…]}` | ready task over concatenated bounded chunks |

Bounds and allowlist/origin checks are unchanged from 0121/0122.

### Evidence

- kotoba-kir#14 — `task-fulfill!` + multi-chunk helpers (4 tests / 14 assertions)
- provider#18 — object + http `as-bytes-task!` accept pending / chunks
- compiler object/http provider tests: pending→fulfill→read + multi-chunk ready
- Pin kotoba-kir → `314d65e6f6b736abd645398673e05fe1810c60ed`
- Pin provider → `90938d52cf9adbb19b5df87d31eba018d3702c8a`
- Suite: 625 tests / 5630 assertions green

## What this does NOT claim

- Guest-language poll/read/fulfill ops (host-side only)
- True async multi-chunk producers (chunks are joined before the task becomes ready)
- Live HTTPS / object store stream transport (mock transports in this slice)
- Linear Component v0.3 handle ABI / `:wasm-aot`

## Related

- ADR 0121 — object get-stream ready-task dual-runtime
- ADR 0122 — http get-stream ready-task dual-runtime
- ADR 0120 — runtime `:bytes`
- Migration plan: pending→ready scheduling / multi-chunk
