# ADR-0360 -- The Apple row: the subgroup-size-parametric reduce on the Vulkan route

- Status: accepted as design. The selection row is implemented 2026-10-23
  (code + tests in `kotoba.compiler.accelerator-variants`); the row is
  UNMEASURED. The 2026-10-23 amendment at the end of this ADR extends the
  row from the Vulkan route to the MSL route as well (implemented same
  date). [The "UNMEASURED" clause predates the same-day measurement
  amendments further down: the MSL arm ran on Apple M1 Max, the row is
  NARROWED to that device, and the measured cells flip the honesty lock.
  Those amendments govern; this line describes the state at adoption.]
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
designed here. [DECIDED later the same day in ADR-0373: that separate
variant is now DESIGNED there -- design only, not implemented. "Not
designed HERE" stands as to this ADR.]) The
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
Apple device still gets. [DECIDED 2026-10-23, ADR-0373: the Metal-native
simdgroup row is now DESIGNED there (design only, not implemented). That
ADR's MSL ladder supersedes "keep as designed is what every other Apple
device gets" as to non-m1-max Apple MSL descriptors FROM THE MOMENT THE
ROW IS IMPLEMENTED (rule 3); until then selection is unchanged and this
clause governs.][UPDATE 2026-10-23, ADR-0373 rule 3 steps 1-2: the row IS
implemented (emission + selection) and the supersession has TAKEN EFFECT
as to non-m1-max Apple MSL descriptors carrying the `:simd-reduce` fact
(they answer `:simdgroup-reduce`, UNMEASURED); the m1-max class keeps
this clause's narrowed `:baseline` answers unchanged, and the shuffle
facts without `:simd-reduce` keep answering `:subgroup-reduce` here,
byte-for-byte.]

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

## Amendment 2026-10-23 (the low band): W = 32..128 on M1 Max is MEASURED on the MSL arm

The "MSL W = 32..128 is UNMEASURED" clause that every later record carried
is SUPERSEDED. The same native-Metal harness measured the remaining three
widths of the MSL band on the same host (Apple M1 Max, reported subgroup
size 32), same protocol (6 fresh processes, 20 interleaved pairs per
operator per run, alternating AB/BA, verified read-back),
docs/evidence/gpu-subgroup-reduce-m1max-wsweep-low-20261023/. Paired
within-run ratios (variant/baseline gpu-ns, per-run median of pairs, then
the median of six), anchors from the earlier sessions in parentheses:

| W | :sum | :max | :min |
|---|------|------|------|
| 32 | 0.918 (0.917-0.920 per run) | 0.923 | 1.019 |
| 64 | 1.221 | 1.216 | 1.202 |
| 128 | 1.246 | 1.243 | 1.242 |
| 256 | 1.220 | 1.217 | 1.217 |
| 512 | 1.196 | 1.195 | 1.197 |
| 1024 | 1.186 | 1.186 | 1.185 |

Read-back: ok=1 on all 108 verify lines of the three cells; :max/:min
bit-exact against the CPU reference and between arms in every cell; :sum
bit-exact between arms at W = 32 (one simdgroup per group regroups
identically), divergent in the low bits at W = 64/128 as in the wider band.

What the numbers say. The penalty band is NOT monotone toward small W. The
W-sweep's "the penalty narrows with W" holds over W = 128..1024 (peak
1.246 at W = 128, narrowing to 1.186 at W = 1024); W = 64 sits in the same
band (~1.20-1.22). W = 32 is the single cell where the variant is not
slower: :sum is faster in every fresh process (0.916-0.920) and :max is
faster in the slow-clock runs (0.916-0.924) -- roughly 8% ahead. REGIME
NOISE, named: the GPU changed clock state mid-session in this cell (per-run
median gpu-ns steps 109k -> 36k), and in the fast regime the W = 32 arms
are within noise of each other (:min runs 3-6 at 1.017-1.024; :max runs 4/6
at 0.958/1.017). The W = 32 :min cell's overall sign (median 1.019) is
therefore NOT ESTABLISHED -- its per-run ratios straddle 1 with the regime
shift -- and "the variant is faster at W = 32" is scoped to the slow regime
where :sum ran all six processes.

What this contradicts, stated plainly: the narrowing's rationale ("the
variant measured slower at every W, so `:baseline` at every W on this
device") is contradicted at W = 32 by this device's own measurement. What
this does NOT do: no selection behavior changes here. Whether the
narrowing's W = 32 cell should answer `:subgroup-reduce` (and how the
honesty-lock flip set -- currently W = 256/512/1024 in
`kotoba.compiler.accelerator-variants` -- and its test label follow) is a
new design question, PROPOSED by this evidence and decided nowhere; it is
one implementation slice with tests. Until that slice, the W = 32..128
answers keep the lock (:measured? false) and the demotion stands as the
fail-safe.

DECIDED 2026-10-23 (the low band's selection question, JUN-58): the
W = 32 cell keeps answering `:baseline` for all three operators on the
measured device. The demotion there changes status: it was the fail-safe
on unmeasured ground, it is now a DECISION on measured ground. The basis:
the cell's only not-slower signs are scoped to the slow clock regime the
device sat in while every :sum run happened (per-run median gpu-ns
109k -> 36k mid-session; no :sum run exists in the fast regime), :max's
win follows the regime, and :min's sign is NOT ESTABLISHED across the
shift. A regime-scoped sign is not a selection basis -- the same standard
that keeps the LABELED BOOTSTRAP GLSL runs verdict-free -- and an
operator-split answer at one cell off one shape would be overfitting. The
W = 32 answer keeps the honesty lock (:measured? false): no cross-regime
verdict chose it, the decision did, and its basis carries the decision
note (apple-w32-note). The flip set follows the measurement: W = 64 and
W = 128 JOIN it (their measurement chose the demotion -- all three
operators 1.20-1.25, the penalty band of W >= 256), so the flipped widths
are W = 64/128/256/512/1024 and the record's evidence list carries the
low-band directory. The paragraphs above that leave the question open
describe the state before this decision and are superseded as to their
status claims only. The stale clause "MSL W = 32..128 is UNMEASURED" is
superseded everywhere (the flip-set prose in `kotoba.compiler.accelerator-
variants`, the pipeline docstring and the test label updated in the same
slice).

Instrument defect found and fixed in the same record (named, not hidden):
the harness's verified read-back scratch arrays were fixed at 3907
elements (W = 256's group count) and overflowed the stack at W = 32 (31251
groups) -- the guard admitted [32, 1024] but the instrument could only run
[256, 1024] before this fix. The timing path never used the arrays.

Supersession note on the contract caveat above: question (1) was DECIDED
2026-10-23 (the decision reached code in the honesty-lock flip,
`accelerator_variants`'s `:measured-cell` and the `:variant-measured?`
axis; the decision text is the flip commit's and the namespace docstrings').
The admitted channel is this native-Metal harness FOR THE MSL ARM (wire 42
executes SPIR-V through Vulkan and can never run MSL), the flip records the
tested device class as the `:measured-cell` keys (name fragment `m1 max`
AND reported subgroup size 32, MSL route, a W the channel ran). The
paragraphs above that call question (1) undecided describe the state before
that decision and are superseded as to their status claims only; the GLSL
arm keeps its LABELED BOOTSTRAP status at every width and no workgroup row
(ADR-0355/0358) has been touched by any of this.

## Amendment 2026-10-23 (the second shape and the op-order regime
measurement): the W = 32 regime scoping is MEASURED, every decision
unchanged

Two more same-channel cells landed (same host, Apple M1 Max, reported
subgroup size 32; same ADR-0358 protocol; records under `docs/evidence/`),
and the flip contract's basis text cites them from this slice (no flag,
no `:measured-cell` set and no workgroup row moves):

1. **Shape 2** (`gpu-subgroup-reduce-m1max-shape2-20261023/`): n = 2^20 =
   1,048,576 -- a clean multiple of every W in [32, 1024], the padded-lane
   tail every earlier shape (n = 1,000,003) exercised now absent -- at
   W = 256 (the anchor of the flip set) and W = 32 (the decided cell).
   The verdicts replicate: W = 256's penalty band is 1.220-1.227 (shape 1:
   1.217-1.220) and W = 32's :sum is 0.919 with every one of the six fresh
   processes below 1 (0.916-0.922). The narrowing's demotion basis is
   therefore NOT a padded-tail artifact. The W = 32 sign straddles 1
   across clock levels on this shape too (fast-level :max 1.026, :min
   1.021-1.026 against slow-level ~0.92), and :sum still had no
   fast-level sample in that cell -- the harness's fixed operator order
   (sum first, every process) made that structural, and the record names
   it.

