# ADR 0120: W5 deepen — runtime `:bytes` leaf type on the reference path

Status: accepted; intermediate evidence that kit field type `:bytes` is a
first-class runtime leaf; not get-stream dual-runtime and not task/stream

## Decision

Admit **`:bytes`** as a runtime typed leaf in `kotoba.kir.value`:

| Host | Representation |
| --- | --- |
| JVM | `byte[]` (`bytes?`) |
| cljs/nbb | `js/Uint8Array` |

- `bytes-value-byte-limit` = 65536 (matches stream-object `max-pull-bytes`)
- `bounded-bytes!`, lexicographic `compare-typed-values`, aggregate
  indirect-byte charging
- `utf8-string->bytes` host/fixture helper (not a guest op)

### Object put-block

`provider.object/put-block-request` field type is **`:bytes`** (was `:string`
workaround from ADR 0095). Transport still receives `{:bytes <host-bytes>}`.

## Evidence

- kotoba-kir#12 — value type + 4 tests / 21 assertions
- provider#15 — object put-block field type + kir pin
- compiler object dual-runtime tests (clj + nbb) updated for byte payloads
- Pin `kotoba-kir` → `50572a5ade86a7dee26eef773946daa430228c9a`
- Pin `provider` → `17bb5d1f6bcc05607b8787b5b4974520483c8644`

## What this does NOT claim

- Linear `get-stream` / `http/get-stream` dual-runtime
- Task/stream handle values on the reference path
- Canonical ABI / WIT bytes lowering changes beyond existing list-u8 paths

## Related

- ADR 0095 — stream-object write dual-runtime (string-as-bytes workaround)
- Migration plan: get-stream dual-runtime once `:bytes`/task exist
