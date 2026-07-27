# ADR 0096: W5 stream-object write-path wasm packaging — dual-export provider

Status: accepted; intermediate packaging evidence, not stream-object kit exit
and not linear get-stream qualification

## Decision

Ship a synthetic Wasm Component Model dual-export provider for the
stream-object **write path**:

- `kotoba.component.core/object-write-provider-wat`
- `kotoba.component.composition/package-object-write-provider`

Exports both `:object/put-block` and `:object/compare-and-set-ref` on the
shared `object-store` interface. Bounds-checks non-empty keyword/string
leaves, option discriminant ∈ {0,1}, and payload ≤ 65536. Always returns
`true`. No ambient object store. Kit field `:bytes` is admitted as host
`:string` (same intermediate representation as ADR 0095 dual-runtime).

## Evidence

- kotoba-component#53 — implementation + 3 unit tests
- Full component suite 71 / 552 green
- Pin advanced to `0b7edb18bc1ac1843f9370c904d1e597734df127`

## What this does NOT claim

- `:wasm-aot :implemented` on stream-object write ops
- Real put/CAS with durable backend in Wasm
- Linear get-stream / bytes-task packaging
- Production object-store transport

## Related

- ADR 0095 — write-path dual-runtime
- Migration plan stream-object remaining packaging
