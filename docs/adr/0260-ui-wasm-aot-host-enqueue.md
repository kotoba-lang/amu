# ADR 0260: ui :wasm-aot is host enqueue, not always-none

Status: accepted

## Decision

`:wasm-aot` on `ui-v1.edn` is `:implemented`.

`next-event` pops a one-slot queue. The slot starts empty (option none),
which is why ADR 0113's commit-then-next-event driver still returns 2.
A host fills the slot through exported `ui-host.enqueue` with the kit
event record. That is the inject seam; there is still no ambient DOM.

## Evidence

`ui-wasm-aot-qualification-test`: wasmtime `run --invoke run()` after
`enqueue(revision=7, target=btn, kind=click)` returns `7`. An always-none
provider cannot pass.

Requires kotoba-component `639b14d` (PR #121).

## What this does NOT claim

- Browser DOM reconciliation
- Multi-event ring (one slot)
- `:wasm-aot` on http / http-ingress / storage / llm
- `:native-aot` / `:jit`
