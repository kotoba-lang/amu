# ADR 0135: W5 deepen — full Component Model `resource bytes-task` packaging

Status: accepted; packaging ABI for CM `resource bytes-task` on object
get-stream (embed + component new + validate + WIT surface). Not Wasmtime
multi-step of CM resources; not host dual-runtime table (ADR 0133); free-function
multi-step table remains ADR 0134.

## Decision

### 1. WIT surface

`package-object-get-stream-cm-resource-provider` exports:

```wit
resource bytes-task {
  poll-ready: func() -> bool;
  body-len: func() -> s64;
}
get-stream: func(request: ...) -> own<bytes-task>;
```

### 2. Core exports (cm32p2-prefixed)

| export | role |
|---|---|
| `[resource-new]bytes-task` | rep → handle (identity) |
| `[resource-rep]bytes-task` | handle → rep (identity) |
| `[resource-drop]bytes-task` | clear live; double-drop traps |
| `[method]bytes-task.poll-ready` | live → true |
| `[method]bytes-task.body-len` | live → i64 2 |
| `get-stream` | alloc live rep over fixed payload |

### 3. Evidence boundary

- wasm-tools embed / component new / validate
- `wasm-tools component wit` shows `resource bytes-task`
- **Not claimed**: closed multi-step Wasmtime invoke of CM resources (observed
  `unknown handle index` on wasmtime 42 host path; free-function multi-step is
  ADR 0134; host ownership plane is ADR 0133)

### Evidence

- kotoba-component#76 — packaging + suite 108/713
- Pin kotoba-component → `5873c1db48c35a4f37926ea825eda3fda14f776f`

## What this does NOT claim

- Wasmtime multi-step product walk of CM resources
- Host dual-runtime resource table (ADR 0133)
- Free-function packaging multi-step (ADR 0134)
- Guest typed move across arbitrary `let` bindings
- `:wasm-aot` qualification

## Related

- ADR 0130–0132 — packaging without resource table
- ADR 0133 — host linear resource table
- ADR 0134 — intermediate free-function packaging table
- Migration plan: fuller product apps / wasmtime resource host path
