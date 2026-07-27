# ADR 0113: W5 deepen — UI multi-step commit+next-event dual-export sequence

Status: accepted; intermediate multi-step execution evidence for ui-v1
multi-function walk; not DOM/browser host and not `:wasm-aot`

## Decision

Deepen family-5 ui with a **multi-function multi-step Wasmtime driver**
(commit then next-event), enabled by dual-export `compose-closed` (ADR 0111):

1. Application imports `ui.commit` + `ui.next-event`
2. One empty commit (`base-revision` 0, empty nodes) → revision 1
3. One `next-event` (`after-revision` 0) → option none (synthetic provider
   never emits events)
4. Returns `revision + none-count` as `s64` → **2**
5. Composed closed with dual-export `package-ui-provider`
6. Wasmtime yields **2**

Complements ADR 0104 (commit-only multi-step). UI multi-step now covers
commit-only and commit+next-event dual-export walks.

## Evidence

- kotoba-component#67 — driver in `ui_provider_component_test`
- 5 tests / 19 assertions green (includes Wasmtime run)
- Pin advanced to `ed5a915559f23d8c138cc578e3ea302ec907854c`

## What this does NOT claim

- DOM reconciliation or browser host
- Real event queue / host-injected next-event
- `:wasm-aot :implemented`

## Related

- ADR 0090 / 0092 — ui dual-runtime / wasm packaging
- ADR 0104 — commit-only multi-step
- ADR 0111 — dual-export compose-closed
- Migration plan: multi-function multi-step drivers
