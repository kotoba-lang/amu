# ADR 0109: W5 deepen — http-ingress multi-step Wasmtime accept→none sequence

Status: accepted; intermediate multi-step execution evidence for
http-ingress-v1 wasm packaging; not host inject queue and not `:wasm-aot`

## Decision

Deepen family-3 http-ingress wasm packaging with a **multi-step Wasmtime
driver**:

1. Hand-authored application component imports `http-ingress.accept` only
   (compose-closed primary capability is `:http/accept`)
2. Performs two accepts with `slot = 0`
3. Synthetic dual-export provider always returns option none (no ambient
   queue)
4. Returns none-count `(1-d1)+(1-d2)` as `s64` (disc 0 = none)
5. Composed closed with real synthetic `package-http-ingress-provider`
6. Wasmtime execution yields **2**

This extends the multi-step suite to family-3 ingress packaging (accept
path). Reply multi-step remains optional follow-up. Canonical ABI uses
retptr for the option result (`MAX_FLAT_RESULTS=1`).

## Evidence

- kotoba-component#63 — driver in `http_ingress_provider_component_test`
- 4 tests / 16 assertions green (includes Wasmtime run)
- Pin advanced to `56d6b93625c45c03cf364c429aa9062d001b2fe1`

## What this does NOT claim

- Host inject / multi-inflight real incoming requests
- reply multi-step path
- workerd product path (already ADR 0100/0103)
- `:wasm-aot :implemented`

## Related

- ADR 0097–0099 — dual-runtime / multi-inflight / packaging
- ADR 0098 — http-ingress wasm packaging
- ADR 0101–0108 — multi-step Wasmtime pattern
- Migration plan: Wasmtime multi-step drivers
