# ADR 0167: T1.5 golden digests for pure-product pilot

- Status: Accepted
- Date: 2026-07-28
- WBS: T1.5

## Context

T1.3 dual-backend execution catches result skew but not silent IR/artifact
rewrites that preserve results. T1.5 asks for golden digests so CI fails on
semantic drift of KIR body or wasm bytes.

## Decision

1. Resource `resources/kotoba/lang-conformance/pilot-golden.edn`  
2. Per case:  
   - `kir-sha256` = `artifact.core/sha256` of selected KIR keys  
   - `wasm-sha256` = SHA-256 hex of raw `wasm32-kotoba-v1` bytes  
3. CLI: `clojure -M:conformance --check-golden` / `--write-golden`  
4. Test: `lang-conformance-golden-test` always-on

## Non-claims

- Does not golden the full kotoba-lang conformance matrix (still progressive)  
- Does not pin native/js targets (T1.4 / optional)

## Related

- ADR 0161–0166, T1.3 pilot
