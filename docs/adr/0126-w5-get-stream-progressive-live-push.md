# ADR 0126: W5 deepen — progressive live push (open chunk-queue)

Status: accepted; intermediate dual-runtime evidence for producer enqueue
while consumer polls stream-read; not guest poll/read language ops and not
linear Component v0.3 handles

## Decision

### 1. Runtime primitives (`kotoba.kir.value`, kotoba-kir#16)

- `make-open-chunk-queue-bytes-stream` — empty open queue
- `stream-enqueue!` / `stream-close!` — progressive producer side
- `make-ready-open-chunk-queue-task` / `task-fulfill-open-chunk-queue!`
- `stream-read!` on open queue:
  - empty + open → `{:pending? true :done? false}`
  - non-empty → one producer chunk (`done?` only when closed and drained)
  - empty + closed → done

Pre-filled closed queues (`{:chunk-queue [...]}`, ADR 0125) keep
`:open? false` so empty remains done immediately.

### 2. Provider transport reply (provider#20)

| reply | result |
|---|---|
| `{:open-stream true}` | ready task with open progressive stream |

Host drives body via `stream-enqueue!` then `stream-close!`. Other shapes
from ADR 0121–0125 unchanged.

### Evidence

- kotoba-kir#16 — progressive stream helpers + 5 tests (suite 44/216)
- provider#20 — object/http `:open-stream`
- compiler dual-runtime object/http + nbb cases
- Pin kotoba-kir → `ebcfec46a9bb1996154ad51b3d25cebf8093b29b`
- Pin provider → `1275094988018b4c31288dee301740923746714c`

## What this does NOT claim

- Guest-language poll/read/enqueue ops (host-side only)
- Blocking/async wait until a chunk arrives
- Live HTTPS / object-store stream transport
- Linear Component v0.3 handle ABI / `:wasm-aot`

## Related

- ADR 0125 — closed chunk-queue (pre-filled, no live push)
- ADR 0123 — join-before-ready multi-chunk
- Migration plan: progressive live push
