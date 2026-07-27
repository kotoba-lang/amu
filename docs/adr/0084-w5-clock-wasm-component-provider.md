# ADR 0084: W5 second slice — real clock-v1 wasm component provider

Status: accepted; intermediate W5 family-1 evidence (wasm component package +
closed composition), not family exit and not production host-time

## Decision

Advance **Delivery 5 / W5 host capability qualification** family 1 (log and
clock) past the dual-runtime reference path (ADR 0079) by shipping the first
**real** (non-wiring-only) Wasm Component Model provider for `clock-v1`:

- `kotoba.component.core/clock-provider-wat`
- `kotoba.component.composition/package-clock-provider`

Implementation lives in `kotoba-lang/kotoba-component` (extracted provider
composition surface; ADR-2607266000). This compiler repo consumes the pin
and records the application-side closed-world composition evidence.

### Semantics (synthetic, self-contained)

Production host wall/monotonic injection remains the CLJ/CLJS transport path
(ADR 0073). The component-model contract lists WASI clocks as intended
provider-wasi imports; those are **not** wired in this slice. Instead the
core module owns three mutable i64 globals:

| Global | Policy |
| --- | --- |
| `$wall` | starts at `1700000000000` Unix-ms, `+1` per wall observation |
| `$mono` | starts at `0`, `+1000` per monotonic observation (nondecreasing) |
| `$obs` | starts at `0`, `+1` before every successful observation |

This proves: Canonical ABI flattening for the clock-v1 variant crossing,
observation-sequence persistence across calls within one instance, closed
`wac` composition with a `typed-cap-call` application, and
`wasm-tools validate` of the provider and closed component.

Shape admission is strict (clock-v1 tags + field names/types/order), matching
`state-provider-shape` (ADR 0060) — not a generic asymmetric-variant provider.

## Evidence

- kotoba-component#47 — implementation + 3 unit tests / 11 assertions
- `clock-real-provider-rejects-non-clock-v1-shape` (this suite)
- `clock-real-provider-closes-the-application-world` (this suite)

## What this does NOT claim

- `:wasm-aot :implemented` on `clock-v1.edn` (left **pending**, same honesty
  bar as state after ADR 0060/0061 — packaging evidence ≠ production
  host-time / security review)
- Production wall/monotonic sources inside Wasm (WASI clocks follow-up)
- `log-v1` wasm provider (`log-provider-wat` — sets of records; next within
  family 1)
- Full W5 family exit (timeout/quota/cancellation matrices on every target)

## Related

- ADR 0079 — W5 first slice (log/clock dual-runtime)
- ADR 0073 — production clock transport (CLJ/CLJS)
- ADR 0060/0061 — state-provider-wat pattern this mirrors
- Migration plan W5 item 1 — log and clock; next: log wasm provider
