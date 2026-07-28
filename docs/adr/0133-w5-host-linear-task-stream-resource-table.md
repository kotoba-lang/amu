# ADR 0133: W5 deepen — host linear resource table for task/stream

Status: accepted; intermediate dual-runtime ownership plane for affine
`[:task [:stream :bytes]]` / `[:stream :bytes]` handles; not Component Model
resource ABI / wasm packaging table

## Decision

### 1. Host registry (`kotoba.kir.value`)

| op | effect |
|---|---|
| construction (`make-*-task` / `make-*-stream`) | register id as `:alive` |
| `task-poll` / `stream-read!` / fulfill / enqueue / close / cancel | require live |
| `task-drop!` / `stream-drop!` | clear alive; double-drop fails closed |
| `task-live?` / `stream-live?` | query |
| `resource-table-reset!` | test helper |

Use-after-drop fails closed with `"bytes-task is not live"` /
`"bytes-stream is not live"`.

### 2. Guest consume

`bytes-task-byte-count` (ADR 0127) **drops** the task after a successful
drain (linear consume). Re-using the same host handle after guest consume
fails closed.

### 3. Scope

This is the **reference dual-runtime** ownership plane that pairs with
pending→ready / multi-chunk / progressive streams (ADR 0121–0126). Wasm
Component resource tables for packaging (ADR 0130–0132) remain intermediate
i64 aggregates and do **not** yet host this table.

### Evidence

- kotoba-kir#18 — table + drop + 5 tests (suite 52/240)
- provider#23 — pin kir
- compiler dual-runtime drop/consume vector
- Pin kotoba-kir → `ba86b2f1f475c3dfb150795f7dd6da0624212c98`
- Pin provider → `20fc4041b9a2444263009b4f2729bf9ef45163d7`

## What this does NOT claim

- Component Model `resource bytes-task` / `bytes-stream` packaging ABI
- Full move typing across arbitrary guest `let` bindings
- Wasm multi-step resource-table execution

## Related

- ADR 0121–0127 — task/stream dual-runtime + guest poll/read
- ADR 0130–0132 — packaging without resource table
- Migration plan: linear task resource table
