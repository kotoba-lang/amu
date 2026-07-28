# ADR 0134: W5 deepen — intermediate CM packaging linear resource table

Status: accepted; intermediate Component packaging free-function handle table
for get→poll→read→drop multi-step Wasmtime; not full Component Model
`resource` types and not host dual-runtime table (ADR 0133)

## Decision

### 1. In-module packaging table

`package-object-get-stream-linear-table-provider` exports free-function
stand-ins on `object-store` (not CM `resource` methods):

| export | meaning |
|---|---|
| `get-stream` | alloc live task+stream over fixed payload `"ok"`; return task handle (s32) |
| `task-poll` | live task → stream handle (ready); dead → trap |
| `stream-read-len` | live stream → body length **2** (i64); dead → trap |
| `task-drop` / `stream-drop` | clear alive; double-drop traps |

Fixed capacity 8 handles; WIT params use `task-h` / `stream-h` (WIT reserves
`stream`). Void drops use empty post-return `[] -> []`.

### 2. Multi-step evidence

Driver: get → poll → read-len → drop stream → drop task; closed composition
returns **2**. This is the first packaging slice that walks a linear table
ownership sequence inside Wasmtime without host CM resource methods.

### Evidence

- kotoba-component#74 — packaging + multi-step (suite 105/696)
- Pin kotoba-component → `ede5e06083f26afeff2b15b38f35204a9890ad64`

## What this does NOT claim

- Full Component Model `resource bytes-task` / `bytes-stream` ABI
- Host dual-runtime resource table (ADR 0133 remains the ownership plane)
- Live object-store transport inside the synthetic module (ADR 0129)
- Guest typed move across arbitrary `let` bindings

## Related

- ADR 0130–0132 — packaging without resource table (i64 aggregates / put+get)
- ADR 0133 — host linear resource table (dual-runtime)
- Migration plan: Component Model resource ABI / fuller product apps
