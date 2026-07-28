# ADR 0136: W5 deepen — CM resource multi-step Wasmtime

Status: accepted; multi-step Wasmtime of Component Model `resource bytes-task`
for object get-stream (get → poll-ready → body-len → drop → body length 2).
Corrects cm32p2 **export-resource** ABI vs ADR 0135's identity exports.

## Decision

### 1. Correct cm32p2 Standard ABI for exporting a resource

ADR 0135 packaged a valid WIT surface but exported identity
`[resource-new]/[resource-rep]/[resource-drop]` functions that wit-component
did not wire into the runtime handle table. Multi-step Wasmtime then failed
with `unknown handle index`.

Exporting a resource under cm32p2 Standard naming requires:

| core item | role |
|---|---|
| **import** `cm32p2\|_ex_<iface>` `bytes-task_new` | `canon resource.new` — rep → handle |
| **export** `bytes-task_dtor` | rep destructor (wired as resource dtor) |
| **export** `[method]bytes-task.poll-ready` / `body-len` | methods; core receives **rep** after lift |
| **export** `get-stream` | alloc live rep, return `call $rnew` (handle) |

### 2. Multi-step driver

Closed composition (wac plug) of:

1. driver imports `object-store` (`get-stream`, methods, `bytes-task_drop`)
2. provider exports CM `resource bytes-task`
3. `run`: get → poll-ready (must be true) → body-len → drop → return **2**

### Evidence

- kotoba-component#77 — ABI fix + multi-step Wasmtime; suite **109 / 721**
- Pin kotoba-component → `0129c988d6f060198611eb3558b17c5595632a77`

## What this does NOT claim

- Host dual-runtime resource table (ADR 0133)
- Free-function packaging multi-step (ADR 0134) — still valid intermediate
- Guest typed move across arbitrary `let` bindings
- Product apps beyond synthetic packaging
- `:wasm-aot` qualification

## Related

- ADR 0135 — packaging surface (WIT + validate); superseded on core ABI
- ADR 0134 — free-function table multi-step
- ADR 0133 — host linear table
- Migration plan: fuller product apps / guest move typing
