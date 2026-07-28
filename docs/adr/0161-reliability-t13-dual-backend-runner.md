# ADR 0161: Reliability T1.3 dual-backend runner (KIR + wasm32 pilot)

- Status: Accepted
- Date: 2026-07-28
- WBS: T1.3

## Context

T1.2 declared that pure-product cases require `#{:kir :wasm32-kotoba-v1}`.
Many kotoba-lang conformance fixtures still fail compiler admission (set ops,
destructuring, etc.). R1 needs an **executable** dual-backend gate for the
subset that *can* run today, without claiming full matrix green.

## Decision

1. Ship `kotoba.compiler.lang-conformance` dual-backend runner.
2. Vendor a **pilot** pure-product suite under
   `resources/kotoba/lang-conformance/` (5 control fixtures proven DUAL_OK).
3. Gate: KIR `ir/execute` result and Node `browser-host.mjs` wasm `main`
   must both equal `:expect :kotoba`.
4. CLI: `clojure -M:conformance` (exit 0 only if pilot suite passes).

## Non-claims

- Not full kotoba-lang manifest green (15/20 pure-product still admission-blocked)
- Does not implement native backends (T1.4)
- Does not change guest admission surface

## Evidence

- pilot-manifest + 5 fixtures
- `test/kotoba/compiler/lang_conformance_test.clj`
- alias `:conformance`

## Related

- kotoba-lang T1.2 matrix / ADR-reliability-t12
- WBS T1.3
