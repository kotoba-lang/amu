# ADR 0360 — The whole-program budget bounds: expression nodes and lowered nodes (proposed)

- Date: 2026-10-01
- Status: Proposed (measured; not applied: it moves values that `lang/limits.edn` pins in several repositories, which is the
  owner's wave, as ADR 0358 was).
- Would amend: `lang/guest-grammar.edn` `:admission-limits :max-expression-nodes` (50 000), `kotoba.compiler.frontend.analyze/max-lowered-nodes`
  (100 000), `kotoba.verifier/max-expression-nodes` and its `.kotoba` twins, `kotoba.compiler.project/max-project-expression-nodes`
  (200 000) and `max-project-literals` (65 536).
- Related: ADR 0354 (limits are kept only when they bound a resource), 0358 (function count), 0359 (module literal bytes).

## Context

The project linker produces ONE source unit and the frontend analyses it as one program, so every per-program budget is a bound on the
whole compiler, not on a module. `analyze` charges one node per sub-expression of every desugared function body
(`validate-expr`, `max-expression-nodes`) and, after the helpers and dispatcher families are synthesized, one unit per lowered node
(`check-lowering-budget!`, `max-lowered-nodes`). The compiler's own sources are the largest program there is.

## Evidence (2026-10-01, native checker built from the sources with the bounds raised and a counter, `scripts/selfhost-wall/module-overlay.py`)

The unit `frontend/desugar.cljk` links (desugar, base, kernel-region, closure-types, expand and the three definitions it takes from validate and infer):

| quantity | measured | bound |
|---|---|---|
| functions after desugaring, before helpers | 1 471 | 16 384 (ADR 0358) |
| expression nodes (`validate-expr` budget) | 24 515 | 50 000 |
| functions after the helpers and dispatchers | 1 949 | 16 384 |
| lowered cost (`lowered-cost`) | 133 837 | 100 000 |

So the first Kotoba-route module of the frontend that is not small already exceeds `max-lowered-nodes` (`lowered program budget exhausted`) and uses half of
`max-expression-nodes`. The frontend is 12 modules; desugar is about two fifths of its Kotoba text.

## Decision (proposed)

`max-expression-nodes` and `max-lowered-nodes` become 4 194 304 (2^22) each: eight times what the linked frontend is expected to need
(about 4 x the desugar unit), still a bound (the analysis is linear in nodes; the `check` of a 3076-function module took ~19 s, ADR 0358). The linker's
`max-project-expression-nodes` and `max-project-literals` move with them (they are per source unit, measured by the same program). The agreement test
`value_bounds_agreement_test` lists the copies.

## Consequences

Programs refused today for a total between the old and new bounds are admitted; nothing admitted is refused. Until this lands, `amu check` of
`frontend/desugar.cljk` on the project route can pass only against a checker built with the bounds raised (BOOTSTRAP-REFERENCE builds in
this session did, and report `ok`).
