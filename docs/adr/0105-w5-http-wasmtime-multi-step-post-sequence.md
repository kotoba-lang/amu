# ADR 0105: W5 deepen — HTTP multi-step Wasmtime post sequence driver

Status: accepted; intermediate multi-step execution evidence for http-v1 wasm
packaging; not production transport and not `:wasm-aot` flip

## Decision

Deepen family-2 http wasm packaging with a **multi-step Wasmtime driver**:

1. Hand-authored application component imports `http-post.post` only
   (capability interface name is `http-post`, not bare `http`)
2. Performs two posts to `https://` (empty headers/body; timeout-ms 1000)
3. Returns `(status1 + status2) / 200` as `s64`
4. Composed closed with real synthetic `package-http-provider`
5. Wasmtime execution yields **2** (fixed ok status 200 twice; no ambient
   network)

This is the http counterpart to ADR 0101 (clock), ADR 0102 (log), and
ADR 0104 (ui). Canonical ABI uses retptr for the variant result
(`MAX_FLAT_RESULTS=1`); ok status sits at retptr + 8.

## Evidence

- kotoba-component#59 — driver in `http_provider_component_test`
- 4 tests / 13 assertions green (includes Wasmtime run)
- Pin advanced to `a90656e48d787e4b54ccac728c3bc15b3692346e`

## What this does NOT claim

- Production JVM HTTP transport (ADR 0066) or cljs transport
- Redirect following, DNS-rebinding closure, or stream ops
- `:wasm-aot :implemented`

## Related

- ADR 0086 — http dual-runtime
- ADR 0087 — http wasm packaging
- ADR 0101 / 0102 / 0104 — multi-step Wasmtime pattern
- Migration plan: Wasmtime multi-step drivers
