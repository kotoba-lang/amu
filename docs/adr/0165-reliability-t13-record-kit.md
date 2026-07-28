# ADR 0165: T1.3 dual-backend pilot — sealed record kit (T4.4 evidence)

- Status: Accepted
- Date: 2026-07-28
- WBS: T1.3 / T4.4

## Context

T4.4 asks for a pure-product record cookbook; T5.1 prefers records over packs.
Sealed `record-new` / `record-get` already lower on KIR + wasm32; the T1.3
runner lacked a fixture.

## Decision

Add pilot case `:record-kit` (`values/record_kit.kotoba`, expect 7 = 3+4).
Suite **12 → 13**.

## Evidence

- `clojure -M:conformance` 13/13

## Related

- ADR 0161–0164, T5.1 structural args
