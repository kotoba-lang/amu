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

### Scope of that first bullet, as of 2026-08-18

It was about THIS path -- the synthetic component provider, which range-checks
the discriminant and always answers `:missing`. That is still all it does, and
it still does not qualify anything.

`storage-v1` now does carry `:wasm-aot :implemented`, earned on a different
seam: the guest compiles to `:wasm32-browser-kotoba-v1` and its own
`:kotoba.storage/request` / `:kotoba.storage/result` cross `kotoba:typed/cap-call`
(id 12) to a host inject, which is the same seam dataspace-v1 was qualified on.
Real put/get/delete with versions, and the `[:option :i64]` expected-version and
conflict current-version, do round-trip there. Evidence and the break/unbreak
runs are in `kotoba.compiler.storage-wasm-aot-test`; the kit's
`:wasm-aot-surface` block names the import, id, grant, target and schemas.

`:native-aot` remains `:pending` for storage, and that is measured, not
assumed -- the native targets reject this ABI at `:phase :target`.

## Related

- ADR 0089 — storage dual-runtime
- ADR 0071 — production storage transport
- Migration plan remaining kit wasm packaging