2. **Op-order** (`gpu-subgroup-reduce-m1max-oporder-20261023/`): the
   instrument variant that removes that blocker -- the harness takes a
   dispatch order (`argv[4]` / `--op-order`, default `sum,max,min`
   byte-identical to every earlier cell), this cell running **sum LAST**
   (W = 32, n = 1,000,003 -- the flip contract's shape -- otherwise the
   standard protocol). The first :sum fast-regime samples in the series
   measure the variant SLOWER there. Regime-conditioned within-pair
   medians (variant/baseline gpu-ns, by observed clock level -- slow
   ~109k, middle ~45-69k, fast ~35.6-37k baseline gpu-ns per pair):

   | op  | slow | middle | fast |
   |-----|------|--------|------|
   | :sum | 0.919 (61 pairs) | 0.932 (35) | 1.018 (24) |
   | :max | 0.917 (113) | -- | 1.029 (7) |
   | :min | 0.920 (86) | 0.993 (14) | 1.018 (20) |

   FINDING: the W = 32 sign is regime-scoped for **all three** operators
   -- the slow-regime win (roughly 8%) is a clock artifact, and at the
   fast level the variant is slower in each. What the low-band record
   inferred from structure for :sum is now directly measured.

Supersession (claims only): the low-band DECIDED paragraph's "no :sum run
exists in the fast regime" and ":min's sign is NOT ESTABLISHED across the
shift" describe the state before these two cells and are superseded as to
those claims -- :sum's regime split is measured (1.018 at the fast level
over 24 pairs), and :min's straddle replicates with the mechanism visible
(its sign follows the clock level like the other two). Nothing else
moves: the W = 32 decision (keep `:baseline` for all three operators,
honesty lock on) stands unchanged -- its basis is **strengthened**, from
inference to measurement, and a regime-scoped sign is still not a
selection basis. The flip contract still keys to n = 1,000,003
(`accelerator-variants`' `apple-measured-n`); shape 2 is corroboration,
not a contract cell, and whether the contract should widen to more shapes
is its own later decision. UNMEASURED unchanged: the GLSL arm at every
width beyond its LABELED BOOTSTRAP record, every Apple device but this
M1 Max, shapes beyond these two, and the NVIDIA/Intel/ARM/AMD variant
rows entirely.

## Amendment 2026-10-23 (the flip-contract widening decision): the
contract keys to the two measured shapes

DECIDED (JUN-58, the slice the shape-2 band's record named as the next
row): the flip contract's shape key WIDENS from the single shape
n = 1,000,003 to the two MEASURED shapes -- n = 1,000,003 and
n = 2^20 = 1,048,576. `accelerator-variants`' `apple-measured-n` is
replaced by `apple-measured-shapes` `[1000003 1048576]`, and the
`:measured-cell` record's `:n` field by `:shapes`, naming both.

Grounds (all of it previously measured, no measurement taken in this
slice): shape 2's completed flip-set band
(`docs/evidence/gpu-subgroup-reduce-m1max-shape2-band-20261023`, plus the
W = 256 anchor of `gpu-subgroup-reduce-m1max-shape2-20261023`) measured
`:subgroup-reduce` SLOWER than `:baseline` in all 15 width x operator
cells -- W = 64/128/256/512/1024 x :sum/:max/:min -- with paired
within-run median ratios 1.166-1.239, the same sign and the same penalty
band as shape 1 at every width. The demotion basis is therefore not
shape-dependent over the two measured shapes, and shape 2 is a contract
cell, not corroboration.

What moves: the record's shape field, `apple-measured-evidence` (gains the
two shape-2 directories), and the basis prose (`apple-narrow-note` names
the widening; `apple-w32-note`'s overfitting clause now reads "off the two
measured shapes"). What does NOT move: the flip's gates (device-name
fragment "m1 max" AND reported subgroup size 32, the MSL route, the
verdict-chosen widths 64/128/256/512/1024) and their behavior -- the
shape key never gated selection, it bounded the claim; no workgroup row
(ADR-0355/0358) moves; the W = 32 cell keeps the lock by decision,
unchanged; `:measured?` still means "a measurement CHOSE this answer",
never "optimal".

Supersession (claims only): the previous amendment's "the flip contract
still keys to n = 1,000,003; shape 2 is corroboration, not a contract
cell, and whether the contract should widen to more shapes is its own
later decision" is superseded as to that key -- the decision has now run,
and it widened. Nothing else in that amendment moves.

UNMEASURED, unchanged and named so no claim extends past it: shapes
beyond these two (the answer cannot vary with n, but only these two ran),
the GLSL arm at every width beyond its LABELED BOOTSTRAP record, every
Apple device but this M1 Max, W = 32's selection answer as a verdict
(it is a decision), and the NVIDIA/Intel/ARM/AMD variant rows entirely.

