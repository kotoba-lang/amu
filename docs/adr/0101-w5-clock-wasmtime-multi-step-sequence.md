# ADR 0101: W5 deepen — clock multi-step Wasmtime sequence driver

Status: accepted; intermediate multi-step execution evidence for clock-v1
wasm packaging, not production host clocks and not `:wasm-aot` flip

## Decision

Deepen family-1 clock wasm packaging with a **multi-step Wasmtime driver**:

1. Hand-authored application component imports `clock.now`
2. Performs wall observation then monotonic observation in one `run()` export
3. Returns `(obs2 - obs1)` as `s64`
4. Composed closed with real `package-clock-provider` synthetic sources
5. Wasmtime execution yields **1** (shared observation-sequence advances
   once per successful observation)

This is the multi-step execution counterpart to ADR 0084 packaging-only
evidence (and parallel to the state stateful-sequence / full-capacity
drivers for family-4).

## Evidence

- kotoba-component#56 — driver in `clock_provider_component_test`
- 4 tests / 16 assertions green (includes Wasmtime run)
- Pin advanced to `6607352e996b1eeb7ca454bc8be53bbb119a19a7`

## What this does NOT claim

- Production host wall/monotonic time (still ADR 0073)
- WASI clocks wired on the component contract
- `:wasm-aot :implemented`
- Log multi-step driver (still deferred from ADR 0085)

## Related

- ADR 0084 — clock wasm packaging
- ADR 0060/0061 — state multi-step driver pattern
- Migration plan: Wasmtime multi-step drivers
