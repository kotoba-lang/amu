# ADR 0261: http-ingress wasm-aot is host inject, not ambient listen

Status: accepted

## Decision

`http-ingress-v1` `:wasm-aot` is `:implemented` when a host fills a one-slot
queue through exported `http-ingress-host.inject` and `accept` returns that
incoming request. Empty queue stays option none (existing accept-sequence
drivers). Slot must be 0. First slice stores empty headers only (non-empty
traps). This is not an ambient listen and not `max-queue-depth` 8.

Evidence: `wasmtime-http-ingress-kit-returns-host-injected-path-length`
(inject GET `/x` → accept path length 2), plus kotoba-component
`http-host-inject-then-accept-returns-the-injected-path-length`.

## Remaining gaps (do not flip these)

- **http-v1 post** (`:wasm-aot :pending`): `wasi:http/client@0.3.0` is
  async func + streams. Hand WAT cannot do that
  (`:bounded-wasi-0.3-async`). WASI 0.2 `outgoing-handler` is a forbidden
  spelling. The cljs path stays the production HTTP transport.
- **llm-v1** (`:wasm-aot :pending`): no WASI LLM; host credentials and
  model allowlist have no component import. A fixed `"ok"` completion is
  theater.
- **native-aot / jit** (all kits): C-free aiueos typed-provider syscall
  is still pending. Hosted kexe C loader is rejected.
- Backend-wide wasmtime qualification stays `:pending` until every
  remaining kit has a production provider.

## What this does NOT claim

- compiled `.kotoba` kit-typed guests (drivers are still WAT)
- header round-trip on inject
- native/jit for http-ingress
