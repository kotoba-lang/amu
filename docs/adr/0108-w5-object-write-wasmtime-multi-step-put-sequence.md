# ADR 0108: W5 deepen — object-write multi-step Wasmtime put-block sequence

Status: accepted; intermediate multi-step execution evidence for stream-object
write-path wasm packaging; not production store and not `:wasm-aot` flip

## Decision

Deepen stream-object write-path wasm packaging with a **multi-step Wasmtime
driver**:

1. Hand-authored application component imports `object-store.put-block` only
2. Performs two put-blocks (binding `"b"`, digest `"d"`, empty bytes payload)
3. Synthetic dual-export provider always returns `true`
4. Returns `(ok1 + ok2)` as `s64`
5. Composed closed with real synthetic `package-object-write-provider`
6. Wasmtime execution yields **2** (no ambient object store)

This closes the multi-step Wasmtime suite for intermediate-packaged kits:
clock, log, ui, http, storage, llm, and object-write. Bool results flatten
to a single i32 (no retptr). CAS multi-step remains optional follow-up.

## Evidence

- kotoba-component#62 — driver in `object_write_provider_component_test`
- 4 tests / 15 assertions green (includes Wasmtime run)
- Pin advanced to `95ff2a410a7edced920916b870cefe2333c4b55c`

## What this does NOT claim

- Ambient object store / production backend
- get-stream dual-runtime or linear task ownership
- CAS multi-step path in one Wasmtime invoke
- `:wasm-aot :implemented`

## Related

- ADR 0095 — stream-object write dual-runtime
- ADR 0096 — object-write wasm packaging
- ADR 0101–0107 — multi-step Wasmtime pattern
- Migration plan: Wasmtime multi-step drivers
