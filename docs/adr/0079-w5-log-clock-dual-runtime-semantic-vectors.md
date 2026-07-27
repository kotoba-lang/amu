# ADR 0079: W5 first slice — log/clock dual-runtime semantic vectors + log cljs i64 fix

Status: accepted; intermediate W5 evidence (reference + cljs dual-runtime), not family exit

## Decision

Start **Delivery 5 / W5 host capability qualification** with family 1
(**log and clock**) by recording dual-runtime semantic vectors on the
reference path (`:clj` via `clojure -M:test`, `:cljs` via nbb) and closing
the one real defect that blocked log's cljs path:

`provider.log`'s sequence counters are `:i64` ABI fields. On `:cljs` the
canonical representation is JS `bigint` (same rule ADR 0073 applied to
`provider.clock`). Plain `inc`/`dec` produced numbers that failed
`typed-cap-call` result validation (`invalid-parametric-value: value is
not a signed i64`). The fix lives in `kotoba-lang/provider` and mirrors
clock's `cljs-i64` zero/one counter pattern.

Also restored the nbb dual-runtime harness after the provider extraction:
launchers now resolve classpath with `clojure -Spath -M:test` so
`provider.*` is visible, and admission allow-sets use `js/BigInt` cap ids
matching KIR's cljs effect encoding.

## Evidence

- `test/kotoba/compiler/clock_provider_test.clj` — invalid tick typed
  errors + missing-grant denial
- `test/kotoba/compiler/log_provider_test.clj` — missing-grant denial
- `test/nbb/clock-transport.cljs` — production clock dual-runtime (restored)
- `test/nbb/log-provider.cljs` — append/read, field/read limits, retention
  truncation, denial on cljs
- provider#2 — log cljs i64 sequence fix

## What this does NOT claim

- `:wasm-aot`, `:native-aot`, and `:jit` remain **pending** on
  `clock-v1.edn` / `log-v1.edn`
- No audit-receipt / revocation surface is added (out of v1 kit scope)
- No production log sink / durable export (ADR 0030 exclusions)
- Full W5 family exit (timeout/quota/cancellation matrices on every
  target) is not claimed; this is intermediate dual-runtime evidence for
  family 1

## Related

- ADR 0072 / 0073 (log no-transport / clock production sources)
- Migration plan W5 — Host capability qualification, item 1 (log and clock)
- ADR-2607279200 Delivery 5
