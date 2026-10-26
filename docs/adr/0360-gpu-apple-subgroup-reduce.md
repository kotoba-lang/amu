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

## Amendment 2026-10-25 (the kernel-time channel's harness row): the bracket method is CORRECTED -- the letter's compute-encoder sampling call is REFUTED on the narrowed device's host, and the harness lands on the AtStageBoundary route

ONE implementation slice (JUN-58): the counters channel's harness is
IMPLEMENTED, and the design letter's bracket METHOD is corrected where it
was measured to be wrong. NO arm-vs-arm measurement ran and nothing is
timed; every number is a route-capability probe or the instrument's own
smoke run.

**The refutation (MEASURED).** The letter above adopts "the delta of two
`GPUTimestamp` counter samples bracketing the dispatch inside the compute
encoder (`sampleCountersInBuffer:atSampleIndex:withBarrier:` before and
after...)". That method is UNENCODABLE on the narrowed device's host: the
Metal framework asserts
"`MTLComputeCommandEncoder:sampleCountersInBuffer:atSampleIndex:withBarrier
not supported on this device`" and aborts the process at encode time
(SIGABRT) -- the SDK ties the method to
`MTLCounterSamplingPointAtDispatchBoundary`, which this M1 Max does not
support. The full five-point sampling matrix is now MEASURED
(dispatch=0 stage=1 draw=0 tile=0 blit=0): exactly one point exists here,
`AtStageBoundary`, and the blit-encoder fallback route is closed with it.
This amends the letter's METHOD only; the letter's fact block already
recorded `AtDispatchBoundary = 0`, and the bracket survives the amendment
unchanged.

**The corrected carrier (DECIDED).** The pair brackets the dispatch at the
device's supported sampling point: one dispatch per compute encoder created
from `MTLComputePassDescriptor`, the attachment carrying the timestamp
sample buffer with `startOfEncoderSampleIndex=0` /
`endOfEncoderSampleIndex=1` (MTLComputePass.h: the samples "taken at the
start/end of command encoder processing", valid iff `AtStageBoundary` is
supported), resolved through the blit encoder's
`resolveCounters:inRange:destinationBuffer:destinationOffset:` and read
back as two `MTLCounterResultTimestamp` uint64 values. Probe-verified on
this host (6/6 brackets resolved, non-error pairs, positive deltas --
instrument verification of a trivial kernel, not a measurement of
anything). The delta's span is now precisely named: [encoder start,
encoder end] around a single dispatch -- so the letter's open calibration
question ("whether the sample-pair delta equals the dispatch's GPU time or
carries sampling/barrier overhead") narrows to the encoder-boundary
residual and stays UNMEASURED, the measurement row's own question.

**The harness (IMPLEMENTED: code + tests).**
`scripts/gpu-subgroup-reduce-metal-counters.m` -- the counters-channel
instrument, carrying the MSL campaign instrument's ADR-0358 protocol and
argv contract unchanged, the metric source replaced by the corrected
bracket (`sample ... ts0=.. ts1=.. counter_ns=..`, ERR on an unresolved
sample). Its source pin
(`the-counters-harness-brackets-through-the-stage-boundary-pass-attachment`)
keeps the refuted message-send form out of the instrument, the working
bracket markers in it, the command-buffer bracket (`GPUStartTime`/
`GPUEndTime`) banned (rule 3: three instruments, never merged), and the
misshape argv-gate class pinned out. A smoke run over the committed
metallibs resolved 120/120 brackets and verified read-back on all three
operators (instrument verification only -- no sign is read, no speed
question is answered).

**States.** DECIDED (this row: the corrected bracket method + the named
residual). IMPLEMENTED: the harness + its pin. MEASURED: route-capability
facts only (the five-point matrix, the refutation's verbatim abort, the
bracket resolutions, the smoke's plumbing lines) -- NO performance
measurement. ACCEPTED DESIGN ONLY: the claim protocol and its units; the
narrowing and reopen condition; the second-leg letter (unchanged -- the
letter is method-agnostic by its own words, "device-keyed, not
route-keyed"). PROPOSED (unchanged): the Vulkan-provider timestamp route.
UNMEASURED, named: the sample-bracket calibration (the encoder-boundary
residual), `GPUTimestamp` resolution and clock-domain behavior, the sign
of any counters-channel arm pair, every per-dispatch GPU time of the fold
arms, whether the second leg fires, anything off M1 Max, the WGSL route's
kernel time, every workgroup-row question (`:arm`/`:unknown` stay
provisional `:measured? false` -- no `:measured?` flag, `:shapes` value,
selection answer or workgroup row moves this tick). Rule 4 unchanged.

Gates: scoped GPU gate GREEN 110 tests / 11445 assertions / 0 failures /
0 errors (run 1 red at one pin assertion -- the pin initially matched
prose naming the refused selector; comment text is not code, the pin now
matches the message-send form); FULL `run-tests.cljk` RED at base
("Could not find namespace: kotoba.form", ADR-0362), re-verified since
the diff touches a `.cljk` namespace, no green suite claimed;
`gpu_regime_classify.py --self-test` GREEN 2572 / 0 (unchanged);
`find docs -name '*.sh'` -> 0.

Record: `docs/evidence/gpu/metal-counter-channel-harness-20261025.txt`.

## Amendment 2026-10-25 (the sample-bracket calibration row): the letter's question is ANSWERED -- the delta carries a MEASURED additive residual, and GPUTimestamp quantizes at 125/3 ns

ONE measurement slice (JUN-58): the instrument's own calibration on
synthetic kernels through the harness's exact bracket. The harness row's
UNMEASURED "sample-bracket calibration (the encoder-boundary residual)"
is RESOLVED on this host, and the named "GPUTimestamp resolution" is
MEASURED. NO arm is timed, NO reduce kernel runs, and no speed question
is answered.

**The answer (MEASURED).** counter_ns = [encoder start, encoder end] =
T_dispatch + R(grid shape, state) + epsilon: the delta does NOT equal
the dispatch's pure GPU time. At the fold arms' launch shape (3907 x
256 threads = (1000003+255)/256 at WG=256), R ~= 7.83-8.00 us WARM and
20.6-20.8 us COLD (medians of 12 brackets each); at 1x1, 4.21 us warm /
9.75-9.79 us cold; a zero-groups encoded dispatch ~0.98-1.00 us warm /
1.83-1.88 us cold. The two arms' launch shapes (baseline arm threadgroup
memory WG*4 = 1024 bytes vs subgroup arm 0) differ by 166.5 ns warm /
187 ns cold -- bounded within the spread, NOT zero-claimed. The spin
series (v1, 20 recorded rounds x 9 work levels) is linear in work plus a
floor: low-band fit F = 4417.7 ns, c = 28.5515 ns/iter (top levels bend
28.55 -> 28.64). State dependence: cold is 1.9x-2.6x warm on every
shape; the CAUSE (GPU power/clock ramp) is a hypothesis -- no probe
reads a clock -- and the work threshold that flips the state is
UNMEASURED (48 zero-work grid launches did not; one ~490 ms dispatch
did). GPUTimestamp quantizes at 125/3 ns = 41.667 ns: 776 raw ts values
(cold and warm) sit within 0.651 ns of that lattice with the truncation
signature {0.041, 0.326, 0.651}; 381 fresh deltas within 0.667 ns. A
bracket with no dispatch writes NO samples (2 unwritten / 28 stale
pairs across 30 attempts) -- the one-dispatch-per-encoder contract is
load-bearing. The absolute clock-domain calibration stays UNMEASURED
(rule 3 bars the host-clock merge).

**States.** MEASURED: the residual at four launch shapes x cold/warm,
the spin line, the tick lattice, the staleness counts, the spike list
(single-bracket outliers named in the record). DECIDED: the letter's
question at its narrowed form. IMPLEMENTED: nothing (probe sources
scratch-only, never staged; docs-only diff). ACCEPTED DESIGN ONLY
(unchanged): the claim protocol, the narrowing, the second-leg letter.
PROPOSED (unchanged): the Vulkan-provider timestamp route. UNMEASURED,
named: the residual's internal decomposition; the clock-domain
calibration; the state-flip work threshold; R off M1 Max / under
throttle / at other grids; the fold arms' times and every sign; the
rules-1+2 publication (the classifier's counters route is still
UNIMPLEMENTED); whether the second leg fires; every workgroup-row
question (`:arm`/`:unknown` stay provisional `:measured? false` -- no
`:measured?` flag, `:shapes` value, selection answer or workgroup row
moves this tick). Rule 4 unchanged.

Gates: scoped GPU gate GREEN 110 tests / 11445 assertions / 0 failures
/ 0 errors (docs-only, regression pin); `gpu_regime_classify.py
--self-test` GREEN 2572 / 0 (unchanged); FULL `run-tests.cljk` NOT RUN
this slice (docs-only), documented red at base ("Could not find
namespace: kotoba.form", ADR-0362), no green suite claimed;
`find docs -name '*.sh'` -> 0.

Record: `docs/evidence/gpu/metal-counter-bracket-calibration-20261025.txt`
(+ raw logs in `docs/evidence/gpu/metal-counter-bracket-calibration-20261025/`).

## Amendment 2026-10-25 (the counters channel's classifier-route row): the rules-1+2 machinery lands BEFORE any fold-arms measurement runs

ONE implementation slice (JUN-58): the counters channel's
rules-1+2 publication route lands in `scripts/gpu_regime_classify.py`
(`--counters-log`, one log per fresh process, one cell per session) --
the harness row's named missing piece "the rules-1+2 publication over
this channel's own metric (the classifier's counters route does not exist
yet)". NO hardware ran and nothing is timed; every fixture number is
synthetic. The row runs BEFORE the measurement on the CUDA track's
registration order (rows (ii) before (iii)): a session analyzed by code
written after the fact is not a pre-registered analysis.

The route publishes rule 1 (per-run baseline medians of counter_ns, the
channel's own metric with the calibration row's MEASURED residual named
in the metric text and never subtracted) and rule 2 (the run's
paired-median ratio variant_ns/baseline_ns, never re-oriented;
regime-matched sign per level; channel-scoped sign claims) with GAP-1.15
carried unchanged. Named fail-closed readings (the CUDA block model): a
(run, operator) block is usable only when complete, correctness-
verified (both `verify` lines ok=1), every bracket resolved and
positive, and no sample re-reads an earlier bracket's raw pair (the
calibration row's staleness signature); anything else is named and
excluded; structural corruption raises ValueError. Tests:
`--self-test` GREEN 2617 assertions / 0 failed (committed pin 2572/0,
delta +45; run 1 red at one wrong test matcher, named in the record).

States: IMPLEMENTED (code + tests): the route. DECIDED: the fail-closed
readings; the run unit (one fresh process per log, one cell per
session); rule 2's unit. MEASURED: nothing. ACCEPTED DESIGN ONLY
(unchanged): the claim protocol, the narrowing, the second-leg letter,
ADR-0355's channel rule. PROPOSED (unchanged): the Vulkan-provider
timestamp route. UNMEASURED, named: every counters-channel per-dispatch
GPU time and every arm-pair sign (the fold-arms measurement row has not
run); rules 1+2 ON REAL DATA; whether the second leg fires; anything off
M1 Max; every workgroup-row question (`:arm`/`:unknown` stay provisional
`:measured? false` -- no `:measured?` flag, `:shapes` value, selection
answer or workgroup row moves this tick). Gates: `--self-test` GREEN
2617/0 (real run); scoped GPU gate NOT RUN (session budget -- the diff
touches no `.cljk` namespace, the committed 110/11445 pin is
unre-verified and named NOT green); FULL `run-tests.cljk` NOT RUN
(documented red at base, ADR-0362), no green suite claimed;
`find docs -name '*.sh'` -> 0.

Record: `docs/evidence/gpu/metal-counter-classifier-route-20261025.txt`.

## Amendment 2026-10-25 (the counters channel's fold-arms MEASUREMENT row): rules 1+2 publish on real hardware, and the fold-arm sign is regime-invariant slower at the anchor cell

ONE measurement slice (JUN-58): the fold arms run on the counters
channel for the first time -- 6 fresh ADR-0358 processes at cell
(n = 1000003, W = 256) on this host's Apple M1 Max, the instrument's
20 interleaved AB/BA pairs per operator per run, WARMUP=2 discarded,
correctness re-verified inside every measurement (36/36 `verify` lines
ok=1, 720/720 brackets resolved, zero named exclusions). The run
protocol was declared in the record directory before the first run
(`protocol.txt`); the analysis is ONLY the pre-committed route
(`--counters-log`), so the counter-route row's registration order
survives. The metric is counter_ns bracket deltas (raw pairs on every
sample line); the calibration row's MEASURED residual is named and
never subtracted.

THE FINDING (the publication is `publication.txt`, byte-for-byte
pinned in the corpus self-test): rule 1 clusters the 6 runs' baseline
medians as sum ONE level (103458.5..103813.0), max and min TWO levels
(run 5 alone fast at 54187.5/54250.0, runs 1,2,3,4,6 slow at
~103.6k..103.9k). Rule 2 answers REGIME-INVARIANT, SLOWER at every
operator and at the cell -- all 18 per-run paired-median ratios
(variant_ns/baseline_ns, never re-oriented) above 1.0, band
1.204..1.221, every observed regime one-sided, roll-up "18/18 slower".
The verdict holds in BOTH observed counter states (fast level
1.204-1.206, slow level 1.217-1.219). The sign is CHANNEL-SCOPED: it
never flips an MSL command-buffer cell, never flips a WGSL cell and
never answers a workgroup row.

STATE OBSERVATION (MEASURED; cause stays a hypothesis): the counter_ns
plateau shifts MID-RUN at this workload -- run 5's sum block walked
103.8k -> 84k -> 64k and its max/min blocks ran at ~54k; run 6's sum
block shifted to 64k and its max/min blocks RETURNED to ~103.7k (not
monotonic). The calibration row's question "whether the fold arms' own
dispatches at their workload cross that threshold" is answered as an
OBSERVATION: yes, sometimes; no clock is read and the threshold stays
UNMEASURED. Cross-channel context, never merged (rule 3): the MSL
command-buffer record at the same cell (1.220/1.217/1.217) reports the
same sign and near-identical bracket ratios -- corroboration context
only.

CONSEQUENCE (rule 4, unchanged): nothing moves -- no `:measured?` flag,
no `:shapes` value, no selection answer, no workgroup row; the
narrowing stands (parity is not a fold win). The second leg's LETTER
CONDITION now EXISTS (a counters-channel record of the fold arms on the
narrowed device); its EVALUATION (including whether it reaches the
narrowing's route-scope question from an MSL-route counters record) is
its own next row and nothing fires here beyond the record.
[SECOND LEG EVALUATED 2026-10-25 -- the leg FIRES (the first-leg
bracket's fire criterion: letter condition met AND a regime-invariant
sign present -- this record carries 18/18 slower, band 1.204..1.221,
every observed regime one-sided), and the evaluation answers the named
question SPLIT: the device-level premise (is the fold refuted on the
device?) is REACHED and CONFIRMED -- a third instrument of the same
device measures the same sign on GPU-core timestamps, the metric class
the leg waited for -- while the route-level residual (the WGSL-spelled
arms' own GPU-core behavior) is NOT REACHED and is unreachable from
this channel (the letter's scope, "the WGSL route's arms are NOT
COVERED"; rule 2's channel scoping; Chrome owns its command buffers).
CONSEQUENCE: the narrowing's route scope STANDS -- the revisit confirms
part 2's WGSL ride-along, nothing moves (rule 4). Both legs now carry
evaluations (first leg: evaluated, did not fire; second leg: fired,
confirm verdict); the reopen condition stays in force as narrowed and
this record is spent as a trigger -- a future revisit needs NEW
evidence (a claim-protocol WGSL sign that is regime-invariant, an
opposing counters-channel sign, or a WGSL-arm GPU-core measurement
waiting on the Vulkan-provider route). Full decision:
docs/evidence/gpu/second-leg-evaluation-20261025.txt and the amendment
at the end of this file.]

States: MEASURED (this row): the 6-run record, rule 1's clusters, rule
2's sign, the mid-run state shifts, the spike list. IMPLEMENTED (code +
tests): `_self_test_counters_corpus`, the corpus join this row's
predecessor named for this slice (parse pins + cluster/verdict pins +
byte-for-byte publication reproduction). DECIDED: the run protocol as
declared. ACCEPTED DESIGN ONLY (unchanged): the claim protocol, the
narrowing and reopen condition, the second-leg letter, ADR-0355's
channel rule. PROPOSED (unchanged): the Vulkan-provider timestamp
route. UNMEASURED, named: every other W and shape 2 on this channel
(and R at those grids); the residual's decomposition and the absolute
clock domain; the state-shift cause and threshold; op-order dependence;
cross-day replication of this cell; anything off M1 Max; the second
leg's EVALUATION; every workgroup-row question (`:arm`/`:unknown` stay
provisional `:measured? false` -- no `:measured?` flag, `:shapes` value,
selection answer or workgroup row moves this tick; this channel can
never move one). Gates: `--self-test` GREEN 2649/0 (pin 2617/0, delta
+32 = the corpus join); scoped GPU gate GREEN 110 tests / 11445
assertions / 0 failures / 0 errors (re-verifies the pin the previous
tick left unre-verified; no `.cljk` namespace touched); FULL
`run-tests.cljk` NOT RUN (no `.cljk` touched; documented red at base,
ADR-0362), no green suite claimed; `find docs -name '*.sh'` -> 0.

Record: `docs/evidence/gpu/metal-counter-foldarms-20261025/`
(`protocol.txt`, `run-1.txt`..`run-6.txt`, `publication.txt`,
`record.txt`).

## Amendment 2026-10-25 (the second leg's EVALUATION): the leg FIRES at its letter, the route-scope question is answered SPLIT -- device premise CONFIRMED, route residual unreachable -- and the narrowing STANDS

ONE decision/analysis slice (JUN-58): the reopen's second leg is
EVALUATED against the committed 6-run counters record -- the fold-arms
measurement row's own named next row ("its EVALUATION ... is its own
next row"). NO hardware ran and nothing is re-measured; the record is
consumed through the pre-committed route only, which reproduces the
committed `publication.txt` BYTE-FOR-BYTE this tick
(`--counters-log run-1..6.txt | diff - publication.txt` ->
DIFF-IDENTICAL, exit 0 -- tool output in the record).

**The leg FIRES.** The fire criterion is the first-leg bracket's own
committed reading: the first leg "does NOT FIRE: neither run carries a
regime-invariant sign" -- a leg fires when its letter condition is met
AND its record carries a regime-invariant rule-2 sign. Both hold: the
letter condition ("a counters-channel record of the fold arms on the
narrowed device") exists, and the record's verdict is REGIME-INVARIANT
SLOWER (18/18 per-run paired-median ratios above 1.0, band
1.204..1.221, every observed regime one-sided). The reopen's revisit
of the narrowing's route scope happens now.

**The evaluation's named question, answered SPLIT.** "Whether the
leg's evaluation reaches the narrowing's route-scope question from an
MSL-route counters record": (2a) the DEVICE-LEVEL PREMISE (is the fold
refuted on the device?) is REACHED and CONFIRMED -- part 2's ride-along
decides on exactly this premise ("the refutation is of the FOLD on that
device ... the refuted variant is not selected on the device that
refuted it on any route that spells the same fold"), and the counters
record measures the same fact on a THIRD instrument of the same device,
on GPU-core timestamps -- the metric class the leg waited for -- with
the same sign as both prior arms; (2b) the ROUTE-LEVEL RESIDUAL (is
the WGSL-spelled fold also slower on this device?) is NOT REACHED and
is unreachable from this channel: the letter's own scope ("the WGSL
route's arms are NOT COVERED"), rule 2's channel scoping ("a
counters-channel sign never flips a WGSL cell"), and the physical
route (Chrome owns its command buffers; WebGPU timestamp routes CLOSED
by probe; letter rejection (e)). It stays UNMEASURED until a
Vulkan-provider timestamp route exists (PROPOSED, DEFERRED to the ADR
0371 track).

**Consequence: the narrowing's route scope STANDS.** The revisit
CONFIRMS part 2's WGSL ride-along at the layer the letter lets this
record answer and contradicts nothing: the "m1 max" descriptor keeps
answering `:baseline` on the WGSL route too (conservative answer;
`:measured-cell` records stay MSL-scoped; every WGSL answer keeps
`:measured? false`). Rule 4: NOTHING MOVES -- no `:measured?` flag, no
`:shapes` value, no selection answer, no workgroup row (this channel
can never move one), no WGSL cell flip, no cross-instrument magnitude
claim.

**Reopen condition status.** BOTH legs now carry an evaluation (first
leg: evaluated 2026-10-25, did NOT fire -- both claim-protocol WGSL
runs REGIME-SCOPED everywhere; second leg: FIRED this row, confirm
verdict). The reopen condition stays in force as narrowed; the
anchor-cell counters record is spent as a trigger (one visit per
record). A FUTURE revisit needs NEW evidence, named fail-closed: a
claim-protocol WGSL measurement carrying a REGIME-INVARIANT sign (the
first leg can still fire); a counters-channel record carrying an
OPPOSING device-level sign (another cell/W, or a cross-day replication
of the anchor cell contradicting it -- cross-day replication is
UNMEASURED); a WGSL-arm GPU-core-timestamp measurement (waits on the
Vulkan-provider route).

Named, not hidden: the fired record is ONE cell (n = 1000003, W = 256)
on ONE day on ONE device -- the confirm verdict is scoped to that
coverage; the mid-run counter_ns state shifts do not touch the verdict
(rule 2 held in both observed states); the calibration residual R stays
named and never subtracted (design reasoning: it compresses ratios
toward 1, so the slower sign is if anything understated -- not a
measurement); the counterfactual the fire criterion covers is named
(an opposing regime-invariant sign would have forced the route-scope
question open adversarially -- closed by measurement); no number is
read across instruments (rule 3).

States: DECIDED (this row: the evaluation, the split answer, the
confirm verdict, the reopen status and the named future-revisit
conditions). MEASURED: nothing new (NO hardware ran). IMPLEMENTED:
nothing (docs-only). ACCEPTED DESIGN ONLY (unchanged): the claim
protocol, the narrowing (now evaluated on both legs) and the reopen
condition, the second-leg letter, ADR-0355's channel rule. PROPOSED
(unchanged): the Vulkan-provider timestamp route. UNMEASURED, named:
the WGSL-spelled arms' GPU-core behavior; cross-day replication of the
anchor cell; every other W and shape 2 on this channel; the residual's
decomposition and the absolute clock domain; the state-shift cause and
threshold; op-order dependence; anything off M1 Max; every workgroup-row
question (`:arm`/`:unknown` stay provisional `:measured? false` -- no
`:measured?` flag, `:shapes` value, selection answer or workgroup row
moves this tick). Gates: see the record (self-test and scoped gate are
regression pins for this docs-only diff; FULL `run-tests.cljk` NOT RUN,
documented red at base "Could not find namespace: kotoba.form"
(ADR-0362), no green suite claimed; `find docs -name '*.sh'` -> 0).

Record: `docs/evidence/gpu/second-leg-evaluation-20261025.txt`.

## Amendment 2026-10-26 (the counters channel's CROSS-DAY REPLICATION
row): the anchor cell's sign REPRODUCES on day 2 (regime-invariant,
slower, 18/18) and the rule-1 regime structure does NOT -- the
state-shift class is day-variable

ONE measurement slice (JUN-58): the anchor record's own named
UNMEASURED item -- "cross-day replication of this cell" -- is CLOSED BY
MEASUREMENT at one additional day, and the second-leg evaluation's
named future-revisit trigger class ("a cross-day replication of the
anchor cell contradicting it") is adjudicated: the replication does NOT
contradict. HARDWARE RAN: 6 fresh ADR-0358 processes at the anchor
cell (n = 1000003, W = 256) on this M1 Max, run window
2026-10-26T19:23:48Z..19:23:49Z (run-window.txt, verbatim) against the
anchor record's 2026-10-25 UTC runs -- different UTC days at the
protocol's letter. The run protocol is the anchor row's, unchanged;
predictions P0..P6 were registered in `protocol.txt` BEFORE the first
run.

**The realization control (P0a HOLD).** The arms and instrument were
rebuilt this row from the COMMITTED emitters into a fresh build dir and
sha256-compared against the anchor row's build: 8/8 files IDENTICAL
(6 metallibs + probe.metallib + the counters binary itself,
4cb76bdc..). The realization is held fixed across the two days, so
every difference below is run/day level.

**The named question, answered: the sign REPRODUCES (P2a HOLD).**
Rule 2 at its letter over day-2 data: REGIME-INVARIANT, SLOWER at every
operator and the cell -- all 18 per-run paired-median ratios above 1.0
(sum 1.214..1.221, max 1.197..1.220, min 1.198..1.222), every observed
regime one-sided, roll-up "regime-invariant, slower (18/18 slower)".
The anchor cell's device-level sign holds on the second day; the
registered adversarial branch (P2b -- an OPPOSING device-level sign
firing the reopen condition) did NOT occur. The reopen condition is NOT
triggered; the narrowing's route scope STANDS. Magnitude (P3): the
day-2 band overlaps the anchor band (1.204..1.221) -- stable -- and the
anchor's ratio-vs-state pattern reproduces (fast-state ratios slightly
lower, still the slower side: day-2 fast 1.197..1.212 vs slow
1.216..1.222).

**The regime structure does NOT reproduce (P4, named).** Day 2 shows
FOUR rule-1 levels at max (32937.5 / 53958.0 / 78541.5 /
103521.0..103583.5) and FOUR at min (32917.0 / 42708.0..42854.5 /
83687.5 / 103520.5) against the anchor's TWO (one fast run ~54k, the
slow ~103.6k level); sum reproduces ONE level both days. The state-shift
class is DAY-VARIABLE and stronger on day 2 (faster levels than the
anchor ever saw), and the arm-pair sign is invariant across every
observed state. Raw-log observations (P5, named, never explained):
mid-run plateau walks reproduce (run-2's min baseline block walks
103.5k -> 83.5k -> 63.8k/64.0k -> 83.5k; run-4's max block flat fast
~32.9k for all 20 pairs); the one-bracket spike class reproduces at
reduced frequency (5 samples >= 200k, largest 721583, against the
anchor's ~200k-871k class). The cause stays the calibration row's
hypothesis; the threshold and the day-to-day prevalence stay UNMEASURED.

**Consequence.** Rule 4: NOTHING MOVES -- no `:measured?` flag, no
`:shapes` value, no selection answer, no workgroup row (this channel
can never move one), no WGSL cell flip, no MSL command-buffer cell
flip, no cross-instrument magnitude claim. The sign stays
CHANNEL-SCOPED and M1-Max scoped. Reopen condition status: unchanged
and NOT triggered by this record; the future-revisit list keeps its
shape (a claim-protocol WGSL measurement carrying a regime-invariant
sign; a counters-channel record carrying an OPPOSING device-level sign
at any cell/W/day; a WGSL-arm GPU-core-timestamp measurement waiting on
the Vulkan-provider route) -- this replication record carries no
opposing sign and is not a trigger.

Named, not hidden: the rule-1 divergence is real (the states did not
reproduce; the sign did); day 3+ replications are UNMEASURED -- the
closure is scoped to one additional day; the run window is one second
of wall clock (the instrument's dispatches are tiny; wall time is no
metric); the realization control's own artifact (build-shas.txt) is
committed as a .txt log.

States: MEASURED (the cross-day replication record: 720 resolved
brackets, the realization control, rule 2's cross-day reproduction,
rule 1's non-reproduced regime structure, the walk/spike
observations). IMPLEMENTED: nothing (evidence + prose only). DECIDED:
nothing new (the protocol is the anchor row's). ACCEPTED DESIGN ONLY
(unchanged): the claim protocol and its units; the narrowing and reopen
condition; the second-leg letter; ADR-0355's channel rule. PROPOSED
(unchanged): the Vulkan-provider timestamp route. UNMEASURED, named:
day 3+ cross-day replications; every other W and shape 2 on this
channel (and R at those grids); the residual's decomposition and the
absolute clock domain; the state-shift cause, threshold and prevalence;
op-order dependence; anything off M1 Max; the WGSL route's kernel time;
every workgroup-row question (`:arm`/`:unknown` stay provisional
`:measured? false` -- no flag, shape, selection answer or workgroup row
moves this tick).

Gates: see the record (self-test 2649/0 pin; scoped GPU gate GREEN
123/12162 twice; FULL `run-tests.cljk` RUN LIVE, red at base "Could not
find namespace: kotoba.form" (ADR-0362), outside this diff, no green
suite claimed; `find docs -name '*.sh'` -> 0).

Record: `docs/evidence/gpu/metal-counter-foldarms-crossday-20261026/`.

## Amendment 2026-10-26 (the counters channel's W-GRID row): the first
off-anchor cell (W = 32) answers the sign's W-dependence -- the sign is
W-DEPENDENT, and op=sum FLIPS side across W (regime-invariant faster at
W = 32 against regime-invariant slower at W = 256)

ONE measurement slice (JUN-58): the anchor record's own named
UNMEASURED item -- "every other W (32/64/128/512/1024) and shape 2
(n = 2^20) on this channel (R at those grids is unmeasured too)" --
taken ONE CELL AT A TIME at the route's own unit; this row takes the
list's FIRST width: (n = 1000003, W = 32). HARDWARE RAN: 6 fresh
ADR-0358 processes at that cell on this M1 Max, run window
2026-10-26T20:03:19Z..20:03:20Z (run-window.txt, verbatim) -- the same
UTC day as the cross-day row (named; this row makes NO day claim of any
kind; it is a W row). The run protocol is the anchor row's, unchanged
(6 fresh processes, 20 interleaved AB/BA pairs per operator, WARMUP=2
discarded, verified read-back, op-order sum,max,min fixed);
predictions P0..P3 were registered in `protocol.txt` BEFORE the first
run, both branches of the named question included.

**The realization control (P0a HOLD).** Arms rebuilt this row from the
COMMITTED emitters (`--width 32`) into a fresh build dir; the
W-INDEPENDENT artifacts are sha256-IDENTICAL to the anchor row's
2026-10-25 build -- probe.metallib 80dbf4fd.. and the counters binary
4cb76bd.. -- so the instrument is constant across the two cells. A
named artifact fact rides the control: the three BASELINE metallibs are
byte-identical to the anchor's W = 256 builds (the baseline arm's
artifact is W-invariant on this emitter), while the three SUBGROUP
metallibs W-move as expected (the subgroup arm embeds the width). All
six shas are recorded (build-shas.txt) so a later cross-day replication
of THIS cell can hold its realization fixed the same way.

**The named question, answered: the sign is W-DEPENDENT (P1b).** Rule 2
at its letter over the W = 32 session, cell roll-up: **regime-scoped**
(5 of 18 per-run paired-median ratios above 1.0, 13 below -- not a
selection basis), against the anchor cell's "regime-invariant, slower
(18/18)" on both days. Per operator:

- **sum: regime-invariant, FASTER (6/6)** -- all per-run ratios below
  1.0 (0.915..0.930), every observed regime one-sided. This is a SIDE
  FLIP across W at one operator: the same pair (subgroup-reduce vs the
  threadgroup-memory baseline), the same instrument and host, is
  regime-invariant SLOWER at W = 256 (1.204..1.221 on day 1,
  1.197..1.222 on day 2) and regime-invariant FASTER at W = 32.
- **max: regime-scoped** (straddles 1.0 WITHIN regime 1: 0.992/1.017/
  1.012 in the fast level; one-sided faster 0.910..0.921 in the two
  slow levels).
- **min: regime-scoped** (straddle SEPARATES by regime: fast level
  one-sided SLOWER 1.007..1.031, the three slower levels one-sided
  faster 0.917..0.918).

No W-invariant reading of this channel's fold-arm sign survives this
cell; the W-shape of the sign is OPEN (named, not explained). The
anchor's sign keeps its scope exactly as recorded (the anchor cell, two
days); it is not contradicted at its own cell -- the contradiction is
across cells, which is precisely the shape the anchor's list invited.

**Rule 1 at this cell (P2, named whatever it is).** The state-shift
class is W-variable too: max THREE levels (36020.5..36188.0 /
46292.0 / 108875.0..109521.0), min FOUR (36084.0..36167.0 /
44979.0 / 88729.0 / 108958.5), sum ONE (108562.5..109437.5). The raw
bracket band at this grid (36.0k..109.5k counter_ns medians) is
published as the route's raw band -- R at this grid is NOT decomposed
and NOT compared with the anchor's residual figures (the anchor's
~7.8-8.0us warm / ~20.6-20.8us cold belong to the 3907 x 256 launch
shape; this cell's shape is different).

**Consequence.** Rule 4: NOTHING MOVES -- no `:measured?` flag, no
`:shapes` value, no selection answer, no workgroup row (this channel
can never move one), no WGSL cell flip, no MSL command-buffer cell
flip, no cross-instrument magnitude claim. The sign stays
CHANNEL-SCOPED and M1-Max scoped; the sum side-flip is a counters-
channel statement about this cell only. The named item moves in RECORD
STATE only: "every other W ... on this channel" UNMEASURED -> W = 32
MEASURED at this protocol's letter (sign W-DEPENDENT; sum side-flip
named); W = 64/128/512/1024, shape 2 (n = 2^20) and R at every grid
stay UNMEASURED. The reopen condition's trigger class ("a
counters-channel record carrying an OPPOSING device-level sign at any
cell/W/day") is exercised by this record's sum side-flip at a DIFFERENT
CELL -- named as exactly that observation; the second-leg evaluation's
route-scope narrowing answered the DEVICE premise at the anchor cell
and this row does not re-open it (its own protocol registers no reopen
claim).

Named, not hidden: the same-day fact (this row and the cross-day row
share the UTC day 2026-10-26; no day claim rides here); the baseline
arm's W-invariant metallib fact (above); the fast-level max straddle
(0.992..1.017) is a within-level mixed-side band, thinner than the
slow-level separation.

States: MEASURED (the W = 32 cell record: 720 resolved brackets, the
instrument-constant control, rule 2's W-dependence verdict, rule 1's
W = 32 regime structure, the raw bracket band). IMPLEMENTED: nothing
(evidence + prose only). DECIDED: nothing new (the protocol is the
anchor row's). ACCEPTED DESIGN ONLY (unchanged): the claim protocol and
its units; the narrowing and reopen condition; the second-leg letter;
ADR-0355's channel rule. PROPOSED (unchanged): the Vulkan-provider
timestamp route. UNMEASURED, named: W = 64/128/512/1024 on this
channel; shape 2 (n = 2^20) at every W; R at every grid (the W = 32
raw band is not an R decomposition); the W-shape's cause; the state-
shift cause, threshold and prevalence (now named W-variable as well as
day-variable); day 3+ cross-day replications; op-order dependence;
anything off M1 Max; the WGSL route's kernel time; every workgroup-row
question (`:arm`/`:unknown` stay provisional `:measured? false` -- no
flag, shape, selection answer or workgroup row moves this tick).

Gates: see the record (self-test 2649/0 pin; scoped GPU gate GREEN
123/12162 twice; FULL `run-tests.cljk` RUN LIVE, red at base "Could not
find namespace: kotoba.form" (ADR-0362), outside this diff, no green
suite claimed; `find docs -name '*.sh'` -> 0).

Record: `docs/evidence/gpu/metal-counter-foldarms-w32-20261026/`.

## Amendment 2026-10-26 (the counters channel's W-GRID row, second
cell): W = 64 does NOT continue the W = 32 side-flip -- the sign is
back on the anchor's side at every operator (regime-invariant, slower,
18/18), so the W-shape of the sign is NOT a one-flip shape and stays
OPEN

ONE measurement slice (JUN-58): the anchor record's own named
UNMEASURED item -- "every other W (32/64/128/512/1024) and shape 2
(n = 2^20) on this channel (R at those grids is unmeasured too)" --
taken ONE CELL AT A TIME at the route's own unit; this row takes the
list's NEXT width after the W = 32 row: (n = 1000003, W = 64).
HARDWARE RAN: 6 fresh ADR-0358 processes at that cell on this M1 Max,
run window 2026-10-26T20:19:04Z..20:19:05Z (run-window.txt, verbatim)
-- the same UTC day as the cross-day row's day-2 runs and the W = 32
row (named; this row makes NO day claim of any kind; it is a W row).
The run protocol is the anchor row's, unchanged (6 fresh processes, 20
interleaved AB/BA pairs per operator, WARMUP=2 discarded, verified
read-back, op-order sum,max,min fixed); predictions P0..P3 were
registered in `protocol.txt` BEFORE the first run, both branches of the
named question included.

**The realization control (P0a HOLD).** Arms rebuilt this row from the
COMMITTED emitters (`--width 64`) into a fresh build dir; the
W-INDEPENDENT artifacts are sha256-IDENTICAL to the anchor row's
2026-10-25 build AND the W = 32 row's build -- probe.metallib 80dbf4fd..
and the counters binary 4cb76bd.. -- so the instrument is constant
across all three cells. The W = 32 row's named artifact fact is
RE-CHECKED here and HOLDS: the three BASELINE metallibs are
byte-identical across the anchor's W = 256 builds, the W = 32 build and
this W = 64 build (the baseline arm's artifact is W-invariant on this
emitter), while the three SUBGROUP metallibs W-move as expected. All
six shas are recorded (build-shas.txt) so a later cross-day replication
of THIS cell can hold its realization fixed the same way.

**The named question, answered (P1b, second clause): no
continuation.** Rule 2 at its letter over the W = 64 session, cell
roll-up: **regime-invariant, SLOWER (18 of 18 per-run paired-median
ratios above 1.0)** -- the anchor cell's exact verdict class, NOT the
W = 32 cell's regime-scoped one. Per operator:

- **sum: regime-invariant, SLOWER (6/6)** -- ratios 1.214..1.222,
  every observed regime one-sided. op=sum is BACK ON THE ANCHOR'S SIDE
  at W = 64: against W = 32's regime-invariant FASTER (0.915..0.930)
  and against the anchor's W = 256 regime-invariant SLOWER on both
  days (1.204..1.221 / 1.197..1.222).
- **max: regime-invariant, SLOWER (6/6)** -- 1.199..1.218.
- **min: regime-invariant, SLOWER (6/6)** -- 1.198..1.217.

The measured W-shape of the sign is now THREE cells deep and is NOT a
one-flip shape: W = 32 (regime-scoped roll-up, sum faster) differs
from BOTH W = 64 (regime-invariant slower 18/18) and W = 256
(regime-invariant slower 18/18, two days). W = 64 and W = 256 agree in
verdict class and their raw ratio bands overlap (W = 64 1.198..1.222
vs the anchor's 1.197..1.222 union across days) -- named as the
route's raw bands at this instrument's letter, no cross-instrument
claim. WHY W = 32 alone sits on the other side stays OPEN (the
instrument-constant control and the baseline arm's W-invariant artifact
are facts, not explanations).

**Rule 1 at this cell (P2, named whatever it is).** max THREE levels
(29459.0..29646.0 / 38437.5 / 91771.0..91958.5), min THREE
(29500.0..29666.0 / 38187.5 / 90916.5..91875.0), sum ONE
(91604.5..92271.0). The raw bracket band at this grid (29.5k..92.3k
counter_ns medians) is published as the route's raw band -- R at this
grid is NOT decomposed and NOT compared with the anchor's residual
figures (the anchor's ~7.8-8.0us warm / 20.6-20.8us cold belong to the
3907 x 256 launch shape; this cell's shape is different). NAMED
OBSERVATION: sum sits at ONE level in all four sessions of this channel
so far (anchor day 1, anchor day 2, W = 32, W = 64) while max/min shift
level structure between sessions (2/2, 4/4, 3/4, 3/3) -- recorded as an
observation, not explained.

**Consequence.** Rule 4: NOTHING MOVES -- no `:measured?` flag, no
`:shapes` value, no selection answer, no workgroup row (this channel
can never move one), no WGSL cell flip, no MSL command-buffer cell
flip, no cross-instrument magnitude claim. The sign stays
CHANNEL-SCOPED and M1-Max scoped. The named item moves in RECORD STATE
only: "every other W ... on this channel" UNMEASURED -> W = 64
MEASURED at this protocol's letter (regime-invariant, slower, 18/18;
sum back on the anchor side; W-shape not a one-flip shape); W =
128/512/1024, shape 2 (n = 2^20) and R at every grid stay UNMEASURED.
The reopen condition's trigger class ("a counters-channel record
carrying an OPPOSING device-level sign at any cell/W/day") is NOT
exercised by this record (this cell's sign matches the anchor's); the
W = 32 row's sum side-flip remains the single exercising observation
and stays unadjudicated (this row registers no reopen claim).

Named, not hidden: the same-day fact (this row shares the UTC day
2026-10-26 with the cross-day row's day-2 runs and the W = 32 row; no
day claim rides here); the baseline arm's W-invariant metallib fact
re-checked at W = 64; the W = 64 band's overlap with the anchor's band
is a raw-band observation at one instrument, not a stability claim.

States: MEASURED (the W = 64 cell record: 720 resolved brackets, the
instrument-constant three-cell control, rule 2's 18/18 verdict, rule
1's W = 64 regime structure, the raw bracket band). IMPLEMENTED:
nothing (evidence + prose only). DECIDED: nothing new (the protocol is
the anchor row's). ACCEPTED DESIGN ONLY (unchanged): the claim protocol
and its units; the narrowing and reopen condition; the second-leg
letter; ADR-0355's channel rule. PROPOSED (unchanged): the
Vulkan-provider timestamp route. UNMEASURED, named: W =
128/512/1024 on this channel; shape 2 (n = 2^20) at every W; R at
every grid (the W = 64 raw band is not an R decomposition); the
W-shape's cause; the state-shift cause, threshold and prevalence; day
3+ cross-day replications; op-order dependence; anything off M1 Max;
the WGSL route's kernel time; every workgroup-row question
(`:arm`/`:unknown` stay provisional `:measured? false` -- no flag,
shape, selection answer or workgroup row moves this tick).

Gates: see the record (self-test 2649/0 pin; scoped GPU gate GREEN
123/12162 twice; FULL `run-tests.cljk` RUN LIVE, red at base "Could not
find namespace: kotoba.form" (ADR-0362), outside this diff, no green
suite claimed; `find docs -name '*.sh'` -> 0).

Record: `docs/evidence/gpu/metal-counter-foldarms-w64-20261026/`.

## Amendment 2026-10-26 (the counters channel's W-GRID row, third
cell): W = 128 joins W = 64 and W = 256 on the anchor's side at every
operator (regime-invariant, slower, 18/18) -- the W = 32 side-flip
does NOT reappear, so the W-shape now reads "W = 32 alone differs"
across FOUR cells and its cause stays OPEN

ONE measurement slice (JUN-58): the anchor record's own named
UNMEASURED item -- "every other W (32/64/128/512/1024) and shape 2
(n = 2^20) on this channel (R at those grids is unmeasured too)" --
taken ONE CELL AT A TIME at the route's own unit; this row takes the
list's NEXT width after the W = 64 row: (n = 1000003, W = 128).
HARDWARE RAN: 6 fresh ADR-0358 processes at that cell on this M1 Max,
run window 2026-10-26T20:33:59Z..20:34:00Z (run-window.txt, verbatim)
-- the same UTC day as the cross-day row's day-2 runs, the W = 32 row
and the W = 64 row (named; this row makes NO day claim of any kind; it
is a W row). The run protocol is the anchor row's, unchanged (6 fresh
processes, 20 interleaved AB/BA pairs per operator, WARMUP=2
discarded, verified read-back, op-order sum,max,min fixed); predictions
P0..P3 were registered in `protocol.txt` BEFORE the first run, both
branches of the named question included.

**The realization control (P0a HOLD).** Arms rebuilt this row from the
COMMITTED emitters (`--width 128`) into a fresh build dir; the
W-INDEPENDENT artifacts are sha256-IDENTICAL to the anchor row's
2026-10-25 build AND the W = 32 and W = 64 rows' builds --
probe.metallib 80dbf4fd.. and the counters binary 4cb76bd.. -- so the
instrument is constant across all FOUR cells. The baseline arm's
W-invariant artifact fact is RE-CHECKED and HOLDS at W = 128 (the
three BASELINE metallibs byte-identical across all four builds), while
the three SUBGROUP metallibs W-move as expected. All six shas are
recorded (build-shas.txt) so a later cross-day replication of THIS
cell can hold its realization fixed the same way.

**The named question, answered (P1a): no re-flip.** Rule 2 at its
letter over the W = 128 session, cell roll-up: **regime-invariant,
SLOWER (18 of 18 per-run paired-median ratios above 1.0)** -- every
operator regime-invariant slower (sum 1.231..1.247, max 1.221..1.243,
min 1.222..1.246; every observed regime one-sided). op=sum does NOT
return to the W = 32 side. The measured W-shape is now FOUR cells deep
and reads "W = 32 ALONE DIFFERS": W = 32 (regime-scoped roll-up, sum
faster) against W = 64, W = 128 and W = 256 (regime-invariant slower
18/18 each; the anchor W = 256 on two days). No second off-anchor
width joins W = 32's side, so the shape so far is a single-width
anomaly at W = 32 -- WHY W = 32 alone sits on the other side stays
OPEN and is now the shape's sole anomaly (the instrument-constant
control and the baseline arm's W-invariant artifact are facts, not
explanations).

**Rule 1 at this cell (P2, named whatever it is).** max THREE levels
(30375.0..30584.0 / 44770.5 / 95354.0..95500.5), min FOUR
(30250.0..30542.0 / 39416.0 / 77333.0 / 95271.0), sum TWO
(49896.0 / 95187.0..95417.0). The raw bracket band at this grid
(30.25k..95.5k counter_ns medians) is published as the route's raw
band -- R at this grid is NOT decomposed and NOT compared with the
anchor's residual figures. NAMED OBSERVATION: the W = 64 row's "sum
sits at ONE level in all four sessions" BREAKS at the fifth session --
sum sits at TWO levels here (run 3 alone at the fast level), and run 3
is the mid-level session for max and min as well; the level structure
is recorded session-variable, not explained.

**Magnitude (P3).** The W = 128 raw ratio band (1.221..1.247) sits
slightly ABOVE the W = 64 band (1.198..1.222) and the anchor's union
across days (1.197..1.222), overlapping only at the 1.221..1.222 edge
-- a raw-band observation at one instrument (rule 3; no cross-instrument
magnitude claim, no magnitude invariance claimed across W either).

**Consequence.** Rule 4: NOTHING MOVES -- no `:measured?` flag, no
`:shapes` value, no selection answer, no workgroup row (this channel
can never move one), no WGSL cell flip, no MSL command-buffer cell
flip, no cross-instrument magnitude claim. The sign stays
CHANNEL-SCOPED and M1-Max scoped. The named item moves in RECORD STATE
only, one cell at a time (W = 128 -> MEASURED at this protocol's
letter; W = 512/1024, shape 2 (n = 2^20) and R at every grid stay
UNMEASURED). The reopen condition's trigger class is NOT exercised by
this record (this cell's sign matches the anchor's); the W = 32 row's
sum side-flip remains the single exercising observation and stays
unadjudicated (this row registers no reopen claim).

Named, not hidden: the same-day fact (this row shares the UTC day
2026-10-26 with the cross-day row's day-2 runs, the W = 32 row and the
W = 64 row; no day claim rides here); the baseline arm's W-invariant
metallib fact re-checked at W = 128; the W = 128 band's slight upward
shift against the W = 64/W = 256 bands (raw bands at one instrument,
edge overlap only); run 3 as the transition session.

States: MEASURED (the W = 128 cell record: 720 resolved brackets, the
instrument-constant four-cell control, rule 2's 18/18 verdict, rule
1's W = 128 regime structure, the raw bracket band). IMPLEMENTED:
nothing (evidence + prose only). DECIDED: nothing new (the protocol is
the anchor row's). ACCEPTED DESIGN ONLY (unchanged): the claim protocol
and its units; the narrowing and reopen condition; the second-leg
letter; ADR-0355's channel rule. PROPOSED (unchanged): the
Vulkan-provider timestamp route. UNMEASURED, named: W = 512/1024 on
this channel; shape 2 (n = 2^20) at every W; R at every grid (the
W = 128 raw band is not an R decomposition); the W-shape's cause; the
state-shift cause, threshold and prevalence; day 3+ cross-day
replications; op-order dependence; anything off M1 Max; the WGSL
route's kernel time; every workgroup-row question (`:arm`/`:unknown`
stay provisional `:measured? false` -- no flag, shape, selection answer
or workgroup row moves this tick).

Gates: see the record (self-test 2649/0 pin; scoped GPU gate GREEN
123/12162 twice; FULL `run-tests.cljk` RUN LIVE, red at base "Could not
find namespace: kotoba.form" (ADR-0362), outside this diff, no green
suite claimed; `find docs -name '*.sh'` -> 0).

Record: `docs/evidence/gpu/metal-counter-foldarms-w128-20261026/`.

## Amendment 2026-10-26 (the counters channel's W-GRID row, fourth cell): the first width above 256 joins the anchor's side at every operator -- "W = 32 alone differs" survives, now FIVE cells deep

The anchor record's counters-channel fold-arms list item, its named
UNMEASURED item -- "every other W (32/64/128/512/1024) and shape 2
(n = 2^20) on this channel (R at those grids is unmeasured too)" --
taken ONE CELL AT A TIME at the route's own unit; this row takes the
list's NEXT width after the W = 128 row: (n = 1000003, W = 512).
HARDWARE RAN: 6 fresh ADR-0358 processes at that cell on this M1 Max,
run window 2026-10-26T20:47:51Z..20:47:52Z (run-window.txt, verbatim)
-- the same UTC day as the cross-day row's day-2 runs and the W = 32,
W = 64 and W = 128 rows (named; this row makes NO day claim of any
kind; it is a W row). The run protocol is the anchor row's, unchanged
(6 fresh processes, 20 interleaved AB/BA pairs per operator, WARMUP=2
discarded, verified read-back, op-order sum,max,min fixed); predictions
P0..P3 were registered in `protocol.txt` BEFORE the first run, both
branches of the named question included.

**The realization control (P0a HOLD).** Arms rebuilt this row from the
COMMITTED emitters (`--width 512`) into a fresh build dir; the
W-INDEPENDENT artifacts are sha256-IDENTICAL to the anchor row's
2026-10-25 build AND the W = 32, W = 64 and W = 128 rows' builds --
probe.metallib 80dbf4fd.. and the counters binary 4cb76bd.. -- so the
instrument is constant across all FIVE cells. The baseline arm's
W-invariant artifact fact is RE-CHECKED and HOLDS at W = 512 (the
three BASELINE metallibs byte-identical across all five builds), while
the three SUBGROUP metallibs W-move as expected. All six shas are
recorded (build-shas.txt) so a later cross-day replication of THIS
cell can hold its realization fixed the same way.

**The named question, answered (P1a): the first width above 256 does
not re-flip.** Rule 2 at its letter over the W = 512 session, cell
roll-up: **regime-invariant, SLOWER (18 of 18 per-run paired-median
ratios above 1.0)** -- every operator regime-invariant slower (max
1.175..1.192, min 1.175..1.193, sum 1.189..1.198; every observed
regime one-sided). Every operator, including op=sum, is on the
ANCHOR'S SIDE at this width. The measured W-shape is now FIVE cells
deep and still reads "W = 32 ALONE DIFFERS": W = 32 (regime-scoped
roll-up, sum faster) against W = 64, W = 128, W = 256 and W = 512
(regime-invariant slower 18/18 each; the anchor W = 256 on two days).
The "W = 32 alone" reading has survived its first width above 256
(P1b did not fire); WHY W = 32 alone sits on the other side stays
OPEN and is the shape's sole anomaly (the instrument-constant control
and the baseline arm's W-invariant artifact are facts, not
explanations).

**Rule 1 at this cell (P2, named whatever it is).** max TWO levels
(36312.5..36667.0 / 114937.5..115145.5), min THREE
(36416.5..36542.0 / 70249.5 / 114916.5), sum THREE
(36937.5 / 84104.5 / 114708.0..115000.0). The raw bracket band at
this grid (36.3k..115.1k counter_ns medians) is published as the
route's raw band -- R at this grid is NOT decomposed and NOT compared
with the anchor's residual figures. NAMED OBSERVATION: the W = 128
row's "sum sits at TWO levels" does not hold here -- sum sits at THREE
(run 5 alone at the fast level, run 3 at the mid level), run 2 is the
mid-level session for min, and max sits at TWO; the level structure
continues to be session-variable at every W, recorded, not explained.

**Magnitude (P3).** The W = 512 raw ratio band (1.175..1.198) sits
slightly BELOW every other cell's band (W = 64 1.198..1.222, W = 128
1.221..1.247, the anchor's union across days 1.197..1.222),
overlapping only at the 1.197..1.198 edge -- a raw-band observation at
one instrument (rule 3; no cross-instrument magnitude claim, no
magnitude invariance claimed across W either).

**Consequence.** Rule 4: NOTHING MOVES -- no `:measured?` flag, no
`:shapes` value, no selection answer, no workgroup row (this channel
can never move one), no WGSL cell flip, no MSL command-buffer cell
flip, no cross-instrument magnitude claim. The sign stays
CHANNEL-SCOPED and M1-Max scoped. The named item moves in RECORD STATE
only, one cell at a time (W = 512 -> MEASURED at this protocol's
letter; W = 1024, shape 2 (n = 2^20) and R at every grid stay
UNMEASURED). The reopen condition's trigger class is NOT exercised by
this record (this cell's sign matches the anchor's); the W = 32 row's
sum side-flip remains the single exercising observation and stays
unadjudicated (this row registers no reopen claim).

Named, not hidden: the same-day fact (this row shares the UTC day
2026-10-26 with the cross-day row's day-2 runs and the W = 32, W = 64
and W = 128 rows; no day claim rides here); the baseline arm's
W-invariant metallib fact re-checked at W = 512 (five builds); the
W = 512 band's slight downward shift against every other cell's band
(raw bands at one instrument, edge overlap only); run 5 as the only
fast sum session and run 3 as the mid-level session.

States: MEASURED (the W = 512 cell record: 720 resolved brackets, the
instrument-constant five-cell control, rule 2's 18/18 verdict, rule
1's W = 512 regime structure, the raw bracket band). IMPLEMENTED:
nothing (evidence + prose only). DECIDED: nothing new (the protocol is
the anchor row's). ACCEPTED DESIGN ONLY (unchanged): the claim protocol
and its units; the narrowing and reopen condition; the second-leg
letter; ADR-0355's channel rule. PROPOSED (unchanged): the
Vulkan-provider timestamp route. UNMEASURED, named: W = 1024 on this
channel; shape 2 (n = 2^20) at every W; R at every grid (the W = 512
raw band is not an R decomposition); the W-shape's cause; the
state-shift cause, threshold and prevalence; day 3+ cross-day
replications; op-order dependence; anything off M1 Max; the WGSL
route's kernel time; every workgroup-row question (`:arm`/`:unknown`
stay provisional `:measured? false` -- no flag, shape, selection answer
or workgroup row moves this tick).

Gates: see the record (self-test 2649/0 pin; scoped GPU gate GREEN
123/12162 twice; FULL `run-tests.cljk` RUN LIVE, red at base "Could not
find namespace: kotoba.form" (ADR-0362), outside this diff, no green
suite claimed; `find docs -name '*.sh'` -> 0).

Record: `docs/evidence/gpu/metal-counter-foldarms-w512-20261026/`.

## Amendment 2026-10-26 (the counters channel's W-GRID row, fifth and final cell): the top width joins the anchor's side at every operator -- "W = 32 alone differs" now spans the COMPLETE width list

The anchor record's counters-channel fold-arms list item, its named
UNMEASURED item -- "every other W (32/64/128/512/1024) and shape 2
(n = 2^20) on this channel (R at those grids is unmeasured too)" --
taken ONE CELL AT A TIME at the route's own unit; this row takes the
list's LAST remaining width: (n = 1000003, W = 1024), the top of the
admitted width range (a power of two in [32, 1024]). HARDWARE RAN: 6
fresh ADR-0358 processes at that cell on this M1 Max, run window
2026-10-26T21:04:50Z..21:04:51Z (run-window.txt, verbatim) -- the same
UTC day as the cross-day row's day-2 runs and the W = 32, W = 64,
W = 128 and W = 512 rows (named; this row makes NO day claim of any
kind; it is a W row). The run protocol is the anchor row's, unchanged
(6 fresh processes, 20 interleaved AB/BA pairs per operator, WARMUP=2
discarded, verified read-back, op-order sum,max,min fixed); predictions
P0..P3 were registered in `protocol.txt` BEFORE the first run, both
branches of the named question included, plus a pre-registered
DEVICE-LIMIT BRANCH (the instrument checks
`maxTotalThreadsPerThreadgroup` and prints `shape=UNUSABLE` rather
than dispatching past it).

**The realization control (P0a HOLD).** Arms rebuilt this row from the
COMMITTED emitters (`--width 1024`) into a fresh build dir; the
W-INDEPENDENT artifacts are sha256-IDENTICAL to the anchor row's
2026-10-25 build AND the W = 32, W = 64, W = 128 and W = 512 rows'
builds -- probe.metallib 80dbf4fd.. and the counters binary 4cb76bd..
-- so the instrument is constant across all SIX cells. The baseline
arm's W-invariant artifact fact is RE-CHECKED and HOLDS at W = 1024
(the three BASELINE metallibs byte-identical across all six builds),
while the three SUBGROUP metallibs W-move as expected. All six shas
are recorded (build-shas.txt) so a later cross-day replication of THIS
cell can hold its realization fixed the same way.

**The device-limit branch did NOT fire.** W = 1024 dispatches on this
pipeline (`shape=UNUSABLE` never printed; all 6 processes ran the full
protocol) -- the top width is a MEASURED usable width for this
(instrument, kernel) pair on this device.

**The named question, answered (P1a): the top width does not
re-flip.** Rule 2 at its letter over the W = 1024 session, cell
roll-up: **regime-invariant, SLOWER (18 of 18 per-run paired-median
ratios above 1.0)** -- every operator regime-invariant slower (max
1.167..1.185, min 1.168..1.185, sum 1.183..1.188; every observed
regime one-sided). Every operator, including op=sum, is on the
ANCHOR'S SIDE at this width. The measured W-shape is now COMPLETE in
the width dimension and reads "W = 32 ALONE DIFFERS" across ALL SIX
cells: W = 32 (regime-scoped roll-up, sum faster) against W = 64,
W = 128, W = 256, W = 512 and W = 1024 (regime-invariant slower 18/18
each; the anchor W = 256 on two days). The "W = 32 alone" reading has
survived every other width in the admitted range and the width list
carries no remaining cell at the anchor's shape (P1b did not fire);
WHY W = 32 alone sits on the other side stays OPEN and is the shape's
sole anomaly (the instrument-constant six-cell control and the
baseline arm's W-invariant artifact are facts, not explanations).

**Rule 1 at this cell (P2, named whatever it is).** max THREE levels
(40708.5 / 52937.5 / 128312.5..128416.5), min FOUR
(40729.5 / 52729.0 / 103583.5 / 128312.0..128395.5), sum ONE
(128208.5..128479.0). The raw bracket band at this grid (40.7k..128.5k
counter_ns medians) is published as the route's raw band -- R at this
grid is NOT decomposed and NOT compared with the anchor's residual
figures. NAMED OBSERVATION: the level structure continues to be
session-variable and now shows a WITHIN-ROW descent at max/min -- runs
1-4 sit at the slow ~128k level, run 5 at the ~52k level, run 6 at the
~40k level -- while sum holds ONE level across all six runs (the
W = 512 row's "sum at THREE levels" and the W = 64 row's one-level sum
both fail to reproduce here); recorded, not explained.

**Magnitude (P3).** The W = 1024 raw ratio band (1.167..1.188) sits
BELOW every other cell's band (W = 512 1.175..1.198, W = 64
1.198..1.222, W = 128 1.221..1.247, the anchor's union across days
1.197..1.222), overlapping only W = 512's band -- a raw-band
observation at one instrument (rule 3; no cross-instrument magnitude
claim, no magnitude invariance claimed across W either).

**Consequence.** Rule 4: NOTHING MOVES -- no `:measured?` flag, no
`:shapes` value, no selection answer, no workgroup row (this channel
can never move one), no WGSL cell flip, no MSL command-buffer cell
flip, no cross-instrument magnitude claim. The sign stays
CHANNEL-SCOPED and M1-Max scoped. The named item moves in RECORD STATE
only (W = 1024 -> MEASURED at this protocol's letter; the width list
is CLOSED at the anchor's shape -- W = 64/128/256/512/1024 on the
anchor's side, W = 32 alone differing; shape 2 (n = 2^20) and R at
every grid stay UNMEASURED). The reopen condition's trigger class is
NOT exercised by this record (this cell's sign matches the anchor's);
the W = 32 row's sum side-flip remains the single exercising
observation and stays unadjudicated (this row registers no reopen
claim).

Named, not hidden: the same-day fact (this row shares the UTC day
2026-10-26 with the cross-day row's day-2 runs and the W = 32, W = 64,
W = 128 and W = 512 rows; no day claim rides here); the baseline arm's
W-invariant metallib fact re-checked at W = 1024 (six builds); the
W = 1024 band's position below every other cell's band (raw bands at
one instrument, overlap with W = 512 only); the within-row max/min
descent across runs 4 -> 5 -> 6 while sum holds one level; the
pre-registered device-limit branch not firing.

States: MEASURED (the W = 1024 cell record: 720 resolved brackets, the
instrument-constant six-cell control, rule 2's 18/18 verdict, rule 1's
W = 1024 regime structure, the raw bracket band, W = 1024 usable at
this pipeline). IMPLEMENTED: nothing (evidence + prose only). DECIDED:
nothing new (the protocol is the anchor row's). ACCEPTED DESIGN ONLY
(unchanged): the claim protocol and its units; the narrowing and
reopen condition; the second-leg letter; ADR-0355's channel rule.
PROPOSED (unchanged): the Vulkan-provider timestamp route.
UNMEASURED, named: shape 2 (n = 2^20) at every W; R at every grid (the
W = 1024 raw band is not an R decomposition); the W-shape's cause; the
state-shift cause, threshold and prevalence; day 3+ cross-day
replications; op-order dependence; anything off M1 Max; the WGSL
route's kernel time; every workgroup-row question (`:arm`/`:unknown`
stay provisional `:measured? false` -- no flag, shape, selection answer
or workgroup row moves this tick).

Gates: see the record (self-test 2649/0 pin; scoped GPU gate GREEN
123/12162 twice; FULL `run-tests.cljk` RUN LIVE, red at base "Could not
find namespace: kotoba.form" (ADR-0362), outside this diff, no green
suite claimed; `find docs -name '*.sh'` -> 0).

Record: `docs/evidence/gpu/metal-counter-foldarms-w1024-20261026/`.

## Amendment 2026-10-26 (the counters channel's SHAPE-2 row, first cell): the anchor's reading REPRODUCES at the second shape -- shape-stable at fixed W = 256 from n = 1000003 to n = 2^20

The anchor record's counters-channel fold-arms list item, its named
UNMEASURED item -- "every other W (32/64/128/512/1024) and shape 2
(n = 2^20) on this channel (R at those grids is unmeasured too)" --
taken ONE CELL AT A TIME at the route's own unit; the width half of
the list is CLOSED (the W = 1024 row) and this row takes the shape
item's FIRST cell: (n = 2^20 = 1048576, W = 256), the anchor WIDTH at
the second shape, so the moved axis is the shape alone. The launch
shape is 4096 x 256 (n an exact multiple of W; the anchor's 3907 x 256
had a partial last group) and the anchor's residual R numbers do not
transfer to it. HARDWARE RAN: 6 fresh ADR-0358 processes at that cell
on this M1 Max, run window 2026-10-26T21:19:06Z..21:19:07Z
(run-window.txt, verbatim) -- the same UTC day as the cross-day row's
day-2 runs and the W = 32/64/128/512/1024 rows (named; this row makes
NO day claim of any kind; it is a SHAPE row). The run protocol is the
anchor row's, unchanged (6 fresh processes, 20 interleaved AB/BA pairs
per operator, WARMUP=2 discarded, verified read-back, op-order
sum,max,min fixed); predictions P0..P3 were registered in
`protocol.txt` BEFORE the first run, both branches of the named
question included.

**The realization control (P0a HOLD).** Arms rebuilt this row from the
COMMITTED emitters (`--width 256`) into a fresh build dir (the
anchor's build dir not reused -- the artifacts are re-derived and
compared, not copied); the W-INDEPENDENT artifacts are
sha256-IDENTICAL to the anchor row's 2026-10-25 build AND the
W = 32, W = 64, W = 128, W = 512 and W = 1024 rows' builds --
probe.metallib 80dbf4fd.. and the counters binary 4cb76bd.. -- so the
instrument is constant across all SEVEN cells. ADDITIONAL FACT CHECK,
this row's shape analogue of the baseline-arm W-invariance check
(checked, not assumed): ALL SIX fold-arm metallibs are byte-identical
to the anchor row's W = 256 build (baseline 2e2f3654.. / 1169a1a8.. /
2cd19335.., subgroup a8de6377.. / bda54358.. / a2046b53..) -- the
fold-arm artifacts are n-INVARIANT on this emitter at W = 256 (n is a
dispatch-time argument; the arms' code does not depend on n), the
first named n-invariance fact of the fold arms. All six shas are
recorded (build-shas.txt) so a later cross-day replication of THIS
cell can hold its realization fixed the same way.

**The named question, answered (P1a): the anchor's reading reproduces
at the second shape.** Rule 2 at its letter over the (n = 2^20,
W = 256) session, cell roll-up: **regime-invariant, SLOWER (18 of 18
per-run paired-median ratios above 1.0)** -- every operator
regime-invariant slower (max 1.206..1.228, min 1.208..1.227, sum
1.223..1.230; every observed regime one-sided). The anchor cell's
verdict class REPRODUCES at the second shape (P1b did not fire): the
anchor's regime-invariant-slower reading is shape-stable at fixed
W = 256 across n = 1000003 (3907 x 256) -> n = 2^20 (4096 x 256), and
the W = 32 side-flip class is NOT reproduced by moving the shape axis
alone at the anchor width (this narrows nothing about WHY W = 32
flips -- the W-shape's cause stays OPEN as the shape's sole anomaly).

**Rule 1 at this cell (P2, named whatever it is).** max THREE levels
(33979.5..34000.0 / 55896.0 / 107208.0..107354.0), min THREE
(33958.0..34021.0 / 44187.5 / 107312.5..107396.0), sum ONE
(106208.5..107333.0). The raw bracket band at this grid (33.96k..107.4k
counter_ns medians) is published as the route's raw band -- R at this
grid is NOT decomposed and NOT compared with the anchor's residual
figures (those belong to 3907 x 256). NAMED OBSERVATION: the
WITHIN-ROW descent class the W = 1024 row named REPRODUCES here at
max/min with later runs at faster levels -- runs 1-2 sit at the slow
~107k level, run 3 at the mid level, runs 4-6 at the fast ~34k level
(the W = 1024 row's descent ran 1-4 slow -> 5 mid -> 6 fast; the run
boundaries differ, the class does not) -- while sum holds ONE level
across all six runs (the W = 1024 row's one-level sum reproduces; the
W = 512 row's three-level sum does not); recorded, not explained.

**Magnitude (P3).** The shape-2 raw ratio band (1.206..1.230 pooled
across operators) sits slightly ABOVE the anchor's union band across
days (1.197..1.222), overlapping 1.206..1.222 -- a raw-band
observation at one instrument (rule 3; no cross-instrument magnitude
claim, no magnitude invariance claimed across n either).

**Consequence.** Rule 4: NOTHING MOVES -- no `:measured?` flag, no
`:shapes` value, no selection answer, no workgroup row (this channel
can never move one), no WGSL cell flip, no MSL command-buffer cell
flip, no cross-instrument magnitude claim. The sign stays
CHANNEL-SCOPED and M1-Max scoped. The named item moves in RECORD STATE
only ("shape 2 (n = 2^20) on this channel" UNMEASURED -> its W = 256
cell MEASURED at this protocol's letter, regime-invariant slower
18/18, anchor reading reproduced at the second shape; shape 2 at
W = 32/64/128/512/1024 and R at every grid stay UNMEASURED). The
reopen condition's trigger class is NOT exercised by this record (this
cell's sign matches the anchor's); the W = 32 row's sum side-flip
remains the single exercising observation and stays unadjudicated
(this row registers no reopen claim).

Named, not hidden: the same-day fact (this row shares the UTC day
2026-10-26 with the cross-day row's day-2 runs and all five W rows; no
day claim rides here); the fold-arm artifacts' n-invariance at W = 256
(all six arms byte-identical to the anchor build -- checked, not
assumed); the shape-2 band's position above the anchor's union band
(raw bands at one instrument, overlap 1.206..1.222); the within-row
max/min descent reproducing with different run boundaries (the class,
not the boundaries).

States: MEASURED (the (n = 2^20, W = 256) cell record: 720 resolved
brackets, the instrument-constant seven-cell control, rule 2's 18/18
verdict, rule 1's regime structure at this grid, the raw bracket band,
the fold arms' n-invariance at W = 256). IMPLEMENTED: nothing
(evidence + prose only). DECIDED: nothing new (the protocol is the
anchor row's). ACCEPTED DESIGN ONLY (unchanged): the claim protocol
and its units; the narrowing and reopen condition; the second-leg
letter; ADR-0355's channel rule. PROPOSED (unchanged): the
Vulkan-provider timestamp route. UNMEASURED, named: shape 2
(n = 2^20) at W = 32/64/128/512/1024; R at every grid (the shape-2
raw band is not an R decomposition); the W-shape's cause; the
state-shift cause, threshold and prevalence (the within-row descent
class now at two rows); day 3+ cross-day replications; op-order
dependence; anything off M1 Max; the WGSL route's kernel time; every
workgroup-row question (`:arm`/`:unknown` stay provisional
`:measured? false` -- no flag, shape, selection answer or workgroup
row moves this tick).

Gates: see the record (self-test 2649/0 pin; scoped GPU gate GREEN
123/12162 twice; FULL `run-tests.cljk` RUN LIVE, red at base "Could not
find namespace: kotoba.form" (ADR-0362), outside this diff, no green
suite claimed; `find docs -name '*.sh'` -> 0).

Record: `docs/evidence/gpu/metal-counter-foldarms-shape2-20261026/`.

## Amendment 2026-10-26 (the counters channel's SHAPE-2 row, second cell): the W = 32 side-flip REPRODUCES at the second shape -- the flip is shape-stable and needs no partial tail

The anchor record's counters-channel fold-arms list item, its named
UNMEASURED item -- "every other W (32/64/128/512/1024) and shape 2
(n = 2^20) on this channel (R at those grids is unmeasured too)" --
taken ONE CELL AT A TIME at the route's own unit; the width half of
the list is CLOSED (the W = 1024 row), the shape item's FIRST cell
(n = 2^20, W = 256) went to the shape2 row, and this row takes the
shape item's SECOND cell, in the width order the width half itself
used: (n = 2^20 = 1048576, W = 32) -- the W-shape's SOLE ANOMALY at
the second shape, so the moved axis is the shape alone and the cell is
the strongest test the list offers of whether the W = 32 side-flip is
shape-stable. The launch shape is 32768 x 32 (n an exact multiple of
W; at n = 1000003 the W = 32 launch was 31250 x 32 PLUS a partial
last group of 3 elements -- the tail is ABSENT at this cell) and the
anchor's residual R numbers do not transfer to it. HARDWARE RAN: 6
fresh ADR-0358 processes at that cell on this M1 Max, run window
2026-10-26T21:35:39Z..21:35:40Z (run-window.txt, verbatim) -- the
same UTC day as the cross-day row's day-2 runs, the W = 32/64/128/512/
1024 rows and the shape2-W = 256 row (named; this row makes NO day
claim of any kind; it is a SHAPE row). The run protocol is the anchor
row's, unchanged (6 fresh processes, 20 interleaved AB/BA pairs per
operator, WARMUP=2 discarded, verified read-back, op-order sum,max,min
fixed); predictions P0..P3 were registered in `protocol.txt` BEFORE
the first run, both branches of the named question included.

**The realization control (P0a HOLD).** Arms rebuilt this row from the
COMMITTED emitters (`--width 32`) into a fresh build dir (the W = 32
row's build dir not reused -- the artifacts are re-derived and
compared, not copied); the W-INDEPENDENT artifacts are
sha256-IDENTICAL to the anchor row's 2026-10-25 build AND the W = 32,
W = 64, W = 128, W = 512, W = 1024 and shape2-W = 256 rows' builds --
probe.metallib 80dbf4fd.. and the counters binary 4cb76bd.. -- so the
instrument is constant across all EIGHT cells. ADDITIONAL FACT CHECK,
this row's shape analogue of the baseline-arm W-invariance check
(checked, not assumed): ALL SIX fold-arm metallibs are byte-identical
to the W = 32 ROW's 2026-10-26 build (baseline 2e2f3654.. / 1169a1a8.. /
2cd19335.., subgroup 27d99c98.. / 8aac28a5.. / c8328a1d..) -- the
fold-arm artifacts are n-INVARIANT at W = 32 too, the W = 32
counterpart of the shape2-W = 256 row's named fact; the baseline
metallibs are additionally byte-identical across ALL EIGHT builds
(W-invariant and n-invariant). All six shas are recorded
(build-shas.txt) so a later cross-day replication of THIS cell can
hold its realization fixed the same way.

**The named question, answered (P1a): the W = 32 side-flip class
reproduces at the second shape.** Rule 2 at its letter over the
(n = 2^20, W = 32) session: roll-up REGIME-SCOPED (5 above 1.0, 13
below) and op=sum REGIME-INVARIANT FASTER 6/6 (0.915..0.926) -- the
flip's defining sign carries to n = 2^20 -- with max regime-scoped
straddling within regime 1 (fast level mixed) and min regime-scoped
straddling with regimes disagreeing (fast level one-sided SLOWER
3/3 at 1.009..1.018, slower levels one-sided faster): the same
verdict-class structure as the W = 32 row at n = 1000003 at every
operator (P1b did not fire). NAMED: the flip reproduces WITHOUT the
tail -- the two W = 32 cells differ in the partial-last-group fact and
the flip does not require it; this narrows nothing about WHY W = 32
flips (the W-shape's cause stays OPEN as the shape's sole anomaly; this
row does not isolate the tail's role, it only shows the flip is not
removed by the tail's absence). The W-shape at shape 2 now has TWO
measured widths -- W = 32 (flip) and W = 256 (anchor side, the
shape2-W = 256 row) -- so the W contrast holds at BOTH measured shapes
at their measured widths; shape 2 at W = 64/128/512/1024 stays
UNMEASURED and this row closes no width half of the shape item.

**Rule 1 at this cell (P2, named whatever it is).** max THREE levels
(37520.5..37729.5 / 71687.5 / 113583.5..113854.5), min THREE
(37333.5..37541.5 / 60771.0 / 113438.0..113937.5), sum ONE
(111666.5..113541.5). The raw bracket band at this grid (37.3k..113.9k
counter_ns medians) is published as the route's raw band -- R at this
grid is NOT decomposed and NOT compared with the anchor's residual
figures (those belong to 3907 x 256). NAMED OBSERVATION: the W = 32
row's one-level sum REPRODUCES (sum one level in both W = 32 cells, at
both shapes) and the within-row max/min descent reproduces with the
SAME run boundaries as the W = 32 row at n = 1000003 (runs 1-2 slow
~113k, run 3 mid, runs 4-6 fast ~37.5k) -- while the W = 32 row's
FOUR-level min collapses to THREE here (run 2 no longer a level of its
own) -- recorded, not explained.

**Magnitude (P3).** The shape-2 W = 32 raw ratio band (0.915..1.019
pooled across operators) sits at the W = 32 row's pooled band
(0.910..1.031 at n = 1000003 -- NAMED CORRECTION: protocol.txt's P3
wrote 0.915..1.031 for that band, mis-stating its lower end; the
W = 32 publication's own pooled minimum is 0.910, from max run 3; the
pre-registered file is not edited post-hoc, the error is corrected
here) with near-complete overlap -- raw-band observation at one
instrument (rule 3; no cross-instrument magnitude claim, no magnitude
invariance claimed across n either) -- while at FIXED shape 2 the W
contrast is total between the two measured widths (this row's sum
0.915..0.926 against the shape2-W = 256 row's sum 1.223..1.230).

**Consequence.** Rule 4: NOTHING MOVES -- no `:measured?` flag, no
`:shapes` value, no selection answer, no workgroup row (this channel
can never move one), no WGSL cell flip, no MSL command-buffer cell
flip, no cross-instrument magnitude claim. The sign stays
CHANNEL-SCOPED and M1-Max scoped. The named item moves in RECORD STATE
only ("shape 2 (n = 2^20) at W = 32" UNMEASURED -> MEASURED at this
protocol's letter, flip class reproduced, sum regime-invariant faster
6/6, roll-up regime-scoped 5/18; shape 2 at W = 64/128/512/1024 and R
at every grid stay UNMEASURED). The reopen-trigger count RISES 1 -> 2
(NAMED, NOT HIDDEN -- the earlier rows' "the single exercising
observation" sentence is superseded): the second-leg evaluation's
reopen trigger class ("a counters-channel record carrying an OPPOSING
device-level sign at any cell/W/day") is now exercised by TWO records
-- the W = 32 row's sum side-flip at n = 1000003 and THIS row's sum
side-flip at n = 2^20, both at W = 32, both opposing the anchor's
device-level sign at sum -- same class, one width, two shapes; both
unadjudicated; this row registers no reopen claim.

Named, not hidden: the same-day fact (this row shares the UTC day
2026-10-26 with the cross-day row's day-2 runs, all five W rows and the
shape2-W = 256 row; no day claim rides here); the reopen-trigger count
rising 1 -> 2; the fold-arm artifacts' n-invariance at W = 32 (all six
arms byte-identical to the W = 32 row's build -- checked, not assumed);
the pooled-count coincidence (5/18 above 1.0 at both W = 32 cells --
raw counts at one instrument, no claim rides on the coincidence); the
protocol's P3 band-figure error and its correction above; the min
level count moving FOUR -> THREE between the W = 32 cells.

States: MEASURED (the (n = 2^20, W = 32) cell record: 720 resolved
brackets, the instrument-constant eight-cell control, rule 2's flip
verdict, rule 1's regime structure at this grid, the raw bracket band,
the fold arms' n-invariance at W = 32). IMPLEMENTED: nothing (evidence
+ prose only). DECIDED: nothing new (the protocol is the anchor
row's). ACCEPTED DESIGN ONLY (unchanged): the claim protocol and its
units; the narrowing and reopen condition; the second-leg letter;
ADR-0355's channel rule. PROPOSED (unchanged): the Vulkan-provider
timestamp route. UNMEASURED, named: shape 2 (n = 2^20) at W =
64/128/512/1024; R at every grid (this row's raw band is not an R
decomposition); the W-shape's cause (WHY W = 32 alone flips side --
this row shows the flip needs no partial tail, which narrows nothing
about the mechanism); the partial tail's quantitative role; the
state-shift cause, threshold and prevalence (the within-row descent
class now at three rows); day 3+ cross-day replications; op-order
dependence; anything off M1 Max; the WGSL route's kernel time; every
workgroup-row question (`:arm`/`:unknown` stay provisional
`:measured? false` -- no flag, shape, selection answer or workgroup
row moves this tick).

Gates: see the record (self-test 2649/0 pin; scoped GPU gate GREEN
123/12162 twice; FULL `run-tests.cljk` RUN LIVE, red at base "Could not
find namespace: kotoba.form" (ADR-0362), outside this diff, no green
suite claimed; `find docs -name '*.sh'` -> 0).

Record: `docs/evidence/gpu/metal-counter-foldarms-shape2-w32-20261026/`.

## Amendment 2026-10-26 (the counters channel's SHAPE-2 row, third cell): the W = 64 anchor-side reading REPRODUCES at the second shape -- the W = 32 side-flip stays a single-width anomaly at both measured shapes

The anchor record's counters-channel fold-arms list item, its named
UNMEASURED item -- "every other W (32/64/128/512/1024) and shape 2
(n = 2^20) on this channel (R at those grids is unmeasured too)" --
taken ONE CELL AT A TIME at the route's own unit; the width half of
the list is CLOSED (the W = 1024 row), the shape item's FIRST cell
(n = 2^20, W = 256) went to the shape2-W = 256 row (anchor reading
reproduced) and its SECOND cell (n = 2^20, W = 32) to the shape2-W = 32
row (the W = 32 side-flip class reproduced at the second shape). This
row takes the shape item's THIRD cell, in the width order the width
half itself used: (n = 2^20 = 1048576, W = 64) -- the width whose
n = 1000003 reading sat on the ANCHOR'S side (regime-invariant slower
18/18, the W = 64 row) at the second shape, so the moved axis is the
shape alone and the cell is the anchor-side counterpart test of the
W = 32 flip's shape-stability question. The launch shape is 16384 x 64
(n an exact multiple of W; at n = 1000003 the W = 64 launch was
15625 x 64 PLUS a partial last group of 3 elements -- the tail is
ABSENT at this cell) and the anchor's residual R numbers do not
transfer to it. HARDWARE RAN: 6 fresh ADR-0358 processes at that cell
on this M1 Max, run window 2026-10-26T21:48:59Z..21:49:00Z
(run-window.txt, verbatim) -- the same UTC day as the cross-day row's
day-2 runs, the W = 32/64/128/512/1024 rows and the shape2-W = 256 and
shape2-W = 32 rows (named; this row makes NO day claim of any kind; it
is a SHAPE row). The run protocol is the anchor row's, unchanged (6
fresh processes, 20 interleaved AB/BA pairs per operator, WARMUP=2
discarded, verified read-back, op-order sum,max,min fixed); predictions
P0..P3 were registered in `protocol.txt` BEFORE the first run, both
branches of the named question included.

**The realization control (P0a HOLD).** Arms rebuilt this row from the
COMMITTED emitters (`--width 64`) into a fresh build dir (the W = 64
row's build dir not reused -- the artifacts are re-derived and
compared, not copied); the W-INDEPENDENT artifacts are
sha256-IDENTICAL to the anchor row's 2026-10-25 build AND the W = 32,
W = 64, W = 128, W = 512, W = 1024, shape2-W = 256 and shape2-W = 32
rows' builds -- probe.metallib 80dbf4fd.. and the counters binary
4cb76bd.. -- so the instrument is constant across all NINE cells.
ADDITIONAL FACT CHECK, this row's shape analogue of the baseline-arm
W-invariance check (checked, not assumed): ALL SIX fold-arm metallibs
are byte-identical to the W = 64 ROW's 2026-10-26 build (baseline
2e2f3654.. / 1169a1a8.. / 2cd19335.., subgroup 8514b29d.. / 4ab48d31.. /
3c5a8c58..) -- the fold-arm artifacts are n-INVARIANT at W = 64 too,
the W = 64 counterpart of the shape2-W = 256 and shape2-W = 32 rows'
named fact; the baseline metallibs are additionally byte-identical
across ALL NINE builds (W-invariant and n-invariant). All six shas are
recorded (build-shas.txt) so a later cross-day replication of THIS cell
can hold its realization fixed the same way.

**The named question, answered (P1a): the W = 64 anchor-side reading
reproduces at the second shape.** Rule 2 at its letter over the
(n = 2^20, W = 64) session: roll-up REGIME-INVARIANT, SLOWER (18/18
per-run paired-median ratios above 1.0) -- every operator
regime-invariant slower (max 6/6 1.218..1.223, min 6/6 1.215..1.224,
sum 6/6 1.223..1.228, every observed regime one-sided) -- the anchor
cell's verdict class carries to n = 2^20 at this width and NO
side-flip appears here (P1b did not fire). The W-shape at shape 2 now
has THREE measured widths -- W = 32 (flip: sum faster 6/6) against
W = 64 and W = 256 (anchor side: regime-invariant slower 18/18 each) --
so the W = 32 side-flip remains a SINGLE-WIDTH anomaly at BOTH measured
shapes, and the W contrast holds at every measured width of shape 2 so
far; shape 2 at W = 128/512/1024 stays UNMEASURED and the width half of
the shape-2 item is NOT closed by this row.

**Rule 1 at this cell (P2, named whatever it is).** max TWO levels
(49916.5 / 95291.5..95937.5), min THREE (39708.5 / 77625.0..79146.0 /
95625.5..95896.0), sum ONE (95334.0..95645.5). The raw bracket band at
this grid (39.7k..95.9k counter_ns medians) is published as the route's
raw band -- R at this grid is NOT decomposed and NOT compared with the
anchor's residual figures (those belong to 3907 x 256). NAMED
OBSERVATION: sum's one level REPRODUCES (sum one level in both W = 64
cells, at both shapes) while the level structure is again
session-variable -- max moves THREE -> TWO levels between the W = 64
cells and the earlier rows' within-row descent ordering does NOT
reproduce here (run 3 alone is the fast-level session at max and min's
fastest, min's mid level sits at runs 2/6, and runs 4-6 are back at the
slow level at max, against the shape2 rows' runs 1-2 slow / run 3 mid /
runs 4-6 fast descent) -- recorded, not explained.

**Magnitude (P3).** The shape-2 W = 64 raw ratio band (1.215..1.228
pooled across operators) sits slightly ABOVE the W = 64 row's pooled
band (1.198..1.222 at n = 1000003) and the anchor's union band across
days (1.197..1.222), overlapping only at the 1.215..1.222 edge --
raw-band observation at one instrument (rule 3; no cross-instrument
magnitude claim, no magnitude invariance claimed across n either) --
while at FIXED shape 2 the W contrast is total between the two sides
(this row's sum 1.223..1.228 against the shape2-W = 32 row's sum
0.915..0.926) and this row's sum band sits at the shape2-W = 256 row's
sum band (1.223..1.230, overlapping 1.223..1.228).

**Consequence.** Rule 4: NOTHING MOVES -- no `:measured?` flag, no
`:shapes` value, no selection answer, no workgroup row (this channel
can never move one), no WGSL cell flip, no MSL command-buffer cell
flip, no cross-instrument magnitude claim. The sign stays
CHANNEL-SCOPED and M1-Max scoped. The named item moves in RECORD STATE
only ("shape 2 (n = 2^20) at W = 64" UNMEASURED -> MEASURED at this
protocol's letter, anchor-side class reproduced, roll-up
regime-invariant slower 18/18; shape 2 at W = 128/512/1024 and R at
every grid stay UNMEASURED). The second-leg evaluation's reopen
trigger class ("a counters-channel record carrying an OPPOSING
device-level sign at any cell/W/day") is NOT exercised by this record
(this cell's sign matches the anchor's) -- the count stays at the
shape2-W = 32 row's TWO exercising records (the W = 32 row's sum
side-flip at n = 1000003 and that row's at n = 2^20), both
unadjudicated; this row registers no reopen claim.

Named, not hidden: the same-day fact (this row shares the UTC day
2026-10-26 with the cross-day row's day-2 runs, all five W rows and the
shape2-W = 256 and shape2-W = 32 rows; no day claim rides here); the
reopen-trigger count staying at 2; the fold-arm artifacts' n-invariance
at W = 64 (all six arms byte-identical to the W = 64 row's build --
checked, not assumed); the band's slight upward shift against the
W = 64 row's and the anchor's bands (raw bands at one instrument, edge
overlap 1.215..1.222 only); max's level count moving THREE -> TWO
between the W = 64 cells and the within-row descent ordering not
reproducing at this cell.

States: MEASURED (the (n = 2^20, W = 64) cell record: 720 resolved
brackets, the instrument-constant nine-cell control, rule 2's
anchor-side verdict, rule 1's regime structure at this grid, the raw
bracket band, the fold arms' n-invariance at W = 64). IMPLEMENTED:
nothing (evidence + prose only). DECIDED: nothing new (the protocol is
the anchor row's). ACCEPTED DESIGN ONLY (unchanged): the claim protocol
and its units; the narrowing and reopen condition; the second-leg
letter; ADR-0355's channel rule. PROPOSED (unchanged): the
Vulkan-provider timestamp route. UNMEASURED, named: shape 2
(n = 2^20) at W = 128/512/1024; R at every grid (this row's raw band is
not an R decomposition); the W-shape's cause (WHY W = 32 alone flips
side -- this row adds a third anchor-side width at shape 2 and narrows
nothing about the mechanism); the partial tail's quantitative role; the
state-shift cause, threshold and prevalence; day 3+ cross-day
replications; op-order dependence; anything off M1 Max; the WGSL route's
kernel time; every workgroup-row question (`:arm`/`:unknown` stay
provisional `:measured? false` -- no flag, shape, selection answer or
workgroup row moves this tick).

Gates: see the record (self-test 2649/0 pin; scoped GPU gate GREEN
123/12162 twice; FULL `run-tests.cljk` RUN LIVE, red at base "Could not
find namespace: kotoba.form" (ADR-0362), outside this diff, no green
suite claimed; `find docs -name '*.sh'` -> 0).

Record: `docs/evidence/gpu/metal-counter-foldarms-shape2-w64-20261026/`.

## Amendment 2026-10-26 (the counters channel's SHAPE-2 row, fourth cell): the W = 128 anchor-side reading REPRODUCES at the second shape -- the W = 32 side-flip stays a single-width anomaly at all four measured widths of shape 2

The anchor record's counters-channel fold-arms list item, its named
UNMEASURED item -- "every other W (32/64/128/512/1024) and shape 2
(n = 2^20) on this channel (R at those grids is unmeasured too)" --
taken ONE CELL AT A TIME at the route's own unit; the width half of
the list is CLOSED (the W = 1024 row), the shape item's FIRST cell
(n = 2^20, W = 256) went to the shape2-W = 256 row (anchor reading
reproduced), its SECOND cell (n = 2^20, W = 32) to the shape2-W = 32
row (the W = 32 side-flip class reproduced at the second shape) and
its THIRD cell (n = 2^20, W = 64) to the shape2-W = 64 row (anchor-side
class reproduced at the second shape). This row takes the shape item's
FOURTH cell, in the width order the width half itself used:
(n = 2^20 = 1048576, W = 128) -- the width whose n = 1000003 reading
sat on the ANCHOR'S side (regime-invariant slower 18/18, sum
1.231..1.247 / max 1.221..1.243 / min 1.222..1.246, the W = 128 row) at
the second shape, so the moved axis is the shape alone and the cell is
the anchor-side counterpart test of the W = 32 flip's shape-stability
question at the third anchor-side width. The launch shape is
8192 x 128 (n an exact multiple of W; at n = 1000003 the W = 128
launch was 7813 x 128 PLUS a partial last group of 67 elements -- the
tail is ABSENT at this cell) and the anchor's residual R numbers do not
transfer to it. HARDWARE RAN: 6 fresh ADR-0358 processes at that cell
on this M1 Max, run window 2026-10-26T22:05:05Z..22:05:06Z
(run-window.txt, verbatim) -- the same UTC day as the cross-day row's
day-2 runs, the W = 32/64/128/512/1024 rows and the shape2-W = 256,
shape2-W = 32 and shape2-W = 64 rows (named; this row makes NO day
claim of any kind; it is a SHAPE row). The run protocol is the anchor
row's, unchanged (6 fresh processes, 20 interleaved AB/BA pairs per
operator, WARMUP=2 discarded, verified read-back, op-order sum,max,min
fixed); predictions P0..P3 were registered in `protocol.txt` BEFORE the
first run, both branches of the named question included.

**The realization control (P0a HOLD).** Arms rebuilt this row from the
COMMITTED emitters (`--width 128`) into a fresh build dir (the W = 128
row's build dir not reused -- the artifacts are re-derived and
compared, not copied); the W-INDEPENDENT artifacts are
sha256-IDENTICAL to the anchor row's 2026-10-25 build AND the W = 32,
W = 64, W = 128, W = 512, W = 1024, shape2-W = 256, shape2-W = 32 and
shape2-W = 64 rows' builds -- probe.metallib 80dbf4fd.. and the
counters binary 4cb76bd.. -- so the instrument is constant across all
TEN cells. ADDITIONAL FACT CHECK, this row's shape analogue of the
baseline-arm W-invariance check (checked, not assumed): ALL SIX
fold-arm metallibs are byte-identical to the W = 128 ROW's 2026-10-26
build (baseline 2e2f3654.. / 1169a1a8.. / 2cd19335.., subgroup
847c9165.. / 43463cbf.. / d2a14e52..) -- the fold-arm artifacts are
n-INVARIANT at W = 128 too, the W = 128 counterpart of the
shape2-W = 256, shape2-W = 32 and shape2-W = 64 rows' named fact; the
baseline metallibs are additionally byte-identical across ALL TEN
builds (W-invariant and n-invariant). All six shas are recorded
(build-shas.txt) so a later cross-day replication of THIS cell can
hold its realization fixed the same way.

**The named question, answered (P1a): the W = 128 anchor-side reading
reproduces at the second shape.** Rule 2 at its letter over the
(n = 2^20, W = 128) session: roll-up REGIME-INVARIANT, SLOWER (18/18
per-run paired-median ratios above 1.0) -- every operator
regime-invariant slower (max 6/6 1.212..1.237, min 6/6 1.212..1.238,
sum 6/6 1.238..1.240, every observed regime one-sided) -- the anchor
cell's verdict class carries to n = 2^20 at this width and NO
side-flip appears here (P1b did not fire). The W-shape at shape 2 now
has FOUR measured widths -- W = 32 (flip: sum faster 6/6) against
W = 64, W = 128 and W = 256 (anchor side: regime-invariant slower
18/18 each) -- so the W = 32 side-flip remains a SINGLE-WIDTH anomaly
at BOTH measured shapes, and the W contrast holds at every measured
width of shape 2 so far; shape 2 at W = 512/1024 stays UNMEASURED and
the width half of the shape-2 item is NOT closed by this row.

**Rule 1 at this cell (P2, named whatever it is).** max THREE levels
(32041.0..32083.0 / 61708.5 / 99958.5..100271.0), min THREE
(32042.0..32166.5 / 46917.0 / 99958.0..100021.0), sum ONE
(99958.5..100146.0). The raw bracket band at this grid (32.0k..100.3k
counter_ns medians) is published as the route's raw band -- R at this
grid is NOT decomposed and NOT compared with the anchor's residual
figures (those belong to 3907 x 256). NAMED OBSERVATION: the W = 128
row's "sum sits at TWO levels" does NOT hold here -- sum sits at ONE
level (all six runs 99958.5..100146.0) and min's FOUR levels collapse
to THREE between the W = 128 cells, while the within-row descent class
reappears at max/min with run 6 back at the slow level (runs 4-5 fast /
run 3 mid / runs 1-2 and 6 slow, against the shape2-W = 256 and
shape2-W = 32 rows' runs 1-2 slow / run 3 mid / runs 4-6 fast descent
and the shape2-W = 64 row's non-reproducing ordering) -- the level
structure continues to be session-variable at every cell, recorded,
not explained.

**Magnitude (P3).** The shape-2 W = 128 raw ratio band (1.212..1.240
pooled across operators) sits slightly BELOW the W = 128 row's pooled
band (1.221..1.247 at n = 1000003), overlapping 1.221..1.240, and
overlaps the anchor's union band across days (1.197..1.222) at
1.212..1.222 -- raw-band observation at one instrument (rule 3; no
cross-instrument magnitude claim, no magnitude invariance claimed
across n either) -- while at FIXED shape 2 the W contrast is total
between the two sides (this row's sum 1.238..1.240 against the
shape2-W = 32 row's sum 0.915..0.926) and this row's sum band sits
beside the shape2-W = 64 row's sum band (1.223..1.228) and the
shape2-W = 256 row's sum band (1.223..1.230).

**Consequence.** Rule 4: NOTHING MOVES -- no `:measured?` flag, no
`:shapes` value, no selection answer, no workgroup row (this channel
can never move one), no WGSL cell flip, no MSL command-buffer cell
flip, no cross-instrument magnitude claim. The sign stays
CHANNEL-SCOPED and M1-Max scoped. The named item moves in RECORD STATE
only ("shape 2 (n = 2^20) at W = 128" UNMEASURED -> MEASURED at this
protocol's letter, anchor-side class reproduced, roll-up
regime-invariant slower 18/18; shape 2 at W = 512/1024 and R at every
grid stay UNMEASURED). The second-leg evaluation's reopen trigger
class ("a counters-channel record carrying an OPPOSING device-level
sign at any cell/W/day") is NOT exercised by this record (this cell's
sign matches the anchor's) -- the count stays at the shape2-W = 32
row's TWO exercising records (the W = 32 row's sum side-flip at
n = 1000003 and that row's at n = 2^20), both unadjudicated; this row
registers no reopen claim.

Named, not hidden: the same-day fact (this row shares the UTC day
2026-10-26 with the cross-day row's day-2 runs, all five W rows and the
shape2-W = 256, shape2-W = 32 and shape2-W = 64 rows; no day claim
rides here); the reopen-trigger count staying at 2; the fold-arm
artifacts' n-invariance at W = 128 (all six arms byte-identical to the
W = 128 row's build -- checked, not assumed); the band's slight
downward shift against the W = 128 row's pooled band (raw bands at one
instrument, overlap 1.221..1.240); sum's level count moving TWO -> ONE
and min's FOUR -> THREE between the W = 128 cells; run 6 back at the
slow level at max/min (the within-row descent's run boundaries do not
reproduce).

States: MEASURED (the (n = 2^20, W = 128) cell record: 720 resolved
brackets, the instrument-constant ten-cell control, rule 2's
anchor-side verdict, rule 1's regime structure at this grid, the raw
bracket band, the fold arms' n-invariance at W = 128). IMPLEMENTED:
nothing (evidence + prose only). DECIDED: nothing new (the protocol is
the anchor row's). ACCEPTED DESIGN ONLY (unchanged): the claim protocol
and its units; the narrowing and reopen condition; the second-leg
letter; ADR-0355's channel rule. PROPOSED (unchanged): the
Vulkan-provider timestamp route. UNMEASURED, named: shape 2
(n = 2^20) at W = 512/1024; R at every grid (this row's raw band is
not an R decomposition); the W-shape's cause (WHY W = 32 alone flips
side -- this row adds a third anchor-side width at shape 2 and narrows
nothing about the mechanism); the partial tail's quantitative role;
the state-shift cause, threshold and prevalence; day 3+ cross-day
replications; op-order dependence; anything off M1 Max; the WGSL
route's kernel time; every workgroup-row question (`:arm`/`:unknown`
stay provisional `:measured? false` -- no flag, shape, selection answer
or workgroup row moves this tick).

Gates: see the record (self-test 2649/0 pin; scoped GPU gate GREEN
123/12162 twice; FULL `run-tests.cljk` RUN LIVE, red at base "Could not
find namespace: kotoba.form" (ADR-0362), outside this diff, no green
suite claimed; `find docs -name '*.sh'` -> 0).

Record: `docs/evidence/gpu/metal-counter-foldarms-shape2-w128-20261026/`.
