# Seed R5 part B (effects): report, 2026-10-03

Rung R5 of the seed ladder, part B (docs/selfhost-seed-r5-design-20261002.md sections 5 and 6; what was built is section 11
of that design): local state (`atom swap! reset! deref @x`), the state ability (`defhandler perform handle with resume`,
`(handle body (catch e h))`), effect ceilings `{:effects #{..}}`, namespace `:capabilities` and the compile-time capability
policy `--policy`. Tag `seed-r5b` on the record commit, record `seed/rungs/r5b.record`. Every timing below was taken on a
loaded host (load average 40-47); they are indications, not results.

## Result

| item | value |
|---|---|
| bridge | commit 9e70b2470 (features, written in the R4B/R5A language): the head seed 4502396d **and** the recorded R4B seed 568d6152 both compile its unity to a49a6098 (552,016 B), which is its own fixed point |
| rung proof | commit 2d72ca46e: the seed uses its own effects (below); the bridge compiles that unity (13,806 lines, sha256 34526917..) to **04c11dbe** (552,688 B) = seed-1 = seed-2 |
| gates | `gates.sh --rung r5b --no-build --with-aux --with-unit` READY, 14 rows: BUILD ERR G1 (19/19, seed-0 and seed-1) G2 (65/66, 1 front-end refusal as before) G3 (refusal-r5b.txt, 276 programs, 0 differ) G4 (fixed point; seed-0 vs seed-1 containers 84/84 identical) G5 GR (r1 r3 r4 r4b + **r5 full: 77/77, 16/16 pinned texts TEXT-OK**) XTRA (run-r5b 19/19; R5A split fixed point 178c9ce4 558,872 B, SPLIT-G1/G2/G4, SEP 18/18) UNIT 12/12 KIR 19/19 LEXREAD LW A64GEN 756/756 |
| part B cases | the 38 of seed/tests/r5a/part-b.txt: 38/38 (11 conformance values = the manifest's, 16 pinned negatives with the reference text, 4 feature negatives, 7 feature positives incl. p13 = 12,497,500 over 5,000 stateful calls and p23 handle/catch = 705, both hand-derived in r5.spec) |
| sources | +1,115 / -34 lines in seed/*.kotoba and the contracts against c7123892b (21-check +605, 90-drv +174, 00-ns +66 generated, 60-proj +63, 30-lower +57, 20-names +29, 41-a64gen +24, 11-read +19, 10-lex +2); tests seed/tests/r5b (19 cases), golden refusal-r5b.txt |
| lineage | `scripts/seed/bootstrap.sh --no-head` from the committed R0 seed: every recorded rung r0 .. r4b reproduced, then r5b: bridge a49a6098 (by the R4B seed), seed-1 = seed-2 = 04c11dbe = record: `OK (recorded rungs through r5b)` |
| Embench compile | 19 ports, medians of 3, seed 24.8-30.5 ms per port vs stage-0 77.9-909.6 ms (`rung-report.sh`, load 42; indication only) |

## Rung proof: where the seed now uses local state and handlers

| place | before | after |
|---|---|---|
| 21-check `ck-r5b-cap` (every capability call) | `(-> M (ck-f2-or ..) (nm-put MM-CAPS ..))` | the heap handle in a cell: `(atom M)`, `swap!`, `reset!`, `@m` |
| 21-check `ck-r5b-clause-of` (every defhandler) | a loop counting the clauses into `M[MM-R1]` | the count is the state of `(defhandler ck-tally [:state :i64] ..)`; `ck-r5b-clause-scan` is stateful and self-recursive, so the seed compiles a specialization of itself under a handler |
| 90-drv `drv-r5b-set` (effect-set texts of E2154/E2176/E2177) | a loop accumulator | the text is the state of `(defhandler drv-acc [:state :string] ..)` whose put appends |

The seed contains two defhandlers, so its self-compile runs the handler checks, the stateful fixed point, cloning and
specialization, RES2/RET2 and the string state on itself; the fixed point holds and seed-0 (bridge) vs seed-1 produce identical
containers for G1/G2's 84 programs.

## Open

- KIR5's request (wire 23 `:entropy/draw`) is not done: it needs a keyword code (HEADS), the wire table of 21-check, 30-lower and a
  loader check; recorded in CONTRACT-REQUESTS.
- The rung proof is small (3 functions); the stat cells `M[MM-R0/R1]` remain return registers elsewhere in 21-check. Moving more of
  them to handler state is possible but changes no gate.
- Differences from stage-0 kept on purpose are listed in the design's section 11 (grant-set print order, E2159 suffix, 4-parameter
  stateful limit, E2169).
