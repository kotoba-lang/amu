# ADR 0092: W5 remaining kit wasm packaging — synthetic ui-v1 dual-export provider

Status: accepted; intermediate packaging evidence, not family-5 exit and not
DOM reconciliation

## Decision

Ship a synthetic Wasm Component Model provider for `ui-v1`:

- `kotoba.component.core/ui-provider-wat`
- `kotoba.component.composition/package-ui-provider`

Dual-export `ui@1|commit` and `ui@1|next-event` share a revision counter.
Commit checks base-revision match and node count ≤ 32, returns
revision/node-count via Canonical indirect result. Next-event always returns
option none (no host event queue in this slice). No ambient DOM.

## Evidence

- kotoba-component#50 — implementation + 3 unit tests
- Full component suite 62 / 524 green
- Reference dual-runtime for UI already landed (ADR 0090)

## What this does NOT claim

- `:wasm-aot :implemented` on ui-v1
- Real event queue / host enqueue in Wasm
- Browser DOM reconciliation (W4 document path remains separate)

## Related

- ADR 0090 — UI dual-runtime
- ADR 0084/0085/0087 — clock/log/http wasm packaging pattern
- Migration plan W5 remaining kit wasm packaging
