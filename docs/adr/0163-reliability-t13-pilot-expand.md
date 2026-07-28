# ADR 0163: T1.3 dual-backend pilot expand (string kit fixtures)

- Status: Accepted
- Date: 2026-07-28
- WBS: T1.3

## Context

Pilot suite (ADR 0161) had 5 control fixtures. T4.2 landed `string-join`;
PVA `string-from-i64` needs dual-backend regression in the conformance runner.

## Decision

Add two pure-product pilot cases:

| id | entry | expect |
|---|---|---|
| `:string-join-kit` | `control/string_join_kit.kotoba` | 5 |
| `:string-from-i64-kit` | `values/string_from_i64_kit.kotoba` | 4 |

Suite size **5 → 7**. Full kotoba-lang matrix still admission-blocked for most
collection fixtures.

## Evidence

- `clojure -M:conformance` 7/7
- lang_conformance_test updated

## Related

- ADR 0161, 0162
