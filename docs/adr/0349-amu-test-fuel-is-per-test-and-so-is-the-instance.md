# ADR 0349 — `amu test --fuel`, one instance per test, and integer capability ids on the wasm probe

- Date: 2026-09-15
- Status: Accepted
- Related: ADR 0348 (`amu test` is on the nbb route), ADR 0075 (declared fuel budgets),
  root ADR-2609151600 (the component that measured this).

## Context

`amu test` compiled its js/wasm probes with the emitter's default budget (512, per
instance, non-replenishing) and ran every `test-*` export on ONE instance. Measured
2026-09-15 on `cloud-itonami/cloud-itonami-commands` (`src/cloud/itonami/commands.kotoba`,
18 tests, a registry scan ~2,700 fuel): two tests passed and sixteen reported
`unreachable` on the wasm probe — the tests after the one that spent the budget trapped
for a reason that was not theirs — and the whole run answered
"Kotoba target test process failed" with the cause hidden in `ex-data`. The runner
could not gate that component at all; the repository shipped its own fresh-instance
runner (`scripts/test_kotoba.cljk`) to have a JVM-free gate.

Also found on the way: `test-profile-test`'s own fixture (`:capabilities #{:http/post}`)
was red on the nbb route at origin/main — the wasm probe passed the wire ids as JSON
strings (`["4"]`, what `json.data-json` writes for the id on this route) and
`browser-host.mjs` admits integers only: `capability ids must be unique integers in
[0,255]`.

## Decision

1. `amu test <file> [--fuel <n>]`. The budget goes into the compile policy as
   `{:budgets {:fuel n}}` (the same key `amu compile --fuel` reads) and to the
   interpreter target as `ir/execute`'s `:fuel`. A value that is not a positive decimal
   integer is refused by name, as `compile` refuses it.
2. Every test runs on its own instance on the js and wasm probes. The budget is therefore
   per test, which is what "a test IS a predicate" needs: a test's verdict cannot depend on
   which tests ran before it.
3. The wasm probe hands the host `ids.map(Number)`.

## Measured

- `test_profile_test`: the original fixture green on all three targets (was red on
  wasm); a 900-step loop fails on the js probe at the default budget and passes at
  `:fuel 1000`; two such tests both pass at 1000 (each 900..1000) — and fail on the
  previous shared-instance probe (`test-second` traps), which is the control.
- The js probe meters loop steps; the wasm probe meters calls and lets a `loop` run for
  free — so "only js starves" is the measured expectation, not an assumption.
- `cloud-itonami-commands`: 54/54 and 63/63 on `[:jvm-kir :js :wasm]` with `--fuel
  5000000`, where the same files answered 2/54 before.
- The interpreter target traps self-recursion past 100 frames whatever the budget,
  reported as `fuel-exhausted` (bisected: 100 passes, 101 fails). Not changed here;
  recorded so a component author writes such walks as `loop`.

## Not done

`amu test` still takes one standalone module; a module with `(:require …)` is refused
as before. The multi-module test gate remains the project's own harness.
