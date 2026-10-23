# ADR-0360 -- The Apple row: the subgroup-size-parametric reduce on the Vulkan route

- Status: accepted as design. The selection row is implemented 2026-10-23
  (code + tests in `kotoba.compiler.accelerator-variants`); the row is
  UNMEASURED. The 2026-10-23 amendment at the end of this ADR extends the
  row from the Vulkan route to the MSL route as well (implemented same
  date).
- Date: 2026-10-23
- Tracking: JUN-58 (Apple). Parent JUN-55. This is one vendor per decision,
  the rule ADR-0356 set and ADR-0357 (ARM) followed.

## Decision

The Apple row of the per-vendor kernel variant table is the SAME
`:subgroup-reduce` variant ADR-0356 designed for Intel and ADR-0357 bound
for ARM: a subgroup-size-parametric intra-subgroup fold, one write barrier,
a cross-subgroup tree over the `W/S` partials. The selection predicate is
vendor `:apple` (as ADR-0355 classifies it: PCI 4203, or an `apple` /
`m1`/`m2`/`m3`/`m4` device-name fragment), op `:reduce`, operator in
`{:sum :max :min}`, `W >= 32`, on the Vulkan route (`:vulkan` or
`:glsl-v1`), under ADR-0356 rule 6's capability gate: the device
descriptor must report the fold's subgroup operations (`:subgroup-ops`
containing `:basic` and `:shuffle-relative`) and a subgroup size
(`:subgroup-size`) that divides `W`. Every other answer -- the MSL route, a
device that confirms no capability, another shape -- is `:baseline`. The
rules of ADR-0356 bind this row unchanged, and ADR-0357's P1 (the `:sum`
association scope) and P2 (subgroup IDs, not `lid` arithmetic) bind the
emission byte-for-byte: this row reuses the existing emission, it emits
nothing new.

## Why the Vulkan route, and not MSL

