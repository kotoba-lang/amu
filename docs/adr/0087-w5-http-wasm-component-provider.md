# ADR 0087: W5 family-2 second slice — synthetic http-v1 wasm component provider

Status: accepted; intermediate W5 family-2 evidence (provider package +
validate), not family exit and not production network-in-wasm

## Decision

Advance **HTTP egress** past dual-runtime mock vectors (ADR 0086) by shipping
a **synthetic** Wasm Component Model provider for `http-v1` post:

- `kotoba.component.core/http-provider-wat`
- `kotoba.component.composition/package-http-provider`

The core module enforces kit bounds (timeout `[1,30000]`, headers ≤ 32,
URL/body byte limits), rejects fragments and non-`https://` prefixes, and
returns a fixed `ok` result (status 200, empty headers, body `"ok"`). There
is **no ambient network** and no host transport import — packaging/ABI
qualification only.

## Evidence

- kotoba-component#49 — implementation + 3 unit tests
- Full component suite 59 / 515 green

## What this does NOT claim

- `:wasm-aot :implemented` on `http-v1.edn`
- Production HTTPS from Wasm (WASI HTTP / host transport follow-up)
- KIR application emit for record→variant with nested header sets
- Live redirect/SSRF matrices inside the component (still JVM transport ADR 0066)

## Related

- ADR 0086 — HTTP dual-runtime
- ADR 0066 — production JVM HTTP transport
- Migration plan W5 item 2
