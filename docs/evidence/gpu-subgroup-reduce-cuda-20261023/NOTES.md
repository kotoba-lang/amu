# The CUDA arm of :subgroup-reduce (emit-cuda), 2026-10-23

Tick: amu-gpu chain (bot/amu-gpu-chain). Tracking: JUN-57 (the NVIDIA
vendor row), parent JUN-55. One row of work: the CUDA arm of the shared
subgroup-size-parametric reduce emission -- the LAST of the four emitters
to carry the fold (GLSL 2026-10-22, WGSL and MSL 2026-10-23) -- so that
rule 3 ("emission admission first") holds on the CUDA path exactly as it
now holds on the other three.

## What landed (implemented, with tests)

- `kotoba.compiler.accelerator-subgroup-reduce/emit-cuda`: the same fold
  to its letter, in CUDA spellings. `lower` admits the
  (:cuda-v1, :subgroup-reduce) pair in BOTH readings (the W3 `:kotoba` arm
  through `subgroup-emit-cuda`, the host arm directly), so the seal regime
  covers the emission like any other (a :subgroup-reduce CUDA artifact
  seals and verifies; relabeled baseline bytes fail closed -- pinned).
- The fold's CUDA letter (every spelling pinned to the NVIDIA CUDA C++
  Programming Guide, fetched 2026-10-23 -- VENDOR DOCUMENTATION, NOT A
  MEASUREMENT):
  - runtime size query: `warpSize`, the guide's built-in device variable
    ("a run-time value defined as the number of threads in a warp"). The
    width is 32 on every shipping NVIDIA device; the emission names the
    spelling, not the number -- no 32 is baked into the fold, and none of
    Intel's 8/16/32 variance is claimed here.
  - the shuffle: `__shfl_down_sync(mask, v, d, fold)` -- the guide's
    optional width parameter carries the runtime fold width (partitions
    the warp into fold-sized subsections, logical lane IDs from 0), and
    the guide's own return contract (an out-of-range source lane returns
    the caller's own var) is exactly why the `sgid + d < fold` guard
    drops the read instead of folding it in -- the same letter as every
    other arm.
  - the participation mask: `__activemask()`, the runtime active-lane
    query. No 32-lane constant (`0xffffffffu` -- the shuffle arm's baked
    spelling) appears anywhere in this arm's bytes; a test pins its
    absence. The guide's warning on `__activemask()` (an instantaneous
    snapshot, not a branch probe) is satisfied by construction: this
    kernel has no early exit (padded lanes fold the identity) and every
    launched lane calls every shuffle unguarded, so the snapshot names
    exactly the participating lanes.
  - P2 unchanged: the partial index is the SUBGROUP index --
    `threadIdx.x / warpSize`, CUDA's own spelling of the warp id (CUDA
    has no subgroup-id builtin) -- never a lid-derived fallback.
  - the partials array is a fixed `__shared__ float partials[W]` (the
    MSL/WGSL arms' fixed-workgroup-array choice), not the baseline CUDA
    reduce's dynamic `extern __shared__ float s[]` -- an arm-level
    deviation, documented in the ns docstring.
  - entry: the kernel's :kernel/name under the CUDA family's own extern-C
    kernel linkage (what the :warp-shuffle-reduce arm emits); the variant
    family's name-free `main` convention does not extend here.

Tests (accelerator-subgroup-reduce-test): cuda-emission-queries-the-
subgroup-size-at-runtime (including the negative pins: no baked fold loop
bound, no baked 0xffffffffu warp mask), cuda-each-operator-carries-its-
combine-and-identity (fmaxf/fminf and the __uint_as_float infinite
neutrals), cuda-cites-the-guide-spellings-only (including the negative
pins that the fold stays the shuffle loop -- never a __reduce_*_sync or
cub:: rewrite -- and that no GLSL/WGSL/MSL spelling leaks in),
cuda-cross-subgroup-fold-covers-every-partial (P2: partials[sg], strided
by sgsize), cuda-workgroup-shape-mirrors-the-kir (fixed partials[W], n as
the third kernel argument, and the `void main(` negative pin),
cuda-emission-refuses-off-its-row-and-is-deterministic.
accelerator-test: the CUDA admission block (the "CUDA arm admits no
Vulkan variant" block moved to "carries the variant" -- the same move the
MSL slice made), cuda-v1-subgroup-reduce-routes-to-the-arm-emitter
(routed bytes = the arm's bytes; seal/verify; relabel fails closed), the
CUDA row of every-arm-shares-one-operator-meaning, and the
(:cuda-v1, :subgroup-reduce) row of the exhaustive lower routing matrix
moved from "refuses" to "lowers".

## Compiler verification: NONE -- UNCOMPILED

Unlike the MSL arm (which compiled under the Apple Metal compiler), this
arm has NO compiler verification: no nvcc exists on the testing host and
none was installed. This is the WGSL arm's regime exactly -- the text
contracts the tests pin are the whole verification. Nothing has executed
this arm on any GPU (the CUDA emitter has no execution path in this
repository; wire 42 runs Vulkan only), and no speedup, timing or tuning
value is measured or claimed anywhere in this directory. UNMEASURED
stands.

## Verification (runner output, not paraphrase)

Touched namespaces, scoped run of the gate engine (kbb --backend sci),
scoped-gate-touched-namespaces.txt in this directory:

    Testing kotoba.compiler.accelerator-targets-test
    Testing kotoba.compiler.accelerator-variants-test
    Testing kotoba.compiler.accelerator-test
    Testing kotoba.compiler.accelerator-pipeline-test
    Testing kotoba.compiler.accelerator-subgroup-reduce-test
    Testing kotoba.compiler.accelerator-spirv-test
    Testing kotoba.compiler.accelerator-spirv-compile-test

    Ran 80 tests containing 3851 assertions.
    0 failures, 0 errors.

Baseline BEFORE this diff (scoped-gate-before.txt here; the same runner
over HEAD's six touched files re-shadowed first on the classpath, so the
baseline is a real run and not a recollection):

    Ran 73 tests containing 3684 assertions.
    0 failures, 0 errors.

-- the +7 tests / +167 assertions are this slice's.

The dual-reading form: the W3 `:kotoba` reading of `lower` gained the same
routing through `subgroup-emit-cuda`, mirroring the MSL slice's edit. It
is UNVERIFIED like its predecessors: the W3 scan refuses this module
(accelerator.cljk's own header records the E1005 at a `#'` fn literal), so
no runner on this host executes the typed reading -- the host reading is
what the gate above covers.

The FULL gate (`kbb --backend sci --classpath "src:test:$(kbb -Spath
-M:test)" run-tests.cljk`) is RED AT BASE and unchanged by this diff
(full-gate-kbb.txt here): it aborts at load with zero tests run --
"Error: Could not find namespace: kotoba.form", reached through
kotoba.compiler.js-value-target's :default arm (the W3 port; on the kbb
route `kotoba.form` resolves only to `src/kotoba/form.kotoba`, which nbb
cannot load). Same abort, same cause as every prior tick's evidence.
Named, not hidden; outside this diff. The suite is NOT green and this
report does not claim it is.

The emitted sources in shaders/ are the emitter's own bytes
(scripts/emit-gpu-subgroup-reduce-cuda.cljk writes them; rerun with

    kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" \
      scripts/emit-gpu-subgroup-reduce-cuda.cljk

). Deterministic: same emitter, same bytes.

## Comment-truth fixes riding along (no behavior change)

Three prose spots still said what was true before the MSL arm landed and
were false against the code: accelerator-variants' rule-3 note ("CUDA
only for :warp-shuffle-reduce" as an emitter fact), the-nvidia-row-rides-
the-vulkan-route-only's "(rule 3: each route's emitter admits its own
variant)", and the-wgsl-route-carries-the-intel-and-arm-rows' "(rule 3:
the MSL emitter admits :baseline only)". All three now state the true
reason a route answers :baseline despite an admitting emitter: ROW
SCOPE. Assertions did not move.

## State honesty

IMPLEMENTED: the CUDA emission arm and its `lower` admission (code +
tests), the fourth and last emitter of the fold.
ACCEPTED DESIGN ONLY: the four vendor selection rows (ADR-0356/0357/0360/
0361), which are UNCHANGED by this slice.
PROPOSED, decided nowhere: whether the NVIDIA CUDA-route selection row
should ever answer :subgroup-reduce (ADR-0361's amendment).
UNMEASURED: everything about performance. No `:measured?` flag moved, no
workgroup row was touched (the ADR-0358 measured rows keep their
provenance; :arm and :unknown stay provisional), and the JUN-57
measurement contract stands blocked on the ADR 0371 provider exactly as
before (no NVIDIA hardware exists here either).
