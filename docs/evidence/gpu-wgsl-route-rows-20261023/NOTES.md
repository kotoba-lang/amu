# The WGSL route carries the Intel and ARM :subgroup-reduce rows (2026-10-23)

Tick: amu-gpu chain (bot/amu-gpu-chain). Tracking: JUN-55 (parent), serving
JUN-59 (Intel) and JUN-60 (ARM). Backlog item 4: a design decision plus its
thin implementation slice, no hardware needed. Decision of record:
docs/adr/0363-gpu-wgsl-route-subgroup-reduce-rows.md.

## The decision (ACCEPTED DESIGN + IMPLEMENTED same tick)

The 2026-10-23 WGSL-arm amendment of ADR-0356 proposed extending the
Intel/ARM selection rows to :wgsl-v1 and said "decided nowhere". This tick
decides it: YES for Intel and ARM, NO (undecided, separate per-vendor
decisions) for Apple and NVIDIA.

- The WGSL route is one route under two names -- api `:webgpu`, emitter
  target `:wgsl-v1` -- the ADR-0359 decision-3 idiom. `route-names` gains
  `:wgsl-v1 #{:webgpu :wgsl-v1}`.
- `select-variant` answers `:subgroup-reduce` for `:intel` and `:arm` on
  that route under the SAME gate as the Vulkan route: rule 3 (emission
  admission -- satisfied by the WGSL arm + `lower`'s (:wgsl-v1,
  :subgroup-reduce) admission, landed earlier 2026-10-23) and rule 6 /
  ADR-0357's capability precondition (:subgroup-ops carrying :basic and
  :shuffle-relative, :subgroup-size dividing W; anything else fails closed
  to :baseline).
- Apple (ADR-0360) and NVIDIA (ADR-0361) rows keep their ADRs'
  Vulkan-route scope: :apple/:nvidia answer :baseline on the WGSL route.
  What speaks against extending them is recorded in ADR-0363 (their
  vendor-default targets are :msl-v1/:cuda-v1, so no default path lights
  up) so a later decision can disagree on purpose.
- Why extend at all (ADR-0363 rationale): (1) rule 3 is an ordering rule,
  not a ban, and the CUDA row selects today with no in-repo execution
  path; (2) the Intel/ARM designs explicitly name the WGSL subgroup
  builtin as the runtime size query (ADR-0356 Intel row; ADR-0357 P2's
  surface clause); (3) `target-for`/`vendor-default-target` make :wgsl-v1
  the DEFAULT emission target for api-less Intel/ARM devices -- without
  the extension the two rows can never select on their own vendors'
  default path.

## What changed (implemented, with tests)

- `kotoba.compiler.accelerator-variants`: route-names WGSL pair; the
  subgroup-reduce selection branch admits the WGSL route for :intel/:arm
  only; docstrings updated (select-variant, route-names).
- `test/kotoba/compiler/accelerator_variants_test.cljk`:
  - NEW deftest `the-wgsl-route-carries-the-intel-and-arm-rows`: 216
    selection combinations (2 vendors x 6 wg x 3 operators x 2 target
    names x 3 subgroup sizes) each pinned to :subgroup-reduce with
    :measured? false and a string basis; the same rule-6 gate failing
    closed on this route (nil/{}/missing-op/non-dividing-size descriptors,
    ewise shape, malformed KIR); :msl-v1/:metal still :baseline (rule 3);
    rule 3 end to end -- the selected variant compiles on :wgsl-v1, the
    bytes carry `enable subgroups;` and NOT `enable subgroup_id;` (the
    spec pin: enable-ing the language extension is a shader-creation
    error), the fold starts at `fold/2u` with no baked width
    (`d:u32=\d+u` must not match), and the artifact seals and verifies;
    determinism pin.
  - the fail-closed target block re-scoped: :cuda/:cuda-v1/:msl-v1/:metal/
    nil still :baseline for all four vendors; :webgpu/:wgsl-v1 now
    :baseline for Apple/NVIDIA only.
  - `each-route-selects-under-either-of-its-names` extended with the WGSL
    name pair for :intel/:arm.
- docs/adr/0363-gpu-wgsl-route-subgroup-reduce-rows.md (the decision) and
  a dated amendment in ADR-0356 superseding its "decided nowhere" clause.

## Verification (runner output, not paraphrase)

GPU-owned seven-namespace scoped gate, kbb --backend sci, same engine and
classpath as run-tests.cljk (scoped runner over
accelerator{-targets,-variants,-test,-pipeline,-subgroup-reduce,-spirv,
-spirv-compile}-test):

  BEFORE (scoped-gate-before.txt): 66 tests, 2858 assertions,
  0 failures, 0 errors. (Verbatim transcript of the scoped run executed
  BEFORE the first edit of this tick; the runner is the scratch
  scoped-gpu-gate.cljk, never committed. Its totals equal the previous
  tick's recorded AFTER, which is how the regime was confirmed identical.)
  AFTER  (scoped-gate-after.txt):  67 tests, 3546 assertions,
  0 failures, 0 errors. (+1 test / +688 assertions.)

The FULL gate (run-tests.cljk) is RED AT BASE and unchanged by this diff:
it aborts at namespace load with zero tests run -- "Error: Could not find
namespace: kotoba.form" (the W3 port via kotoba.compiler.js-value-target;
outside this diff). Full text: full-gate-kbb.txt. No green suite is
claimed.

UNCOMPILED claim verified this tick (which-wgsl-tools.txt): `which tint
naga wgsl_analyzer` empty (exit 1), `which nvcc` empty (exit 1) -- no WGSL
compiler or validator on this host.

## State honesty

- IMPLEMENTED (code + tests): the WGSL-route selection rows for Intel/ARM
  and their fail-closed gate.
- ACCEPTED DESIGN ONLY: the vendor rows themselves as measurement
  contracts (ADR-0356/0357/0360/0361); ADR-0363's Apple/NVIDIA deferral.
- PROPOSED (undecided): extending the Apple/NVIDIA rows to the WGSL
  route; a Metal simdgroup row on the MSL route.
- UNCOMPILED: the WGSL emission text is test-pinned only (no validator on
  host), same regime as the nvcc-less CUDA arm.
- UNMEASURED: everything. No WebGPU execution path exists in this
  repository; no hardware ran the variant on this route (or any route).
  No `:measured?` flag moved and no workgroup row was touched. The rule-6
  fact producer (ADR-0362) is still unimplemented, so on BOTH routes
  every row still fails closed to :baseline without a filled descriptor.
