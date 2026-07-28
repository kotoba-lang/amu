# ADR 0171: T1.3 pilot 13→20; T3.2 capability deny envelope; T9.3 test harness UX

- Status: Accepted
- Date: 2026-07-28
- WBS: T1.3 / T3.2 / T9.3

## T1.3

Expand dual-backend pilot with and/or, if-not, let, arith, nested-fn, true
literal, string-replace-all. Suite **13 → 20**. Regenerate pilot-golden.edn.

## T3.2

`admit!` wrapper rewrites admission denials to name **missing grants**, ABAC
violations, crypto/hardware/flow denials with stable
`:kotoba.error/capability-*` codes.

## T9.3

Documented harness: export zero-arity `test-*` returning i64 1.
CLI `kotoba test` human summary (default) + `--json`.
Fixture: `resources/kotoba/test-harness/smoke.kotoba`.
