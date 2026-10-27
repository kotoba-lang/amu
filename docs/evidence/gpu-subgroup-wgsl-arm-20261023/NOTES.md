# The WGSL arm of the :subgroup-reduce emission (2026-10-23)

Tick: amu-gpu chain (bot/amu-gpu-chain). Tracking: JUN-55 (parent), JUN-56,
serving JUN-59 (Intel, ADR-0356) and JUN-60 (ARM, ADR-0357). Backlog item 4:
an implementation slice that needs no hardware.

## What landed (implemented, with tests)

- `kotoba.compiler.accelerator-subgroup-reduce/emit-wgsl`: the
  subgroup-size-parametric reduce fold in WGSL spellings -- the same fold as
  the Vulkan/GLSL arm (`emit-glsl`) to its letter (runtime `subgroup_size`,
  no baked width; P1 option-b scoping unchanged; P2: the partial index is
  `subgroup_id`, the cross-subgroup tree strides by `subgroup_size` and runs
  over `num_subgroups` partials; the same INFINITE extrema neutrals via
  `bitcast<f32>`).
- `lower` admits (:wgsl-v1, :subgroup-reduce) in both readings (the W3
  `:kotoba` arm via the `subgroup-emit-wgsl` cross-module wrapper, and the
  host arm). Rule 3 satisfied on the WGSL path: emission admission first.
- Selection rows did NOT move: `select-variant` still answers
  `:subgroup-reduce` only on the Vulkan route. Extending the rows to
  :wgsl-v1 is a separate design decision, proposed in ADR-0356's new
  amendment and decided nowhere.
- ADR-0356 amended (the WGSL-arm amendment; one stale sentence of the
  fact-producer amendment corrected to its landed state per ADR-0362's
  amendments).

## Spec pins (vendor documentation, not measurements; fetched 2026-10-23)

W3C WGSL spec (w3.org/TR/WGSL) + the merged gpuweb subgroups proposal
(github.com/gpuweb/gpuweb/proposals/subgroups.md):
- `subgroups` is an ENABLE extension (`enable subgroups;`).
- `subgroup_id` / `num_subgroups` are a LANGUAGE extension (automatically
  available where supported; `enable subgroup_id;` is a shader-creation
  error -- the emission must not spell it).
- Builtins: `subgroup_size`, `subgroup_invocation_id`, `subgroup_id`,
  `num_subgroups`; the fold uses `subgroupShuffleDown(v, delta)` (delta
  dynamically uniform; out-of-range source reads return an indeterminate
  value -- the emit-glsl guard is mirrored).

## Verification (runner output, not paraphrase)

GPU-owned seven-namespace gate (kbb --backend sci, the gate's engine and
classpath; scoped runner over accelerator{-targets,-variants,-test,
-pipeline,-subgroup-reduce,-spirv,-spirv-compile}-test):

  BEFORE (scoped-gate-before.txt): 60 tests, 2720 assertions,
  0 failures, 0 errors.
  AFTER  (scoped-gate-after.txt):  66 tests, 2858 assertions,
  0 failures, 0 errors.

The FULL gate (run-tests.cljk) is RED AT BASE and unchanged by this diff:
it aborts at namespace load with zero tests run -- "Error: Could not find
namespace: kotoba.form" (the W3 port; outside this diff). Full text:
full-gate-kbb.txt. No green suite is claimed.

Sample emission (W=64, :sum): sample-wgsl-w64-sum.txt.

## State honesty

- IMPLEMENTED: the WGSL emission arm and its admission (code + tests).
- ACCEPTED DESIGN ONLY: the vendor rows (ADR-0356/0357/0360/0361) -- their
  selection rows are unchanged; the row extension to :wgsl-v1 is PROPOSED
  (named in the ADR-0356 amendment) and not decided.
- UNCOMPILED: no WGSL compiler or validator exists on this host
  (`which tint naga wgsl_analyzer nvcc` -- empty, exit 1), so the emission's
  text contracts are the whole verification. The CUDA arm is in the same
  regime (no nvcc). The nbb/sci gate reads both readings' syntax (this run
  covers the :kotoba arm's parse), but the :kotoba arm's EXECUTION has no
  runner here and is UNVERIFIED.
- UNMEASURED: everything. No WebGPU execution path exists; no hardware ran
  this arm. No `:measured?` flag moved and no workgroup row was touched.
- Residue, not hidden: ADR-0357's own amendment paragraph was not updated
  this tick (ADR-0356's amendment names the P2 binding for the WGSL arm);
  no WGSL fixture tripwire exists (the regen script covers the GLSL
  fixtures only).
