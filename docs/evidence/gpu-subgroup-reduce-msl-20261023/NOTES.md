# The MSL arm of :subgroup-reduce (emit-msl), 2026-10-23

Tick: amu-gpu chain (bot/amu-gpu-chain). Tracking: JUN-58 (the Apple
vendor row), parent JUN-55. One row of work: the MSL arm of the shared
subgroup-size-parametric reduce emission, so that rule 3 ("emission
admission first") holds on the MSL path exactly as the GLSL (2026-10-22)
and WGSL (2026-10-23) arms established it for theirs.

## What landed (implemented, with tests)

- `kotoba.compiler.accelerator-subgroup-reduce/emit-msl`: the same fold
  to its letter, in Metal spellings. `lower` admits the
  (:msl-v1, :subgroup-reduce) pair in BOTH readings (the W3 `:kotoba` arm
  through `subgroup-emit-msl`, the host arm directly).
- Entry point = the kernel's :kernel/name, NOT `main`: Metal refuses a
  kernel named `main`. This is compiler-verified, not folklore:

      msl-probe.metal:4:13: error: kernel function cannot be called 'main'

  (Apple metal 32023.883, the probe this tick ran before writing the
  emitter). The variant family's name-free `main` convention is a
  wire-42/GLSL-WGSL artifact and does not extend to Metal; the arm
  follows the ADR-0002 MSL family's own entry contract instead.
- Selection rows do NOT move (that is the NEXT decision, JUN-58's own):
  `select-variant` answers `:subgroup-reduce` for :apple on the Vulkan
  route only; :msl-v1 / :metal still answer :baseline. The reason text
  moved (emitter refusal -> row scope) and ADR-0356/0360/0363 say so.

Tests (accelerator-subgroup-reduce-test): msl-emission-queries-the-
subgroup-size-at-runtime, msl-each-operator-carries-its-combine-and-
identity, msl-cites-the-spec-spellings-only (including the negative pins
that the fold stays the shuffle loop -- never a simd_sum/simd_max/simd_min
rewrite -- and that no GLSL/WGSL spelling leaks in),
msl-cross-subgroup-fold-covers-every-partial (P2: the partial index is
the SIMD-group index, never lid arithmetic),
msl-workgroup-shape-mirrors-the-kir (including the `kernel void main(`
negative pin), msl-emission-refuses-off-its-row-and-is-deterministic.
accelerator-test: the MSL admission block, the MSL row of
every-arm-shares-one-operator-meaning (one identity per operator across
all arms), and the (:msl-v1, :subgroup-reduce) row of the exhaustive
lower routing matrix moved from "refuses" to "lowers".

## Compiler verification (toolchain fact, NOT a measurement)

All 18 emitted sources -- W in {32, 64, 128, 256, 512, 1024} x operator
in {sum, max, min}, the whole admitted row -- compile to AIR under the
Apple Metal compiler:

    toolchain: Apple metal version 32023.883 (metalfe-32023.883)
    host: Darwin 25.4.0 arm64
    all-compiled=yes   (compile-log.txt; 18/18 OK, no diagnostics)

The sources in shaders/ are the emitter's own bytes
(scripts/emit-gpu-subgroup-reduce-msl.cljk writes them; rerun with

    kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" \
      scripts/emit-gpu-subgroup-reduce-msl.cljk

then `xcrun metal -c shaders/<file>.emitted.metal -o air/<file>.air`
per file). This is the FIRST arm of :subgroup-reduce with any compiler
verification at all. It says what compiles, nothing more: NO Metal
execution path exists in this repository (the GPU brokers died with the
C loader; the replacement is the ADR 0371 provider track), nothing has
executed this arm on any GPU, and no speedup, timing or tuning value is
measured or claimed anywhere in this directory. UNMEASURED stands.

## Verification (runner output, not paraphrase)

Touched namespaces, scoped run of the gate engine (kbb --backend sci),
scoped-gate-touched-namespaces.txt in this directory:

    Testing kotoba.compiler.accelerator-test

    Testing kotoba.compiler.accelerator-subgroup-reduce-test

    Testing kotoba.compiler.accelerator-variants-test

    Ran 44 tests containing 3371 assertions.
    0 failures, 0 errors.

Baseline BEFORE this diff (measured by swapping HEAD's five files back
in, same scoped run): 38 tests, 3233 assertions, 0 failures, 0 errors
-- the +6 tests / +138 assertions are this slice's.

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

IMPLEMENTED: the MSL emission arm and its `lower` admission (code +
tests), with compiler verification on this host.
PROPOSED, decided nowhere: extending Apple's selection row to the MSL
route (and where its rule-6 facts would come from on a Metal-native
descriptor). ACCEPTED DESIGN ONLY: the row itself stays Vulkan-route-only
(ADR-0360).
UNMEASURED: everything about performance. No `:measured?` flag moved, no
workgroup row was touched (the ADR-0358 measured rows keep their
provenance; :arm and :unknown stay provisional), and the JUN-58
measurement remains BLOCKED on the ADR 0371 provider (wire 42 has no
route today). The Metal Toolchain (17F109) was installed on this host
during this tick to take the compile evidence -- host state, not repo
state.
