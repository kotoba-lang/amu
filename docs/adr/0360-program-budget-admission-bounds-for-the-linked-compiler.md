# ADR 0360 — The whole-program budget bounds: expression nodes and lowered nodes, 2^22

- Date: 2026-10-01
- Status: Accepted (owner direction: the 100% definition is an amu binary built by amu itself; the process of ADR 0358 followed).
- Amends: `lang/guest-grammar.edn` `:admission-limits :max-expression-nodes` (50 000 -> 4 194 304) and adds `:max-lowered-nodes` (was an
  unlisted constant, 100 000 -> 4 194 304); `kotoba.compiler.frontend.validate/max-expression-nodes` and its Kotoba twin, the literal in
  `kotoba.compiler.validate-expr/vx`, `kotoba.compiler.frontend.analyze/max-lowered-nodes`, `kotoba.verifier/max-expression-nodes` and
  `max-lowered-nodes` with their `.kotoba` compat twins (`verifier.kotoba`, `verifier/kir.kotoba`, `verifier/program.kotoba`),
  `kotoba.compiler.project/max-project-expression-nodes` (200 000 -> 4 194 304) and `max-project-literals` (65 536 -> 4 194 304).
- Related: ADR 0354 (limits are kept only when they bound a resource), 0356 (source bound 8 MiB), 0358 (function count, the process followed
  here), 0359 (module literal bytes).

## Context

The project linker produces ONE source unit and the frontend analyses it as one program, so every per-program budget bounds the whole
compiler, not a module. `analyze` charges one node per sub-expression of every desugared body (`validate-expr`, `max-expression-nodes`)
and, after the helpers and dispatcher families are synthesized, one unit per lowered node (`check-lowering-budget!`,
`max-lowered-nodes`). The compiler's own sources are the largest program there is, so on the real route every module behind
`frontend/namespace-defs` joining base + kernel-region + closure-types + expand was refused with `program expression budget exhausted`
or `lowered program budget exhausted`.

## Evidence (2026-10-01/02)

### What the compiler needs

Fully ported (Kotoba-route-clean) modules, measured on the real route with the bounds lifted and a counter on `charge-node!` /
`lowered-cost` (a bisection of the bound agrees with the counter: `expand.cljk`, 27 887 / 71 500; the counter sees 2.05x the budget
because the budget is charged by two passes with separate counters):

| module (closure) | source | functions | expression nodes (budget) | lowered cost |
|---|---|---|---|---|
| `frontend/expand.cljk` | 14 modules | 1 190 | 27 887 | 71 500 |
| `kotoba/mir.cljk` | 401 KB | 1 015 | ~24 400 | 49 680 |
| `compiler/affine.cljk` | 91 KB | 462 | ~7 000 | 10 024 |
| `compiler/definition_identity.cljk` | 98 KB | 810 | ~15 200 | 23 529 |
| `frontend/desugar` unit (overlay, earlier measurement) | | 1 949 | 24 515 | 133 837 |

That is 60 - 155 expression nodes and 110 - 240 lowered units per KB of source. The compiler's reach list (162 sources, 3 063 top-level
defns, 6.77 MB of text including the host arms and comments) is therefore expected to need roughly 0.25 - 0.6 M expression nodes and
0.45 - 1.0 M lowered units once its Kotoba arm is complete. The old 50 000 / 100 000 were exhausted by the first modules of the frontend
(`frontend/namespace-defs` joined with its closure).

### What a bigger bound costs

`check-native.sh` (the BOOTSTRAP-REFERENCE native checker rebuilt from these sources; user CPU seconds, on a host at load average 50 - 100, so
absolute numbers are upper bounds):

| shape | functions | expression nodes | check time |
|---|---|---|---|
| 1-line bodies, 1 module | 1 000 / 2 000 / 4 000 / 8 000 | 21 k / 42 k / 84 k / 168 k | 1.3 / 3.6 / 10.6 / 40.6 s |
| fixed 500 functions, bodies grow | 500 | 9 k / 17 k / 33 k / 65 k / 129 k | 0.43 / 0.89 / 1.9 / 4.4 / 9.4 s |
| same, larger | 500 / 500 / 1 000 | 513 k / 1.03 M / 2.05 M | 49 / 149 / 376 s |

