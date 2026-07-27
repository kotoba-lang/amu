# ADR 0089: W5 family-4 second slice — storage dual-runtime semantic vectors + cljs i64 versions

Status: accepted; intermediate W5 family-4 evidence (reference + cljs with
mock transport), not family exit and not production cljs storage transport

## Decision

Continue **family 4 (state and storage)** with `storage-v1` dual-runtime
semantic vectors on `:clj` and nbb `:cljs`, and close the version i64 defect:

Entry `:version`, option expected-version, and conflict current-version are
`:i64` ABI fields. On `:cljs` the canonical representation is JS `bigint`.
`valid-version?` used `integer?`, which rejects bigint; fixed in
`provider.storage` with host-branch validation and host Number handoff to
transport for expected-version.

Production **cljs** storage transport remains unimplemented (JVM path ADR
0071). This slice uses a **mock** host transport on both runtimes.

## Evidence

- `test/kotoba/compiler/storage_provider_test.clj` — existing vectors + denial
- `test/nbb/storage-provider.cljs` — put boundary, missing/conflict, redaction,
  invalid version fail-closed, denial (5 cases)
- provider#5 — storage cljs i64 versions
- State dual-runtime ADR 0088; family 4 dual-runtime intermediate evidence
  now covers both state and storage reference kits

## What this does NOT claim

- Production cljs storage transport / live KV endpoint
- `:wasm-aot` storage component provider
- Full family-4 exit (timeout/quota/cancellation matrices on every target)

## Related

- ADR 0071 — production storage transport (JVM)
- ADR 0088 — state dual-runtime
- Migration plan W5 item 4
