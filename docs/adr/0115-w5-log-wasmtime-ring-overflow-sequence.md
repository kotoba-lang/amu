# ADR 0115: W5 deepen — log multi-step ring-overflow oldest-drop sequence

Status: accepted; intermediate multi-step execution evidence for log-v1
ring-buffer oldest-drop; not production transport and not `:wasm-aot`

## Decision

Deepen family-1 log with a **ring-overflow multi-step Wasmtime driver**
(capacity-bound oldest-drop), building on dual-export `compose-closed`
(ADR 0111) and append+read (ADR 0111):

1. Application imports `log.append` + `log.read`
2. Provider packaged with **capacity 2** (parametric `package-log-provider`)
3. Three appends (empty fields; sequences 1, 2, 3)
4. One read (`after-sequence` 0, `limit` 8)
5. Returns `oldest-sequence` as `s64` → **2** (sequence 1 dropped)
6. Composed closed with dual-export `package-log-provider`
7. Wasmtime yields **2**

Closes ADR 0111's deferred "Full ring-buffer walk of N entries /
truncation multi-step" for the **oldest-drop** slice. Log multi-step now
covers append-only, append+read, and ring-overflow oldest-drop.

## Evidence

- kotoba-component#69 — driver in `log_provider_component_test`
- 6 tests / 26 assertions green (includes Wasmtime run)
- Pin advanced to `14dc63dc13e7f00bb6cefeb4faf33c357cf170e5`

## What this does NOT claim

- Truncation-flag multi-step when `limit` < available entries
- Production host log transport
- `:wasm-aot :implemented`

## Related

- ADR 0085 / 0102 / 0111 — log packaging / append / append+read
- Migration plan: multi-step Wasmtime drivers
