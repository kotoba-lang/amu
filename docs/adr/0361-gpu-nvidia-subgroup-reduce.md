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

## Amendment (2026-10-25, third the same day: whether a cell-level
rule-2 unit should exist on this channel is DECIDED -- the unit is
ADOPTED at the code's answer-cell shape, per-operator cells are
REJECTED, and the standing (op :sum, W = 64) candidate's fate is
decided under it)

DECIDED (JUN-57, the row the subgroup-preference amendment left
PROPOSED -- "whether a cell-level unit should exist"). Three parts.

**Part 1 -- ADOPTED: a cell-level rule-2 unit exists on this
channel, by citation of the ADR-0373 flip-cell precedent's unit
shape.** The cell is the code's own answer granularity -- (metric,
W, pair-type, shape) -- with the reduce shape selected as a whole
(`:operators #{:sum :max :min}` pooled; the cell's pooled verdict
governs -- ADR-0373's decided shape: "the reduce shape is selected
as a whole ... the contract has no per-operator flip"). The cell's
own rule-2 verdict is rule 2 at its letter applied to the cell's
pooled per-run ratios (each pair block's paired-median ratio in the
named metric at that (W, shape, pair-type), one per operator per
session): REGIME-INVARIANT FASTER / SLOWER (every per-run ratio of
every observed regime on one side of 1.0) is the ONLY selection
role a cell verdict may play -- the MSL channel's flip-cell role, a
per-W measured-cell flip of the kind `:measured-cell` records
already key; anything else (any straddle) is regime-scoped and no
basis, in either direction. Metrics classify separately and never
mix (rule 3 unchanged). Publications under this unit are a FULL
CENSUS -- every (metric, W, pair-type, shape) cell published, so no
cell is cherry-picked out of the scan grid. Sessions carry the
ADR-0373 same-day re-session rule by citation: a same-day second
session is corroboration and licenses nothing the cell's own
session did not; a cross-day replication is its own record kind.
This unit is the ONLY cross-stratum roll-up this channel carries:
the operator pooling inside a cell is exactly the roll-up the
2026-10-25 adoption deferred to "its own design row" -- this row
names it and bounds it (operators only; no pooling across W,
pair-type, metric, shape, device or channel; a CUDA cell verdict
stays CHANNEL-SCOPED and DEVICE-SCOPED). Rule 4 unchanged.

**Part 2 -- REJECTED: per-operator cell units** ((op, W) verdicts
as selection units). Grounds: (a) the composed contract's decided
position (ADR-0373: "the contract has no per-operator flip and
none is invented here"; apple-w32-note: "an operator-split answer
at one cell off the two measured shapes would be overfitting");
(b) the selection surface carries no operator axis to answer --
`select-variant`'s answer cells and `:measured-cell` records key on
(device class, channel, W) and carry `:operators #{:sum :max :min}`
as a whole. NAMED, NOT HIDDEN: this rejection does NOT call the
(op :sum, W = 64) interaction noise -- it is real as data and
replicated 8/8 across both same-day sessions, both shapes and both
clocks (the ratios in Part 3 and its record) -- the rejection rules
it INADMISSIBLE as a selection unit under this protocol. Its
admissible home is a separate prospective row: operator-aware
selection would need its own design + code row (an operator axis in
`select-variant`'s answer surface -- expressible, since the KIR
carries the reduce operator and `select-variant` already reads KIR
facts, so this is a design refusal and not a structural
impossibility), a pre-registered hypothesis, and fresh sessions
under that registration -- PROPOSED here, deliberately NOT decided
here; the (op :sum, W = 64) interaction is that row's standing
candidate evidence.

**Part 3 -- the standing candidate's fate under the adopted unit:
it does not qualify. NOTHING MOVES.** Under the adopted unit the
(op :sum, W = 64) cell is not a cell (the unit pools operators).
The pooled (W = 64, warp-shuffle/subgroup) cell STRADDLES 1.0 in
every (session, shape, metric) slice -- 1 above / 2 below in all
eight slices (run1 gpu_ns 1.0848 / 0.9073 / 0.8901 at n = 1000003
and 1.0683 / 0.9081 / 0.8970 at n = 1048576; run2 gpu_ns 1.0813 /
0.9130 / 0.9083 and 1.0726 / 0.9191 / 0.9130; host_ns likewise
1-above/2-below in every slice; 4 above / 8 below pooled over all
12 blocks in EACH metric) -- so the cell cannot be REGIME-INVARIANT
FASTER under any regime clustering (a straddle fails rule 2's first
condition before regimes enter), and the straddle is
pooling-robust: every sub-pool straddles, so the conclusion holds
under the strictest reading (the cell's own session only) and the
most permissive (both sessions pooled) alike. The reopen condition
is RE-STATED at the adopted unit: (i) a REGIME-INVARIANT FASTER
verdict for `:subgroup-reduce` over `:warp-shuffle-reduce` at a
pooled (metric, W, pair-type, shape) cell of this channel on a
named device (the W = 64 cell is NOT a standing candidate under it
-- its data is spent and named), or (ii) unchanged: a stratum-level
regime-invariant sign in some stratum. The previous row's
"(op, W) cell" phrasing in (i) is superseded by this row's unit --
named, not hidden. The ladder stays `:warp-shuffle-reduce` ->
`:subgroup-reduce` -> `:baseline` byte-for-byte; no `:measured?`
flag, `:shapes` value, workgroup row or selection answer moves
(rule 4).

**States.** DECIDED (this row: the unit, the per-operator
rejection, the candidate's fate, the restated reopen). ACCEPTED
DESIGN ONLY: the cell unit's publication machinery does not exist
-- full-census cell publication (rule-1 regimes + rule-2 signs at
cells) is UNIMPLEMENTED and its own later implementation row;
until it lands NO cell-level rule-2 verdict may be published (this
row publishes no sign claim -- Part 3's straddle is arithmetic over
committed citations, tool-re-derived in the record, not a
verdict). MEASURED: nothing new (no hardware ran; both committed
sessions consumed, not re-measured). IMPLEMENTED: nothing (no code
moves). UNMEASURED, named: every cell-level verdict including the
W = 64 cell's (no machinery); the operator-aware selection row
(PROPOSED here); the :sum ordering between the two variants at
W = 64 on any device under any unit that could carry it; every
three-way sign on non-sm_72 hardware; run 3+; every workgroup row
(no `:measured?` flag moves; `:arm`/`:unknown` stay provisional
`:measured? false`). Record:
`docs/evidence/gpu/cuda-cell-unit-decision-20261025.txt`.

## Amendment (2026-10-25, fourth the same day: the cell unit's
publication machinery LANDS -- full-census cell publication moves
UNIMPLEMENTED -> IMPLEMENTED and the first cell censuses are
published over the two committed adopted sessions)

IMPLEMENTED (JUN-57, the implementation row the cell amendment
named): `scripts/gpu_regime_classify.py` now carries the full-census
cell publication -- `cuda_cell_census` (cell = (metric, W,
pair-type, shape); rule 1 at the cell over the pooled reference-arm
per-run medians; rule 2 at its letter over the cell's pooled per-run
ratios, operators pooled as a whole; an incomplete operator pool
names the gap and publishes NO verdict -- fail closed) and
`render_cuda_cell_census` (the FULL CENSUS publication, metrics
separately, both clocks' raw per-block times beside every cell row
per rule 3, cell verdicts CHANNEL-SCOPED and DEVICE-SCOPED, the
same-day session rule named, rule 4 unchanged), on the CLI route
`--cuda-cells`. The `--cuda-log` route is untouched and stays
byte-stable (re-derivation of both committed claim-protocol
publications still diffs EMPTY, 912 lines each).

PUBLISHED (derived, not re-measured): the first two cell censuses --
`docs/evidence/gpu/cuda-cell-census-run1-20261025/census.txt` (72
cells, 72 verdicts) and `docs/evidence/gpu/cuda-cell-census-run2-
20261025/census.txt` (72 cells, 72 verdicts; CORROBORATION ONLY, the
same-day rule). The decided candidate's verdict at the adopted unit
is now a published verdict, not arithmetic: every (W = 64,
warp-shuffle/subgroup) cell is REGIME-SCOPED in every (session,
shape, metric) slice -- the straddle separates BY REGIME (op=sum
one-sided above 1.0 in the fast level; op=max/op=min one-sided below
1.0 in the slow level) -- so no W = 64 cell is regime-invariant and
the reopen condition (i) is not triggered; NOTHING MOVES (rule 4;
this amendment still writes no `:measured-cell` record and moves no
selection answer -- whether any published cell verdict enters the
selection surface is its own later row). Cross-session (same-day,
corroboration-only): 71/72 cells agree in verdict class and side;
ONE NAMED DIFF: (gpu_ns, W = 256, subgroup/baseline, n = 1000003) --
run 1 regime-invariant slower, run 2 regime-scoped straddle.

**States.** IMPLEMENTED: the full-census cell publication machinery
(code + tests; `--self-test` TOTAL 2536 assertions passed / 0
failed, +45 over the committed 2491 pin at 189288da8). MEASURED:
nothing new -- no hardware ran; both sessions consumed, not
re-measured. ACCEPTED DESIGN ONLY: the claim-protocol adoption, the
cell unit, ADR-0358, ADR-0373 (unchanged). UNMEASURED, named: any
cell verdict on non-xavier hardware; run 3+; whether a published
cell verdict may enter the selection surface (its own row);
operator-aware selection (PROPOSED, its own row); every workgroup
row (no `:measured?` flag moves; `:arm`/`:unknown` stay provisional
`:measured? false`). Record:
`docs/evidence/gpu/cuda-cell-census-machinery-20261025.txt`.

## Amendment (2026-10-25, fifth the same day: whether a published
cell verdict may enter the selection surface is DECIDED -- YES,
under the entry contract)

DECIDED (JUN-57, the row the machinery amendment left standing):
**a published cell verdict MAY enter `select-variant`'s selection
surface**, under an entry contract adapted from the ADR-0373 flip
contract at the cell unit's own shape. Ground: the two committed
adopted sessions, re-derived byte-exactly this tick (the
`--cuda-cells` output of each committed measure-log diffs EMPTY
against the committed `census.txt`, 72 cells each -- nothing
quoted blind); no hardware ran.

**Entry contract (adopted).** (1) *Unique-winner rule*: entry is
per (W, shape) group of cells; arm v wins iff for every other arm
u the (v, u) pair cell is REGIME-INVARIANT with side "v faster";
anything else -- a scoped pair among the candidates, a cycle, no
arm beating every rival -- REFUSES and keeps the design ladder's
answer with no record (the measured-but-scoped refusal at its
letter). (2) *Both clocks or refuse*: the winner must hold
identically in `gpu_ns` and `host_ns` (no metric axis exists on
the record and the answer is metric-agnostic; NAMED AS NEW, the
flip records ran one clock; rule 3 untouched). (3) *Record shape
unchanged*: `:device` (the tested device class, xavier sm_72,
keyed the uB5G name-fragment way), `:channel`, `:route :cuda-v1`,
`:workgroup-size`, `:operators #{:sum :max :min}` whole,
`:shapes` (qualifying shapes only), `:evidence` (the group's own
session's runs + sanctioned cross-day replications; a same-day
second session is flip-note prose only, ADR-0373's naming rule by
citation). (4) *Flip and confirm are both entry*: a winner equal
to the design answer CONFIRMS (answer text unchanged,
`:measured?` true with the record -- the precedent's kept-
`:baseline` refutation records already do this); a differing
winner FLIPS the cell. (5) *Scope*: answer cells of the CUDA route
only; sign claims stay CHANNEL-SCOPED and DEVICE-SCOPED; no
workgroup row answers or moves.

**Rejected, named.** (a) single-pair entry -- the three-arm
ladder would answer a variant measured slower than its own lower
rung at that W (the (op :sum, W = 64) interaction is the standing
hazard shape: `:subgroup-reduce` beats `:warp-shuffle-reduce` in
every :sum run there while its pair against `:baseline` is scoped
and often slower); (b) metric-split or one-clock entry; (c)
regime-scoped verdicts as partial basis; (d) per-operator entry
(the cell-unit row's rejection, restated).

**Entry census over the committed evidence (derived):** winner =
`:warp-shuffle-reduce` (the design answer) at 10 of 12 (W, shape)
groups (W = 32/128/256/512/1024 x both shapes), both metrics,
IDENTICALLY in both sessions; REFUSE at W = 64 both shapes (the
warp-shuffle/subgroup cell straddles in both metrics and both
sessions); ZERO flips. The named cross-session cell diff
(`gpu_ns`, W = 256, subgroup/baseline, n = 1000003) touches no
entry outcome -- no group's winner reads that pair. Projected
consequence of the wiring row (its own later row; nothing moves
today, rule 4): 10 confirming `:measured-cell` records
(`:measured?` true, no answer text change), W = 64 keeps
`:measured? false` and no record, no flip anywhere. Reopen (i)
now reads mechanically: a future group whose unique winner is
`:subgroup-reduce` (REGIME-INVARIANT FASTER than both rivals,
both clocks) flips the CUDA-route answer at that W.

**States.** DECIDED: this row (the contract, the rejections, the
projection). IMPLEMENTED: nothing (no code moves; the wiring is
its own later row -- until it lands no cell verdict is consumed).
MEASURED: nothing new (consumed, not re-measured). ACCEPTED DESIGN
ONLY: the claim-protocol adoption, the cell unit + census
machinery, ADR-0358, ADR-0373. UNMEASURED, named: every workgroup
row (`:arm`/`:unknown` stay provisional `:measured? false`); any
cell verdict on non-xavier hardware; run 3+ / cross-day
replication; the :sum ordering at W = 64 on any device;
operator-aware selection (PROPOSED, its own row). Record:
`docs/evidence/gpu/cuda-cell-selection-surface-20261025.txt`.

## Amendment (2026-10-25, sixth the same day: the entry contract's
WIRING row LANDS -- the CUDA flip/confirm predicate + record data,
pinned by its tests)

IMPLEMENTED (JUN-57, the implementation row the fifth amendment
named): the entry contract is now APPLIED in
`kotoba.compiler.accelerator-variants`. NO hardware ran and nothing
is re-measured -- the table's ground is the committed cell censuses of
the two adopted sessions.

**What landed.** (1) `cuda-cell-entries` (public data): the entry
census as a table -- the five entered widths W =
32/128/256/512/1024, each `{:winner :warp-shuffle-reduce, :shapes
[1000003 1048576], :evidence [run 1]}`; W = 64 absent (its groups
refused). The valid rung-1 width band is exactly
32/64/128/256/512/1024 (validate!'s rule), so 64 is the band's only
non-entry. (2) `cuda-entry-cell` (private predicate): keys the tested
device class (the uB5G name fragment "xavier" AND a reported compute
capability exactly 7.2 -- both, fail closed), the measured channel's
route (`:cuda-v1`, either spelling), the reduce shape whole, an
entered width, and the rung-1 design answer (so a rung-2 answer cell
can never attach a record -- the tested class reports 7.2 by
definition); answers `:confirm` (winner equals the design answer --
answer text frozen, no note in `:basis`, `:measured?` true with the
record), `:flip` (a differing winner -- the cell answers the winner
with the record and `cuda-flip-note`), or refuse (nil). (3) The
record (point 3, shape unchanged): `:device "xavier sm_72"`,
`:channel :native-cuda`, `:route :cuda-v1`, `:workgroup-size`,
`:operators #{:sum :max :min}` whole, `:shapes` qualifying-only,
`:evidence` the group's own session's runs + sanctioned cross-day
replications (none exist -- run 2 is same-day prose only). (4)
`select-variant` consumes the record through the `:measured-cell` /
`:measured?` surface exactly as the Apple flip records do.

**The projection realized.** The 10 confirming (W, shape) groups
attach confirming records at W = 32/128/256/512/1024 on the tested
class on the CUDA route with NO answer text change anywhere; W = 64
keeps `:measured?` false and no record; ZERO flips. NAMED, NOT
HIDDEN: the 10 groups realize as FIVE per-W records naming both
shapes each -- the record keys carry no shape axis and the selection
query has none, so each (W, shape) group's record rides its W with
the qualifying shapes listed.

**States.** IMPLEMENTED (code + tests, +1 test +194 assertions over
the scoped-gate pin): the wiring in full, BOTH arms. MEASURED:
nothing new (consumed, not re-measured). ACCEPTED DESIGN ONLY: the
claim-protocol adoption, the cell unit + census machinery, the entry
contract (this ADR's earlier 2026-10-25 amendments), ADR-0358,
ADR-0373. UNMEASURED, named: every workgroup row (`:arm`/`:unknown`
stay provisional `:measured? false`); any cell verdict on non-xavier
hardware; run 3+ / cross-day replication; the :sum ordering at W = 64
on any device; operator-aware selection (PROPOSED, its own row); the
flip arm on real data (ZERO real flips -- its test is synthetic); the
name-fragment key's coarseness (a Jetson Xavier NX descriptor, also
sm_72, reads as the tested class under "xavier" + 7.2; a narrower key
is its own later row). Gates: scoped GPU gate GREEN 107 tests / 11240
assertions / 0 failures / 0 errors; FULL `run-tests.cljk` RED at base
(`Could not find namespace: kotoba.form`, ADR-0362, outside this
diff); `gpu_regime_classify.py --self-test` 2536/0 (regression pin).
Record: `docs/evidence/gpu/cuda-cell-entry-wiring-20261025.txt`.

## Amendment (2026-10-25, seventh the same day: the operator-aware
selection row is DECIDED -- the CUDA route gains an operator axis
under a PRE-REGISTERED contract, and the two committed sessions are
ruled exploratory and inadmissible as entry)

DECIDED (JUN-57, the row every earlier amendment carried as
"operator-aware selection (PROPOSED, its own row)"). NO hardware ran
this tick; the ground is the two committed adopted sessions consumed
as EXPLORATORY derivation through the committed parser
(`parse_cuda_pair_blocks`, scratch script, never staged) -- they
GENERATE the hypotheses below and can satisfy no entry under it.

**Exploratory census (derived, inadmissible).** At the per-operator
reading (one reading = one (session, metric) over the group's three
pair blocks, the block's paired-median ratio the statistic, unique
winner = faster than BOTH rivals in EVERY reading of both sessions x
both clocks): 36 (op, W, shape) groups, 36/36 with a unique winner --
ZERO refusals at this unit; the pooled W = 64 refusal resolves as
exactly the operator split. 34 groups' winner is `:warp-shuffle-reduce`;
EXACTLY TWO -- (op `:sum`, W = 64, both shapes) -- winner
`:subgroup-reduce`, with subgroup/baseline paired-median ratios
0.8763 / 0.8646 (n = 1000003) and 0.8715 / 0.8790 (n = 1048576)
gpu_ns, within-block one-sided 19-20/20, in both sessions and both
clocks. NAMED: this cuts against the entry contract's rejection-(a)
hazard reading ("its pair against `:baseline` is scoped and often
slower") -- that was the pooled-stratum reading; at the per-op unit
the (:sum, W = 64) subgroup/baseline pair is decisively one-sided
the other way in every reading.

**Adopted contract.** (1) *Unit + surface*: a per-operator record
keys `:operators #{op}` and applies only to KIRs of that operator;
the pooled records are unchanged and answer everywhere no per-op
record applies; PRECEDENCE: the per-op record answers its operator at
its W (the KIR carries the reduce operator, `select-variant` reads
KIR facts). (2) *Entry group*: (op, W), `:shapes` qualifying-only,
the pooled record shape (3) with single-op `:operators`. (3) *Entry
rule*: unique-winner + both-clocks + **CROSS-RUN INVARIANCE** (NAMED
AS NEW -- rule 2's regime machine has no pool at this unit, so
REGIME-INVARIANCE is replaced by every qualifying reading agreeing
one-sided: every session x both clocks x every qualifying shape;
anything else REFUSES and keeps the standing answer with no record).
(4) *Replication requirement*: EVERY per-op entry (confirm or flip)
requires at least TWO fresh sessions UNDER THIS REGISTRATION on at
least TWO different UTC days agreeing in every reading -- the two
committed sessions (same-day, hypothesis-generating) are EXPLORATORY
forever and flip-note prose only (ADR-0373's same-day rule by
citation); a flip cannot land before the cross-day replication
exists. (5) *Pre-registration*: H1 (the standing candidate): at
(op `:sum`, W = 64) on xavier sm_72 on the CUDA route
`:subgroup-reduce` is the unique winner in every qualifying reading;
H2 (the contrast): every other (op, W) group's unique winner is
`:warp-shuffle-reduce` (confirms). The admissible sessions' protocol
is FIXED here (the ADR-0358 instrument class, the full 108-block
grid, one fresh process per block, PAIRS=20 interleaved, WARMUP=2,
AB/BA alternating, published LCG seed, both clocks, untimed verified
read-back, correctness re-verified inside the measurement, the
committed classifier routes); a hypothesis that fails REFUSES its
group and the failure is recorded -- pre-registration includes the
failure mode. (6) *Scope*: CUDA route only; sign claims CHANNEL-
SCOPED and DEVICE-SCOPED to xavier sm_72 (the name fragment AND
reported 7.2, fail closed); rung-2 cells never attach a per-op
record; no workgroup row answers or moves; the name-fragment key's
coarseness rides along unchanged (NAMED -- the per-op records widen
the Xavier-NX-key gap's blast radius; the narrower key is its own
later row).

**Rejected, named.** (a) consuming the committed sessions (or any
pre-registration data) as entry -- the overfitting hazard at its
letter, and the exploratory census's strength is exactly why the
registration must precede the fresh data; (b) single-pair entry (the
three-arm rule is what structurally excludes the "slower than its own
lower rung" hazard); (c) the operator axis on the Metal/MSL channel
(ADR-0373's "no per-operator flip" stands there -- the two channels'
contracts now differ at the operator axis, named); (d) per-sample
sign counts as the statistic (reported beside every ratio, consumed
nowhere); (e) workgroup-row movement or pooled-layer change (the per-
op layer only ADDS where the pooled layer refused or an admissible
per-op winner differs); (f) amending the pooled unit to carry
operators (the operator axis is a narrower layer over it, not a
replacement).

**Consequence today: NOTHING MOVES** (docs-only diff; rule 4). No
record, no `:measured?` flag, no selection answer, no `:shapes`
value, no workgroup row. At (op `:sum`, W = 64) the design-ordered
answer stands UNCLAIMED (measured but inadmissible -- named as
unclaimed, not measured-ordered). Projected once the later rows land:
under the registration, reproducing the exploratory census would
FLIP (:sum, W = 64) for `:sum` KIRs on the tested class, CONFIRM
(:max/:min, W = 64) (`:measured?` true there -- the one projected
`:measured?` movement, leaving the pooled refusal's false), and
materialize no per-op record at the 34 design-answer groups. New
rows created, each its own later row: (i) the wiring (per-op entry
table + per-op arm of `cuda-entry-cell` + precedence + tests);
(ii) the per-op census publication route in
`scripts/gpu_regime_classify.py` (UNIMPLEMENTED); (iii) the
measurement rows (fresh session A, then cross-day session B);
(iv) the narrower device-class key. Named interactions: the
cell-unit row's reopen (i) is NOT triggered and this track runs
parallel to it; the "READING 2" decision stands scoped to the pooled
protocol (H1 is its registered successor question, registered not
answered); the entry contract's rejection (d) "per-operator entry
stays rejected" is SUPERSEDED for the CUDA route at the (op, W) unit
by this row (earlier records stand as history).

**States.** DECIDED: this row (contract, rejections, pre-registration,
consequence). IMPLEMENTED: NOTHING (no code moves). MEASURED: nothing
new (consumed as exploratory derivation, not re-measured). ACCEPTED
DESIGN ONLY: the claim-protocol adoption, the cell unit + census
machinery, the entry contract + wiring (earlier 2026-10-25
amendments), ADR-0358, ADR-0373. UNMEASURED, named: H1/H2 under
admissible sessions; every per-op verdict on non-xavier hardware; run
3+ / cross-day replication; the :sum ordering at W = 64 on any device
under any admissible unit; the flip arm on real data (ZERO real
flips); every workgroup row (`:arm`/`:unknown` stay provisional
`:measured? false`); the name-fragment key's coarseness. Gates:
scoped GPU gate GREEN 107 tests / 11240 assertions / 0 failures / 0
errors (docs-only diff, regression pin); FULL `run-tests.cljk` NOT
RUN this slice (no .cljk touched) -- documented red at base
(`Could not find namespace: kotoba.form`, ADR-0362), NO green suite
claimed; `gpu_regime_classify.py --self-test` 2536/0 (regression
pin); `--cuda-cells` re-derivation of both committed censuses diffs
EMPTY. Record:
`docs/evidence/gpu/cuda-operator-aware-selection-20261025.txt`.

## Amendment (2026-10-25, eighth the same day: the per-op census
publication route LANDS -- row (ii) of the operator-aware row's
created rows, the pre-registration's analysis fixed in committed
code BEFORE any fresh session is measured)

IMPLEMENTED (JUN-57; NO hardware ran this tick, nothing
re-measured). WHAT LANDED: `scripts/gpu_regime_classify.py` gains
`cuda_op_census` + `render_cuda_op_census` + the `--cuda-op-census`
CLI route + self-test fixtures (`_self_test_cuda_op_unit`,
`_self_test_cuda_op_corpus`): the full per-operator census over one
or more CUDA paired-timing sessions -- group (op, W, shape), one
reading per (session, metric) over the group's three pair blocks,
the block's paired-median ratio (armA/armB as declared, never
re-oriented) the statistic, the reading's unique winner = the arm
faster than BOTH rivals, the group's fold = the same unique winner
in EVERY reading (unique-winner + both-clocks + CROSS-RUN
INVARIANCE, the entry rule's reading arm), and the (op, W) entry
fold over qualifying shapes (`:shapes` qualifying-only). The
within-block one-sided count rides beside every ratio and is
consumed NOWHERE (rejection (d)).

**Why before row (iii).** The pre-registration fixes the admissible
sessions' protocol as "the committed classifier routes"; a session
analyzed by code written after the fact is not a pre-registered
analysis. Rows (ii) then (iii) is therefore the registration's own
order, not a preference.

**Named, the fail-closed readings this row adopts where the
registration left a gap** (each named so no later reading silently
upgrades): (1) a shape QUALIFIES iff every reading at that shape
(every session x both clocks) agrees one-sided on one unique winner;
(2) two qualifying shapes naming different winners REFUSE the entry
group outright -- one record cannot name two winners and the
selection query carries no shape axis; (3) a missing pair block
fails its reading closed (no unique winner) and is published as a
named gap; (4) the replication requirement (two fresh registration
sessions on two different UTC days) is NOT derivable from the logs
(their contents carry no UTC dates) and is decided at ENTRY by the
wiring row -- the census never reads session admissibility (its
verdict column is labeled "reading-arm verdict" for exactly that).

**Verified (real runs).** `--self-test` TOTAL 2572/0 (the committed
base pin 2536/0, delta +36 = this slice's fixtures; every
pre-existing assertion still green). The route over the two
committed 2026-10-25 measure-logs exits 0 with stderr 0 bytes and
re-derives the exploratory census EXACTLY: 36/36 groups fold (ZERO
fold diffs against the exploratory scratch derivation), fold census
warp-shuffle 34 / subgroup 2 (the two being (op `:sum`, W = 64) at
both shapes), 18/18 entry groups entering at the reading arm. The
decision record's cited numbers reproduce at 4 dp inside the corpus
self-test. Scoped GPU gate GREEN 107 tests / 11240 assertions / 0
failures / 0 errors (the diff touches NO .cljk namespace -- regression
pin at the committed pin). FULL `run-tests.cljk` NOT RUN this slice
(no .cljk touched) -- documented red at base (`Could not find
namespace: kotoba.form`, ADR-0362) outside this diff, not
re-verified here, NO green suite claimed. `find docs -name '*.sh'` ->
0 files.

**Consequence today: NOTHING MOVES** (rule 4): no record, no
`:measured?` flag, no selection answer, no `:shapes` value, no
workgroup row; the ladder
`:warp-shuffle-reduce -> :subgroup-reduce -> :baseline` stays
byte-for-byte.

**States.** DECIDED: this row (the (ii)-before-(iii) ordering, the
fail-closed readings (1)-(4)). IMPLEMENTED: the per-op census
publication route (row (ii)) -- code + tests. MEASURED: nothing new
(NO hardware ran; the two committed sessions CONSUMED as exploratory
derivation, re-derived through the now-committed route -- not
re-measured, still inadmissible as entry, rejection (a) stands).
ACCEPTED DESIGN ONLY: the operator-aware contract + pre-registration
(seventh amendment) and its remaining rows (i) the wiring, (iii) the
measurement rows, (iv) the narrower device-class key. UNMEASURED,
named: H1/H2 under admissible sessions (this route answers nothing
about them), every per-op verdict on non-xavier hardware, run 3+ /
cross-day replication, the `:sum` ordering at W = 64 on any device
under any admissible unit, the flip arm on real data (ZERO real
flips), every workgroup row (`:arm`/`:unknown` stay provisional
`:measured? false`), the name-fragment key's coarseness. Record:
`docs/evidence/gpu/cuda-op-census-route-20261025.txt`.

## Amendment (2026-10-25, ninth the same day: row (iii) first half --
fresh session A under the pre-registration LANDS)

**MEASURED (JUN-57, the first measurement row of the operator-aware
registration).** Fresh session A -- the first admissible
(hypothesis-testing) paired-timing session -- ran on xavier sm_72
(Jetson AGX Xavier, L4T R35.4.1, nvcc 11.4 V11.4.315) at
2026-10-25T08:53:58Z, the full pre-registered protocol at its letter
(the 108-block grid, one fresh process per block, PAIRS=20
interleaved, WARMUP=2 per arm, AB/BA alternating, LCG seed 20261023,
gpu_ns CUDA-event + host_ns CLOCK_MONOTONIC, untimed verified
read-back, correctness re-verified inside the measurement), the
instrument and the three arms' corpora byte-identical to the
committed ones (the log's received-file sha256 block: 55/55
matched). The run driver differed from the exploratory runs' driver
in its working directory ONLY. The log was analyzed ONLY by the
committed pre-registered routes (`--cuda-log`, `--cuda-cells`,
`--cuda-op-census`, all exit 0, stderr 0 bytes) -- row (ii) before
row (iii) at its letter.

**Reading-arm findings (session A ONLY -- nothing adjudicated,
nothing entered).** 108/108 cells ran, 0 failed; 218/218 verify
lines ok=1; 36 (op, W, shape) groups published, 36 folded to a
winner in every session-A reading, 0 refused; fold census
warp-shuffle 34 / subgroup 2 -- exactly the exploratory census's
split, the two subgroup folds being (op `:sum`, W = 64) at both
shapes (warp/subgroup 1.0700/1.0656/1.0905/1.0962 and
subgroup/baseline 0.8788/0.8912/0.8746/0.8858, gpu_ns then host_ns
per shape; unique winner `:subgroup-reduce` in every reading). At
(`:max`/`:min`, W = 64) every session-A reading folds
`:warp-shuffle-reduce` (the projected CONFIRM cells). Pooled cell
census: 48 regime-invariant faster / 3 slower / 21 regime-scoped of
72 cells. H1/H2 STATUS: NOT ADJUDICATED -- session A's readings
point the registered way (H1's contrast group folds
`:subgroup-reduce`; H2's 34 groups fold `:warp-shuffle-reduce`), but
the replication requirement is HALF MET: session A's UTC day is
2026-10-25, the earliest admissible session B is 2026-10-26 UTC or
later, and no verdict may be recorded before B exists and agrees in
every reading of both.

**Named, not hidden.** (a) session A shares its UTC day (2026-10-25)
with the two EXPLORATORY sessions; the replication rule at its
letter constrains the fresh PAIR's days (A and B on different UTC
days) and the exploratory sessions are excluded from every count
forever (rejection (a) stands); (b) the exploratory fold census
matching session A's (34/2, same two groups) is corroboration
CONTEXT ONLY -- the exploratory sessions generated the hypotheses
and enter nothing; (c) session A's readings enter NOTHING today:
entry is the wiring row's (row (i)) job and additionally requires
the completed cross-day pair.

**Consequence today: NOTHING MOVES** (rule 4): no record, no
`:measured?` flag, no selection answer, no `:shapes` value, no
workgroup row; the ladder
`:warp-shuffle-reduce -> :subgroup-reduce -> :baseline` stays
byte-for-byte and at (op `:sum`, W = 64) the design-ordered answer
stands UNCLAIMED.

**States.** MEASURED: session A (one fresh pre-registered session on
xavier sm_72, 2026-10-25 UTC, analyzed by the committed routes) --
the only measured thing this row. IMPLEMENTED: nothing new (evidence
+ this amendment only). DECIDED: nothing new. ACCEPTED DESIGN ONLY:
the operator-aware contract + pre-registration (seventh amendment),
the row (ii) route set, the entry contract + wiring, ADR-0358,
ADR-0373. UNMEASURED, named: session B (cross-day; earliest
2026-10-26 UTC) and therefore H1/H2 and every per-op
entry/flip/confirm verdict; the wiring (row (i)); every per-op
verdict on non-xavier hardware; run 3+; the `:sum` ordering at
W = 64 on any other device; the flip arm on real data (ZERO real
flips); every workgroup row (`:arm`/`:unknown` stay provisional
`:measured? false` -- no `:measured?` flag moves this row); the
name-fragment key's coarseness (row (iv)). Gates: scoped GPU gate
GREEN 107 tests / 11240 assertions / 0 failures / 0 errors
(docs-only diff, regression pin); `gpu_regime_classify.py
--self-test` 2572/0 (regression pin); FULL `run-tests.cljk` NOT RUN
this slice (no .cljk touched) -- documented red at base (`Could not
find namespace: kotoba.form`, ADR-0362) outside this diff, NO green
suite claimed; `find docs -name '*.sh'` -> 0 files. Record:
`docs/evidence/gpu/cuda-registered-sessionA-20261025/`.


## Amendment (2026-10-25, tenth the same day: row (i) LANDS -- the
per-op wiring)

**IMPLEMENTED (JUN-57, the operator-aware selection row's wiring).**
The entry mechanism of the seventh amendment lands in
`kotoba.compiler.accelerator-variants`, in four parts: (1)
`cuda-op-entries`, the PER-OPERATOR entry table -- entry group
(op, W), `:shapes` qualifying-only, single-op `:operators` in the
record (contract point 2) -- carrying the entry rule (contract point
3: unique-winner + both-clocks + cross-run invariance, fail closed),
the replication requirement (contract point 4: at least TWO fresh
sessions under the registration on at least TWO different UTC days
agreeing in every reading of both) and the materialization rule
(rejection (e): the per-op layer only ADDS where the pooled layer
refused or an admissible per-op winner differs -- the 15 (op, W)
groups whose winner equals the standing pooled answer materialize NO
per-op record, so a full reproduction of the exploratory census would
populate exactly three groups: (`:sum`, 64) FLIP and (`:max`/`:min`,
64) CONFIRM -- the projection, NOT a measurement); (2)
`cuda-op-flip-note`, the per-op flip note (naming THIS operator only
plus the standing DEVICE/CHANNEL scoping); (3) `cuda-entry-op`, the
per-op arm of the entry application -- the pooled arm's keys (tested
class both keys fail closed, `:cuda-v1` under either spelling, the
reduce op with an operator in `#{:sum :max :min}`, a design-ladder
rung-1 answer) plus the entry's OWN key `[op W]` -- answering
`:confirm` (winner equals the design answer: answer text frozen) or
`:flip` (a differing winner: the cell answers the winner with the
single-op record and the per-op flip note); (4) PRECEDENCE in
`select-variant` (contract point 1): `cuda-entry-op` is consulted
FIRST and its record answers its operator at its W OVER the pooled
record; `cuda-entry-cell` answers everywhere no per-op record applies.
The entry maps now carry their flip note (`:flip-note`) so one basis
path serves both layers. Pinned by the new deftest
`the-cuda-op-entry-wiring-answers-its-operator-at-its-width`: the
empty-by-rule table, the byte-identical no-entry surface (every
CUDA-route answer the pooled layer's alone, W = 64 keeping the honesty
lock), and the confirm arm, the flip arm, the precedence and every
fail-closed key exercised by SYNTHETIC entries (`with-redefs`) --
ZERO real per-op entries, so no production answer is confirmed or
flipped by this row.

**Named, not hidden.** (a) `cuda-op-entries` is EMPTY BY RULE, not by
oversight: the replication requirement is HALF MET -- fresh session A
ran under the registration on 2026-10-25 UTC and its readings enter
NOTHING (they await the pair), the earliest admissible session B is
2026-10-26 UTC or later -- so the per-op arm keys nothing today and
every CUDA-route answer is byte-identical to the pooled layer's
(pinned); (b) the arm and the precedence are exercised ONLY by
synthetic entries -- the mechanism is implemented, not exercised on
real data (a real entry additionally requires the completed cross-day
pair agreeing in every reading of both, contract point 4 at its
letter); (c) the first gate run was RED at ONE wrong test case -- the
rung-2 case merged the tested class's `:compute-capability 7.2` into
the no-capability descriptor, making it exactly the tested class (the
CODE was right to attach the record there; the TEST case was wrong) --
the case now names the no-capability descriptor like the pooled
wiring test's rung-2 case and the second run is GREEN; (d) the
`:measured?` movement the projection names at (`:max`/`:min`, 64) is
still PROJECTION, not measurement, and lands only with the entry.

**Consequence today: NOTHING MOVES** (rule 4): `cuda-op-entries` is
empty, no record exists beyond the pooled layer's, no `:measured?`
flag, no selection answer, no `:shapes` value and no workgroup row
moves; the ladder
`:warp-shuffle-reduce -> :subgroup-reduce -> :baseline` stays
byte-for-byte and at (op `:sum`, W = 64) the design-ordered answer
stands UNCLAIMED.

**States.** IMPLEMENTED (code + tests): the per-op wiring (row (i)) --
the table, the per-op arm (`cuda-entry-op`) with both outcomes, the
precedence in `select-variant`, the entry-carried flip notes. MEASURED:
nothing new (NO hardware ran this slice). DECIDED: nothing new.
ACCEPTED DESIGN ONLY: the operator-aware contract + pre-registration
(seventh amendment) and its remaining rows (iii) session B and the
entry it enables, (iv) the narrower device-class key; the entry
contract + pooled wiring (fifth/sixth amendments); ADR-0358,
ADR-0373. UNMEASURED, named: session B (cross-day; earliest
2026-10-26 UTC) and therefore H1/H2 and every per-op
entry/flip/confirm verdict (the wiring is not a measurement); every
per-op verdict on non-xavier hardware; run 3+; the `:sum` ordering at
W = 64 on any other device; the flip arm on real data (ZERO real
flips); every workgroup row (`:arm`/`:unknown` stay provisional
`:measured? false` -- no `:measured?` flag moves this row); the
name-fragment key's coarseness (row (iv)). Gates: scoped GPU gate
GREEN 108 tests / 11405 assertions / 0 failures / 0 errors (glslang
16.6.0 real-spawn; committed pin 107/11240, delta = this slice's
test); FULL `run-tests.cljk` RED at base -- `Could not find namespace:
kotoba.form` (ADR-0362) fails the run before any test executes,
OUTSIDE this diff (re-verified this tick since the diff touches .cljk
namespaces, exit 1) -- the touched namespaces' own tests are the
scoped gate above, NO green full suite claimed; `find docs -name
'*.sh'` -> 0 files. Record:
`docs/evidence/gpu/cuda-op-entry-wiring-20261025.txt`.

## Amendment (2026-10-25, eleventh the same day: row (iv) LANDS --
the narrower device-class key, naming BOTH entry layers' records)

IMPLEMENTED + DECIDED (JUN-57, the operator-aware row's created row
"(iv) the narrower device-class key"). NO hardware ran this tick and
nothing was re-measured.

**The key.** The tested device class is now keyed by BOTH name
fragments `"xavier"` and `"agx"` sitting in ONE name part
(case-insensitively, the uB5G per-name-part idiom) AND the reported
compute capability 7.2 exactly -- fail closed at every key --
replacing the single fragment `"xavier"`. The ground is the tested
device's own reported name, NVIDIA Jetson AGX Xavier (sm_72), the
one device where the CUDA route's measurements ran. The hole this
closes: under the single fragment a Jetson Xavier NX descriptor
(also sm_72) read as the tested class and would have received every
entry-contract record -- pooled AND per-op -- with no measurement
behind it. One shared predicate (`cuda-tested-class?`) keys BOTH
`cuda-entry-cell` and `cuda-entry-op` -- row (iv) names the per-op
records too. The fragments must sit in ONE name part (the three
name keys are alternate spellings of the device's name, not a
fragment kit). Record shape (3) is UNCHANGED: the record's `:device`
label stays `"xavier sm_72"`; what narrowed is the KEY deciding
which descriptors are the class.

**Rejected, named.** (a) a negative key ("xavier" and NOT "nx") --
a substring blacklist naming only today's known wrong answer; (b)
exact-name equality -- brittle across producers' spellings and
against the uB5G idiom's tolerance; (c) a device-id/UUID/PCI-id key
-- the descriptor surface carries `:device`/`:name`/`:vendor`
strings and `:compute-capability`, no device-id axis exists and none
is invented here (PROPOSED, its own row if a producer ever supplies
one); (d) narrowing `kotoba.compiler.accelerator-targets`'
workgroup rows' `:measured-device "xavier"` in the same slice --
that table's scoping is its own decision (ADR-0355/0358) and stays
coarse, named.

**Named residual, not hidden.** The key is still name-based: any
name part carrying both fragments with a reported 7.2 still reads as
the class -- `"Jetson AGX Xavier Industrial"` (also sm_72) is the
concrete residual, PINNED AS BEHAVIOR by the new test (it attaches
today; pinned so the coarseness is named behavior, not an accident,
and not a claim anything was measured on it).

**Consequence today: NOTHING MOVES for any measured device.** The
narrowed key only removes descriptor classes that were never
measured: the tested class matches exactly as before, no record, no
`:measured?` flag, no selection answer, no `:shapes` value and no
workgroup row moves. The one behavioral delta is fail-closed (Xavier
NX and across-parts-split descriptors now attach nothing).

**States.** DECIDED: this row (the key + its rejections).
IMPLEMENTED (code + tests): the narrowed key (`cuda-tested-class-
fragments` + `cuda-tested-class?`) over both entry arms, pinned by
`the-tested-class-key-is-the-agx-xavier-name-and-72` and the
extended fail-closed case lists. MEASURED: nothing new (NO hardware
ran). ACCEPTED DESIGN ONLY: the operator-aware contract +
pre-registration (seventh amendment) and its remaining row (iii)
second half (session B and the per-op entry it enables); the entry
contract + pooled wiring (fifth/sixth amendments); ADR-0358,
ADR-0373. UNMEASURED, named: session B (cross-day; earliest
2026-10-26 UTC) and therefore H1/H2 and every per-op
entry/flip/confirm verdict; every per-op verdict on non-xavier
hardware; run 3+; the `:sum` ordering at W = 64 on any device; the
flip arm on real data (ZERO real flips); the named residual on real
hardware; every workgroup row (`:arm`/`:unknown` stay provisional
`:measured? false` -- no `:measured?` flag moves this row). Gates:
scoped GPU gate GREEN 109 tests / 11434 assertions / 0 failures / 0
errors (glslang 16.6.0 real-spawn; committed pin 108/11405, delta =
this slice's new deftest + extended case lists); FULL
`run-tests.cljk` RED at base -- `Could not find namespace:
kotoba.form` (ADR-0362) fails the run before any test executes,
OUTSIDE this diff (re-verified this tick since the diff touches
.cljk namespaces, exit 1) -- NO green full suite claimed;
`gpu_regime_classify.py --self-test` 2572/0 (regression pin); `find
docs -name '*.sh'` -> 0 files. Record:
`docs/evidence/gpu/cuda-device-class-key-20261025.txt`.

## Amendment (2026-10-26: row (iii) second half LANDS -- FRESH
SESSION B, the cross-day replication pair's second session)

MEASURED (JUN-57, the second half of the seventh amendment's row
"(iii) the measurement rows"). HARDWARE RAN: one fresh paired-timing
session on xavier sm_72 at 2026-10-26T05:09:51Z (UTC day 2026-10-26,
a DIFFERENT UTC day from session A's 2026-10-25 -- the registration's
cross-day constraint at its letter), analyzed ONLY by the committed
pre-registered routes (row (ii) before row (iii), at its letter).

**What ran.** The registered protocol verbatim: the ADR-0358
instrument class, the full 108-block grid (2 shapes x 6 widths x 3
operators x 3 pair types), one fresh process per block, PAIRS=20
interleaved, WARMUP=2 per arm, AB/BA alternating, LCG seed 20261023
reset per process, gpu_ns CUDA-event + host_ns CLOCK_MONOTONIC,
untimed verified read-back, correctness re-verified inside the
measurement. The run driver (Hermes scratch only, never staged) is
byte-identical to session A's driver except the comment's session
letter and the working directory; the fresh remote tree carried 55
files (54 committed emitted corpora + the committed instrument), 0
sidecars, and the log's received-file sha256 block re-derives 55/55
against the committed corpora + instrument. Verified: 108/108 cells
run, 0 failed (driver exit 0), 218/218 verify lines ok=1, 4360
sample lines (4320 grid + 40 named smoke orphans), all three
committed routes exit 0 with 0-byte stderr.

**Session B's reading-arm verdicts (the record; nothing entered).**
Per-op census: 36 (op, W, shape) groups, 36 folded / 0 refused,
fold census warp-shuffle 34 / subgroup 2 -- exactly session A's
split, the two subgroup folds being (op :sum, W = 64) at both
shapes. The contrast group's session-B readings: subgroup unique
winner in both clocks of both shapes (n=1000003: warp/subgroup
1.0705/1.0727, subgroup/baseline 0.8937/0.8962; n=1048576:
1.0612/1.0586 and 0.8993/0.8865 -- gpu_ns/host_ns, each reading's
one-sided count 13..19 of 20). H2's confirm cells (:max/:min,
W = 64) fold warp-shuffle in every session-B reading. Pooled cell
census: 72/72 verdicts -- session B 48 faster / 1 slower / 23
regime-scoped vs session A's 48/3/21 (NAMED: the pooled split is
not identical across the pair; the registered criterion reads the
(op, W) reading unit and never the pooled split).

**Status and consequence: NOTHING MOVES (rule 4).** H1/H2 stay
NOT ADJUDICATED by this record: the pair now exists but the entry
criterion ("agreeing in every reading of both") is decided in the
evaluation row -- this amendment records the measurement only. No
record, no `:measured?` flag, no selection answer, no `:shapes`
value and no workgroup row moves; at (op `:sum`, W = 64) the
design-ordered answer stands UNCLAIMED. Row (iii) is complete at
the measurement letter; its EVALUATION is the named next row.

**States.** MEASURED: session B (the only measured thing this
row). IMPLEMENTED: nothing (evidence + this amendment only).
DECIDED: nothing new. ACCEPTED DESIGN ONLY (unchanged): the
operator-aware contract + pre-registration (seventh amendment) and
its remaining evaluation row, the row (ii) route set, the entry
contract + wiring, ADR-0358, ADR-0373. UNMEASURED, named: the
cross-day agreement adjudication and therefore H1/H2 and every
per-op entry/flip/confirm verdict; run 3+; every per-op verdict on
non-xavier hardware; the `:sum` ordering at W = 64 on any other
device; the flip arm on real data (ZERO real flips); the pooled
cell-split difference's cause; every workgroup row (`:arm`/
`:unknown` stay provisional `:measured? false`). Gates: scoped GPU
gate GREEN (docs-only diff -- regression pin at the committed
count, the run's numbers in the commit message); FULL
`run-tests.cljk` NOT RUN this slice (no .cljk touched) --
documented red at base `Could not find namespace: kotoba.form`
(ADR-0362), outside this diff, NO green suite claimed;
`gpu_regime_classify.py --self-test` 2649/0 (regression pin); `find
docs -name '*.sh'` -> 0 files. Record:
`docs/evidence/gpu/cuda-registered-sessionB-20261026/`.

## Amendment (2026-10-26, the evaluation row: the cross-day agreement
adjudication LANDS -- H1 and H2 are CONFIRMED and every per-op
entry/flip/confirm verdict is DECIDED)

