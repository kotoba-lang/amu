# ADR 0107: W5 deepen — LLM multi-step Wasmtime generate sequence

Status: accepted; intermediate multi-step execution evidence for llm-v1 wasm
packaging; not production transport and not `:wasm-aot` flip

## Decision

Deepen family-6 llm wasm packaging with a **multi-step Wasmtime driver**:

1. Hand-authored application component imports `llm.generate` only
2. Performs two generates (model `"m"`, empty system/prompt; tokens=64;
   temperature-milli=0)
3. Synthetic provider returns fixed ok completion (`text "ok"`,
   `finish-reason "stop"`, zero usage)
4. Returns sum of text lengths `(2 + 2)` as `s64`
5. Composed closed with real synthetic `package-llm-provider`
6. Wasmtime execution yields **4** (no ambient network/credentials)

This is the llm counterpart to ADR 0101–0106 multi-step drivers. Canonical
ABI uses retptr for the variant result (`MAX_FLAT_RESULTS=1`); text length
sits at retptr + 12.

## Evidence

- kotoba-component#61 — driver in `llm_provider_component_test`
- 4 tests / 15 assertions green (includes Wasmtime run)
- Pin advanced to `7ea98cc397ba17e94f350cdecbc1f279ae7a1e4d`

## What this does NOT claim

- Production LLM transport (ADR 0064) or murakumo-main wiring
- Streaming / tool-calls / cancel
- `:wasm-aot :implemented`

## Related

- ADR 0091 — llm dual-runtime
- ADR 0094 — llm wasm packaging
- ADR 0101–0106 — multi-step Wasmtime pattern
- Migration plan: Wasmtime multi-step drivers
