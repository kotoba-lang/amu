# ADR 0356 — The source admission bound: 1 MiB → 8 MiB

- Date: 2026-09-29
- Status: Accepted (owner decision, 2026-09-29).
- Amends: `lang/guest-grammar.edn` `:admission-limits :max-source-bytes`, ADR 0005
  (linked-source bound) as restated in ADR 0353.
- Related: ADR 0354 (limits are kept only when they bound a resource).

## Context

The reader refused any source over 1 MiB. On the selfhost route the compiler's
own modules are linked into one closure, and `frontend.cljk` alone is over 800 KiB.
The 2026-09-29 wall scan (316 sources, first refusal each) found 30 sources
refused by `source exceeds 1 MiB admission limit` and nothing else: the single
largest wall. The project linker already bounds a linked closure at 8 MiB
(`max-project-source-bytes`), so the 1 MiB was the tighter, older number.

## Decision

`:max-source-bytes` is 8 MiB (8388608), in the authority
(`kotoba-lang` `lang/guest-grammar.edn`), its vendored copy in kotoba-sema, and
`kotoba.compiler.frontend/max-source-bytes`, which `read-forms` now reads. The
bound still bounds a resource (reader time and memory) and stays a fail-closed
refusal, now naming 8 MiB.

## Consequences

- All 30 sources moved past this wall (measured): 13 of them stop next at
  `count requires a bounded vector…` (untyped parameters), the rest at
  assorted single walls.
- `bounded_edn`'s own `max-source-bytes` (EDN files, not guest source) is a
  separate bound and is unchanged.