Record: `docs/evidence/gpu/flip-contract-widen-20261023.txt` (the
decision's record; this slice ran no hardware measurement). Tests:
`test/kotoba/compiler/accelerator_variants_test.cljk` pins the widened
record map and the basis prose (scoped GPU gate 87 tests / 7118
assertions, 0 failures; full suite RED AT BASE at `kotoba.form`, the W3
port path, outside this diff -- both re-verified in the slice).

## Amendment 2026-10-23 (the regime-robust magnitude claim protocol):
how sign and magnitude claims are published under clock regimes

DECIDED (JUN-58, the slice the shape-2 re-sweep's closing record named
as the strengthened case -- "a regime-robust magnitude claim protocol --
PROPOSED, decided nowhere, own slice if taken"): the claim rules this
campaign's records already practiced ad hoc become the protocol for sign
and magnitude claims in this evidence family (the gpu-subgroup-reduce
measurement records; a later vendor campaign adopts it by citation, its
own row). NO hardware measurement runs in this slice -- the ground is
all previously measured: the regime term was named at every one of the
ten re-swept cells (shape-1 and shape-2 re-sweeps, W = 64/128/256/512/
1024), and at the closing cell (W = 512 shape 2) it quantified as a
session-mixing effect on the `:min` median -- :sum/:max reproduce within
0.002/0.003 while :min lands +0.010 above the historical cell because
the two sessions' regime mixes differ. The mechanism is measured
directly (the op-order cell's within-pair medians by clock level, W =
32: :sum slow 0.919 / fast 1.018, :max 0.917 / 1.029, :min 0.920 /
1.018): ratio magnitude AND sign both follow the clock level.

The protocol (four rules):

1. **Regime classification is published, not hidden.** Every measurement
   record publishes each run's baseline per-run median gpu-ns per
   operator and the regime clusters its session observed (the discrete
   clock levels; the harness reads no GPU clock, so clusters are the
   observed baseline-median levels, named by their gpu-ns ranges). A
   magnitude claim whose record does not publish them is inadmissible.

2. **Sign claims are regime-invariant or regime-scoped, and only a
   regime-invariant sign is a selection basis.** "Regime-invariant":
   every per-run ratio of every observed regime lies on the same side of
   1.0 (the flip-set cells' 18/18 slower). A sign that follows the
   regime (the W = 32 straddle) is published regime-scoped and cannot
   choose a variant -- the standard that kept the LABELED BOOTSTRAP GLSL
   runs verdict-free and the W = 32 answer decision-locked, now stated
   once for every cell.

3. **Magnitude claims are regime-matched.** A magnitude comparison
   across sessions or cells is drawn within matched regime strata. When
   the regime mixes differ, the claim names the split ("magnitude splits
   by clock regime") and attributes the deviation to session mixing --
   it is NOT published as a failure to reproduce. The reproduction
   vocabulary is exactly three phrases: "reproduces in sign strictly"
   (all per-run ratios hold the historical sign), "magnitude reproduces
   within <delta>" (matched regime mixes), "magnitude splits by clock
   regime" (mixed).

4. **Nothing here measures anything.** No `:measured?` flag, no
   workgroup row (ADR-0355/0358), no flip gate and no selection answer
   moves. The protocol changes what a record may CLAIM, not what any row
   answers.

State (the honesty rule's three states): ACCEPTED DESIGN ONLY (this
amendment). No harness implements regime classification -- the records
classify manually in NOTES.md -- and harness-side classification is
UNIMPLEMENTED, its own later slice. This amendment does not make the
protocol "implemented".

Record: `docs/evidence/gpu/regime-robust-protocol-20261023.txt` (the
decision's record; this slice ran no hardware measurement). UNMEASURED,
unchanged: shapes beyond the two measured; the GLSL arm at every width
beyond its LABELED BOOTSTRAP record; every Apple device but this M1 Max;
W = 32 as a verdict (it is a decision); the NVIDIA/Intel/ARM/AMD variant
rows entirely; cross-day replication of every cell; regime
classification inside the harness.

## Amendment 2026-10-23 (rule 1 mechanised): harness-side regime
classification is IMPLEMENTED (the GAP-1.15 clustering)

The slice the protocol's state paragraph named ("harness-side
classification is UNIMPLEMENTED, its own later slice") lands for
**rule 1 only**. `scripts/gpu_regime_classify.py` clusters the per-run
baseline medians into clock levels and every `summary.md` the
measurement driver (`scripts/gpu-subgroup-reduce-metal-measure.py`)
writes now carries a "Regime classification (claim protocol rule 1)"
section: the per-run baseline medians per operator (rule 1's first
publication, also in the first table as before) and the regime clusters,
named by their gpu-ns ranges with run membership.

The clustering rule is named **GAP-1.15** and is data-derived, not
tuned: per operator, the per-run medians sorted ascending,
single-linkage -- the next median joins the current level at <= 1.15x
the previous, else a new level starts. 1.15 is the geometric midpoint
of the separation window the committed corpus itself establishes
between prose-decided within-level drift (1.0753: the wsweep-low
W = 32 `:max` runs 4 and 6, one "fast regime" in that record's prose)
and prose-decided between-level steps (1.2343: the shape-2 re-sweep
W = 512 `:min` run 3 "dropped" from the slow level). Gaps strictly
between the anchors were decided by no prose in the corpus; GAP-1.15
decides them mechanically and the published ranges make every such
decision visible. `--self-test` enumerates them (12 gaps at this
writing) so a new record cannot hide one.

State, precisely: rule 1's harness-side publication is IMPLEMENTED
(code + tests: 606 assertions -- unit fixtures, the corpus regression
over all 28 committed summaries, and the pinned manual classifications
of the w512 shape-2 re-sweep cell, the shape-2 W = 32 cell and the
wsweep-low W = 32 cell reproduced from their committed summary.md
text). Rule 1's claims discipline is unchanged and no existing record is
rewritten: the older records stand with their manual NOTES.md
classification until their own re-sweep rows re-derive them.
**UNIMPLEMENTED, named:** rule 2's sign classification (regime-invariant
vs regime-scoped) harness-side; rule 3's regime-matched comparison
machinery; pair-level classification (the op-order cell's within-run
ramping needs per-pair levels -- `analyze-oporder.py` remains the manual
instrument); cross-operator level identity (the harness reads no clock
and does not assert that two operators' clusters are one clock level).
No `:measured?` flag, workgroup row, flip gate or answer moves (rule 4,
untouched).

Record: `docs/evidence/gpu/regime-classification-20261023.txt`.

## Amendment 2026-10-23 (rule 2 mechanised): harness-side sign
classification is IMPLEMENTED

The row the protocol's state paragraph named ("rule 2's sign
classification (regime-invariant vs regime-scoped) harness-side", listed
UNIMPLEMENTED after rule 1's GAP-1.15 slice) lands now.
`scripts/gpu_regime_classify.py` gains sign_classification() and
render_sign_section(), and every `summary.md` the measurement driver
(`scripts/gpu-subgroup-reduce-metal-measure.py`) writes now carries a
"Sign classification (claim protocol rule 2)" section beneath the rule-1
clusters: per operator the verdict and its detail, and the cell's
admissibility roll-up over pooled per-run ratios (the "18/18 slower"
shape).

The verdict is exactly rule 2's dichotomy, mechanically:
REGIME-INVARIANT when every per-run ratio of every observed regime lies
strictly on one side of 1.0 (only such a sign may be a selection basis);
anything else REGIME-SCOPED (cannot choose a variant). Two boundary
cases the prose did not decide are decided mechanically and published,
not hidden (the GAP-1.15 ethos applied to signs):

- the straddle's shape: "by-regime" (every regime one-sided, regimes
  disagree -- sign follows the regime; the shape-2 W = 32 :max/:min
  cells, reproducing accelerator_variants' "fast-level :max 1.026 and
  :min 1.021-1.026 against slow-level ~0.92"), "within-regime" (one
  regime holds both sides -- wsweep-low W = 32 :max, whose fast regime
  runs 4/6 are 0.958/1.017, both sides inside ONE regime), or "no-side"
  (every ratio exactly 1.0: no sign exists to claim). The shape never
  changes the verdict -- rule 2's second sentence already denies a
  regime-scoped sign any selection role whatever its shape;
- a ratio at exactly 1.0 sits on NEITHER side of 1.0, so a cell holding
  one is not regime-invariant ("the same side of 1.0" is read strictly).

Because cross-operator level identity is NOT asserted (rule 1's own
named limit), the cell row is only an admissibility roll-up -- it carries
no cross-operator regime structure.

State, precisely: rules 1 and 2's harness-side publication is IMPLEMENTED
(code + tests). Tests (real output):
`python3 scripts/gpu_regime_classify.py --self-test` = 887 assertions, 0
failed -- unit fixtures (invariant on either side, the exact-1.0
boundary, both straddle shapes on real committed W = 32 numbers, the
cell roll-ups, the driver's call shape), a corpus regression over all 28
committed summaries (84 operator-cells classified: 75 regime-invariant
slower, 3 regime-invariant faster, 5 regime-scoped by-regime, 1
regime-scoped within-regime, 0 no-side; every verdict independently
recomputed from rule 2's condition), and pinned classifications
reproducing committed prose (wsweep-low w32 :max within-regime; shape2
w32 :max/:min by-regime; shape2-resweep w512 18/18 slower). No record is
rewritten: the older records stand with their manual NOTES.md
classification until their own re-sweep rows re-derive them.
UNIMPLEMENTED, unchanged and named: rule 3's regime-matched comparison
machinery; pair-level classification (the op-order cell's within-run
ramping needs per-pair levels -- analyze-oporder.py remains the manual
instrument); cross-operator level identity. No `:measured?` flag,
workgroup row, flip gate or answer moves (rule 4, untouched). This slice
ran no hardware measurement.

Record: `docs/evidence/gpu/rule2-sign-classification-20261023.txt` (this
slice ran no hardware measurement).

## Amendment 2026-10-23 (rule 3 mechanised): harness-side regime-matched
comparison is IMPLEMENTED

The row rules 1's and 2's state paragraphs named ("rule 3's
regime-matched comparison machinery", listed UNIMPLEMENTED after both
earlier slices) lands now. `scripts/gpu_regime_classify.py` gains
median_draw(), draw_levels(), strata_matched(),
regime_matched_comparison() / cell_regime_matched_comparison() /
render_rule3_section(), and a `--compare <historical.md> <new.md>` CLI:
the protocol's exactly-three-phrase reproduction vocabulary, applied to
a comparison of two measurement records, with the magnitude comparison
drawn within matched regime strata as rule 3 requires.

The verdicts are rule 3's, mechanically. The SIGN phrase ("reproduces
in sign strictly") is rule 2's, for reproduction: exactly when the
historical cell is regime-invariant on one side and every new-cell
per-run ratio holds it. The MAGNITUDE phrase is keyed on the regime mix
of the paired medians' draws (the closing cell's "the medians' regime
mixes differ"): "magnitude reproduces within <delta>" when the mixes
match, "magnitude splits by clock regime" when they do not -- the
deviation attributed to session mixing, never "failed to reproduce".
<delta> is the observed deviation of the published paired medians,
quoted from the summary's own median column so the phrase digits match
the committed prose. Beside the cell-median delta the machinery
publishes the within-stratum comparison (per matched stratum pair, the
per-run ratio medians of the member runs): at the closing cell the :min
comparison drawn within the matched slow stratum is 1.194 vs 1.197 =
0.003 against the cell-median 0.010 -- the session-mixing artifact,
quantified within strata.

Two boundary cases the prose did not decide are decided mechanically
and published (the GAP-1.15 ethos applied to comparisons):

- the DRAW tie rule: the paired median's draw is the middle run(s) of
  the (ratio, run) sort, and every run tying a middle ratio is a
  candidate draw -- a tie cannot silently pick the pure stratum. At the
  closing cell's historical :max this matters: its per-run ratios tie
  at 1.192 across THREE strata (the 49k / 96k / 119k levels), so the
  draw is mixed whatever the tie resolution;
- the cross-cell STRATUM-MATCHING rule: two levels from different
  sessions match under rule 1's own single-linkage test at GAP-1.15.
  The harness reads no clock, so "matched" is gpu-ns compatibility
  under the same constant that defines a level within a session, not
  verified cross-session clock identity -- the corpus prose's
  cross-session slow/fast naming is the assumption this replaces with a
  visible test.

Consequence, pinned and not bent away: the machine's mix-keyed verdicts
DIVERGE from pre-protocol manual prose wherever that prose published
"within <delta>" by deviation size on a mixed-draw comparison. The
first case is the closing cell's :max (manual: "within 0.003";
machine: "magnitude splits by clock regime", within-stratum 0.001).
Across the ten re-sweep pairs the enumeration shows 30/30 signs
reproducing strictly and 11 split phrases, only one of which the manual
prose had also published as splitting. Nothing is weakened -- rule 3's
own text forbids publishing a mixed comparison as "failed to
reproduce", and every relabeled comparison's within-stratum delta is
<= 0.005 where any matched stratum exists. A second finding rides the
enumeration: at shape-2 W = 1024 the two sessions observed NO common
regime (zero matched strata on :max/:min), so the split phrase is the
only admissible one there -- the mechanical account of that cell's
record-wide +0.017/+0.016 deviation (disjoint session regimes, not
non-reproduction).

State, precisely: rules 1, 2 and 3's harness-side publication is
IMPLEMENTED (code + tests). Tests (real output):
`python3 scripts/gpu_regime_classify.py --self-test` = 908 assertions,
0 failed -- the previous 887 plus rule-3 unit fixtures (draws
even/odd/tie, purity, the 1.15 matching boundary on both sides, the
matched/mixed/unmatched phrase matrix, both sign-phrase refusals, the
three-way tie robustness shape on the real historical :max w512
numbers, the cell roll-up, the renderer) and the corpus pins (the
closing cell's three operators, the :min within-stratum 0.003 datum,
the ten-pair enumeration). No record is rewritten.
UNIMPLEMENTED, unchanged and named: pair-level classification (the
op-order cell's within-run ramping needs per-pair levels --
`analyze-oporder.py` remains the manual instrument); cross-operator
level identity; driver auto-wiring of `--compare` (the rule-3 section
is consumed manually today -- the measurement driver writes
single-record sections only). No `:measured?` flag, workgroup row, flip
gate or answer moves (rule 4, untouched). This slice ran no hardware
measurement.

Record: `docs/evidence/gpu/rule3-regime-matched-20261023.txt` (this
slice ran no hardware measurement).

## Amendment 2026-10-23 (rule 3 auto-wired): the driver publishes the
comparison itself

The row rule 3's state paragraph named ("driver auto-wiring of
`--compare`", listed UNIMPLEMENTED) lands now. The measurement driver
`scripts/gpu-subgroup-reduce-metal-measure.py` gains
`--compare-historical HIST.md` (a prior record's summary.md, read once,
never modified): the summary it writes then carries the rule-3
regime-matched comparison against that record as its final section,
drawn from exactly the text being published -- no manual `--compare`
consumption step remains. `finalize_summary()` is the exact function
`main()` calls; without the flag the text passes through unchanged. The
`--compare` CLI itself is unchanged and still works: auto-wiring is an
additional publication path, not a replacement.

Honesty detail, decided and pinned: `render_rule3_section()` gains a
`via` name in the section header. The auto-wired section says "Published
by the measurement driver's --compare-historical auto-wiring
(scripts/gpu-subgroup-reduce-metal-measure.py; rule-3 machinery:
scripts/gpu_regime_classify.py)", never the CLI phrase -- a section
never claims a publication path it did not take. The default header
("Published by scripts/gpu_regime_classify.py --compare: ...") is
pinned unchanged by test.

State, precisely: rules 1, 2 and 3's harness-side publication,
including driver auto-wiring, is IMPLEMENTED (code + tests). Tests
(real output): `python3 scripts/gpu_regime_classify.py --self-test` =
916 assertions, 0 failed (the previous 908 plus 8 auto-wire fixtures:
the pinned default header, the via substitution, the additive-append
prefix property, the appended-section-equals-`--compare`-output
property, three parser round-trips, the appended-record-stays-loadable
property -- all over the real shape2-band/w512 -> shape2-resweep/w512
corpus pair); `python3 scripts/gpu-subgroup-reduce-metal-measure.py
--self-test` = 7 assertions, 0 failed (the hardware-free finalize path
over the same corpus pair). Scoped GPU gate: 88 tests / 7122
assertions, unchanged (no .cljk in this diff). Full suite RED AT BASE
(`Could not find namespace: kotoba.form`), outside this diff.
UNIMPLEMENTED, unchanged and named: pair-level classification (the
op-order cell's within-run ramping needs per-pair levels --
`analyze-oporder.py` remains the manual instrument); cross-operator
level identity. No `:measured?` flag, workgroup row, flip gate or
answer moves (rule 4, untouched). This slice ran no hardware
measurement.

Record: `docs/evidence/gpu/rule3-autowire-20261023.txt` (this slice ran
no hardware measurement).

## Amendment 2026-10-23 (pair-level classification): rule 1's rule at
pair granularity

The row the auto-wire amendment's state paragraph named ("pair-level
classification (the op-order cell's within-run ramping needs per-pair
levels -- `analyze-oporder.py` remains the manual instrument)") lands
now. A run's clock can ramp mid-run, so run-level classification is
blind to within-run regime changes; `scripts/gpu_regime_classify.py`
gains the pair-level machinery (`parse_run_log_pairs` /
`pair_level_classification` / `render_pair_level_section`, CLI `--pairs
<run-log.txt>`): the individual pairs of a driver run-log are clustered
by the pair's baseline gpu-ns under rule 1's OWN rule, unchanged --
GAP-1.15 single-linkage -- and each level publishes its pair count,
baseline range, median pair ratio and sides. Incomplete pairs (an arm
missing) are named and excluded, never silently dropped.

Decided and pinned (the GAP-1.15 ethos): the manual instrument's hand
buckets (`analyze-oporder.py`: slow > 80k, middle 40k..80k, fast <=
40k) are NOT reused by the machine -- only the granularity changes, not
the rule or the constant. The rule-2 machine runs at pair granularity
too but is published as an ANALOGUE only: the section's own text says
"it is not rule 2" -- rule 2's verdicts stay run-level over per-run
ratios, no rule-2 verdict is amended, and the analogue cannot choose a
variant. `via` names the publication path (rule 3's honesty rule).

The machine-vs-manual comparison over the committed op-order run-log
(360 complete pairs = 6 runs x 3 ops x 20) is pinned in --self-test on
both sides: for every manual bucket row the two instruments agree
exactly on pair population and 3dp median (8 rows, parsed from
analyze-oporder.txt, not transcribed), AND the manual buckets pool what
the machine splits -- fast is one machine plateau per op (35708..36250
max @ 1.029, 35708..37167 min @ 1.018, 35583..36958 sum @ 1.018), while
middle splits into 2 and slow into 2..5 machine levels, including an
~88k plateau (gap 1.21 to the ~107k plateau) the hand buckets pooled
into slow and the single-pair glitch spikes (0.295..0.784) that become
their own levels instead of hiding inside it. The finer classification
does not move the cell's published regime story: fast = variant slower
~1.02, the ~88k and ~107k plateaus = variant faster ~0.92 both sides of
the split. The pair-level sign analogue is regime-scoped
(within-regime, single pairs spike both ways) for all three ops -- NOT
a rule-2 verdict.

State, precisely: rules 1, 2 and 3's harness-side publication plus
pair-level classification is IMPLEMENTED (code + tests). Tests (real
output): `python3 scripts/gpu_regime_classify.py --self-test` = 1019
assertions, 0 failed (the previous 916 plus 103 pair-level fixtures --
unit parse/boundary/sign-analogue/rendering pins over synthetic logs,
corpus pins over the op-order record: the 360/0 pair population, the
machine level structure (lo/hi/count/median per level), the
sign-analogue pins, the 8 machine-equals-manual bucket relations and
the pool/split divergence);
`python3 scripts/gpu-subgroup-reduce-metal-measure.py --self-test` = 7
assertions, 0 failed. Scoped GPU gate: 88 tests / 7122 assertions,
unchanged (no .cljk in this diff). Full suite RED AT BASE
(`Could not find namespace: kotoba.form`), outside this diff.
UNIMPLEMENTED, unchanged and named: cross-operator level identity.
No `:measured?` flag, workgroup row, flip gate or answer moves (rule 4,
untouched). This slice ran no hardware measurement.

Record: `docs/evidence/gpu/pair-level-classification-20261023.txt`
(this slice ran no hardware measurement).

## Amendment 2026-10-23 (f): cross-operator level identity lands

The pair-level state paragraph named one UNIMPLEMENTED residue:
"cross-operator level identity (classification stays per operator; a
:sum level and a :min level are never called one clock level)". That
row is now IMPLEMENTED (code + tests): `cross_operator_level_identity`
in `scripts/gpu_regime_classify.py` tests, mechanically, whether the
operators' rule-1 run partitions AGREE -- for every run pair, every
operator must agree on whether the two runs sit in the same GAP-1.15
level. Agreement on every pair = "identity holds" (a record's prose may
then name one level across operators); any divergent pair = "identity
refuted", the pairs named with every operator's relation, and the
disagreement's shape published as partition refinement (equal / one
refines the other / cross-cutting). `render_identity_section` publishes
it in the single-record output (and therefore every future summary.md
the driver writes) when the record has at least two operators.

This is a publication fact about one record's regime structure. Rule 4
stands: it changes no rule-2 verdict (the cell row is still only the
admissibility roll-up), no rule-3 phrase, no selection answer, no
`:measured?` flag, no workgroup row. What stays unasserted, named:
CLOCK identity (the harness reads no clock) and pair-level
cross-operator identity (the pair-level section's levels are never
compared across operators).

Finding over the committed corpus (machine output over committed
summary.md text; NO hardware measurement ran in this slice): of the 28
multi-operator records, 9 hold (only 2 of those with multi-level
partitions) and 19 refute -- and every one of the 19 refuted records
has refinement structure (a strict refinement edge; asserted over every
refuted record). [UPDATE 2026-10-25: the "asserted over every refuted
record" half is SUPERSEDED by the 2026-10-25 cross-cutting-only
decision (Amendment 2026-10-25 below): the 2026-10-25 cross-day
W = 32 record refutes with NO strict refinement edge (all three
operator pairs cross-cut), so the corpus-wide structural claim fails
its pin at 36/37 and is re-stated as the named crossing-only set pin.
The dated 19/19 tally stands as history of the 2026-10-23 corpus.] Three
named consequences:

1. The closing cell (shape2-resweep w512) HOLDS: all three partitions
   are {3} / {1,2,4,5,6}, so that record's cross-operator fast/slow
   prose ("run 3 sat fast/intermediate"; "fast-level :max 1.026 /
   :min 1.021-1.026 vs slow ~0.92") is mechanically licensed.
2. wsweep-low w32 REFUTES: the record's "runs 4/6 one fast regime"
   naming is :max's partition alone (:min splits [3,4,5,6]/[2]/[1],
   :sum pools all six, and :max and :min CROSS-CUT). The cross-operator
   "the fast regime" prose of that cell is not mechanically
   licenseable; the W = 32 regime story stays per-operator.
3. The op-order cell is the corpus's only record where :sum's partition
   is the FINEST (and :max pools all six runs) -- :sum ran LAST in that
   cell's op order, so the within-run ramping the pair-level slice
   named shows up at run level in the operator that ran last.
   [UPDATE 2026-10-24: SUPERSEDED as a uniqueness claim. The shape-2
   W = 1024 :simdgroup-reduce record
   (docs/evidence/gpu-simdgroup-reduce-m1max-shape2-20261024/w1024) is
   a second corpus record where :sum refines :max (:sum [[2],
   [1, 3, 4, 5, 6]] against :max/:min pooling all six) -- and there
   :sum ran FIRST in the op order, so refinement does not track the
   last-dispatched operator. The op-order cell keeps its own reading
   (:sum ran LAST, the ramping story); the corpus-wide fact is now the
   two-record set pinned in scripts/gpu_regime_classify.py's identity
   corpus self-test. That pin was red from the W = 1024 record's
   commit until the 2026-10-24 corpus-pin fix slice (the measurement
   slice ran no self-test over its evidence addition -- the gap this
   red exposed); fixed and re-verified there,
   docs/evidence/gpu/finest-sum-corpus-pin-20261024.txt.]

Tests (real output): `python3 scripts/gpu_regime_classify.py --self-test`
= 1074 assertions, 0 failed (the previous 1019 plus 55 identity
fixtures -- unit refusal/boundary/refinement/rendering/round-trip pins,
corpus floors, the structural claim over every refuted record, and the
three named-record pins above); `python3
scripts/gpu-subgroup-reduce-metal-measure.py --self-test` = 7
assertions, 0 failed. Scoped GPU gate: 88 tests / 7122 assertions,
unchanged (no .cljk in this diff). Full suite RED AT BASE (`Could not
find namespace: kotoba.form`), outside this diff, re-verified.

Record: `docs/evidence/gpu/cross-operator-level-identity-20261023.txt`.

## Amendment 2026-10-24 (strict-bin reachability at W = 1024): the
hunt row is closed by decision, with named reopen conditions

The fastbin-hunt record's HONEST LEFT named one design sub-row:
"strict-bin reachability at this W". It lands here. The question: the
pair-level ANALOGUE's strict bins are the manual instrument's absolute
hand buckets (`analyze-oporder.py`: slow > 80k, middle 40k..80k, fast
<= 40k -- decided above as NOT reused by the machine, unchanged), and
the strict fast bin (pair baseline <= 40,000 ns) had collected ZERO
pairs at W = 1024 in every session. Is that bin reachable at that W at
all?

Measurement basis (machine output over the committed corpus; NO
hardware measurement ran in this slice -- the census reads every
committed run-log.txt read-only): `docs/evidence/gpu/
strict-bin-reachability-20261024.py`, 54 logs, 0 incomplete pairs.
The strict fast bin is UNREACHED-BY-OBSERVATION at W = 1024 in BOTH
contract shapes -- n = 1000003: 8 logs / 3,600 pairs / zero in the
bin / floor 40,083 ns (+83 ns above the boundary); n = 1048576:
4 logs / 1,440 pairs / zero / floor 41,542 ns -- while REACHED at
every other W in both shapes (1,268 fast-bin pairs at W = 32..512;
per-cell counts in the record). The boundary is W-specific, not an
instrument defect: the shape-1 floor rises with W and the 40k
boundary sits just below the observed floor at the largest workgroup.

Decided (ACCEPTED DESIGN ONLY -- this clause; no code namespace moved,
rule 4 untouched):

1. A strict bin at a (n, W) cell carries a reachability state computed
   from the committed corpus census: REACHED (>= 1 committed pair
   baseline inside the bin at that cell) or UNREACHED-BY-OBSERVATION
   (zero committed pairs inside it at that cell).
2. At W = 1024 the strict fast bin is UNREACHED-BY-OBSERVATION. The
   <= 40k pair-bin ratio at W = 1024 stays UNMEASURED, and the hunt
   row is CLOSED by this decision -- no further tick runs a session
   for that bin at that W by default. Closing the hunt row is NOT
   filling the bin; no ratio, verdict or row is claimed from it.
3. Reopen conditions (any one fires and the row returns to the
   backlog): (a) any committed session -- for any question -- lands a
   pair baseline <= 40,000 ns at W = 1024; (b) an instrument that
   reads the GPU clock exists and shows a level at or below the
   boundary at that W; (c) the owner directs the hunt to resume.
4. Naming, pinned: UNREACHED-BY-OBSERVATION is a CORPUS fact, never a
   hardware claim -- whether the hardware can ever produce a
   <= 40,000 ns pair baseline at W = 1024 is UNMEASURED (the harness
   reads no clock). The bins stay the manual instrument's absolute
   hand buckets; the machine keeps GAP-1.15 and never reuses them.
   Rule 4 stands: no `:measured?` flag, no `:measured-cell` :shapes,
   no selection answer, no workgroup row (ADR-0355/0358) moves.

State, precisely: the reachability clause is ACCEPTED DESIGN ONLY.
IMPLEMENTED: the census instrument (evidence tooling only). Nothing in
`src/kotoba/compiler/*` or `test/*` moved. MEASURED: nothing new on
hardware; every census number is parsed from committed measurements.
UNMEASURED, unchanged: the <= 40k pair-bin ratio at W = 1024, the
hardware reachability of the boundary at that W, the ramp's governing
conditions, and everything the record's NOT LICENSED list names.

Record: `docs/evidence/gpu/w1024-strict-bin-reachability-20261024.txt`
(this slice ran no hardware measurement).

**Amendment (2026-10-24, the WGSL-route selection question is
DECIDED).** The one route question this row left named and undecided --
ADR-0356's 2026-10-23 `:wgsl-v1`-selection amendment said "the Apple and
NVIDIA rows stay Vulkan-route-only ... extending either is a separate
per-vendor decision, undecided", and the NVIDIA half was decided
2026-10-24 (ADR-0361's amendment) leaving "the Apple row's WGSL question
stays UNDECIDED" -- is answered here (JUN-58's own decision, one vendor
per decision; record:
`docs/evidence/gpu/apple-wgsl-route-decision-20261024.txt`). Decided in
three parts:

YES -- the WGSL route (`:webgpu` / `:wgsl-v1`, one route two names, the
ADR-0359 decision-3 idiom) carries the Apple `:subgroup-reduce` row
under the SAME rules 3 + 6 gate as the Vulkan and MSL routes.

  Part 1 -- the row extends with no new gate: the WGSL arm of the shared
    subgroup-size-parametric emission already exists (the ADR-0363
    idiom: emission first, selection after), the fold's width is queried
    at runtime and never baked in (rule 6's `S | W` gate), and no new
    fact, key or floor is invented. Apple reaches this route by NAMING
    it -- ADR-0355's Apple vendor-default target stays `:msl-v1` --
    exactly as NVIDIA reaches it by naming it.
  Part 2 -- the measured-device narrowing RIDES ALONG. A descriptor
    naming the measured device (the "m1 max" fragment) answers
    `:baseline` on the WGSL route too: the refutation is of the FOLD on
    that device (it measured slower than `:baseline` on the two arms
    that ran -- GLSL via MoltenVK and MSL natively), and the refuted
    variant is not selected on the device that refuted it on any route
    that spells the same fold. The WGSL arm on that device is
    UNMEASURED; the conservative answer is the measured one. This is a
    DECISION, not a measurement claim: the narrowing's `:measured-cell`
    records stay MSL-scoped (an MSL measurement never flips a WGSL
    cell), so every WGSL answer -- the narrowed `:baseline` included --
    keeps `:measured? false`. REOPEN CONDITION: a WGSL-arm measurement
    of the narrowed device is new evidence and may revisit the
    narrowing's route scope. [REOPEN VISITED 2026-10-25 -- the trigger
    fired and the narrowing STANDS (record
    `docs/evidence/gpu/wgsl-wallclock-row-mapping-20261025.txt`): the
    2026-10-25 Chrome 155 Dawn/Metal wall-clock read of both WGSL
    reduce arms is a WGSL-arm measurement of the narrowed device
    (host-verified this tick: main-2, Apple M1 Max; the adapter string
    carries no device name) and measures PARITY against `:baseline`
    (paired-median ratios straddle 1, 72/72 answers exact against the
    CPU reference) -- parity is not a fold win, so the conservative
    `:baseline` answer for the named device stands, no `:measured-cell`
    record moves (the read is outside the claim-protocol channel: the
    2026-10-25 channel-rule amendment, ADR-0355), and the part's
    premise sentence "The WGSL arm on that device is UNMEASURED" is
    SUPERSEDED in its plain reading by MEASURED-AS-PARITY at wall-clock
    submit-to-completion (per-kernel GPU time stays UNMEASURED --
    writeTimestamp is refused on this adapter). The REOPEN CONDITION
    narrows to a claim-protocol WGSL measurement or a GPU-core-timestamp
    measurement of the device; the wall-clock parity read has had its
    visit and changed nothing. [FIRST LEG DEFINED 2026-10-25 -- the
    claim-protocol WGSL channel amendment below designs what a
    "claim-protocol WGSL measurement" is (a rule-1-publishing,
    rule-2-sign-scoped record on the channel's own named metric -- for
    this adapter's only clock, host wall-clock submit->completion) and
    finds the first leg REACHABLE on this adapter without GPU-core
    timestamps; it still cannot FIRE until the WGSL harness publishes
    rule-1 classification and a fresh run carries a regime-invariant
    sign -- both UNIMPLEMENTED / UNMEASURED, that amendment's part 3.]
    [FIRST LEG EVALUATED 2026-10-25 -- both pieces landed ((i) the
    WGSL harness publishes rule-1 classification and, since the rule-2
    slice, rule-2 sign classification; (ii) two fresh claim-protocol
    runs exist: `docs/evidence/gpu/wgsl-claimprotocol-run1-20261025`
    and `...-run2-20261025`), and the first leg does NOT FIRE: neither
    run carries a regime-invariant sign -- rule 2's verdict is
    REGIME-SCOPED at every operator and at the cell roll-up in both
    runs (run 1: single 19 above/14 below/3 at 1.0, batch32 20/15/1;
    run 2: single 14/18/4, batch32 16/20/0 -- re-derived this bracket's
    slice from the committed logs' own `pair` lines). No reopen; the
    narrowing stands -- conservative `:baseline` for the named device,
    no `:measured-cell` record moves (rule 4). UNMEASURED, unchanged:
    cross-run regime stability as a property (two uncontrolled runs
    bound no distribution -- and their regime STRUCTURES already
    differ: 5 of 6 metric/operator level structures differ in level
    count) and per-kernel GPU time. Prose only: no flag, cell,
    selection answer or workgroup row moves.]
  Part 3 -- rationale, all of it design fact and not measurement:
    WebGPU-on-Apple is a deployed surface (WebKit ships WebGPU; on
    macOS the browser's WebGPU runs over Metal), so a dispatch there
    previously answered `:baseline` even where the device reports the
    fold's facts; and the AMD row's runtime-width answer covers
    Apple's fixed SIMD-group width a fortiori -- 32 is just the
    reported `S`.

What this amendment does NOT change: `:simdgroup-reduce` stays MSL-only
(rule 3: its emission is admitted on `:msl-v1` only; an Apple WGSL
descriptor reporting only `:simd-reduce` facts fails closed to
`:baseline`); the MSL ladder, the flip cells and every `:measured-cell`
record are byte-for-byte unchanged; no workgroup row (ADR-0355/0358)
moves. UNCOMPILED (the WGSL arm: no validator on this host) and
UNMEASURED (no WebGPU execution path in this repository, and no Apple
hardware has run the WGSL arm) -- every answer this route gives keeps
`:measured? false`. After this decision no route question is UNDECIDED
for the five designed rows.

State: the decision is ACCEPTED DESIGN ONLY (this amendment); the
selection row it names is IMPLEMENTED with tests (one set membership in
`kotoba.compiler.accelerator-variants`, gate evidence in the record).

## Amendment 2026-10-25: cross-cutting-only is a legal refuted shape;
the structural pin's supersession

The 2026-10-25 cross-day W = 32 replica
(docs/evidence/gpu-simdgroup-reduce-m1max-crossday-20261025/w32) is the
corpus's FIRST cross-cutting-only identity refutation -- 5 of 15 run
pairs diverge, no refinement edge in either direction, all three
operator pairs cross-cut (machine output over the committed
summary.md, quoted in the decision record). It failed amendment (f)'s
structural pin exactly as that pin's comment prescribed ("a record
with cross-cutting-only divergence would fail this pin and surface
instead of hiding"), at `36/37`. The record named the decision as its
own next slice, taken before the pin is touched. DECIDED:

YES -- cross-cutting-only is a legal refuted shape. Identity refutes on
partition disagreement alone (any divergent run pair); the refinement
relation is the published SHAPE of the disagreement (equal / one
refines the other / cross-cutting), never a legality condition. A
refuted record is REFINEMENT-STRUCTURED (>= 1 strict refinement edge)
or CROSSING-ONLY (none; the record refutes, so at least one pair
cross-cuts); CROSS-CUTTING-ONLY is the crossing-only record whose every
pair cross-cuts -- this record's shape.

What the pin asserts afterwards: amendment (f)'s corpus-wide claim
"every refuted record has a strict refinement edge" is SUPERSEDED (its
dated 19/19 tally stands as history, bracketed above). The replacement
pin is the `:sum-refines-:max` set pin's idiom: the crossing-only
refuted records are EXACTLY a named set (one member today), and a
future crossing-only record fails the pin on purpose and enters the set
with its own story -- the surfacing mechanism is preserved where it
matters, not dropped. The named record's shape is pinned per record;
the strict-edge tally stays a printed corpus fact.

What this changes: nothing else. Rule 4 stands (no rule-2 verdict,
rule-3 phrase, selection answer, `:measured?` flag or workgroup row
moves); no record is rewritten and no number re-measured.

State: ACCEPTED DESIGN ONLY at this amendment's commit; the pin update
it authorizes is IMPLEMENTED with tests in the next commit of the same
tick (until then the classify self-test stays RED at 36/37, named).
Record: `docs/evidence/gpu/cross-cutting-only-decision-20261025.txt`.

## Amendment 2026-10-25 (the claim-protocol WGSL channel): a host-clock
campaign adopts the protocol, metric-named and sign-scoped

DECIDED (JUN-58, the row the 2026-10-25 wall-clock-row-mapping record's
HONEST LEFT 2 named -- "whether a WGSL measurement under the claim
protocol exists at all (the MSL native-harness idiom for WGSL) is
PROPOSED, not designed; the narrowing's narrowed REOPEN CONDITION waits
on it"). The answer: **YES -- a WGSL measurement under the claim
protocol exists**, by the protocol's own adoption clause ("a later
vendor campaign adopts it by citation, its own row" -- this is that
row), but the adoption is **metric-named and sign-scoped**, because the
adopting channel cannot produce the metric the protocol was written on.
No hardware measurement runs in this slice; the ground is committed
records and committed script text (quoted in the record).

Grounding (facts, not design): the protocol's rule-1 baseline metric
`gpu-ns` is Metal GPU timestamps (the MSL harness's own timer line:
"Metal GPU timestamps (command buffer GPUStartTime->GPUEndTime) around
one reduce dispatch; host submit->completion ns recorded as
secondary"), and the GAP-1.15 clusters are computed over those gpu-ns
baselines. The WGSL Chrome channel has NO GPU timestamps on this
adapter (writeTimestamp refused without
'chromium-experimental-timestamp-query-inside-passes'; no flag exposes
it) -- its only clock is host wall-clock submit->completion. The
committed 2026-10-25 WGSL measure-log publishes NO rule-1
classification (grep -c -i "regime" over it: 0), while every MSL
summary carries the section. So the WGSL channel today is rule-1
EMPTY.

Part 1 -- THE ADOPTION CONTRACT (what makes a WGSL record
claim-protocol):

  (a) Rule 1 carries with the baseline metric NAMED BY THE CHANNEL:
      for the WGSL wall-clock channel the per-run baseline median is
      the channel's own per-run median host submit->completion time per
      operator, and the GAP-1.15 clusters are named in that metric's
      units. The clustering rule is metric-parametric as written
      (single-link over per-run medians; `scripts/gpu_regime_classify.py`
      carries unchanged -- this slice touches no code); only the
      publication names the metric. A claim-protocol WGSL record
      publishes per rule 1: per-run baseline medians per operator in
      the named metric, and the regime clusters.
  (b) Rule 2 carries IN FULL, unchanged: a regime-invariant sign is the
      only selection basis. Sign claims are CHANNEL-SCOPED -- a
      WGSL-channel sign never flips an MSL cell and never answers a
      workgroup row (the mirror of "an MSL measurement never flips a
      WGSL cell") -- and only a WGSL-route cell's own selection
      question consumes it.
  (c) Rule 3 carries with a NAMED LIMIT: magnitude claims stay
      within-channel and regime-matched as written; CROSS-METRIC
      magnitude claims (host-clock vs GPU-timestamp) are INADMISSIBLE.
      Named hazard (design reasoning, NOT a measurement): fixed
      host/queue overhead common to both arms biases paired ratios
      toward 1 -- conservative against win claims (it can hide a real
      win, it cannot invent one through the common part) -- while
      asymmetric arm overhead could bias either way and is not assumed
      away; every magnitude publication on this channel keeps both
      arms' raw per-round times beside the ratios (a record that hides
      them is inadmissible).
  (d) Rule 4 carries unchanged: this adoption measures nothing and
      moves nothing.

Part 2 -- WHAT THE ADOPTION DOES NOT DO: the 2026-10-25 wall-clock
read stays OUT (no rule-1 publication, predates this adoption -- its
parity verdict and its maps-onto-no-row ruling stand); no workgroup
row (ADR-0355/0358), `:measured?` flag, `:shapes` value or selection
answer moves; the dispatch-row channel rule (ADR-0355's 2026-10-25
amendment) is untouched -- a claim-protocol WGSL measurement is CLAIM
currency for the narrowing's route scope and still maps onto no
dispatch row. Two "channels", kept apart on purpose: the row-flip
channel (what evidence may answer a workgroup row) and the
claim-protocol channel (what evidence may carry a sign or magnitude
claim).

Part 3 -- CONSEQUENCE for part 2's narrowing: its REOPEN CONDITION's
first leg ("a claim-protocol WGSL measurement") is now DEFINED and is
REACHABLE on this adapter's host-clock channel; the second leg ("a
GPU-core-timestamp measurement") stays REFUSED here and waits on a
timestamp-capable route (a Vulkan-provider route with timestampValidBits
> 0 or a native Metal counter channel -- UNDESIGNED, its own row).
[DESIGNED 2026-10-25 -- the counter-channel amendment at the end of
this file designs the native Metal counter channel and DECIDES the
second leg's letter (a counters-channel record of the fold arms on the
device satisfies it, MSL-emitted arms named in scope; the WGSL route's
arms are not covered); the Vulkan-provider route stays PROPOSED and
DEFERRED to the ADR 0371 track. The leg still does NOT fire -- it
waits on a measurement row (nothing timed). Record:
`docs/evidence/gpu/metal-counter-channel-design-20261025.txt`.]
Named missing pieces before the first leg can FIRE (each its own later
slice): (i) harness-side rule-1 classification for the WGSL harness --
UNIMPLEMENTED; (ii) a fresh WGSL run of the narrowed device's fold arms
satisfying rules 1 + 2 -- UNMEASURED. UNMEASURED, named so no reading
upgrades: whether the WGSL host-clock baselines cluster into more than
one regime level at all (if single-level, rule 2 degenerates to the
protocol's own single-level standard -- every per-run ratio on one side
of 1.0 -- which the 2026-10-25 read would have FAILED); the sign of any
claim-protocol WGSL run; per-kernel GPU time on this adapter. The
narrowing itself is unchanged: parity is not a fold win, the
conservative `:baseline` answer for the named device stands.
[BOTH MISSING PIECES LAND 2026-10-25 -- (i) harness-side rule-1
classification landed (the amendment below), and rule-2 sign
classification landed with it (`docs/evidence/gpu/
wgsl-rule2-sign-classification-20261025.txt`); (ii) two fresh runs of
the narrowed device's fold arms exist (`docs/evidence/gpu/
wgsl-claimprotocol-run1-20261025`, `...-run2-20261025`), each
publishing rules 1 + 2. The named UNMEASURED question "whether the
WGSL host-clock baselines cluster into more than one regime level at
all" is ANSWERED PER RUN, not generalized: run 1 -- batch32 multi-
level (min 2 levels, boundary 1.1523x; sum 3 levels, boundaries
1.2044x and 1.1590x), single effectively single-level (its sum's
second level is one run n=1000003 W=32 at 1.1809x -- a 1-sample
marginal split, named not read as a regime); run 2 -- 5 of 6
metric/operator level structures differ in level count from run 1
(only single/max is single-level in both), so cross-run regime
stability stays UNMEASURED as a property. "The sign of any
claim-protocol WGSL run" is ANSWERED for these two runs only:
REGIME-SCOPED at every operator and cell in both (see the first-leg
bracket above for the roll-ups).]

State: ACCEPTED DESIGN ONLY (this amendment). IMPLEMENTED: nothing --
no code moves in this slice. MEASURED: nothing -- no hardware ran.
Record: `docs/evidence/gpu/claim-protocol-wgsl-channel-20261025.txt`.

## Amendment 2026-10-25 (WGSL harness rule 1): harness-side rule-1
classification for the WGSL channel is IMPLEMENTED

The adoption's named missing piece (i) -- "harness-side rule-1
classification for the WGSL harness: a run's log/summary must publish
the GAP-1.15 clusters on the WGSL baseline metric" -- lands. The WGSL
measurement harness (scripts/measure-gpu-reduce-wgsl.mjs) now publishes
a "Regime classification (claim protocol rule 1, WGSL wall-clock
channel)" section in its measure-log, computed by
scripts/gpu_regime_classify.py (new `--wgsl-log` route; parse_wgsl_measure_log
/ render_wgsl_rule1_section) from the log's own printed `time` lines, so
the section re-derives from the carrier text exactly. The clustering
mechanism (GAP-1.15, level_clusters) is the MSL channel's, unchanged and
metric-parametric; only the publication names the metric -- host
wall-clock submit->completion, milliseconds, never gpu-ns (pinned by
test). On classifier failure the log prints
`claim-protocol-rule1: UNAVAILABLE -- ... a log without the rule-1
section is NOT a claim-protocol record`; a run cannot silently pass as
claim-protocol.

The run unit the adoption's parenthetical left implicit is now FIXED
mechanically and named in the publication: a run is one cell-arm
sampling block -- (n, W, operator, metric) -- whose per-run median is
the block's median over its paired rounds of host submit->completion
(the measure-log's `time` line); the MSL channel's run is a fresh
process, this channel's is the paired sampling block. single and
batch32 are TWO metrics of the channel (one dispatch per submit vs
amortized over 32 dispatches in one command buffer); each clusters only
its own runs -- never mixed. Rule 2's unit on this channel is NAMED
with it -- the per-run ratio is the block's paired-median ratio (the
`pair` line: median over the block's rounds of subgroup/baseline; the
adoption record's own usage, "its per-run ratios ... 13/36 single and
17/36 batch32 pairs") -- but rule 2's WGSL PUBLICATION stays
UNIMPLEMENTED, its own later slice; the rule-1 section renders no sign
verdict (pinned by test). [SUPERSEDED 2026-10-25 -- rule 2's WGSL
PUBLICATION is IMPLEMENTED (code + tests: render_wgsl_sign_section in
`scripts/gpu_regime_classify.py`, the combined `--wgsl-log`
publication; `docs/evidence/gpu/wgsl-rule2-sign-classification-20261025.txt`
-- the slice named as "its own later slice" above). The pinned
boundary still holds exactly as written: the rule-1 SECTION itself
renders no sign verdict; rule 2 publishes in its own section beside
it. Both claim-protocol runs' rule-2 verdicts and the first-leg
evaluation are bracketed above. Also superseded in this State
paragraph's plain reading: its named UNMEASURED "the WGSL baseline
metric's regime structure; any claim-protocol WGSL run's sign" --
answered per-run by `wgsl-claimprotocol-run1-20261025` and
`...-run2-20261025` (structure per run as bracketed; both runs'
signs REGIME-SCOPED everywhere), while cross-run regime stability as
a property stays UNMEASURED. Per-kernel GPU time and every
workgroup-row question stay UNMEASURED as written; rule 4 unchanged.]

Deliberate boundary, named in code and tests: the classifier is never
run over the committed 2026-10-25 pre-adoption measure-log's values.
That record stays OUT of the claim protocol and the named UNMEASURED
question (do the WGSL host-clock baselines cluster into more than one
regime level at all) is answered only by the fresh claim-protocol run
of missing piece (ii). The corpus self-test checks that log's structure
only and pins that it still carries no regime section.

State, precisely: IMPLEMENTED (code + tests: gpu_regime_classify.py
--self-test GREEN at 2413 assertions, 0 failed -- +97 over the 2316
baseline: 15 WGSL unit fixtures and 82 structure-only corpus
assertions; the MSL corpus regression unchanged and green). ACCEPTED
DESIGN ONLY: the channel adoption and the run/ratio unit definitions
(this amendment). MEASURED: nothing -- no hardware ran in this slice;
every number is tool output or committed record text. UNMEASURED,
unchanged: the WGSL baseline metric's regime structure; any
claim-protocol WGSL run's sign; per-kernel GPU time; every workgroup-row
question. Rule 4 unchanged: no `:measured?` flag and no workgroup row
moves. Not run this slice, named: the scoped GPU gate and the full
suite (this diff touches no `.cljk` namespace; the tick's run-time
budget expired after the self-test/CLI verification) -- no green suite
is claimed and the documented red-at-base is not re-verified here.

Record: `docs/evidence/gpu/wgsl-rule1-classification-20261025.txt`.

## Amendment 2026-10-25 (the kernel-time channel: the native Metal counter-sample channel is DESIGNED, and the reopen's second leg becomes REACHABLE)

DECIDED (JUN-58, HONEST LEFT 1 of the wall-clock-row-mapping record:
"A Vulkan-provider route with timestampValidBits > 0, or a native
Metal counter channel, is UNDESIGNED here -- a design row of its
own"). ONE design slice: NO performance measurement ran and nothing
is timed; the only hardware answers are live route-capability probes
of this host (the fact class the gpu-timestamp-route-probe record
established).

**The decision.** The native Metal counter-sample channel (the
"counters" channel) is DESIGN-ADOPTED as the claim-protocol
GPU-core-timestamp measurement channel on the narrowed device's host:
per-dispatch GPU-core time of one reduce dispatch, in GPU
nanoseconds, as the delta of two `GPUTimestamp` counter samples
bracketing the dispatch inside the compute encoder
(`sampleCountersInBuffer:atSampleIndex:withBarrier:` before and after;
`resolveCounters:inRange:destinationBuffer:destinationOffset:` to
resolve, then read back). The bracket substitutes for the unavailable
dispatch-boundary sampling point -- MEASURED route fact (probe,
verbatim in the record): this M1 Max exposes exactly one counter set
`timestamp` (one counter, `GPUTimestamp`, GPU ns),
`MTLCounterSamplingPointAtDispatchBoundary` unsupported (0),
`AtStageBoundary` supported (1), a sample buffer over the set creates
OK. Whether the sample-pair delta equals the dispatch's GPU time or
carries sampling/barrier overhead is UNMEASURED -- the measurement
row's own calibration question.

**Claim-protocol fit.** Rules 1-4 carry in full. Rule 1's baseline
metric `gpu-ns` is this channel's NATIVE metric (no metric renaming,
unlike the WGSL wall-clock adoption). Rule 2 signs stay
CHANNEL-SCOPED. Rule 3: magnitudes stay within-instrument -- the
counters channel is its own instrument and merges with NEITHER the
command-buffer `GPUStartTime->GPUEndTime` bracket (the MSL campaign's
gpu-ns source) NOR any host wall-clock (all three say "ns" and are
still three instruments). Rule 4 unchanged.

**Second-leg letter DECIDED.** A counters-channel record of the fold
arms on the narrowed device satisfies the second leg's letter ("a
GPU-core-timestamp measurement of the device"): the part-3
parenthetical above already contemplates a NON-Chrome route
("Vulkan-provider ... or a native Metal counter channel") as what the
leg waits on, and the letter is device-keyed, not route-keyed. Scope
named with the decision: the channel answers for the MSL-EMITTED arms
of the same KIR reduce shape; the WGSL route's arms are NOT covered
(Chrome owns its command buffers; the WebGPU timestamp routes are
CLOSED by the 2026-10-25 probe) and the WGSL channel's own per-kernel
GPU time stays UNMEASURED until a Vulkan-provider timestamp route
exists. Whether the leg's EVALUATION reaches the narrowing's
route-scope question from an MSL-route counters record is named as the
evaluation row's question, not pre-answered here. The leg does NOT
fire from this row: a leg fires on a measurement and nothing is
measured here.

**Rejected / deferred, named.** (a) Vulkan timestamp queries
(`VK_QUERY_TYPE_TIMESTAMP` through the wire-42 runtime route) --
DEFERRED, PROPOSED (neither implemented nor accepted): the loader's
broker is gone and the ADR 0371 provider is not implemented; it stays
the runtime-side successor, its own row when a provider answers (this
record does not decide it). (b) Chrome/Dawn `writeTimestamp` routes --
CLOSED (probe, cited). (c) WebGL2 `EXT_disjoint_timer_query_webgl2` --
rejected again (GL/ANGLE channel, different execution path). (d) The
command-buffer `GPUStartTime->GPUEndTime` bracket AS the kernel-time
answer -- rejected (a buffer bracket is not a kernel bracket); it
remains the MSL campaign's valid metric source. (e) Counters-channel
timing of the WGSL route's arms -- impossible (Chrome owns its command
buffers).

**What a future measurement licenses / never licenses.** Its own
later row; on landing: evaluation of the second leg against its own
rules-1+2 record, and the arm-vs-arm GPU-core speed answer for the
MSL-route fold arms on the narrowed device class (channel- and
device-scoped). Never: any ADR-0355 workgroup row (the 2026-10-25
channel-rule amendment -- this channel is neither the wire-42 loader
path nor its provider successor), any WGSL-channel cell flip, any
`:measured?` movement by itself (rule 4), any cross-instrument
magnitude claim.

**States.** DECIDED: this row (the channel + contract + the
second-leg letter + rejections). IMPLEMENTED: nothing (no code moved;
the harness is its own later row; the probe lived in Hermes scratch,
never staged). MEASURED: route-capability facts only (the probe
block). ACCEPTED DESIGN ONLY: the claim protocol and its units; the
narrowing and reopen condition; ADR-0355's channel rule. PROPOSED:
the Vulkan-provider timestamp route. UNMEASURED, named: every
per-dispatch GPU time (nothing timed); the sample-bracket calibration;
`GPUTimestamp` resolution and clock-domain behavior under regimes; the
sign of any counters-channel arm pair; whether the second leg fires;
anything off M1 Max; the WGSL route's kernel time; every workgroup-row
question (`:arm`/`:unknown` stay provisional `:measured? false` -- no
`:measured?` flag, `:shapes` value, selection answer or workgroup row
moves). Gates: scoped GPU gate GREEN 109 tests / 11434 assertions / 0
failures / 0 errors (docs-only diff, regression pin at the committed
109/11434); `gpu_regime_classify.py --self-test` GREEN 2572
assertions / 0 failed (unchanged); FULL
`run-tests.cljk` NOT RUN this slice (docs-only), documented red at
base ("Could not find namespace: kotoba.form", ADR-0362), no green
suite claimed; `find docs -name '*.sh'` -> 0 files.

Record: `docs/evidence/gpu/metal-counter-channel-design-20261025.txt`.
