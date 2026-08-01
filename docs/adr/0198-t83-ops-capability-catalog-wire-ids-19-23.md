# ADR 0198: T8.3 vendor ops capability catalog wire ids 19–23

- Status: Accepted
- Date: 2026-08-01
- Depends: kotoba-lang ADR-t83-ops-capability-catalog-wire-ids-19-23;
  provider ADR 0260–0267 guest host surfaces

## Context

`frontend.cljc` loads `kotoba/lang/capability-catalog.edn` (JVM) and keeps a
CLJS fallback map that must stay byte-for-byte aligned with the authority
catalog. After kotoba-lang registered ops kit names
`:fs/transact`…`:entropy/draw` as wire ids 19–23, the compiler still only
knew 1–18 — named `(cap-call :secret/get …)` failed as unregistered.

## Decision

1. Vendor the updated catalog under `resources/kotoba/lang/capability-catalog.edn`.
2. Extend `capability-registry-cljs-fallback` with ids 19–23.
3. Assert registry seeds for ops kits in
   `frontend_named_capability_test` + one named↔int lower for `:process/spawn`.

## Non-goals

- Component-model WIT expansion for ops kits
- Flipping `:wasm-aot :implemented`

## Evidence

- Named capability tests; backend qualification still gates only
  provider-conformance kit set (unchanged count 9)
