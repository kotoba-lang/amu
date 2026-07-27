# ADR 0085: W5 third slice — real log-v1 dual-export wasm component provider

Status: accepted; intermediate W5 family-1 evidence (provider package +
validate), not family exit and not KIR application emit for record+set

## Decision

Advance **Delivery 5 / W5 host capability qualification** family 1 past the
clock wasm slice (ADR 0084) by shipping the first **real** Wasm Component
Model provider for `log-v1`:

- `kotoba.component.core/log-provider-wat`
- `kotoba.component.composition/package-log-provider`

Requires `kotoba-wasm` `:set` layout (pointer+length, `typed-set-item-limit`
32) so `fields` / `entries` `[:set record]` have a qualified ABI.

### Semantics

One core module exports both `log@1|append` and `log@1|read`, sharing a ring
buffer:

| Op | ABI | Behavior |
| --- | --- | --- |
| append | 8×i32 request → **i64** sequence | store level/event/message + ≤4 fields; oldest-drop when full |
| read | 2×i64 request → **i32** result pointer | after-sequence cursor, limit 1–8, truncated flag, entry list |

Default capacity 8 (parametric; 256 = kit bound). Production CLJ/CLJS
reference provider (ADR 0030/0072/0079) is unchanged.

## Evidence

- kotoba-wasm#33 — `:set` layout
- kotoba-component#48 — implementation + 3 unit tests / 11 assertions
- Full component suite 56 / 507 green

## What this does NOT claim

- `:wasm-aot :implemented` on `log-v1.edn` (pending, same honesty as state/clock)
- KIR/`typed-cap-call` application emit for asymmetric record+set shapes
  (provider packaging only; app composition deferred)
- Wasmtime multi-step driver bitmask
- Full W5 family exit

## Related

- ADR 0079 / 0084 — W5 first/second slices
- ADR 0030 / 0072 — log kit / no-transport
- Migration plan W5 item 1 — log and clock; family 1 wasm providers now
  both present as intermediate packaging evidence
