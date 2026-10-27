# gpu-apple-msl-route-20261023 -- the Apple selection row rides the MSL route

Tick: 2026-10-23 (JST). Chain branch `bot/amu-gpu-chain`, chain PR #1455.
Tracking: JUN-58 (Apple), parent JUN-55 (Linear: the issues moved teams --
JUN-55 is now AWAI-35, JUN-58 is now AWAI-41).

## The slice: ONE design decision + its thin implementation slice

The MSL-arm amendment of ADR-0356 left a named question "proposed here and
decided nowhere": does Apple's `:subgroup-reduce` selection row extend to
the MSL route, and where do the rule-6 facts come from there? This tick
DECIDES it (ADR-0360's same-day amendment, the full record):

1. The row extends. `select-variant` answers `:subgroup-reduce` for
   `:apple` on the MSL route -- `:metal` (api) / `:msl-v1` (emitter
   target), one route two names (the ADR-0359 decision-3 idiom; route-names
   gains the pair) -- under the SAME rules 3 + 6 gate the Vulkan route
   uses, fail closed included. Rule 3 holds (the MSL arm admits
   (:msl-v1, :subgroup-reduce) in both readings since 2026-10-23).
2. The rule-6 facts are the same descriptor keys on every route. The
   `:subgroup-size` / `:subgroup-ops` tokens are this table's capability
   vocabulary (the two ops the fold needs), not a Vulkan binding; a
   Metal-native probe would fill them from the device's SIMD-group facts
   directly. ADR-0362's wire-42 SUBGROUP request stays the VULKAN route's
   producer. No key, request or producer is invented here.

NOT decided here (one vendor per decision): the NVIDIA CUDA-route question
("whether the CUDA-route row should ever answer `:subgroup-reduce`") stays
undecided. The WGSL route still does not carry Apple (ADR-0363's scope is
Intel/ARM).

## What changed

- src/kotoba/compiler/accelerator_variants.cljk: route-names gains
  `:msl-v1 #{:metal :msl-v1}`; the subgroup-reduce row's route gate gains
  `(and (= :msl-v1 route) (= :apple vendor))`; ns + select-variant
  docstrings state the new scope and the route-agnostic fact contract.
- test/kotoba/compiler/accelerator_variants_test.cljk:
  the-apple-row-rides-the-vulkan-route-only is replaced by
  the-apple-row-rides-the-vulkan-and-msl-routes -- positive selection on
  all four route names of the two routes with :measured? false and an
  ADR-0360 basis, :baseline on the WGSL/CUDA routes, the rule-6 battery
  failing closed ON the MSL route (nil/{}/missing op/non-dividing size),
  and rule 3 end to end on :msl-v1 (select -> compile-kernel -> the MSL
  arm's runtime size query `uint sgsize [[threads_per_simdgroup]]`, the
  runtime fold `uint fold = min(sgsize, width);`, `simd_shuffle_down`, no
  baked fold width, the kernel's :kernel/name entry and never `main` --
  Metal refuses `main` -- then verify-artifact! byte round-trip). The
  fail-closed target block re-scopes :msl-v1/:metal out of the
  "outside every row" set for Apple and pins :baseline there for
  Intel/ARM/NVIDIA; each-route-selects-under-either-of-its-names gains the
  :metal/:msl-v1 pair; rule-6-reads-the-facts-the-subgroup-answer-parses
  pins that a parsed SUBGROUP answer selects on the MSL route too (the
  keys are the contract, whatever fills them).
- docs/adr/0360-gpu-apple-subgroup-reduce.md: the decision amendment
  (the state of record).
- docs/adr/0356-gpu-kernel-variant-selection.md: dated amendment
  superseding the MSL-arm paragraph's "proposed here and decided nowhere".
- docs/adr/0363-gpu-wgsl-route-subgroup-reduce-rows.md: its stale
  "the MSL route is untouched" consequence marked superseded.

## Verification (runner output, not paraphrase)

Scoped gate, the seven GPU-owned namespaces (scratch runner
scoped-gpu-gate.cljk -- never committed -- same engine and classpath as
run-tests.cljk), BEFORE this diff (scoped-gate-before.txt):

    Ran 80 tests containing 3851 assertions.
    0 failures, 0 errors.

AFTER this diff (scoped-gate-after.txt):

    Ran 80 tests containing 3886 assertions.
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

- IMPLEMENTED: the MSL-route selection row for Apple + its fail-closed
  gate (code + tests), and the ADR-0360 decision.
- ACCEPTED DESIGN ONLY: the fact-source half is a contract statement --
  no producer exists on any route (the ADR 0371 provider's read/wire reply
  is unimplemented), so every row still fails closed without a filled
  descriptor.
- UNDECIDED: NVIDIA's CUDA-route row question.
- NOT DESIGNED: a Metal simdgroup row (a Metal-native simd_sum/simd_max/
  simd_min variant). This slice routes the existing shared fold.
- UNMEASURED, all of it: no measurement was taken this tick. The MSL arm
  is COMPILED (Apple metal 32023.883, eighteen sources -- a toolchain fact
  recorded in gpu-subgroup-reduce-msl-20261023/, not a measurement and not
  re-measured here); the MSL route has no execution path in this
  repository, nothing has executed this arm on hardware, every answer
  keeps :measured? false, and no workgroup row of ADR-0355/0358 is touched
  (a different axis).
