# ADR 0173: T7.1 loop dual-backend pilot + T3.3 kir pin

- Status: Accepted
- Date: 2026-07-28
- WBS: T7.1 / T3.3

## T7.1

`loop`/`recur` already desugar to a named self-calling helper
(`__kotoba_loop_N`). Dual-backend pilot cases prove KIR + wasm32 agree.

**Not claimed:** machine-level TCO / zero-charge recur (each helper entry still
burns 1 fuel unit per T7.2). True stack-frame reuse remains a follow-up.

## T3.3

Pin `kotoba-kir` to SHA with fuel-trap function/call-stack metadata
(kotoba-kir#20 / ADR 0020). Compiler integration test asserts the envelope.

## Evidence

- pilot 20→22 dual-green + goldens  
- `kir-trap-source-test`
