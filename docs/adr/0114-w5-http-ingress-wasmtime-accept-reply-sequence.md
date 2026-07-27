# ADR 0114: W5 deepen — http-ingress multi-step accept+reply dual-export sequence

Status: accepted; intermediate multi-step execution evidence for http-ingress
multi-function lifecycle walk; not host inject and not `:wasm-aot`

## Decision

Deepen family-3 http-ingress with a **multi-function multi-step Wasmtime
driver** (accept then reply), enabled by dual-export `compose-closed`
(ADR 0111):

1. Application imports `http-ingress.accept` + `http-ingress.reply`
2. One accept (`slot` 0) → option none (synthetic always-none)
3. One reply (`status` 200, empty headers/body) → true
4. Returns `none-count + true` as `s64` → **2**
5. Composed closed with dual-export `package-http-ingress-provider`
6. Wasmtime yields **2**

Complements ADR 0109 (accept-only) and ADR 0110 (reply-only). Closes
ADR 0110's deferred "Lifecycle accept→reply coupling in one Wasmtime
invoke". Family-3 multi-step now covers accept-only, reply-only, and
accept+reply dual-export walks.

## Evidence

- kotoba-component#68 — driver in `http_ingress_provider_component_test`
- 6 tests / 26 assertions green (includes Wasmtime run)
- Pin advanced to `7a1201a165da1c0f8b7fb3f6059138b0cc8f5271`

## What this does NOT claim

- Host inject / multi-inflight real accept→reply lifecycle coupling
- Ambient listen or workerd boundary (see ADR 0100/0103)
- `:wasm-aot :implemented`

## Related

- ADR 0098 — http-ingress wasm packaging
- ADR 0109 / 0110 — accept-only / reply-only multi-step
- ADR 0111 — dual-export compose-closed
- Migration plan: multi-function multi-step drivers
