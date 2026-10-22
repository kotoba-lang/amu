# gpu-amd-vulkan-wgsl-rows-20261023 -- the AMD selection row rides the
# Vulkan and WGSL routes

Tick: 2026-10-23 07:xx JST. Chain branch `bot/amu-gpu-chain`, chain PR #1455.
Tracking: JUN-84 (AMD, Linear AWAI-40), parent JUN-55 (Linear AWAI-35 --
the issues moved teams).

## The slice: ONE design decision + its thin implementation slice

The last tick closed the route matrix for the four designed rows and named
the residue: ":amd has no designed row (unchanged)". This tick designs and
lands it (ADR-0364, the record):

1. `:amd` rides the shared subgroup-size-parametric `:subgroup-reduce`
   on TWO routes: the Vulkan route (`:vulkan` / `:glsl-v1`, RADV -- the
   one route that has ever executed anything in this repository) and the
   WGSL route (`:webgpu` / `:wgsl-v1`) because `:wgsl-v1` is `:amd`'s
   vendor-DEFAULT emission target -- the exact ADR-0363 rationale for
   Intel/ARM. Same rules 3 + 6 gate, fail closed included. AMD has no
   compute-capability contract (no sm_70+ analogue); the MSL and CUDA
   routes are other vendors' native routes and stay `:baseline`.
2. AWAI-40 scope item 1 (RDNA gfx9/10/11 wave32/wave64) is answered by
   design: the fold queries the width at RUNTIME (`gl_SubgroupSize`, the
   WGSL subgroup builtin) and rule 6's S | W gate admits both waves for
   every KIR-admitted workgroup (32..1024 are powers of two; both 32 and
   64 divide all of them). Selection dispatches on no wave.
3. AWAI-40 scope item 3 (RDNA ISA: v_fma_f32 / DPP / ds_swizzle) is
   closed as "not lowerable here, by construction": the emitters answer
   GLSL/WGSL/MSL/CUDA source and instruction selection belongs to the
   consuming driver's compiler (RADV's LLVM). No `:amd`-native arm is
   designed or needed. Scope item 2 (subgroup extension usability) is
   exactly rule 6: the descriptor must REPORT the ops, else `:baseline`.
4. NOT DESIGNED, named not hidden: a wave32 shuffle/DPP reduce row
   (AMD's `:warp-shuffle-reduce` analogue) -- it would bake a wave width
   the device chooses, which is what the parametric fold avoids.

## What changed

- docs/adr/0364-gpu-amd-subgroup-reduce.md: the decision (the state of
  record), with the wave-duality answer and the not-designed list.
- docs/adr/0356-gpu-kernel-variant-selection.md: dated amendment (the
  AMD row joins the table).
- docs/adr/0363-gpu-wgsl-route-subgroup-reduce-rows.md: its ":amd ...
  keep answering :baseline on every route" consequence marked SUPERSEDED
  as to `:amd`.
- src/kotoba/compiler/accelerator_variants.cljk: the subgroup-reduce
  row's vendor set gains `:amd` and the WGSL branch's set gains `:amd`;
  ns / `variant-bases` / `select-variant` docstrings state the row, the
  wave32/64 runtime-query answer, and that `:amd` leaves the
  "no designed row" clause. No emission changed (the row reuses the
  existing arms byte-for-byte -- ADR-0357 P1/P2 bind it).
- test/kotoba/compiler/accelerator_variants_test.cljk: new deftest
  the-amd-row-rides-the-vulkan-and-wgsl-routes -- positive selection
  matrix (4 route spellings x 4 workgroups x 3 operators x 2 wave
  widths) with :measured? false and an ADR-0364 basis; both waves (s=32
  wave32, s=64 wave64) select through the same gate; rule 3 end to end
  on :glsl-v1 (gl_SubgroupSize runtime query, no baked width, seal +
  verify round-trip) and on :wgsl-v1 (enable subgroups; NOT enable
  subgroup_id;, fold/2u start, no baked width, seal + verify); the
  rule-6 fail-closed battery on BOTH routes (8 device shapes x 4 target
  spellings, ewise and malformed KIR); :baseline on :metal/:msl-v1/
  :cuda/:cuda-v1 and on an absent target; determinism. Existing pins
  moved with the row: subgroup-reduce-rows-select-under-their-gates and
  each-route-selects-under-either-of-its-names gain :amd on the Vulkan
  pair and the WGSL pair; the fail-closed battery and the MSL-baseline
  pin gain :amd; "a vendor outside the designed rows" drops :amd from
  its :baseline set (that pin asserted exactly the state this decision
  changes).

## Verification (runner output, not paraphrase)

Scoped gate, the seven GPU-owned namespaces (scratch runner
scoped-gpu-gate.cljk -- never committed -- same engine and classpath as
run-tests.cljk), BEFORE this diff (scoped-gate-before.txt):

    Ran 80 tests containing 3921 assertions.
    0 failures, 0 errors.

AFTER this diff (scoped-gate-after.txt):

    Ran 81 tests containing 4739 assertions.
    0 failures, 0 errors.

-- +1 deftest, +818 assertions. The BEFORE run was taken twice this
tick: once at tick start and again from a clean base via a temporary
stash of this diff (stash push / run / stash pop, this bot's own stash,
dropped on pop); both answered 80 / 3921 / 0 / 0.

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

- IMPLEMENTED: the `:amd` selection row on the Vulkan and WGSL routes
  + its fail-closed gate (code + tests), and the ADR-0364 decision.
- ACCEPTED DESIGN ONLY: the fact-source half -- no producer exists on
  any route (the ADR 0371 provider's SUBGROUP reply is unimplemented),
  so every row, AMD's included, still fails closed without a filled
  descriptor. The AMD measurement channel is the same provider track.
- NOT DESIGNED: a wave32 shuffle/DPP row; any `:amd`-native emission
  arm. Both named in ADR-0364 with reasons.
- UNMEASURED, all of it: no measurement was taken this tick. The WGSL
  arm is UNCOMPILED (no WGSL validator on this host); the GLSL arm's
  toolchain evidence is prior (glslang 11:16.6.0); nothing has executed
  this variant (or any variant) on AMD hardware -- the Radeon 680M
  evidence of 2026-10-18/19 is a wire-42 probe reading and a workgroup
  measurement, NOT this row. Every select-variant answer for :amd keeps
  :measured? false; the :amd workgroup row (1024, measured, ADR-0358)
  is untouched (a different axis). The route matrix is now complete for
  all five classified vendors.