So: in nodes at a fixed function count the check is near linear (about n^1.2 up to 130 k, about n^1.3 beyond; 0.07 - 0.18 ms per node);
the one clearly quadratic term is in the function count (8 000 functions of 21 nodes cost 40 s, 4x the node-linear prediction), which
`max-functions` (ADR 0358) already bounds at 16 384. Extrapolated, a program AT the new bound (4.19 M nodes) costs on the order of 15 - 20
minutes of checking on a loaded host; one at the compiler's expected size (0.25 - 1 M) costs 1 - 3 minutes. It is a bound that still
bounds a resource, not a number chosen for convenience.

### Why 2^22 and not larger

- It is the expression-node bound the source bound already implies: the source bound is 8 MiB (ADR 0356) and one expression node needs at
  least two source bytes (a token and a delimiter), so no program the source bound admits can exceed 2^22 nodes *before desugaring*;
  what the node bound still limits is the desugarer's expansion, which is the resource it was written for.
- The expected need is 0.25 - 0.6 M (expressions) and 0.45 - 1.0 M (lowered): 4 - 17x headroom, enough that the budget is not the next
  wall after the port completes, not so large that a runaway expansion is admitted.
- `max-project-expression-nodes` and `max-project-literals` count the linker's reading of the same text (98 k lists, 95 k non-symbol atoms
  in the reach list, counting both host arms): the old 200 000 / 65 536 (the latter was already below the 95 k atoms) move with it.
- `max-lowered-nodes` equals `max-expression-nodes`: the measured ratio lowered/expression is 1 - 5 (`let` inlining multiplies cost), so
  the lowered bound must be at least as large; at 2^22 its headroom over the expected need is the smaller of the two (4 - 9x) and that is
  the number to re-measure when the port completes.

## Decision

`:max-expression-nodes` and `:max-lowered-nodes` are 4 194 304 (2^22) in the authority (`kotoba-lang` `lang/guest-grammar.edn`,
`:admission-limits`), its vendored copy in `kotoba-sema` (`resources/kotoba/lang/guest-grammar.edn`), the frontend constants, the verifier
constants and their `.kotoba` twins, and `kotoba.compiler.project/max-project-expression-nodes`, which `lang/limits.edn` now lists as a
copy of `:language/admission :max-expression-nodes` (new key `:max-lowered-nodes` lists the frontend and the verifier). The linker's
`max-project-literals` moves to the same number. All remain fail-closed admission refusals.

## Consequences

- `value_bounds_agreement_test`: 98 limit copies compared, `the-admission-limits-agree-across-their-copies` now covers the project twin
  and `:max-lowered-nodes`; 0 failures. kotoba-sema `max_expression_nodes_test` pins the values, checks that a program past the OLD budgets
  (230 functions of 511 nodes) is admitted and that a lowered bound still refuses.
- Rescan of the 162-file reach list on the rebuilt native checker (`scripts/selfhost-wall/check-native.sh`): 92 -> 100 OK, no file that
  was OK is refused, and no file stops at a budget any more. The first walls behind the budget are Kotoba-route port gaps, not
  bounds: `frontend.cljk`, `sema.cljk`, `project.cljk`, `project_files.cljk` and `nbb/cli.cljk` stop at `referred name
  infer-expression-type is not exported by kotoba.compiler.frontend.infer` (the infer module's export surface), `kotoba_reader.cljk` at a
  `[k v]` map-fn destructure.
- The `build-native.sh` agent step traces only a one-line probe: a native image built without extra probes lacks the reflection entry for
  `BigInteger(String)` (constructor from a string) and reports `internal compiler error` on 11 sources (measured: `ios_aot`, `core`,
  `pe32plus`, ... all OK again once the previous build's metadata was merged into `agent-cfg`). `build-native.sh` should be given a probe
  that reads a literal wider than 64 bits.
- The vendored `guest-grammar.edn` copies in `grammar`, `kotoba`, `kotoba-tagline` and the pinned digests in the `guest_grammar_vendor_test`
  files were already out of step with the authority (see ADR 0358); they are NOT advanced here.
