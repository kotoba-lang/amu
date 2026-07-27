# ADR 0104: W5 deepen — UI multi-step Wasmtime commit sequence driver

Status: accepted; intermediate multi-step execution evidence for ui-v1 wasm
packaging; not `:wasm-aot` flip and not DOM/browser host qualification

## Decision

Deepen family-5 ui wasm packaging with a **multi-step Wasmtime driver**:

1. Hand-authored application component imports `ui.commit` only
2. Performs two empty commits (empty node lists; base-revision 0 then 1)
3. Returns `(rev2 - rev1)` as `s64`
4. Composed closed with real dual-export `package-ui-provider`
5. Wasmtime execution yields **1** (provider-local revision advances once
   per successful commit that matches `base-revision`)

This is the ui counterpart to ADR 0101 (clock wall→mono) and ADR 0102
(log append sequence). Canonical ABI uses retptr for the two-field
`commit-result` record (`MAX_FLAT_RESULTS=1`).

## Evidence

- kotoba-component#58 — driver in `ui_provider_component_test`
- 4 tests / 14 assertions green (includes Wasmtime run)
- Pin advanced to `98a99746fe6bb6746e03acb34bed68efda563062`

## What this does NOT claim

- Multi-step `next-event` (still always option none)
- DOM reconciliation or browser host
- Production `:ui/commit` kit exit / `:wasm-aot :implemented`

## Related

- ADR 0090 — ui dual-runtime
- ADR 0092 — ui wasm packaging
- ADR 0101 / 0102 — multi-step Wasmtime pattern
- Migration plan: Wasmtime multi-step drivers
