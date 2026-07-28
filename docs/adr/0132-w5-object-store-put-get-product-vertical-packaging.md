# ADR 0132: W5 deepen — object-store put+get product vertical packaging

Status: accepted; intermediate product-vertical Component packaging for
stream-object put-block + get-stream dual-export and multi-step put-then-get
Wasmtime walk; not linear bytes-task resource table and not live store inside
the synthetic module

## Decision

### 1. Unified packaging

`package-object-store-put-get-provider` exports both ops on `object-store`:

| export | packaging result |
|---|---|
| `put-block` | always `true` (bool) after bounds |
| `get-stream` | always `i64` body length **2** (poll/read aggregate stand-in) |

Same intermediate shapes as ADR 0096 (put) and ADR 0130 (get-stream alone).

### 2. Product multi-step

Driver: put-block then get-stream; closed composition returns **3**
(`true`→1 + length 2). This is the first packaging slice that walks a
store-then-measure product path in one Wasmtime invoke.

### Evidence

- kotoba-component#73 — packaging + multi-step (suite 101/680)
- Pin kotoba-component → `247dbe67b123060dbe502dc206277723610c9168`

## What this does NOT claim

- Linear Component v0.3 task/stream resource table
- Durable store inside the synthetic module (ADR 0129 is live transport)
- Guest single-export put+get (linear ownership still blocks mixed body)

## Related

- ADR 0096 / 0112 — write packaging + put+CAS multi-step
- ADR 0130 — get-stream-only packaging
- Migration plan: product apps
