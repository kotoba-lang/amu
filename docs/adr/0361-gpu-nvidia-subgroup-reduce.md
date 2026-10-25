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
repository, and nothing has run on NVIDIA hardware. [UNCOMPILED CLOSED
2026-10-24 as to one real toolchain: the emitted row (W in 32..1024 x
:sum/:max/:min, 18 files) compiles clean with the real nvcc 11.4
(V11.4.315) on the fleet's CUDA host xavier (Jetson AGX, L4T R35.4.1,
-arch=sm_72) -- 18 .cubin + 18 .ptx, each PTX `.target sm_72` with the
extern-C entry reduce_{sum,max,min}, received bytes sha256-identical to
the emitter's; docs/evidence/gpu/cuda-compile-xavier-20261024/. This host
still has no nvcc, the WGSL arm's UNCOMPILED is untouched, and UNMEASURED
is UNCHANGED -- a compile is not a measurement, no kernel has executed on
any GPU, no :measured? flag and no workgroup row moves.]

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
nothing has run on NVIDIA hardware) [COMPILED 2026-10-24 as to the
`:warp-shuffle-reduce` rung's arm: the arm's emitted row -- the whole
admitted row, W in 32..1024 x :sum/:max/:min, 18 files of 3 distinct
emissions (the arm is workgroup-size-parametric, W never baked) --
compiles clean with the real nvcc 11.4 (V11.4.315) on the fleet's CUDA
host xavier (Jetson AGX, L4T R35.4.1, -arch=sm_72) -- 18 .cubin + 18
.ptx, received bytes sha256-identical to the emitter's,
docs/evidence/gpu/warp-shuffle-cuda-compile-xavier-20261024/ (the
`:subgroup-reduce` rung's arm closed the same day in its own bracket
above); UNMEASURED is UNCHANGED everywhere and this host still has no
nvcc -- a compile is not a measurement.]; every answer keeps `:measured?
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

## Amendment (2026-10-25: the claim-protocol CUDA channel): the
paired-timing campaign adopts the protocol, metric-named and
sign-scoped

DECIDED (JUN-57, the row the baseline execute record's HONEST LEFT (b)
named -- "the claim-protocol adoption row for the CUDA channel ... is
NOT written, so no rule-2-class sign claim exists for this channel and
none is made"): **YES -- a CUDA measurement under the claim protocol
can exist**, by the protocol's own adoption clause ("a later vendor
campaign adopts it by citation, its own row" -- ADR-0360's
regime-robust magnitude claim protocol amendment, 2026-10-23; this is
that row), and the adoption is **metric-named and sign-scoped**, the
shape the WGSL channel's adoption (ADR-0360, 2026-10-25) established.
No hardware measurement runs in this slice; the ground is committed
records and committed instrument text, quoted in the record.

Grounding (facts, not design): the channel's instrument
(`scripts/gpu-cuda-reduce-timing.cu`, the ADR-0373 instrument kind
written for the CUDA channel) times every dispatch on TWO clocks and
prints both on every sample line -- `gpu_ns` "CUDA-event elapsed time
around the kernel on the GPU timeline" and `host_ns`
"CLOCK_MONOTONIC around submit -> completion (the launch ...)". Unlike
the WGSL channel (host clock only), this channel HAS a GPU-timeline
clock, so rule 1's gpu-ns baseline metric carries at its letter here.
The run unit the instrument already implements is the MSL channel's:
one fresh process per pair block, PAIRS = 20 interleaved pairs, WARMUP
= 2 discarded submits per arm, alternating AB/BA order, the Metal
instrument's LCG (seed 20261023, reset per process).

Part 1 -- THE ADOPTION CONTRACT (what makes a CUDA-channel record
claim-protocol):

  (a) Rule 1 carries with the baseline metric NAMED BY THE CHANNEL:
      the per-run baseline median is the pair block's REFERENCE arm
      (the denominator of the paired ratio -- `:baseline` for
      subgroup/baseline and warp-shuffle/baseline, `:subgroup-reduce`
      for warp-shuffle/subgroup) median over its 20 samples, in the
      named metric. Two metrics, never mixed in one clustering or one
      claim: `gpu_ns` (GPU timeline; the protocol's own metric class)
      and `host_ns` (submit -> completion). A claim-protocol CUDA
      record publishes, per metric, the per-run baseline medians per
      operator and the GAP-1.15 regime clusters (the machine is
      metric-parametric and unchanged; only the publication names the
      metric). Clusters run per (metric x operator x pair-type) -- a
      stratum the WGSL adoption did not need (one arm pair per channel
      there): the reference arm differs by pair-type, and rule 1's
      baseline is a clock-level proxy, so a cluster pools runs whose
      proxy is the same kernel. A claim in a metric whose clusters are
      unpublished is inadmissible.
  (b) Rule 2 carries IN FULL, unchanged: a regime-invariant sign is
      the only selection basis. The per-run ratio is the block's
      paired-median ratio (median over the 20 within-pair ratios
      armA/armB in the named metric -- the MSL channel's statistic,
      the one `paired-ratios.txt` already computes), and rule 2's
      correctness precondition (`:max`/`:min` bit-exact against the
      double CPU reference, `:sum` within the 0.05 bound) is verified
      inside the measurement, as the instrument already does. Sign
      claims are CHANNEL-SCOPED -- a CUDA-channel sign never flips an
      MSL or WGSL cell and never answers a workgroup row (the
      row-flip channel stays separate; ADR-0355's 2026-10-25 channel
      rule stands: the instrument channel answers no dispatch row) --
      and only the CUDA route's own selection questions consume it
      (HONEST LEFT (c)'s rows).
  (c) Rule 3 carries with NAMED LIMITS: magnitude claims stay
      within-channel, within-metric and regime-matched as written;
      CROSS-CLOCK magnitude claims (`gpu_ns` vs `host_ns`) are
      INADMISSIBLE -- the two clocks measure different spans (kernel
      only vs submit -> completion), the same cross-metric ban the
      WGSL adoption drew. Named hazard (design reasoning, NOT a
      measurement): fixed per-dispatch overhead common to both arms
      biases `host_ns` paired ratios toward 1 -- conservative against
      win claims (it can hide a real win, it cannot invent one through
      the common part) -- while asymmetric arm overhead could bias
      either way and is not assumed away; the instrument's stop event
      records on the host INSIDE the host span (named in the
      instrument, not hidden). Every magnitude publication on this
      channel keeps both clocks' raw per-block times beside the
      ratios (a record that hides them is inadmissible).
  (d) Rule 4 carries unchanged: this adoption measures nothing and
      moves nothing.

Part 2 -- WHAT THE ADOPTION DOES NOT DO: the committed 2026-10-25
xavier paired-timing run (`docs/evidence/gpu/
cuda-paired-timing-xavier-20261025/`) stays OUT (no rule-1
publication -- "regime" appears 0 times in its log -- and it predates
this adoption; its "RAW DATA, NOT A SIGN CLAIM" standing and its
maps-onto-no-row ruling stand). `paired-ratios.txt` remains raw data.
Named, not hidden: re-deriving rules 1 + 2 over that log's own sample
lines is mechanically possible (the derive parse is re-runnable
against the committed log) and is REFUSED for this record -- an
adoption is not retroactive, the same rule the WGSL channel applied to
its pre-adoption wall-clock read. No workgroup row (ADR-0355/0358),
`:measured?` flag, `:shapes` value, flip cell or selection answer
moves; `:arm`/`:unknown` stay provisional `:measured? false`; and this
adoption touches no MSL/Apple question (ADR-0360's narrowing names the
M1 Max, which no CUDA record measures).

Named missing pieces before a rule-2-class CUDA sign claim can exist
(each its own later slice): (i) harness-side rule-1 + rule-2
publication for the CUDA channel (a parse of the instrument's sample
lines in the `gpu_regime_classify.py` family) -- UNIMPLEMENTED; (ii) a
fresh paired-timing session under this adoption publishing both
sections -- UNMEASURED. Only then does HONEST LEFT (c) -- the
`:warp-shuffle-reduce` vs `:subgroup-reduce` vs `:baseline` speed
question -- have claim currency to consume; until then it is answered
by NO record, as before. UNMEASURED, named so no reading upgrades:
every CUDA sign/speed verdict; the clock/thermal regime structure of
the xavier blocks (rule 1's question on this channel -- the committed
run was one session with no regime control); cross-run stability;
every workgroup row.

State: ACCEPTED DESIGN ONLY (this amendment). IMPLEMENTED: nothing --
no code moves in this slice. MEASURED: nothing -- no hardware ran;
every number quoted here comes from committed records. Record:
`docs/evidence/gpu/claim-protocol-cuda-channel-20261025.txt`.

## Amendment (2026-10-25, later the same day: HONEST LEFT (c) is
ANSWERED -- the three-way speed question consumes the claim currency)

DECIDED (JUN-57, the row the adoption amendment left to "NO record, as
before"): the `:warp-shuffle-reduce` vs `:subgroup-reduce` vs
`:baseline` speed question is answered for what the claim protocol can
answer it for -- the CUDA route on xavier sm_72 -- from the two adopted
sessions (`docs/evidence/gpu/cuda-claimprotocol-run1-20261025/`,
`...-run2-20261025/`), whose verdicts agree 18/18 across sessions and
whose publications re-derive byte-exactly from their committed logs
(re-run this tick, `diff` empty both). Under rule 2 (a regime-invariant
sign is the only selection basis):

  (1) `:warp-shuffle-reduce` vs `:baseline`: REGIME-INVARIANT FASTER,
      6/6 strata (both metrics x :max/:min/:sum), 12/12 per-run ratios
      below 1.0 in each, both sessions -- selection basis at all three
      ops.
  (2) `:warp-shuffle-reduce` vs `:subgroup-reduce`: REGIME-INVARIANT
      FASTER at :max/:min (4/6 strata) -- selection basis there; at
      :sum (2/6) the sign is REGIME-SCOPED and cannot choose a variant
      either way (the W=64 run is above 1.0 in both shapes, both
      clocks, both sessions -- at :sum and W=64 `:subgroup-reduce` is
      faster every time it was measured -- while W>=128 sits far below
      1.0).
  (3) `:subgroup-reduce` vs `:baseline`: REGIME-SCOPED 6/6 (faster
      only in the W=32 regime, slower at W>=64) -- no selection basis.

Consequence: `select-variant`'s CUDA-route answer stays
`:warp-shuffle-reduce` and NOTHING MOVES -- the standing ladder is now
measurement-supported where rule 2 permits signs ((1) all ops, (2)
:max/:min) and design-ordered where it does not ((2)'s :sum gap, which
is named as unclaimed, not as measured). `(:cuda-v1,
:subgroup-reduce)` stays by-name-only; (3) promotes nothing. The
separate per-vendor question ADR-0356 names ("whether the CUDA-route
row should ever answer `:subgroup-reduce`") is NOT decided here.

Limits (the answer's scope, named so no reading upgrades): ONE device
(xavier, L4T R35.4.1, sm_72) -- every sign is xavier-scoped and every
other NVIDIA device is UNMEASURED on this question; sign claims are
CHANNEL-SCOPED (CUDA route only) -- they flip no MSL/WGSL cell and
answer no workgroup row (ADR-0355's 2026-10-25 channel rule stands);
reduce ops :max/:min/:sum, two shapes, six widths only; rule 3's
cross-clock magnitude ban stands (both metrics classify separately and
agree everywhere here); two agreeing sessions bind no distribution --
run 3+ cross-run stability is UNMEASURED. No `:measured?` flag,
`:shapes` value or workgroup row moves; `:arm`/`:unknown` stay
provisional `:measured? false`.

State: DECIDED (this amendment, the answer and its no-move
consequence) over MEASURED ground (the two sessions' signs, consumed
not re-measured). IMPLEMENTED: nothing -- no code moves. Record:
`docs/evidence/gpu/cuda-selection-answer-20261025.txt`.

## Amendment (2026-10-25, again later the same day: whether the
CUDA-route row should ever answer `:subgroup-reduce` is DECIDED --
both readings, with the reopen condition named)

DECIDED (JUN-57, the row the selection-answer record left to "NO
record ... this row does NOT decide it"): the question ADR-0356 names
-- "whether the CUDA-route row should ever answer `:subgroup-reduce`"
-- has TWO readings and this row closes BOTH. Ground: the two adopted
sessions (`docs/evidence/gpu/cuda-claimprotocol-run1-20261025/`,
`...-run2-20261025/`); their publications re-derived BYTE-EXACTLY
this tick (classifier over each committed log, `diff` empty, 912
lines each), so every number below is a tool-reproducible citation,
not an eyeball reading.

**Reading 1 -- answering the row at all. CLOSED since 2026-10-23.**
The CUDA-route selection question of that day's amendment is decided
and IMPLEMENTED: the ladder `:warp-shuffle-reduce` ->
`:subgroup-reduce` -> `:baseline`, rung 2 answering where the warp
gate does not reach (rule-6 subgroup facts reported, NO compute
capability; a reported cc below 7.0 or a malformed one fails closed
on both rungs -- `accelerator_variants.cljk` `cuda-cap-ok?` /
`nvidia-floor-ok?`, pinned by `accelerator-variants-test`, green in
the scoped gate this tick). NAMED, NOT HIDDEN, a citation hazard in
the 2026-10-25 selection record: its "(`:cuda-v1`,
`:subgroup-reduce`) stays by-name-only" describes the `lower`
by-name admission and must NOT be read as "select-variant never
answers `:subgroup-reduce` on the CUDA route" -- rung 2 selects it
on descriptor facts. The record stands as history; this row carries
the reconciliation.

**Reading 2 -- answering it IN PREFERENCE where the warp gate
holds. DECIDED: NO, on this evidence under this protocol.**

Part 1 -- what the evidence shows (sign claims CHANNEL-SCOPED,
DEVICE-SCOPED to xavier sm_72; paired-median ratios, warp/subgroup
above 1.0 means `:subgroup-reduce` faster): the ONLY measured cell
where `:subgroup-reduce` beats `:warp-shuffle-reduce` is (op :sum,
W = 64) -- run1 gpu_ns 1.0848 / 1.0683, host_ns 1.0874 / 1.0700;
run2 gpu_ns 1.081 / 1.073, host_ns 1.070 / 1.070; 8/8 per-run
ratios above 1.0 across both shapes, both clocks, both sessions.
Every other measured cell has `:warp-shuffle-reduce` first (at
:max/:min all widths; at :sum W = 32 and W >= 128). A raw-median
three-arm check at that cell (RAW DATA, outside the protocol's
ratio regime -- the adoption publishes no cross-stratum roll-up and
these arms sit in different pair blocks/processes) puts
`:subgroup-reduce` fastest there in both sessions (run1, n=1000003:
subgroup 111888 / 111248, warp 120000 / 120848, baseline 128448 /
128640 ns gpu; run2 subgroup 111664, warp 120080, baseline 127664
/ 129088) -- it bears on the question and, under the protocol,
decides nothing.

Part 2 -- why NO under the standing protocol. Rule 2 (adopted for
this channel, carried at its letter): a regime-invariant sign is
the ONLY selection basis. The (op :sum) warp/subgroup stratum is
REGIME-SCOPED in both sessions and both metrics, and the straddle
is WITHIN regime 1: rule 1's GAP-1.15 clustering pools the W = 64
runs with W = 128..512 (the reference arm `:subgroup-reduce`'s
per-run medians at W = 64 and W = 128 are 111248 / 111168 in
run1), so the W = 64 cell is NOT its own regime level and its
one-sided sign is not a regime-invariant sign anywhere. "A
regime-scoped sign cannot choose a variant, in either direction" --
the selection-answer record's ruling stands. Per-cell selection
units do not exist on this channel: the adoption's rule-2 unit is
the (metric x operator x pair-type) stratum and names no roll-up;
the Apple flip-cell precedent's "the cell's OWN claim-protocol
rule-2 verdict at that shape" is a DIFFERENT unit this channel has
never published. Adopting one is a rule-2 amendment -- its own
design row, PROPOSED here and deliberately NOT decided in this row.
Binding limits unchanged: one device (xavier, sm_72); two agreeing
sessions bind no distribution (run 3+ UNMEASURED); rule 3's
cross-clock magnitude ban stands.

Part 3 -- consequence and reopen. NOTHING MOVES: the ladder stays
`:warp-shuffle-reduce` -> `:subgroup-reduce` -> `:baseline`
byte-for-byte; at (op :sum, W = 64) the design-ordered answer
stands UNCLAIMED -- named as unclaimed, not as measured-ordered.
REOPEN CONDITION, either fires the question again: (i) a
cell-level (or other unit-level) rule-2 amendment for this channel,
adopted by its own row, and under it a REGIME-INVARIANT FASTER
verdict for `:subgroup-reduce` over `:warp-shuffle-reduce` at a
named (op, W) cell on a named device -- the (op :sum, W = 64) cell
is the standing candidate, its runs one-sided in both sessions; or
(ii) a stratum-level regime-invariant sign for `:subgroup-reduce`
over `:warp-shuffle-reduce` in some stratum.

CORRECTION to the selection-answer record, re-derivation-grounded
(publications reproduced byte-exactly this tick), named not hidden:
its (3) detail -- "the straddle separates by regime: the W = 32
regime is one-sided FASTER (~0.88..0.93), the W >= 64 regimes are
one-sided SLOWER (~1.03..1.18)" -- holds for the FOUR :max/:min
strata (verified: W = 32 0.919..0.927 faster, W >= 64
1.027..1.177 slower) but NOT for the two :sum strata, where the
straddle is WITHIN regime 1 (W = 256 marginally above 1.0 -- run1
1.011 / 1.009, run2 0.992 / 1.003 gpu_ns, 2-above/6-below then
1-above/7-below -- while W = 64/128/512/1024/32 sit below,
0.865..0.976). The (3) VERDICT is unchanged (REGIME-SCOPED 6/6,
no selection basis either way); only the straddle's shape was
mischaracterized for 2 of 6 strata.

States: DECIDED (this amendment: both readings' answers, the
no-move consequence, the reopen condition). MEASURED: nothing new
-- no hardware ran; every number is a citation of the two committed
sessions, re-derived this tick through the classifier. IMPLEMENTED:
nothing -- no code moves. ACCEPTED DESIGN ONLY: the claim-protocol
adoption, the ADR-0358 paired statistic, the ADR-0373 instrument
class. UNMEASURED, named so no reading upgrades: the (op :sum,
W = 64) cell's status under any cell-level unit (no such unit
exists); the :sum ordering on any device; every three-way sign on
non-sm_72 NVIDIA hardware; run 3+ cross-run stability; whether a
cell-level unit should exist (PROPOSED here); every workgroup row
(no `:measured?` flag moves; `:arm`/`:unknown` stay provisional
`:measured? false`). Record:
`docs/evidence/gpu/cuda-subgroup-preference-question-20261025.txt`.
