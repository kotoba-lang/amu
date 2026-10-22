# ADR 0355 — Value-type descriptor bounds: depth 12 → 64, nodes 64 → 512

- Date: 2026-09-29
- Status: Accepted (owner decision, 2026-09-29).
- Amends: osaho ADR 0025 and amu ADR 0196 (depth 12), the depth/node clauses of
  ADR 0353, and `lang/limits.edn` `:language/static`
  `:type-descriptor-depth` / `:type-descriptor-nodes`.
- Related: ADR 0354 (language semantics are target-independent),
  `docs/selfhost-priority.md`.

## Context

The compiler's own passes walk Clojure-shaped s-expressions: symbols, keywords,
strings, integers, lists, vectors, maps. To write them in Kotoba the language
needs a closed sum type for that data. A closed sum type in this language has no
recursion; a recursive shape is written as an unrolled descriptor, and the
descriptor depth is how deep a tree the type can describe.

Depth 12 and 64 nodes were sized for the browser-row work (ADR 0025: structured
key/value spines). An s-expression type unrolled to a useful depth does not fit:
one level of the sum is around ten nodes, so depth 12 already needs more than
the 64-node budget, and real compiler input nests deeper than 12.

Neither number was a safety invariant. They bound the checker's work per type
(`lang/limits.edn`: "bounds the checker's work per type"), and
adr-2609242100 already makes the resource side a target-profile matter.

## Decision

1. `:type-descriptor-depth` 12 → **64**; `:type-descriptor-nodes` 64 → **512**.
   One unrolled level of an s-expression sum type (variant, then its list of
   children) costs two levels of descriptor depth, so depth 64 gives about 31
   levels of source nesting; roughly 8 nodes per level keeps that inside 512.
   (The first cut of this ADR was depth 32, which allowed only about 15 levels.)
2. Every copy moves together, as `lang/limits.edn` lists them: osaho
   `adt-depth-limit`/`adt-node-limit`, kotoba-sema `max-type-depth`/`max-type-nodes`
   and `max-schema-depth`/`max-schema-nodes`, kotoba-script
   `max-type-depth`/`max-type-nodes`, `runtime/browser-host.mjs`, and the
   vendored table in amu. `value_bounds_agreement_test` and kotoba-lang's
   `limits_test` compare them (98 copies at this change).
3. The other structural bounds are unchanged: `max-variant-cases` 32,
   `max-record-fields` 32, `max-expression-nodes`, `max-lowered-nodes`. They are
   not what limits an s-expression type.
4. Per ADR 0354, a target whose runtime cannot decode a 64-deep, 512-node
   descriptor refuses the program by name; the language bound is not lowered to
   suit it.

## Consequences

- Tests that pinned 12/13 and 20/21-field counts move: the record-literal test
  now meets `max-record-fields` (32) before the node budget, and the depth tests
  use 64/65.
- The browser host's descriptor decoder accepts the same bounds, so values that
  cross the boundary keep the same limits on both sides.
- Descriptor checking costs more per type in the worst case (still bounded).
