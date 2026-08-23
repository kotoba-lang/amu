# ADR 0268: http :wasm-aot is a sync kit-shaped host, not WASI http

Status: accepted

## Decision

`http-v1` `:wasm-aot` is `:implemented` when the provider validates kit
bounds (https prefix, timeout, header/body limits) then forwards the
Canonical-flat request to imported `http-host.post`. Tests plug an echo
stub: status 200, empty headers, body = request body.

`wasi:http/client@0.3.0` stays off this path. It is `async func` plus
`stream`/`future`. The kit is `:synchronous-reference`. standard32 has no
future/stream intrinsic surface under `--reject-legacy-names`. WASI 0.2
`outgoing-handler` remains a forbidden spelling. The cljs path (ADR 0066)
is still the production HTTP transport.

Echo is the test host, analogous to WASI clocks vs synthetic epoch: a
fixed `"ok"` body is theater; a host that returns the caller's bytes is
the substitutable boundary a production embedder fills with real HTTP
and the origin allowlist.

## Evidence

`http-wasm-aot-qualification-test` must:

1. `package-http-echo-provider` composed closed with a two-post driver
2. wasmtime `run --invoke run()` returns `7` (`hello` 5 + `xy` 2)
3. The same driver against `package-http-host-provider` (no stub) fails
   to link on `http-host`

Requires kotoba-component `5ab001f` (PR #121).

## What this does NOT claim

- Ambient network or ADR 0066 redirect-following on wasm
- `wasi:http/client@0.3.0` / `:bounded-wasi-0.3-async`
- `:wasm32-kotoba-v1` i64 surface
- native-aot / jit
- backend-wide wasmtime `:qualified`
