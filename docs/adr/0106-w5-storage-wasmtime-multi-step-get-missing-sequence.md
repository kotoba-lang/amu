# ADR 0106: W5 deepen — storage multi-step Wasmtime get→missing sequence

Status: accepted; intermediate multi-step execution evidence for storage-v1
wasm packaging; not production transport and not `:wasm-aot` flip

## Decision

Deepen family-4 storage wasm packaging with a **multi-step Wasmtime driver**:

1. Hand-authored application component imports `storage.transact` only
2. Performs two `get` requests (key `"k"`)
3. Synthetic provider always returns `:missing` (discriminant 1)
4. Returns `(disc1 + disc2)` as `s64`
5. Composed closed with real synthetic `package-storage-provider`
6. Wasmtime execution yields **2** (no ambient backend)

This is the storage counterpart to ADR 0101 (clock), 0102 (log), 0104 (ui),
and 0105 (http). Canonical ABI uses retptr for the variant result
(`MAX_FLAT_RESULTS=1`).

## Evidence

- kotoba-component#60 — driver in `storage_provider_component_test`
- 4 tests / 13 assertions green (includes Wasmtime run)
- Pin advanced to `b0b211853e57342a78ef044223f167e17776def4`

## What this does NOT claim

- Production storage transport (ADR 0071) or host-configured KV
- Real put/get round-trip or conflict paths
- `:wasm-aot :implemented`

## Related

- ADR 0089 — storage dual-runtime
- ADR 0093 — storage wasm packaging
- ADR 0101 / 0102 / 0104 / 0105 — multi-step Wasmtime pattern
- Migration plan: Wasmtime multi-step drivers
