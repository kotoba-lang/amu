# gpu-nvidia-cuda-route-20261023 -- the NVIDIA selection row rides the CUDA
# route as the ladder's second rung

Tick: 2026-10-23 (JST). Chain branch `bot/amu-gpu-chain`, chain PR #1455.
Tracking: JUN-57 (NVIDIA), parent JUN-55 (Linear: the issues moved teams --
JUN-55 is now AWAI-35, JUN-57 is now AWAI-37).

## The slice: ONE design decision + its thin implementation slice

ADR-0361's CUDA-arm amendment left a named question "proposed here and
decided nowhere": whether the CUDA-route row should ever answer
`:subgroup-reduce`, and what that would mean against
`:warp-shuffle-reduce`'s baked-warp fold. This tick DECIDES it (ADR-0361's
same-day amendment, the full record), in two parts:

1. The row extends, as the SECOND rung of a deterministic CUDA ladder.
   `select-variant` answers `:subgroup-reduce` for `:nvidia` on the CUDA
   route (`:cuda` / `:cuda-v1`) under the SAME rules 3 + 6 gate as the
   Vulkan route -- fail closed included, the sm_70+ reported-capability
   floor included -- but `:warp-shuffle-reduce` (the CUDA-native row) is
   checked first in the table's cond and keeps precedence whenever its
   gate holds (a CONFIRMED compute capability 7.0+ and W >= 32). Every
   answer the warp row gives today is unchanged. The ladder is total and
   deterministic: :warp-shuffle-reduce -> :subgroup-reduce -> :baseline.
   The extension answers exactly ONE corner the warp row leaves open: a
   descriptor that reports the rule-6 subgroup facts and NO compute
   capability gets the parametric fold instead of :baseline -- the same
   treatment the Vulkan row already gives an absent capability.
2. The rung means the same fold, not a different one. The CUDA arm is the
   warp fold with the width queried at runtime (`warpSize`) instead of
   the baked 32 -- same shuffle loop, same out-of-range guard, same
   cross-warp tree -- so the ladder changes no reduction semantics
   (ADR-0357 P1's `:sum` association scope binds both rungs). Which rung
   answers is a capability-evidence question, not an algorithmic one.

Not decided here (one vendor per decision): nothing else. The route
matrix is now complete for the four designed rows -- Intel rides
Vulkan+WGSL, ARM rides Vulkan+WGSL (ADR-0363), Apple rides Vulkan+MSL
(ADR-0360 amendment), NVIDIA rides Vulkan+CUDA (this decision); the WGSL
route still does not carry Apple or NVIDIA, and :amd has no designed row.

## What changed

- src/kotoba/compiler/accelerator_variants.cljk: the subgroup-reduce
  row's route gate gains `(and (= :cuda-v1 route) (= :nvidia vendor))`
  with the precedence comment; ns, `variant-bases` and `select-variant`
  docstrings state the ladder and the one-corner scope.
- test/kotoba/compiler/accelerator_variants_test.cljk:
  the-nvidia-row-rides-the-vulkan-route-only is replaced by
  the-nvidia-row-rides-the-vulkan-and-cuda-routes -- Vulkan-route
  positive selection kept (:measured? false, ADR-0361 basis), the CUDA
  ladder pinned (rung 1 :warp-shuffle-reduce for a confirmed capability,
  rung 1 keeps precedence where BOTH gates hold, rung 2 :subgroup-reduce
  for rule-6 facts with NO capability), the rule-6 battery failing closed
  ON the CUDA route (nil/{}/missing op/non-dividing size, a reported
  capability below the floor or malformed), :baseline on MSL/WGSL, and
  rule 3 end to end on :cuda-v1 (select -> compile-kernel -> the CUDA
  arm's runtime `unsigned int sgsize = warpSize;`, `__activemask()`,
  `__shfl_down_sync(mask, v, d, fold)`, no baked fold width, the
  extern-C :kernel/name entry, then verify-artifact! round-trip). The
  fail-closed target block re-scopes NVIDIA out of the CUDA set (its
  absent-target case stays :baseline); each-route-selects-under-either-
  of-its-names gains the CUDA second-rung pair; rule-6-reads-the-facts-
  the-subgroup-answer-parses pins that a parsed SUBGROUP answer selects
  the CUDA second rung too (the SUBGROUP answer carries no compute
  capability -- exactly the corner the rung fills).
- docs/adr/0361-gpu-nvidia-subgroup-reduce.md: the decision amendment
  (the state of record); the closing "proposed here and decided nowhere"
  paragraph marked SUPERSEDED same day.
- docs/adr/0356-gpu-kernel-variant-selection.md: dated amendment
  superseding the CUDA-arm paragraph's clause and the Apple-decision
  amendment's "stays UNDECIDED" sentence.
- docs/adr/0363-gpu-wgsl-route-subgroup-reduce-rows.md: its stale "their
  ADRs scope them to the Vulkan route" consequence marked superseded.

## Verification (runner output, not paraphrase)

Scoped gate, the seven GPU-owned namespaces (scratch runner
scoped-gpu-gate.cljk -- never committed -- same engine and classpath as
run-tests.cljk), BEFORE this diff (scoped-gate-before.txt):

    Ran 80 tests containing 3886 assertions.
    0 failures, 0 errors.

AFTER this diff (scoped-gate-after.txt):

    Ran 80 tests containing 3921 assertions.
    0 failures, 0 errors.

-- the +35 assertions are this slice's (one deftest renamed, not added).

The FULL gate (`kbb --backend sci --classpath "src:test:$(kbb -Spath
-M:test)" run-tests.cljk`) is RED AT BASE and unchanged by this diff
(full-gate-kbb.txt here): it aborts at load with zero tests run --
"Error: Could not find namespace: kotoba.form", reached through
kotoba.compiler.js-value-target's :default arm (the W3 port; on the kbb
route `kotoba.form` resolves only to `src/kotoba/form.kotoba`, which nbb
cannot load). Same abort, same cause as every prior tick's evidence.
Named, not hidden; outside this diff. The suite is NOT green and this
report does not claim it is.

## State honesty

- IMPLEMENTED: the CUDA-route second rung for NVIDIA's
  `:subgroup-reduce` selection row + its fail-closed gate and precedence
  (code + tests), and the ADR-0361 decision.
- ACCEPTED DESIGN ONLY: the fact-source half is a contract statement --
  no producer exists on any route (the ADR 0371 provider's read/wire
  reply is unimplemented), so every row still fails closed without a
  filled descriptor. The rule-6 keys on the CUDA route would be filled
  by a CUDA-native probe (contract named; no probe exists).
- NOT DESIGNED: :amd has no row (unchanged); no new emission was
  designed or needed (the CUDA arm landed 2026-10-23).
- UNMEASURED, all of it: no measurement was taken this tick. The CUDA
  arm is UNCOMPILED (no nvcc on this host) and the CUDA emitter has no
  execution path in this repository; nothing has run on NVIDIA hardware;
  every answer keeps :measured? false (including both ladder rungs); no
  workgroup row of ADR-0355/0358 is touched (a different axis).
