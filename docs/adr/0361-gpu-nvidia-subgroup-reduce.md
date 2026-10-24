# ADR-0361 -- The NVIDIA row on the Vulkan route: the subgroup-size-parametric reduce

- Status: accepted as design. The selection row is implemented 2026-10-23
  (code + tests in `kotoba.compiler.accelerator-variants`); the row is
  UNMEASURED. The same-day amendment below extends the row to the CUDA
  route (second rung under `:warp-shuffle-reduce`), also implemented with
  tests, also UNMEASURED.
- Date: 2026-10-23
- Tracking: JUN-57 (NVIDIA). Parent JUN-55. One vendor per decision, the
  rule ADR-0356 set and ADR-0357 (ARM) and ADR-0360 (Apple) followed.

## Decision

NVIDIA's row on the Vulkan route is the SAME `:subgroup-reduce` variant
ADR-0356 designed for Intel and ADR-0357/ADR-0360 bound to ARM and Apple:
a subgroup-size-parametric intra-subgroup fold, one write barrier, a
cross-subgroup tree over the `W/S` partials. The selection predicate is
vendor `:nvidia` (as ADR-0355 classifies it: PCI 4318, or an `nvidia` /
`geforce` / `quadro` device-name fragment), op `:reduce`, operator
in `{:sum :max :min}`, `W >= 32`, on the Vulkan route (`:vulkan` or
`:glsl-v1`), under ADR-0356 rule 6's capability gate: the device
descriptor must report the fold's subgroup operations (`:subgroup-ops`
containing `:basic` and `:shuffle-relative`) and a subgroup size
(`:subgroup-size`) that divides `W`. One gate is NVIDIA-specific and
carried over from the CUDA row on purpose: whenever the descriptor reports
a compute capability at all, the CUDA row's sm_70+ floor binds this row
too -- a reported capability below 7.0, or a malformed one, answers
`:baseline` (fail closed), while an absent capability is not a refusal
(the reported subgroup facts are the capability evidence there, exactly as
for the other three rows). Every other answer -- the CUDA route, a device
that confirms no capability, another shape -- is what the rules already
say: the CUDA route keeps its own `:warp-shuffle-reduce` row (its decided
row -- since 2026-10-23 the CUDA emitter ADMITS `:subgroup-reduce` too,
see the amendment below, so the reason is row scope and not rule 3), and
the rest answer `:baseline`.
The rules of ADR-0356 bind this row, and ADR-0357's P1 (the `:sum`
association scope) and P2 (subgroup IDs, not `lid` arithmetic) bind the
emission byte-for-byte: this row reuses the existing emission, it emits
nothing new.

## Why the shared emission, and not a GLSL warp shuffle

