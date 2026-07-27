# ADR 0095: W5 stream-object dual-runtime first slice — put-block + CAS

Status: accepted; intermediate write-path evidence (reference + cljs with
mock transport), not family exit and not linear stream handle qualification

## Decision

Start dual-runtime semantic vectors for **stream-object-v1** on the
synchronous **write path** only:

- `:object/put-block` (id 15)
- `:object/compare-and-set-ref` (id 16)

Implemented in `provider.object` (provider#8/#9) with a closed binding
allowlist, bounded digest/key/etag/payload, bool results, and redacted
transport exceptions. Kit field type `:bytes` is bound as a `:string`
field named `:bytes` on the reference path — `kotoba.kir.value` does not
yet admit `:bytes` as a runtime typed value. Effectful Component fixtures
already lower block bodies as strings the same way. A dedicated binary
bytes value type for the reference path is deferred.

Linear task/stream ops (`:object/get-stream`, `:http/get-stream`) remain on
the Component Model v0.3 / Wasm path (`:component-core
:task-stream-handle-slice`). This slice does **not** claim stream ownership
or async profile qualification.

## Evidence

- `test/kotoba/compiler/object_provider_test.clj` — put boundary, CAS
  win/lose, binding/empty fail-closed, redaction, missing-grant denial
- `test/nbb/object-provider.cljs` — same five vectors on cljs
- provider#8 — `provider.object`

## What this does NOT claim

- Linear get-stream dual-runtime / bytes-task ownership on reference runtime
- Production object-store transport (no ambient backend)
- `:wasm-aot` object provider packaging
- Full stream-object kit exit

## Related

- stream-object-v1 kit
- ADR 0091–0094 — dual-runtime / wasm packaging pattern
- Migration plan W5 remaining next: stream-object dual-runtime
