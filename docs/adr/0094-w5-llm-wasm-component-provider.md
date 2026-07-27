# ADR 0094: W5 remaining kit wasm packaging — synthetic llm-v1 provider

Status: accepted; intermediate packaging evidence, not family-6 exit and not
production LLM transport-in-wasm

## Decision

Ship a synthetic Wasm Component Model provider for `llm-v1` generate:

- `kotoba.component.core/llm-provider-wat`
- `kotoba.component.composition/package-llm-provider`

Enforces model/system/prompt byte bounds plus `max-output-tokens` [1,4096]
and `temperature-milli` [0,2000]. On success returns a fixed ok completion
(text `"ok"`, finish-reason `"stop"`, zero usage). No ambient network,
credentials, or provider SDK. Production transport remains ADR 0064 (JVM) +
dual-runtime mock path (ADR 0091).

## Evidence

- kotoba-component#52 — implementation + 3 unit tests
- Full component suite 68 / 542 green
- Pin advanced to `880e567f2acd56d49b62b789cad0198866c0994c`

## What this does NOT claim

- `:wasm-aot :implemented` on llm-v1
- Real model invocation or streaming in Wasm
- Production cljs LLM transport
- Tool-calls / cancel / stream (out of v1 kit)

## Related

- ADR 0091 — llm dual-runtime
- ADR 0064 — production LLM transport
- Migration plan remaining kit wasm packaging
