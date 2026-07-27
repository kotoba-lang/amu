# ADR 0098: W5 family-3 second slice — http-ingress wasm dual-export provider

Status: accepted; intermediate packaging evidence, not workerd cutover and not
multi-inflight lifecycle

## Decision

Ship a synthetic Wasm Component Model dual-export provider for
`http-ingress-v1`:

- `kotoba.component.core/http-ingress-provider-wat`
- `kotoba.component.composition/package-http-ingress-provider`

Exports `:http/accept` + `:http/reply` on the shared `http-ingress` interface.

- **accept**: slot must be `0`; always returns option **none** (no ambient
  request queue inside Wasm)
- **reply**: status ∈ [100,599], header count ≤ 32, body byte bound; always
  returns `true`

Production dual-runtime host inject remains ADR 0097. `:wasm-aot` stays pending.

## Evidence

- kotoba-component#55 — implementation + 3 unit tests
- Full component suite 74 / 563 green
- Pin advanced to `c128859a561311533a0184a49b88bdb43632ffaa`

## What this does NOT claim

- Real accept queue / multi-inflight inside Wasm
- workerd / Cloudflare Worker entry cutover
- WASI incoming-handler binding
- `:wasm-aot :implemented`

## Related

- ADR 0097 — ingress dual-runtime
- Migration plan W5 family 3
