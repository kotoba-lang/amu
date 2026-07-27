# ADR 0091: W5 family-6 first slice — LLM dual-runtime semantic vectors + cljs i64 tokens

Status: accepted; intermediate W5 family-6 evidence (reference + cljs with
mock transport), not family exit and not streaming/tool-call surface

## Decision

Start **Delivery 5 / W5 host capability qualification** family 6
(**LLM generate/stream/cancel/tool result**) with `llm-v1` dual-runtime
semantic vectors on `:clj` and nbb `:cljs`, and close the i64 defect:

`max-output-tokens`, `temperature-milli`, and usage `input-tokens`/
`output-tokens` are `:i64` ABI fields. On `:cljs` the canonical
representation is JS `bigint`. `valid-token-count?` used `integer?`, which
rejects bigint; range checks mixed number/bigint unsafely. Fixed in
`provider.llm` with host Number handoff to transport.

Production **cljs** LLM transport remains unimplemented (JVM path ADR 0064).
This slice uses a **mock** host transport on both runtimes. Streaming,
tool-calls, and cancel are out of v1 kit scope (kit marks them false).

## Evidence

- `test/kotoba/compiler/llm_provider_test.clj` — generation, model/budget
  fail-closed, typed errors, missing-grant denial
- `test/nbb/llm-provider.cljs` — same four vectors on cljs with bigint
  tokens/temperature
- provider#7 — llm cljs i64 fix

## What this does NOT claim

- Production cljs LLM transport / murakumo live wire
- Streaming, tool-calls, cancel (not in llm-v1)
- `:wasm-aot` llm component provider
- Full family-6 exit

## Related

- ADR 0064 — production LLM transport (JVM)
- ADR 0086–0090 — dual-runtime pattern across kits
- Migration plan W5 item 6