ADR-0355's api-less Apple default target is `:msl-v1`, but there is no
Metal execution path in this repository: the runtime `:gpu/compute`
(wire 42) route is Vulkan at every layer that ever had one (the removed
loader brokers, and ADR 0371's provider plan), and JUN-58's measurement
path is MoltenVK. The MSL emitter admits `:baseline` only (ADR-0002), so
ADR-0356 rule 3 keeps the MSL route at `:baseline`; a Metal simdgroup row
on the MSL route is NOT designed here and nothing in this ADR should be
read as designing it. (SUPERSEDED 2026-10-23 as to the CAUSE, not the
conclusion: the MSL arm of the shared emission landed and the MSL emitter
now admits `:subgroup-reduce` (ADR-0356's MSL-arm amendment); the MSL
route still answers `:baseline` because this ADR scopes the row to the
Vulkan route, and a Metal simdgroup row is still not designed here.
SUPERSEDED AGAIN later the same day as to the conclusion too: the
amendment at the end of this ADR extends the row to the MSL route; a
Metal simdgroup row -- a different, Metal-native variant -- is still not
designed here.) The
measurement this row waits on runs GLSL ->
SPIR-V through glslang (ADR-0359 decision 2's sealed build step) on
MoltenVK.

## Design facts (vendor documentation, not measurements)

Metal's SIMD-group width is 32 (Apple documentation), and MoltenVK's
subgroup surface follows it: the MoltenVK runtime guide lists
`VK_EXT_shader_subgroup_ballot`, `VK_EXT_shader_subgroup_vote`,
`VK_KHR_shader_subgroup_extended_types` and `VK_EXT_subgroup_size_control`
(requiring Metal 2.1 on Mac), and the MoltenVK 1.4.2 notes describe the
macOS subgroup size as 32-wide SIMD groups. Nothing here has PROBED this
host's MoltenVK for a subgroup size (the probe that could is removed with
the loader); these are documentation facts, and the rule-6 gate consumes
the descriptor's REPORTED facts, not the vendor name -- so the row is
admitted only for a device that says so. The emission queries the width at
runtime (`gl_SubgroupSize`) and bakes nothing, so the same bytes are
correct for any width a device reports. The stage arithmetic of ADR-0356
(W = 128, S = 32: 2 stages against the baseline's 7) applies unchanged and
is stage counting, not a speed claim. The design assumption -- UNMEASURED
-- is the same one the Intel and ARM rows carry: removing most of the
barrier cascade wins. No Apple hardware has run this variant here, and no
report may cite this row as optimization evidence.

## Open contract gap (named, not hidden)

Rule 6 consumes descriptor facts (`:subgroup-size`, `:subgroup-ops`) whose
producer does not exist. The wire-42 answers of the ADR-0371 provider plan
carry no such facts: `INFO` is the four fields `<device>|<api>|<maxWgX>|<unified>`
and `DEVCLASS` is one class word. So this row is selected today only for a
descriptor that a future probe or provider supplies with subgroup facts; a
descriptor that reports none fails closed to `:baseline` (rule 1: the
portable variant runs). Producing the facts -- an extended probe answer or
a provider request -- is a separate design decision, made in ADR-0362
(one additive wire-42 request, `SUBGROUP`): design only, the producer does
not exist yet, and this row keeps failing closed without the facts.

## Measurement contract (JUN-58)

The row flips `:measured?` only on an interleaved baseline-vs-variant
reduce comparison with verified read-back (the protocol the workgroup
sweeps established: fresh-process runs, interleaved samples, verified
read-back words), on a NAMED Apple device, recorded under
`docs/evidence/`. The measurement is keyed to the tested device (name and
its reported subgroup size), not to the vendor row: one Apple generation
measured does not flip `:measured?` for any other (ADR-0356 rule 4's lock
is per sufficient descriptor dimension). It also cannot be taken until a
wire-42 route exists again (ADR-0371 provider; ADR-0355's honest state),
so today the row stays `:measured? false` in every answer, and the
provisional workgroup rows of ADR-0355 are untouched by this ADR.

## Amendment (2026-10-23, later the same day): the row rides the MSL route too

This DECIDES the open question the 2026-10-23 MSL-arm amendment of
ADR-0356 named -- "Extending Apple's row to the MSL route (and whether the
rule-6 facts there come from the same wire-42 SUBGROUP request ADR-0362
designed, given a Metal-native descriptor would report SIMD-group facts
directly) is a SEPARATE per-vendor design decision (JUN-58's own),
proposed here and decided nowhere" -- in two parts.

**Part 1: the selection row extends to the MSL route.** `select-variant`
answers `:subgroup-reduce` for `:apple` on the MSL route -- one route under
two names, `:metal` (the api name `target-for` maps) and `:msl-v1` (the
emitter target name `lower` admits), the ADR-0359 decision-3 idiom -- under
the SAME rules 3 + 6 gate the Vulkan route uses, fail closed included.
Rule 3 is satisfied exactly as the WGSL-route rows satisfied it (ADR-0363
rationale 1): the MSL arm landed 2026-10-23 and `lower` admits the
(:msl-v1, :subgroup-reduce) pair in both readings. The NVIDIA CUDA-route
question (whether that row should ever answer `:subgroup-reduce`) stays
UNDECIDED -- one vendor per decision, the rule ADR-0356 set.

**Part 2: the rule-6 facts on the MSL route are the same descriptor keys,
whatever fills them.** `:subgroup-size` and `:subgroup-ops` are this
table's capability contract, not a Vulkan binding: `:basic` and
`:shuffle-relative` name the two ops the fold needs (the vocabulary of
`accelerator-variants`' gate, whose GLSL spelling is the two
GL_KHR_shader_subgroup_* extensions), and a Metal-native descriptor would
answer them from the device's SIMD-group facts directly -- `simd_shuffle_down`
present is the `:shuffle-relative` evidence, and Apple's SIMD-group width
reports as `:subgroup-size`. ADR-0362's wire-42 `SUBGROUP` request stays
the VULKAN route's producer; this amendment invents no key, no request and
no producer. The fact gap is unchanged and still named: nothing produces
the keys today on ANY route, and every row still fails closed to
`:baseline` without a filled descriptor.

Rationale is ADR-0363's, transposed: (1) rule 3 is the ordering rule and
it is satisfied; (2) the emission is the shared fold's own MSL arm -- this
row reuses it and emits nothing new (this ADR's original decision
unchanged) -- and that arm is COMPILED (all eighteen sources to AIR under
Apple metal 32023.883; a toolchain fact of what compiles, not a
measurement); (3) `:msl-v1` is `target-for`'s answer for an api-less Apple
device (`vendor-default-target`): without this extension the row could
never select on its own vendor's default path.

Non-claims, restated so no prose upgrades them: UNMEASURED -- the MSL
route has no execution path in this repository (the brokers died with the
C loader; ADR 0371's provider is the replacement track), nothing has
executed this arm on any hardware, every answer keeps `:measured? false`,
and no workgroup row of ADR-0355/0358 is touched (a different axis).
"A Metal simdgroup row" -- a Metal-native variant built on
simd_sum/simd_max/simd_min -- remains NOT designed: this amendment routes
the EXISTING shared fold's selection, it designs no new emission and no
new spelling. The measurement contract above stands unchanged, keyed to
the tested device class; a native-Metal measurement needs an execution
path that does not exist, and the MoltenVK measurement channel measures
the Vulkan route, not this one.

Implemented the same date (code + tests in
`kotoba.compiler.accelerator-variants`, evidence in
`docs/evidence/gpu-apple-msl-route-20261023/`).

## Amendment (2026-10-23, the MSL arm's first hardware run -- measurement
recorded, every lock unchanged)

PRIOR ART (corrected same tick): the first hardware comparison of the two
reduce arms is NOT this one -- PR #1347/#1348 (ba1fcced, 677fa1cf, merged
2026-10-19, wire-42/MoltenVK, GLSL arm) measured the variant slower than
baseline at W = 256 (~20-27% more time) and never faster over W = 32..256
with the penalty growing with W; PR #1343 (eef57e63) measured S = 32
through the Vulkan side the same day. What is NEW here is the MSL arm's
first hardware EXECUTION (it was COMPILED-only) and its CROSS-ROUTE
REPLICATION of that finding on the native Metal route.

One MEASUREMENT landed with this tick (evidence
`docs/evidence/gpu-subgroup-reduce-m1max-20261023/`): the emitted
`:baseline` and `:subgroup-reduce` MSL arms for :sum/:max/:min at W = 256
(this ADR's measured workgroup row, ADR-0358) ran interleaved on the named
device **Apple M1 Max** -- 6 fresh-process runs, 20 paired samples per
operator per run with alternating AB/BA order, warmup submits discarded
(the ADR-0358 sweep protocol), verified read-back every run. The harness
(`scripts/gpu-subgroup-reduce-metal-measure.{m,py,cljk}`) dispatches the
emitters' own bytes through the Metal API directly.

Result: the variant is **~22% SLOWER** than baseline in every fresh process
and every operator (paired median ratio 1.216-1.223; median GPU time
~103 us baseline vs ~126 us variant per dispatch at n = 1,000,003;
absolute medians shift with the GPU clock regime across processes, the
paired ratio does not). Read-back: :max/:min partials bit-identical between
the arms and against the double CPU reference -- rule 2's ordinary-value-
domain claim is now OBSERVED on hardware for these inputs -- and :sum
differs by at most 3.05e-5 across partials (the low-bit movement rule 2
permits). The device's reported subgroup size (the runtime
`[[threads_per_simdgroup]]` binding) is MEASURED **32**: the Metal-native
channel's reading, confirming eef57e63's Vulkan-side S = 32 -- not a first
(a same-tick correction; the commit message of 009c86ef said "first" and
is superseded). It says nothing about MoltenVK's
`VkPhysicalDeviceSubgroupProperties` -- ADR-0362's unverified clause stands
for the Vulkan route.

Locks unchanged: NO `:measured?` flag moves and no workgroup row is
touched. This run is NOT the contract's measurement: the contract requires
the wire-42 route, which does not exist since the C loader removal
(ADR 0371), and this harness has its own Metal dispatch path. The flip
stays blocked on (a) the route clause above and (b) the per-tested-device
scoping the flip would need (ADR-0358's `:measured-device` machinery
exists for the workgroup rows only).

TWO design questions are PROPOSED here and decided nowhere: (1) whether a
native Metal harness that runs the emitters' own bytes under the sweep
protocol satisfies this ADR's measurement contract, and if so how the flip
records the tested device class; (2) what the Apple row should select given
the measured cell -- the rationale the row inherited ("removing most of the
barrier cascade wins", ADR-0356's Intel design assumption) is contradicted
at W = 256 on M1 Max, where the variant is slower. Options include keeping
the row as designed (one W, one device and one operator family is not the
row), narrowing it, or a Metal-native `simd_sum`/`simd_max`/`simd_min`
simdgroup row (still NOT designed). Nothing here is optimality evidence for
any other W, n, device or operator.

## Amendment (2026-10-23, the second decision: the row is NARROWED to the
measured device)

This DECIDES question (2) above -- what the Apple row should select given
the measured cell -- as **narrowing**, superseding that question's
"PROPOSED, decided nowhere" clause as to (2) only. Question (1) -- whether
a native Metal harness satisfies this ADR's measurement contract, and how
the flip records the tested device class -- REMAINS PROPOSED and undecided.

Decision: the row is narrowed by the uB5G scoping idiom
`kotoba.compiler.accelerator-targets` already uses for workgroup-row
provenance. A device descriptor whose name parts (:device, :name, or the
:name key `:vendor` that `device-from-info` fills with deviceName) carry
the measured-device fragment `m1 max` (case-insensitively) answers
`:baseline` for the reduce shape on BOTH Apple routes (Vulkan/glsl-v1 and
MSL/msl-v1), at every workgroup size; every other Apple device -- including
an unnamed `{:vendor-id 4203}` descriptor -- keeps the designed
`:subgroup-reduce` row (UNMEASURED), and non-Apple vendors are untouched.

Why narrow, and not keep: the row's inherited rationale ("removing most of
the barrier cascade wins") is MEASURED-CONTRADICTED on the named device,
twice, on both routes, across the tested band (GLSL arm never faster over
W = 32..256, penalty growing with W; MSL arm ~22% slower at W = 256 across
:sum/:max/:min). Selecting a variant on the device that measured it slower
would be selecting against one's own evidence. Why narrow, and not delete:
the evidence is ONE device and narrow shape coverage -- it speaks for M1
Max, not for the vendor class (the uB5G rule: evidence about a named
device acts on that device's name and never past it). The options the
question listed that this decision does NOT take stay open on purpose: a
Metal-native `simd_sum`/`simd_max`/`simd_min` simdgroup row is still NOT
designed (a separate decision), and "keep as designed" is what every other
Apple device still gets.

Scope, stated plainly: W > 256 on M1 Max is UNMEASURED (the measured
penalty grew with W over the measured band); the demotion at those sizes
follows that trend toward the fail-safe arm and claims no measurement
there. [SUPERSEDED as to W > 256 on M1 Max's MSL arm -- the same-day
W-sweep amendment below measures those sizes; the clause stands unchanged
for the GLSL arm, whose W = 512/1024 remains UNMEASURED.] `:measured?` is UNCHANGED -- false on every answer of every row --
because question (1) is undecided: the MSL-arm measurement that partly
backs this narrowing ran through a native Metal harness whose contract
status is exactly question (1). The narrowing is implemented with tests in
`kotoba.compiler.accelerator-variants` (the answer's `:basis` carries the
refutation for a narrowed answer only); a refuted device WITHOUT rule-6
facts keeps the ordinary fail-closed `:baseline` basis and no narrowing
note.

### Amendment 2026-10-23 (the W-sweep): W > 256 on M1 Max is MEASURED on the MSL arm

The "Scope, stated plainly" paragraph above is SUPERSEDED as to W > 256 on
M1 Max's MSL arm. The same-day native-Metal W-sweep
(docs/evidence/gpu-subgroup-reduce-m1max-wsweep-20261023/; the JUN-58
measurement driver extended to emit, dispatch and time the two MSL arms at
each width -- the subgroup arm's threadgroup partials array is sized from
the emitted W, so every cell runs the emitters' own bytes for its own
width) measured the reduce shape at W = 512 and W = 1024 for the first
time, with W = 256 re-run in the same session as the anchor. Paired
within-run ratios (median over each fresh process's pairs of
variant/baseline gpu-ns, then the median of the six), all three operators:

| W | :sum | :max | :min |
|---|------|------|------|
| 256 (anchor) | 1.220 | 1.217 | 1.217 |
| 512 | 1.196 | 1.195 | 1.197 |
| 1024 | 1.186 | 1.186 | 1.185 |

The anchor reproduces the earlier same-day W = 256 cell (1.216-1.223), and
the variant is SLOWER at both newly measured sizes, all three operators,
in every fresh process. The demotion to `:baseline` at W > 256 on this
device now rests on this device's own measurement at those sizes, not on
the monotone-trend inference the superseded clause described. The penalty
narrows slightly with W on the MSL arm (1.22 -> 1.19) where the GLSL band's
penalty grew with W; the SIGN is unanimous in every measured cell of both
arms. One noisy run at W = 512 (`:max` run 3, a faster-clocked baseline,
ratio 1.648) is visible in the per-run ratios and does not move the
medians; :max/:min are bit-exact against the CPU reference and between
arms in every cell (rule 2's ordinary-value domain holds on hardware);
:sum's low-bit divergence grows with W (max abs vs other 3.05e-05 at
W = 256, 6.10e-05 at W = 1024).

What does NOT change: the contract caveat. These numbers carry exactly
question (1)'s undecided contract status -- the same native-Metal harness
channel as the W = 256 MSL measurement, not the wire-42 route -- so
`:measured?` stays false on every answer and no workgroup row (ADR-0355 /
0358) is touched. The GLSL arm at W = 512/1024 remains UNMEASURED: the
wire-42 route has no execution path since the C loader removal, and the
2026-10-19 GLSL band stopped at W = 256.
