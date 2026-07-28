# ADR 0164: T1.3 dual-backend pilot expand (string kit surface)

- Status: Accepted
- Date: 2026-07-28
- WBS: T1.3 (+ T4.2 surface coverage)

## Context

Pilot suite (ADR 0161/0163) covered control fixtures plus `string-join` /
`string-from-i64`. Pure-product `:string-ops` also lists contains / eq /
substring / fold-case / code-point-at; these already have unit dual-target
tests but were absent from the T1.3 conformance runner.

## Decision

Add five pure-product pilot cases (suite **7 → 12**):

| id | entry | expect |
|---|---|---|
| `:string-contains-kit` | `values/string_contains_kit.kotoba` | 1 |
| `:string-eq-kit` | `values/string_eq_kit.kotoba` | 2 |
| `:string-substring-kit` | `values/string_substring_kit.kotoba` | 3 |
| `:string-fold-case-kit` | `values/string_fold_case_kit.kotoba` | 1 |
| `:string-code-point-kit` | `values/string_code_point_kit.kotoba` | 65 |

`string-split` remains deferred (T4.2 optional). Full kotoba-lang matrix still
admission-blocked for most collection fixtures.

## Evidence

- `clojure -M:conformance` 12/12
- `lang_conformance_test` count + dual-backend assertions

## Related

- ADR 0161, 0162, 0163
- `lang/pure-product-profile.edn` `:string-ops`