DECIDED (JUN-57, the twelfth amendment's named next row -- "its
EVALUATION is the named next row"). NO hardware ran this tick and
nothing is re-measured: the ground is the two committed admissible
measure-logs (sessions A + B) consumed as derivation through the
committed pre-registered route -- `--cuda-op-census` over BOTH logs in
one invocation (exit 0, stderr 0 bytes, 448 lines, published verbatim
as `op-census-joint.txt` in the record directory), whose reading unit
is exactly the entry criterion's "agreeing in every reading of both"
at its letter (one reading per (session, metric); the group's fold =
the same unique winner in EVERY reading).

**Admissibility (fail-closed reading (4) at its letter -- decided
here, not by the census).** Both sessions are fresh sessions run under
the seventh amendment's registration (their own records) and they sit
on TWO DIFFERENT UTC days -- the logs' own `DATE-UTC` lines, re-read
this tick: session A `2026-10-25T08:53:58Z`, session B
`2026-10-26T05:09:51Z`. Replication requirement (contract point 4):
MET. The two same-day exploratory sessions stay inadmissible forever
(rejection (a)) and enter no count.

**The adjudication (verified tool output).** 36 (op, W, shape) groups
published over 144 readings (both sessions x both clocks), 36 folded,
0 refused -- every reading of both sessions agrees one-sided on one
unique winner at every group. Fold census warp-shuffle 34 / subgroup
2, the two subgroup folds being (op `:sum`, W = 64) at both shapes.
Entry groups (op, W): 18/18 enter at the reading arm, 0 refuse;
`1000003, 1048576` qualify at ALL 18 groups and no group's two shapes
disagree (fail-closed readings (1)-(3) never fire; no missing pair
block). Cross-check (scratch, never staged): the joint folds equal
session A's own published folds at 36/36 groups and session B's at
36/36 -- the agreement is group-by-group, not just aggregate.

**H1/H2.** H1 (at (op `:sum`, W = 64) on xavier sm_72 on the CUDA
route `:subgroup-reduce` is the unique winner in every qualifying
reading): **CONFIRMED** -- 8/8 readings name it (the contrast group's
joint table: warp/subgroup 1.0700/1.0656 (A) and 1.0705/1.0727 (B) at
n = 1000003, 1.0905/1.0962 (A) and 1.0612/1.0586 (B) at n = 1048576;
subgroup/baseline 0.8788/0.8912 (A), 0.8937/0.8962 (B), 0.8746/0.8858
(A), 0.8993/0.8865 (B)). H2 (every other (op, W) group's unique
winner is `:warp-shuffle-reduce`): **CONFIRMED** -- the other 17
groups fold it in every reading of both.

**Per-op entry/flip/confirm verdicts (DECIDED; the materialization
rule, rejection (e), at its letter).** Exactly three groups
materialize a per-op record: (`:sum`, 64) **FLIP** (winner
`:subgroup-reduce` differs from the design rung-1 answer), (`:max`,
64) and (`:min`, 64) **CONFIRM** (winner equals the design answer --
answer text frozen -- and the pooled layer refused at W = 64, so the
per-op layer adds); the 15 (op, W) groups at W =
32/128/256/512/1024 x {sum, max, min} materialize NO record (winner =
standing pooled answer). The seventh/tenth amendments' projection
(three groups, exactly these) is now a measurement-backed verdict
under the registration, no longer a projection.

**Consequence today: NOTHING MOVES** (rule 4). `cuda-op-entries` stays
`{}` this tick: this row DECIDES the verdicts; the surface movement
(the table population, the real FLIP at (`:sum`, 64), the CONFIRM
records, the `:measured?` movement the projection names at the
(`:max`/`:min`, 64) cells, the flip note on `:sum` at W = 64) is "the
entry it enables" -- the named NEXT row, an implementation slice with
its own tests. No record, no `:measured?` flag, no selection answer,
no `:shapes` value and no workgroup row moves; at (op `:sum`, W = 64)
the design-ordered answer stands UNCLAIMED until the entry lands.

**States.** DECIDED: this row (admissibility, agreement, H1/H2
CONFIRMED, the three verdicts, the 15 non-materializations).
MEASURED: nothing new (NO hardware ran; the two committed sessions
consumed as derivation). IMPLEMENTED: nothing (docs + evidence only).
ACCEPTED DESIGN ONLY (unchanged): the operator-aware contract +
pre-registration, the row (ii) route set, the entry contract + wiring,
ADR-0358, ADR-0373. UNMEASURED, named: the entry landing (its own
next row -- no production answer is confirmed or flipped until it
lands); run 3+; every per-op verdict on non-xavier hardware; the `:sum`
ordering at W = 64 on any other device or channel; the flip arm on
real selection data (ZERO real flips landed); the pooled cell-split
difference (session A 48/3/21 vs session B 48/1/23 of 72 cells --
named, outside the registered criterion, cause UNMEASURED); every
workgroup row (`:arm`/`:unknown` stay provisional `:measured? false`).
Gates: scoped GPU gate GREEN (docs-only diff -- regression pin at the
committed count, the run's numbers in the commit message);
`gpu_regime_classify.py --self-test` 2649/0 (regression pin); FULL
`run-tests.cljk` re-verified red at base `Could not find namespace:
kotoba.form` (ADR-0362), outside this diff, NO green suite claimed;
`find docs -name '*.sh'` -> 0 files. Record:
`docs/evidence/gpu/cuda-crossday-adjudication-20261026/`.

## Amendment (2026-10-26, the entry landing: `cuda-op-entries` ENTERS
-- the (:sum, 64) FLIP and the (:max/:min, 64) CONFIRM records reach
the selection surface)

IMPLEMENTED (JUN-57, the thirteenth amendment's named next row -- "the
entry it enables", its own implementation slice). NO hardware ran and
nothing is re-measured: the landed entries consume the two committed
admissible measure-logs (sessions A + B) whose cross-day agreement the
previous row adjudicated. `cuda-op-entries` is POPULATED with exactly
the three materialized groups at the adjudication's verdicts --
(`:sum`, 64) `:winner :subgroup-reduce` (FLIP), (`:max`, 64) and
(`:min`, 64) `:winner :warp-shuffle-reduce` (CONFIRM) -- each with
`:shapes [1000003 1048576]` (qualifying-only) and `:evidence` the two
qualifying sessions' runs (`cuda-registered-sessionA-20261025`,
`cuda-registered-sessionB-20261026`). The 15 (op, W) groups whose
winner equals the standing pooled answer materialize NO record
(rejection (e)) and are absent from the table.

**The surface movement (verified tool output).** On the tested class
(`xavier sm_72`, CUDA route, reduce shape), (`:sum`, 64) now answers
`:subgroup-reduce` -- the FIRST REAL FLIP on the CUDA route -- with
the single-op record and `cuda-op-flip-note` in `:basis`;
(`:max`, 64) and (`:min`, 64) answer `:warp-shuffle-reduce` with the
single-op record, answer text FROZEN, and `:measured?` MOVES TRUE (the
projection's named `:measured?` movement -- the pooled straddle's
W = 64 refusal left those cells unclaimed until now). The 15
non-materialized groups are byte-identical to the pre-entry surface
(pooled whole record at W = 32/128/256/512/1024). The pooled W = 64
refusal stands (`cuda-cell-entries` keeps no 64 key); a cell where no
layer keys keeps the design answer, `:measured? false`, no record.

**Tests.** The empty-table pin is replaced by the real-table pin
(exactly the three groups at value) plus real-surface pins for the
flip, the two confirms and the 15 non-materialized groups; the
synthetic (with-redefs) contract blocks remain and their prose is
re-scoped; the pooled wiring test's refusal pin moved off the tested
class at W = 64 (the landed entries fill that cell). Gate: scoped GPU
gate GREEN 123 tests / 12162 assertions / 0 failures / 0 errors twice
(previous 123/12154; delta +0 tests / +8 assertions).

**States.** IMPLEMENTED: this row (the table, the surface, the
tests). MEASURED: nothing new (NO hardware; the entry's numbers are
the two committed sessions', consumed as the entry's basis). DECIDED:
nothing new (the verdicts were the previous row's). ACCEPTED DESIGN
ONLY (unchanged): the operator-aware contract + pre-registration, the
row (ii) routes, ADR-0358, ADR-0373. UNMEASURED, named: run 3+; every
per-op verdict on non-xavier hardware; the `:sum` ordering at W = 64
on any other device or channel; the pooled cell-split difference's
cause; every workgroup row (`:arm`/`:unknown` stay provisional
`:measured? false` -- no workgroup row moves); the landed rows on a
live CUDA selection path (only xavier hardware can run it). Gates:
scoped GPU gate GREEN twice (numbers above); FULL `run-tests.cljk`
re-verify documented red at base `Could not find namespace:
kotoba.form` (ADR-0362), outside this diff, NO green suite claimed;
`gpu_regime_classify.py --self-test` 2649/0 (regression pin, not
re-run); `find docs -name '*.sh'` -> 0 files. Record:
`docs/evidence/gpu/cuda-op-entry-landing-20261026.txt`.

## Amendment (2026-10-26, run 3+: fresh session C reproduces the
fold census exactly, and the pooled cell-split difference's locus
is a named quartet that moves no entry outcome)

MEASURED (JUN-57 -- "run 3+", the entry-landing row's named first
unmeasured item; ONE measurement slice). HARDWARE RAN: one fresh
paired-timing session on xavier sm_72 at 2026-10-26T06:39:05Z under
the seventh amendment's PROTOCOL at its letter (the run driver is
byte-identical to session B's except the comment's session letter
and the working directory -- diff run this tick: exactly those two
lines). NAMED, NOT HIDDEN: session C shares session B's UTC day
(2026-10-26) -- under contract point 4 it is NOT a cross-day
replication, extends no record's `:evidence` and licenses nothing a
same-day session may not (ADR-0373's same-day rule by citation).
Its role is RUN-3 ROBUSTNESS: a third independent sample of the
session-to-session variance the entry pair could not see.

**Verified (real runs).** 108 cells run / 0 failed (driver exit 0,
stderr 0 bytes), 218/218 verify lines ok=1, 4360 sample lines
(4320 grid + 40 smoke orphans named and excluded), 54/54 OK-cubin,
55 nvcc diagnostics 0 bytes, instrument OK; corpus integrity 55/55
sha256 against the committed corpora + committed instrument by
basename at BOTH ends (the local stage before transfer, the log's
received-file block after), the received block byte-identical to
session B's; the log analyzed ONLY by the committed routes, all
exit 0, stderr 0 bytes (910 / 2069 / 367 lines).

**Finding (1): run 3 reproduces the fold census exactly.** 36
(op, W, shape) groups, 36 folded, 0 refused, fold census
warp-shuffle 34 / subgroup 2 (the two = (`:sum`, 64) at both
shapes). Cross-session comparison over the three committed op
censuses (scratch, never staged): 36/36 group folds IDENTICAL in
sessions A, B and C -- ZERO groups disagree in any session. At the
landed FLIP's cell run 3 again folds `:subgroup-reduce` in every
reading (n=1000003: warp/subgroup 1.0843/1.0786, subgroup/baseline
0.8729/0.8874; n=1048576: 1.0870/1.0913, 0.8674/0.8870 --
gpu_ns/host_ns, one-sided 14..18 of 20); at (`:max`/`:min`, 64) all
four groups fold `:warp-shuffle-reduce` again.

**Finding (2): the pooled cell-split difference's locus is a named
quartet.** Pooled splits A 48/3/21, B 48/1/23, C 48/1/23 of 72 --
session C equals session B. The ONLY cells whose rule-2 class
differs in any session are exactly four: the (pair
subgroup/baseline, W = 256) quartet, both metrics x both shapes
(gpu_ns/1000003: A slower, B scoped, C scoped; gpu_ns/1048576: A
slower, B scoped, C slower; host_ns/1000003: A slower, B scoped, C
scoped; host_ns/1048576: A scoped, B slower, C scoped). The 48
regime-invariant faster cells are identical in all three sessions
and the other 68 cells never change class. The instability is NOT
diffuse session noise: it is this quartet straddling the
slower/scoped boundary. The PHYSICAL CAUSE remains UNMEASURED (more
sessions or wider pair counts; run 3 is same-UTC-day with B).

**Finding (3): the quartet moves no entry outcome.** A scratch
unique-winner derivation over the pooled cells per session (the
entry contract's rule at (W, shape) groups, both clocks) gives the
IDENTICAL map in A, B and C -- `:warp-shuffle-reduce` at W =
32/128/256/512/1024 both shapes, no winner at W = 64 both shapes --
exactly the landed `cuda-cell-entries` table; and zero (op, W)
group folds differ. The landed table (pooled and per-op) is
corroborated by run 3 and contradicted nowhere.

**Consequence today: NOTHING MOVES** (rule 4). No record, no
`:measured?` flag, no selection answer, no `:shapes` value and no
workgroup row; the landed entries stand byte-for-byte. Run 3
reproducing every fold does NOT re-adjudicate anything: the entries
rest on the A+B pair at the criterion's letter, this amendment
records the robustness measurement and the quartet's locus.

**States.** MEASURED: session C (the only measured thing this
row). DERIVED: the cross-session comparisons (scratch over the
three committed censuses). IMPLEMENTED: nothing (evidence + this
amendment only). DECIDED: nothing new. ACCEPTED DESIGN ONLY
(unchanged): the operator-aware contract + pre-registration, the
row (ii) routes, the entry contract + wiring, ADR-0358, ADR-0373.
UNMEASURED, named: the quartet's physical cause; a cross-day run
3+ (a session on a later UTC day would be a sanctioned cross-day
replication and could extend the landed entries' `:evidence`, its
own row); every per-op verdict on non-xavier hardware; the `:sum`
ordering at W = 64 on any other device or channel; the landed rows
on a live CUDA selection path (only xavier hardware runs it);
every workgroup row (`:arm`/`:unknown` stay provisional
`:measured? false`). Gates: scoped GPU gate GREEN twice (numbers
above -- regression pin, no .cljk touched);
`gpu_regime_classify.py --self-test` 2649/0 (regression pin,
re-run live); FULL `run-tests.cljk` NOT RUN this slice (no .cljk
touched) -- documented red at base `Could not find namespace:
kotoba.form` (ADR-0362), outside this diff, NO green suite
claimed; `find docs -name '*.sh'` -> 0 files. Record:
`docs/evidence/gpu/cuda-registered-sessionC-20261026/`.
