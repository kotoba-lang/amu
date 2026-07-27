# ADR 0111: W5 deepen — dual-export compose-closed + log append+read multi-step

Status: accepted; dual-export composition rule + intermediate multi-step
execution evidence for log append→read ring walk; not `:wasm-aot`

## Decision

### 1. Dual-export `compose-closed`

`compose-closed` previously required exact frequency match between
application `:imports` and each provider's primary `:capability`. That
blocked multi-function multi-step drivers (e.g. log append+read) because a
single dual-export artifact only exposes one primary capability.

**New rule:** expand each provider via `:capabilities` (fallback
`:capability`), and require application imports ⊆ supplied set. One dual-
export component may close multiple imports. `wac plug` remains the real
closure gate.

### 2. Log append+read multi-step

1. Application imports `log.append` + `log.read`
2. Appends one entry (empty fields)
3. Reads `after-sequence=0`, `limit=8`
4. Returns `latest-sequence` as `s64`
5. Composed closed with dual-export `package-log-provider`
6. Wasmtime yields **1** (first sequence after append)

Closes ADR 0102's deferred "append+read multi-step" follow-up.

## Evidence

- kotoba-component#65 — compose-closed change + driver in
  `log_provider_component_test`
- 5 tests / 21 assertions green; dual-export regression (ui, http-ingress,
  object-write) green
- Pin advanced to `685709d255781ba34392aec11b881a776092cec7`

## What this does NOT claim

- Full ring-buffer walk of N entries / truncation multi-step
- Production host log transport
- `:wasm-aot :implemented`

## Related

- ADR 0085 / 0102 — log packaging / append-only multi-step
- ADR 0101–0110 — multi-step Wasmtime pattern
- Migration plan: dual-export composition
