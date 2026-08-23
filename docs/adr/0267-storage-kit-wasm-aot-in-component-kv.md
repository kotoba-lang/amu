# ADR 0267: storage wasm-aot is an in-component KV, not a filesystem

Status: accepted

## Decision

`storage-v1` `:wasm-aot` is `:implemented` when a bounded in-component
table performs real put/get/delete with per-key versions and
expected-version `:conflict`. Empty get stays `:missing` (existing
get-sequence drivers). This is the same honesty bar as state-v1's table
(ADR 0264): the wasm instance is the source of truth.

Kit durability remains `:transport-commit-before-result` on the cljs/clj
path (ADR 0071 host-configured HTTP KV). The wasm-aot table is not that
endpoint and not an ambient filesystem (`:ambient-filesystem false`).

Evidence: `wasmtime-storage-kit-kv-vector-is-mask-63` (get-missing, put
written v1, get found v1, put expected 99 → conflict, delete, get
missing). Always-missing cannot set bits 1–4.

## What this does NOT claim

- ADR 0071 HTTP transport on wasm
- durable host filesystem
- `:wasm32-kotoba-v1` i64 surface
- native-aot / jit
