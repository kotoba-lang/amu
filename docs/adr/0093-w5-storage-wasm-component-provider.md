# ADR 0093: W5 remaining kit wasm packaging — synthetic storage-v1 provider

Status: accepted; intermediate packaging evidence, not family-4 exit and not
durable backend-in-wasm

## Decision

Ship a synthetic Wasm Component Model provider for `storage-v1`:

- `kotoba.component.core/storage-provider-wat`
- `kotoba.component.composition/package-storage-provider`

Range-checks the request discriminant (`get`/`put`/`delete`) and always
returns `:missing`. No ambient filesystem or host KV. Production durability
remains ADR 0071 (JVM transport) + dual-runtime mock path (ADR 0089).

## Evidence

- kotoba-component#51 — implementation + 3 unit tests
- Full component suite 65 / 532 green

## What this does NOT claim

- `:wasm-aot :implemented` on storage-v1
- Real put/get/delete with versions in Wasm
- Production cljs storage transport

## Related

- ADR 0089 — storage dual-runtime
- ADR 0071 — production storage transport
- Migration plan remaining kit wasm packaging