`:warp-shuffle-reduce` is NVIDIA's row on the CUDA route only: its
`__shfl_down_sync` fold bakes warp width 32 into the emission and rule 3
keeps it off every other route. But CUDA has no execution path in this
repository (ADR-0002 names the emitters; the runtime `:gpu/compute`
route has only ever been Vulkan, and even that is gone today -- see the
loader-removal bullet of ADR-0355's honest state and ADR-0371). On the
one route that has ever executed anything, NVIDIA therefore had no
designed row at all before this ADR: rule 3 answered `:baseline` for
`:nvidia` on `:vulkan` even on a fully capable device. A second,
shuffle-flavoured GLSL emission would duplicate a fold the existing
emission already expresses; ADR-0360's precedent is one parametric
emission and one selection gate per shape, and NVIDIA's Vulkan subgroup
width (the warp) is exactly the width the emission queries at runtime
(`gl_SubgroupSize`) and never bakes. So NVIDIA joins the shared row on
the Vulkan route instead of growing a fifth emission arm.

## Design facts (vendor documentation, not measurements)

NVIDIA's execution width is the warp, 32. Vulkan subgroup support on
NVIDIA (`VK_KHR_shader_subgroup`) exposes the shuffle-relative operations
the fold needs from compute capability 7.0 (Turing) on; earlier
architectures report no subgroup shuffle. Nothing here has PROBED an
NVIDIA device's Vulkan subgroup surface (the probe that could was removed
with the loader); these are documentation facts, and rule 6 consumes the
descriptor's REPORTED facts, not the vendor name -- so the row is
admitted only for a device that says so, and the sm_70+ floor is stated
twice on purpose (the reported-capability gate above, and the reported-ops
gate) because `variant-bases` already names the floor for the CUDA row.
The stage arithmetic of ADR-0356 (W = 128, S = 32: 2 stages against the
baseline's 7) applies unchanged and is stage counting, not a speed claim.
The design assumption -- UNMEASURED -- is the same one the Intel, ARM and
Apple rows carry: removing most of the barrier cascade wins. No NVIDIA
hardware has run this variant here, and no report may cite this row as
optimization evidence.

What IS measured for NVIDIA, and is NOT this row: ADR-0358 replaced the
NVIDIA workgroup row with a measured one (256, kept inside a flat
128-1024 band) on the Tegra Xavier (nvgpu) through the then-existing
loader path. That is a workgroup-size measurement of that path. It says
nothing about this variant, and this ADR changes no workgroup row.

## Open contract gap (named in ADR-0360, unchanged here)

Rule 6 consumes descriptor facts (`:subgroup-size`, `:subgroup-ops`) whose
producer does not exist: the wire-42 answers of the ADR-0371 provider
plan carry no such facts (`INFO` is the four fields
`<device>|<api>|<maxWgX>|<unified>` and `DEVCLASS` is one class word). So
this row is selected today only for a descriptor that a future probe or
provider supplies with subgroup facts; a descriptor that reports none
fails closed to `:baseline` (rule 1: the portable variant runs). Producing
the facts is a separate design decision: ADR-0362 makes it (one additive
wire-42 request, `SUBGROUP`), design only -- the producer does not exist
yet.

## Measurement contract (JUN-57)

The row flips `:measured?` only on an interleaved baseline-vs-variant
reduce comparison with verified read-back (the protocol the workgroup
sweeps established: fresh-process runs, interleaved samples, verified
read-back words), on a NAMED NVIDIA device, recorded under
`docs/evidence/`. The measurement is keyed to the tested device (name and
its reported subgroup size), not to the vendor row: one NVIDIA generation
measured does not flip `:measured?` for any other (ADR-0356 rule 4's lock
is per sufficient descriptor dimension). It also cannot be taken until a
wire-42 route exists again (ADR-0371 provider; ADR-0355's honest state),
so today the row stays `:measured? false` in every answer, and neither
the provisional workgroup rows of ADR-0355 nor the measured ones of
ADR-0358 are touched by this ADR.

## Amendment (2026-10-23: the CUDA arm of the shared emission lands)

The subgroup-size-parametric emission gains its CUDA arm
(`kotoba.compiler.accelerator-subgroup-reduce/emit-cuda`) and `lower`
admits the (`:cuda-v1`, `:subgroup-reduce`) pair in both readings --
rule 3's emission-admission-first now holds on the CUDA path too, and the
fold has all four emitters covered (GLSL 2026-10-22, WGSL and MSL
2026-10-23, CUDA 2026-10-23). The arm keeps the fold to its letter in
CUDA spellings: the subgroup size is queried at runtime as `warpSize`
(the CUDA C++ Programming Guide's built-in device variable, "a run-time
value defined as the number of threads in a warp" -- the width is 32 on
shipping hardware and the emission names the spelling, not the number),
the shuffle is `__shfl_down_sync(mask, v, d, fold)` (the guide's width
parameter carries the runtime fold width; an out-of-range source lane
returns the caller's own var and the `sgid + d < fold` guard drops it,
exactly as in every arm), the participation mask is `__activemask()` (no
32-lane constant is baked anywhere in the source), and the partial index
is `threadIdx.x / warpSize` (CUDA has no subgroup-id builtin; P2 binds
unchanged). Spellings pinned to the NVIDIA CUDA C++ Programming Guide
(fetched 2026-10-23): vendor documentation, not a measurement.
UNCOMPILED and UNMEASURED: no nvcc exists on the testing host (the same
regime as the WGSL arm), the CUDA emitter has no execution path in this
repository, and nothing has run on NVIDIA hardware.

**The selection rows do NOT move.** `select-variant` still answers
`:warp-shuffle-reduce` for :nvidia on the CUDA route (this ADR's
`:subgroup-reduce` row stays Vulkan-route-only), and (`:cuda-v1`,
`:subgroup-reduce`) lowers only when asked for by name. Whether the
CUDA-route row should ever answer `:subgroup-reduce` (and what that would
mean against `:warp-shuffle-reduce`'s baked-warp fold) is a separate
per-vendor decision, proposed here and decided nowhere. No `:measured?`
flag moves and no workgroup row is touched.

(SUPERSEDED, same day, by the amendment below: the CUDA-route question is
decided and the row now rides the CUDA route as the ladder's second
rung.)

## Amendment (2026-10-23: the CUDA-route selection question is DECIDED)

The CUDA-arm amendment's "proposed here and decided nowhere" question --
whether the CUDA-route row should ever answer `:subgroup-reduce`, and what
that would mean against `:warp-shuffle-reduce`'s baked-warp fold -- is
decided here (JUN-57's own decision; one vendor per decision), in two
parts.

**Part 1: the row extends, as the SECOND rung of a deterministic CUDA
ladder.** `select-variant` answers `:subgroup-reduce` for `:nvidia` on the
CUDA route (`:cuda` / `:cuda-v1`) under the SAME rules 3 + 6 gate as the
Vulkan route -- fail closed included, the sm_70+ reported-capability
floor included -- but `:warp-shuffle-reduce` keeps precedence there: its
gate (a CONFIRMED compute capability 7.0+ and `W >= 32`) is checked first
in the table's `cond` and every answer it gives today is unchanged. The
ladder for an NVIDIA reduce kernel on the CUDA route is total and
deterministic: `:warp-shuffle-reduce` -> `:subgroup-reduce` ->
`:baseline`. The extension therefore answers exactly one corner the warp
row leaves open: a descriptor that reports the rule-6 subgroup facts and
NO compute capability gets the parametric fold instead of `:baseline` --
the same treatment the Vulkan row already gives an absent capability (the
reported subgroup facts are the capability evidence). Everything else is
unchanged: a reported capability below 7.0, or a malformed one, still
fails closed to `:baseline` on both rungs.

**Part 2: what the rung means against the baked-warp fold.** The two
rungs spell the same fold: the CUDA arm of the emission is the warp fold
with the width queried at runtime (`warpSize`) instead of the baked 32 --
the same `__shfl_down_sync` loop, the same out-of-range guard, the same
cross-warp tree. So the ladder changes no reduction semantics (ADR-0357
P1's `:sum` association scope binds both rungs): which rung answers is a
capability-evidence question, not an algorithmic one.

Rule 3 holds on both rungs (the CUDA emitter has admitted
`:subgroup-reduce` since the same day's CUDA-arm amendment, and
`:warp-shuffle-reduce` since the row first existed). The rule-6 facts are
the same descriptor keys as on every route (ADR-0360's fact-contract
decision binds unchanged: `:subgroup-size` / `:subgroup-ops` are this
table's capability vocabulary); ADR-0362's wire-42 `SUBGROUP` request
stays the Vulkan route's producer, and a CUDA-native probe would fill the
same keys from the device's warp facts directly -- no key, request or
producer is invented here. UNCOMPILED and UNMEASURED (no nvcc on the
testing host, the CUDA emitter has no execution path in this repository,
nothing has run on NVIDIA hardware); every answer keeps `:measured?
false`, and no workgroup row is touched.

**Amendment (2026-10-24, the NVIDIA WGSL-route selection question is
DECIDED).** The question ADR-0356's `:wgsl-v1`-selection amendment named
and left open -- "the Apple and NVIDIA rows stay Vulkan-route-only (their
ADRs' scope; extending either is a separate per-vendor decision,
undecided)" -- is decided HERE as to NVIDIA (JUN-57's own decision; one
vendor per decision -- the Apple row's WGSL question stays UNDECIDED):
YES, the WGSL route (`:webgpu` / `:wgsl-v1`, one route two names, the
ADR-0359 decision-3 idiom) carries NVIDIA's `:subgroup-reduce` row under
the SAME rules 3 + 6 gate as the Vulkan route, decided in three parts.

**Part 1: the row extends, with no ladder on this route.**
`select-variant` answers `:subgroup-reduce` for `:nvidia` on
`:webgpu` / `:wgsl-v1` whenever the rule-6 facts hold. There is NO
`:warp-shuffle-reduce` rung on this route -- that variant is CUDA
emission only (rule 3: admission first, and the CUDA emitter is not the
WGSL route's emitter) -- so the row is the route's first and only variant
rung: `:subgroup-reduce` -> `:baseline`, total and deterministic. The
precedence question the CUDA ladder answers does not arise here.

**Part 2: the sm_70+ floor rides along, unchanged.** The floor is
NVIDIA's row-wide requirement (the earlier amendment: "whenever the
descriptor reports a compute capability at all, one below 7.0 (or a
malformed one) answers `:baseline`, fail closed; an absent capability is
not a refusal"), and it binds this rung exactly as it binds the Vulkan
and CUDA rungs -- the gate is route-agnostic in the table. No new floor,
no new fact and no new key is invented.

**Part 3: the rationale is the AMD row's, plus route reality.** The WGSL
arm of the shared emission is the same runtime-width fold as every other
arm (`subgroup_size` queried at runtime, no baked width), so the
heterogeneity question the AMD row settled ("the RDNA wave32/wave64
duality is answered by the emission's runtime width query and rule 6's
`S | W` gate, not by selection") answers NVIDIA's fixed warp width a
fortiori -- 32 is just the reported `S`. And WebGPU-on-NVIDIA is a
deployed surface (browser and wgpu/Dawn-native stacks on NVIDIA hardware);
a dispatch on that surface previously answered `:baseline` even where the
device reports the fold's facts -- an honest but avoidable refusal now
that the emission arm exists and is admitted. Nothing here extends the
`CUDA`-route ladder or the `:warp-shuffle-reduce` row; the questions of
an Apple WGSL row and of any further vendor/route pair stay UNDECIDED,
one vendor per decision.

Implemented with tests (the selection row and its pins); UNCOMPILED (the
WGSL arm -- no WGSL compiler or validator on the testing host, the same
regime as when the arm landed) and UNMEASURED (no NVIDIA hardware has run
anything, no WebGPU execution path exists): every answer keeps
`:measured? false`, no `:shapes` / `:evidence` / flip cell and no
workgroup row (ADR-0355/0358) is touched. The slice record is
`docs/evidence/gpu/nvidia-wgsl-route-decision-20261024.txt`.
