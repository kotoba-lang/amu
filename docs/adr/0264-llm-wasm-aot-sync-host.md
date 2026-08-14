# ADR 0264: llm :wasm-aot is a sync kit-shaped host, not a model

Status: accepted

## Decision

`llm-v1` `:wasm-aot` is `:implemented` when the provider validates kit
bounds (model length, prompt/system caps, token/temperature ranges) then
forwards to imported `llm-host.generate`. Tests plug an echo stub:
completion text = prompt, finish-reason `stop`, usage counts the prompt
length.

There is no WASI LLM. Credentials and the model allowlist stay host-only.
A fixed `"ok"` completion is theater. Echo is the substitutable boundary
a production embedder fills with a real model call.

## Evidence

`llm-wasm-aot-qualification-test` must:

1. `package-llm-echo-provider` composed closed with a two-generate driver
2. wasmtime `run --invoke run()` returns `7` (`hello` 5 + `xy` 2)
3. The same driver against `package-llm-host-provider` (no stub) fails to
   link on `llm-host`

Requires kotoba-component `5ab001f` (PR #121).

## What this does NOT claim

- A real model, streaming, or tool calls
- Host credentials inside the component
- `:wasm32-kotoba-v1` i64 surface
- native-aot / jit
- backend-wide wasmtime `:qualified`
