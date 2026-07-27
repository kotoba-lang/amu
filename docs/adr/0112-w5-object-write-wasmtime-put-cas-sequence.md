# ADR 0112: W5 deepen — object-write multi-step put+CAS dual-export sequence

Status: accepted; intermediate multi-step execution evidence for stream-object
write-path multi-function walk; not ambient store and not `:wasm-aot`

## Decision

Deepen stream-object write-path with a **multi-function multi-step Wasmtime
driver** (put then CAS), enabled by dual-export `compose-closed` (ADR 0111):

1. Application imports `object-store.put-block` +
   `object-store.compare-and-set-ref`
2. One put-block (binding/digest non-empty; empty payload)
3. One compare-and-set-ref (`expected` = none; `next` non-empty)
4. Returns `(ok_put + ok_cas)` as `s64`
5. Composed closed with dual-export `package-object-write-provider`
6. Wasmtime yields **2** (always-true synthetic provider; no ambient store)

Complements ADR 0108 (put-only multi-step). Write-path multi-step now covers
single-export and dual-export walks.

## Evidence

- kotoba-component#66 — driver in `object_write_provider_component_test`
- 5 tests / 20 assertions green (includes Wasmtime run)
- Pin advanced to `844b88908bd7230ae188c06cc5e93ff980ed0b9c`

## What this does NOT claim

- Ambient object store / get-stream
- Real CAS expected-match semantics (synthetic always-true)
- `:wasm-aot :implemented`

## Related

- ADR 0095 / 0096 — write dual-runtime / wasm packaging
- ADR 0108 — put-only multi-step
- ADR 0111 — dual-export compose-closed
- Migration plan: multi-function multi-step drivers
