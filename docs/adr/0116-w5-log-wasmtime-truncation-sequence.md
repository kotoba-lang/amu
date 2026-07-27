# ADR 0116: W5 deepen — log multi-step truncation-flag dual-read sequence

Status: accepted; intermediate multi-step execution evidence for log-v1
`truncated` flag after ring oldest-drop; not production transport and not
`:wasm-aot`

## Decision

Deepen family-1 log with a **truncation-flag multi-step Wasmtime driver**,
building on dual-export compose-closed (ADR 0111) and ring-overflow
oldest-drop (ADR 0115):

1. Application imports `log.append` + `log.read`
2. Provider packaged with **capacity 2**
3. Three appends (sequences 1, 2, 3; seq 1 dropped)
4. Read after-sequence **0** → `truncated=true` (cursor before retained window)
5. Read after-sequence **1** → `truncated=false` (after ≥ oldest-1)
6. Returns `trunc0 + (1 - trunc1)` as `s64` → **2**
7. Wasmtime yields **2**

Closes ADR 0111's deferred truncation multi-step slice. Log multi-step now
covers append-only, append+read, ring-overflow oldest-drop, and truncation
flag dual-read.

## Evidence

- kotoba-component#70 — driver in `log_provider_component_test`
- 7 tests / 31 assertions green (includes Wasmtime run)
- Pin advanced to `7da289169a6a922ab46d97d170dd911062c69892`

## What this does NOT claim

- Production host log transport
- `:wasm-aot :implemented`

## Related

- ADR 0085 / 0102 / 0111 / 0115 — log packaging / append / append+read / oldest-drop
- Migration plan: multi-step Wasmtime drivers
