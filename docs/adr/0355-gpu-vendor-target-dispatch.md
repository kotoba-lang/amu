# ADR-0355 -- Per-vendor GPU target dispatch and provisional workgroup defaults

- Status: accepted; v1 dispatch table implemented, workgroup defaults
  provisional and unmeasured
- Date: 2026-10-18

> **Dated note (2026-10-24, ADR 0371).** The GPU execution path this ADR
> refers to is deleted: the C loader `tools/kexe_loader.c`, and wire 42's
> `:gpu/compute` brokered by `tools/kexe_gpu_vulkan.c`. ADR 0371 replaced
> it with a provider process that the static launcher starts and that
> speaks the same wire-42 protocol. Since #1510 two things hold: main's
> compiler refuses that provider's `--format platform-linked` build, and
> its qualifications are outside mandatory native CDCI (`AGENTS.md`). So
> no current route executes a GPU artifact. The text below is kept as
> written.

## Decision

The accelerator pipeline gains one deterministic dispatch table,
`kotoba.compiler.accelerator-targets`, that turns a device descriptor
(`:vendor-id` or `:vendor` name, optional `:api`) into a vendor keyword, one
of ADR-0002's three emission targets, and a workgroup size.

| vendor  | PCI id | api-less default target | provisional workgroup | assumed execution width |
|---------|--------|-------------------------|-----------------------|-------------------------|
| nvidia  | 4318   | cuda-v1                 | 256                   | 32 (warp)               |
| apple   | 4203   | msl-v1                  | 256                   | 32 (SIMD-group)         |
| intel   | 32902  | wgsl-v1                 | 128                   | 8/16/32 (subgroup)      |
| arm     | 5045   | wgsl-v1                 | 128                   | 4-32 (Mali)             |
| amd     | 4098   | wgsl-v1                 | 256                   | 64 (wavefront)          |
| unknown | --     | wgsl-v1                 | 256                   | --                      |

Rules:

1. The functions are TOTAL. An unknown vendor or api answers the documented
   fallback (:unknown / :wgsl-v1 / 256), never a throw. Dispatch time is
   where a refusal costs the most, and a portable default is honest about
   what it is.
2. An api decides its route outright (:cuda ->
   :cuda-v1, :metal -> :msl-v1, :vulkan -> :glsl-v1, :webgpu -> :wgsl-v1). A
   missing or unknown api falls back to the vendor default. Amended
   2026-10-22 by ADR-0359 decision 3: :vulkan answered :wgsl-v1 before;
   Vulkan names no shading language (it opens compiled SPIR-V), and the only
   source-to-SPIR-V path this repository owns is glslang from GLSL. WebGPU
   keeps its language; the api-less vendor defaults are unchanged.
3. The workgroup values are PROVISIONAL DESIGN DEFAULTS: powers of two
   within ADR-0002's [1, 1024] bound that are multiples of each vendor's
   published execution width. Nothing in this repository has measured them.
   `recommend` marks every answer `:measured? false`, and no caller may
   report these values as optimization evidence until hardware measurement
   (tracked as JUN-57..60) replaces the row it stands on. [SUPERSEDED IN
   PART 2026-10-19 by ADR-0358: four of the six rows (:nvidia, :apple,
   :intel, :amd) are MEASURED -- "nothing has measured them" and "every
   answer :measured? false" stopped being true that day, and `recommend`'s
   flag is scoped to each row's one named measured device (uB5G, amended
   2026-10-22). The provisional rule above still binds :arm and :unknown.
   The code docstring that carried the old state was corrected 2026-10-24,
   docs/evidence/gpu/workgroup-prose-rootcause-20261024.txt.]
4. Same descriptor in, same map out. The table adds no nondeterminism to the
   byte-identical artifact regime of ADR-0002.

## Honest state (measured 2026-10-18, amu at 9b946bb2)

- Implemented: the ADR-0002 emitters (WGSL / CUDA C / MSL) and this dispatch
  table with tests.
- Not implemented: wiring accelerator lowering into the compile pipeline (its
  only callers are tests), any CUDA or Metal execution path (the runtime
  `:gpu/compute` wire 42 is Vulkan only, `tools/kexe_gpu_vulkan.c`), and
  every vendor optimization. Device class does not branch the v1 table.
  SUPERSEDED 2026-10-22 -- see the loader-removal bullet below.
- selfhost (`docs/selfhost-priority.md`) is paused at the 2026-10-12
  checkpoint. This work is owner-directed (2026-10-18) alongside it and
  claims no selfhost evidence.
- Loader removal 2026-10-22 (amu 36479076, JUN-29; `docs/c-loader-removal.md`;
  replacement route amu ADR 0371). The `:gpu/compute` execution path named
  above is GONE: the loader's GPU brokers (`tools/kexe_gpu_vulkan.c`,
  `tools/kexe_gpu_metal.m`) and the probe harnesses (`scripts/test-gpu-*.cljk`)
  were removed with the C loader. Wire 42 has no route at any layer today --
  the seed checker refuses it (E2115) and the static runtime serves wires
  35/37/38/39 only. The accepted replacement is ADR 0371's GPU provider
  process: its decision 1 (the platform boundary) is owner-accepted
  2026-10-22 and its steps 1-2 (protocol table, runtime transport) are
  implemented; the provider, launcher and seed admission are NOT. Until
  they land, NO wire-42 measurement is re-takeable on any host, the
  JUN-58 measurement wiring (Apple, this host) is BLOCKED on the provider,
  and the per-vendor workgroup sweep (JUN-57..60 rows) cannot run.
- The measured rows of ADR-0358 keep their provenance and their label:
  measured 2026-10-18/19 through the then-existing loader path on the M1
  Max. They stand as measurements OF THAT PATH. Nothing re-measures them
  today; they are not provisional (the `:measured?` flags stay as ADR-0358
  set them) and they are not re-derivable until a provider answers INFO.

## Consequences

- One place decides vendor -> target -> workgroup. The runtime loader and the
  emitters stop inventing their own defaults as they get wired up.
- Per-vendor optimization (NVIDIA / Apple / Intel / ARM) replaces provisional
  rows with measured ones one row at a time, and flips `:measured?` only for
  rows that carry hardware evidence.
- An unmeasured row is labeled unmeasured in the code and here, so a reader
  can tell a design default from a tuning result without trusting prose.
- Reporting landed before branching (2026-10-19; shape settled 2026-10-22):
  the loader reports device class as its own wire-42 request, `DEVCLASS` ->
  one word (discrete|integrated|virtual|cpu|other -- the chosen device's
  VkPhysicalDeviceType as a stable token, `tools/kexe_gpu_vulkan.c`), and
  `device-class` maps that word into `device-classes` (total: a word outside
  the loader's five answers :unknown). The earlier fifth-INFO-field shape is
  superseded (owner-directed merge 740caee4): the INFO answer is exactly the
  four fields `<device>|<api>|<maxWgX>|<unified>`, and the harnesses read it
  that way (`scripts/test-gpu-compute.cljk` for INFO,
  `scripts/test-gpu-devclass.cljk` for DEVCLASS). SUPERSEDED 2026-10-22
  (36479076): both harnesses and the DEVCLASS producer (the broker) are
  removed. `device-class`'s five-word map stays implemented and tested as a
  pure map; a future ADR-0371 provider must answer the same five words, or
  the map is re-pointed at the provider's class token -- that decision lands
  with the provider, and until then no DEVCLASS answer exists to map. The
  v1 table still does not branch on device class; when a row needs the
  branch, it lands with the measurement that justifies it (JUN-57..60).

## Amendment (2026-10-25, the measurement channel for row flips)

The Consequences bullet "flips `:measured?` only for rows that carry
hardware evidence" gains its channel rule (the 2026-10-25 licensing
decision, record `docs/evidence/gpu/wgsl-wallclock-row-mapping-20261025.txt`):
hardware evidence for a workgroup row is evidence from THE ROW'S OWN
CHANNEL -- the ADR-0358 protocol (one workload shape, six LocalSize
variants differing in nothing else, within-run paired size-vs-size
comparison, each size timed twice with the first submit discarded,
submit->fence host clock) taken on the wire-42 loader path the rows'
provenance names, or its ADR-0371 provider successor once one answers
INFO. A read on any other channel is a route-level measurement OF THAT
CHANNEL and answers no row -- the same provenance discipline that keeps
the ADR-0358 rows labelled "of that path" cuts both ways.

Applied the day it was decided: the 2026-10-25 Chrome 155 Dawn/Metal
wall-clock read of the two WGSL reduce arms (M1 Max) maps onto NO row
-- different route (a third channel even for Apple, where ADR-0358
already disclaims MoltenVK as "not a native Metal path"), different
workload family (reduce kernels, not the one ewise-FMA shape),
arm-vs-arm pairing at fixed W rather than within-run size-vs-size
pairing, and no clock/thermal regime control. Its batch32 argmin
W = 32 in 11/12 shape-op-arm rows (re-derived from the committed log;
the timing commit's "10/12" does not re-derive) would CONTRADICT the
kept `:apple` 256 if it were mapped -- it is not, and the channel rule
is what keeps that contradiction out of the table. No row moves; the
provisional `:arm`/`:unknown` rows stay provisional (`:measured?
false`). REOPEN CONDITION: a row run on the row's own channel
(JUN-57..60, blocked on the ADR-0371 provider) is new evidence, as is
a future amendment that names a new row channel with its own paired
size protocol. Nothing else reopens the mapping.

## Dated note (2026-10-27, JUN-59 probe: the Intel host's ANV step)

The Intel issue's named first step -- "is ANV/mesa usable for
measurement at all?" -- is ANSWERED YES at the fleet's one Intel host
(aiueos-6600hs-1; the 2026-10-18 note's "vulkaninfo shows only
llvmpipe, ANV suspected unsupported" does not reproduce). ANV (Mesa
25.2.8, `xe` kernel driver) enumerates "Intel(R) Graphics (BMG G31)"
(8086:e223, DISCRETE_GPU) with compute-stage subgroups (size 32, all
eight core VkSubgroupFeatureFlagBits) and maxComputeWorkGroupSize
1024; the llvmpipe-only view is exactly the view of an account without
`/dev/dri/renderD128` access (nobody: llvmpipe only, render-node open
denied; aiueos/root: both devices). PROBED host facts, not
optimization evidence: no timing ran, no row moves, and a subgroup
8/16/32 measurement on this host is a future row whose channel
standing under the 2026-10-25 rule is UNDECIDED. Evidence:
`docs/evidence/gpu/intel-anv-probe-20261027/` (record.txt is the
finding). Correction (same day, record.txt section 7): the issue channel
had ALREADY measured the 2026-10-18 llvmpipe-only view as a render-node
permission failure (fixed then by `usermod -aG render murakumo-ci`) and
recorded the loader's wire-42 answer "Intel(R) Graphics (BMG
G31)|1.4.318|1024|0" -- byte-identical to this probe's derived INFO
mapping; this row's account-dependence probe is confirmatory of that
record, not a new mechanism.

## Dated note (2026-10-27, JUN-59 measurement: subgroup 8/16/32, first session)

The probe note's "future row" ran at its own named INSTRUMENT channel
(a standalone instrument on raw ANV, not the loader path, not the
ADR-0371 provider): three fresh processes on aiueos-6600hs-1 (BMG G31
/ ANV) over forced subgroup sizes via VK_EXT_subgroup_size_control.
MEASURED at that channel: forced S=8 is NOT REALIZABLE (minSubgroupSize
= 16 -- the issue's 8/16/32 question narrows to 16 vs 32 + default=32
here); probe-verified S forcing (54/54 cell-runs), bit-exact
correctness (54/54), and the device's first gpu_ns samples -- which
PIN AT THE TIMESTAMP FLOOR (median 31 ticks = 1614.6 ns at every
(op, W, S) cell; the S=16-vs-32 difference is below the quantum at
n = 1000003), so the narrowed P1 (S=32 strictly fastest) is REFUTED at
all six cells as ties and the S=16-vs-32 timing question stays
UNRESOLVED above the floor. Rule 4 binds: no row moves, no `:measured?`
flag moves, the provisional `:arm`/`:unknown` rows stay provisional,
and the channel question of the probe note stays UNDECIDED. Evidence:
`docs/evidence/gpu/anv-subgroupsize-81632-20261027/` (record.txt is the
finding; publication.txt is produced only by analysis.py over the
committed run logs).

## Dated note (2026-10-27, JUN-59 measurement: subgroup 16-vs-32 floor-lifting rerun)

The first session's named residual -- "S=16-vs-32 above the floor stays
UNRESOLVED; a floor-lifting rerun (larger n and/or several dispatches
per timestamp bracket) is PROPOSED" -- ran at its batched-bracket
option (BATCH=64 dispatches per timestamp bracket, same cells, same
host, same INSTRUMENT channel). MEASURED at that channel: the floor is
lifted at every cell (pooled median brackets 229k..277k ticks = 3,583..
4,333 ticks/dispatch, i.e. 7,400-9,000x session 1's 31-tick
single-dispatch bracket), probe-verified forcing (54/54) and bit-exact
correctness (316,440 workgroup results) hold, and at the batched
steady-state metric S=32 is faster than S=16 by 397..1,139 ns/dispatch
(0.2..0.6%) at 5 of 6 (op, W) pooled cells -- CONSISTENT in all three
runs at (sum,256),(max,256),(min,128),(min,256), RUN-SENSITIVE at
(sum,128),(max,128) where run-1 reverses the sign. Also MEASURED
(derived arithmetic over the two sessions' committed logs): the batched
per-dispatch figure (186.6..225.7 us) is ~116-140x session 1's
single-dispatch bracket median -- session 1's single-dispatch bracket
did NOT capture dispatch work (the mechanism of the discrepancy is
UNMEASURED; session 1's record is not rewritten). Rule 4 binds: no row
moves, no `:measured?` flag moves, the provisional `:arm`/`:unknown`
rows stay provisional, and no vendor optimization exists for Intel.
Evidence: `docs/evidence/gpu/anv-subgroupsize-batch64-20261027/`
(record.txt is the finding; publication.txt is produced only by
analysis.py over the committed run logs).

## Dated note (2026-10-27, JUN-59 measurement: subgroup 16-vs-32 sign
replication, batch64 route)

The floor-lifting rerun's named residual -- "(sum,128),(max,128)
RUN-SENSITIVE, run-1 reverses the sign, pooled verdicts NOT reported as
stable, cause UNMEASURED" -- is REPLICATED at the same cells, host and
INSTRUMENT channel with six new fresh processes of the byte-identical
instrument (18/18 corpus+binary digests re-verified against session 2's
committed census before any run). MEASURED at that channel: the sign is
CONSISTENT 32faster 6/6 at ALL SIX (op, W) cells including the two
run-sensitive ones -- the run-1-type reversal DID NOT REPRODUCE in six
same-day fresh processes (pre-registered letter: "not reproduced", NOT
called absent; rare and cross-day recurrence not excluded) -- no
DIP-RUN appears (per-run (op,128,16) med gpu_ticks within ~2.4k ticks
of the median-of-six), forcing reality 108/108 and bit-exact
correctness hold, and the batch64 floor stays lifted everywhere.
Derived arithmetic over the nine processes now on record (the 6 new +
session 2's 3, publication-rep.txt section 7): the two cells are
32faster in 8/9, the sole contrary run being session 2's run-1, whose
cause stays UNMEASURED. Rule 4 binds: no row moves, no `:measured?`
flag moves, the provisional `:arm`/`:unknown` rows stay provisional,
and no vendor optimization exists for Intel. Evidence:
`docs/evidence/gpu/anv-subgroupsize-batch64-rep-20261027/` (record.txt
is the finding; publication-rep.txt is produced only by analysis-rep.py
over the committed run logs).

## Dated note (2026-10-27, JUN-59 measurement: batch-bracket scaling)

Sessions 2-3's named residual -- "isolated single-dispatch timing above
any floor" and the mechanism of the session-1-vs-session-2 per-dispatch
discrepancy UNMEASURED -- is narrowed by the BRACKET-VS-B CURVE of the
batch instrument (B in {1,2,4,8,16,32,64}, the only independent
variable; one binary per B; the archived session-2 source with exactly
one edit). MEASURED at the INSTRUMENT channel: the 31-tick floor of
session 1 is REPRODUCED at B<=2 (31 ticks at all 18 arms at B=1) while
the same runs' host_ns shows 351,956 ns of real work; capture turns on
between B=2 and B=4; the DERIVED per-dispatch figure converges to a
flat band 3,455.69..4,369.81 ticks (B>=16) containing session 2's
3,583..4,333. The S=32-vs-16 sign is 32faster at every evaluable
(B>=4) cell (3/3 runs, one 2/3 split at (min,256) B=4); B<=2 is
floor-pinned and NOT EVALUABLE. WHY the small-B bracket undercounts
stays UNMEASURED (no causal mechanism claimed). Rule 4 binds: no row
moves, no `:measured?` flag moves, and no vendor optimization exists
for Intel. Evidence: `docs/evidence/gpu/anv-batchscale-20261027/`
(record.txt is the finding; publication-s4.txt is produced only by
analysis-s4.py over the committed run logs).

## Dated note (2026-10-27, JUN-59 measurement: timestamp-stage discriminator)

Session 4's named residual -- WHY the small-B bracket undercounts -- is
NARROWED by the TS-STAGE discriminator (the two vkCmdWriteTimestamp
bracket endpoints' pipeline stages as the only independent variable:
tb=(TOP,BOTTOM) control, tt=(TOP,TOP), bb=(BOTTOM,BOTTOM) x BATCH
{1,2,4,64}, 36 fresh processes, one parameterization edit of the
session-4 instrument). MEASURED at the INSTRUMENT channel: the control
arm reproduces session 4 exactly (31-tick floor at B=1, captured band
at B=64); the large-B capture does NOT depend on ts2's stage placement
(tt tracks tb, ratio 1.04..1.07 at 18/18 cells); the B=1 floor is NOT
removable by any of the three stage placements (all arms floor at
25..31 ticks); bb/tb = 1.00 at B=64. The small-B undercount is
invariant to the endpoint stage placements tested; the mechanism stays
UNMEASURED (no causal mechanism claimed). Rule 4 binds: no row moves,
no `:measured?` flag moves, and no vendor optimization exists for
Intel. Evidence: `docs/evidence/gpu/anv-tsstage-20261027/` (record.txt
is the finding; publication-s5.txt is produced only by analysis-s5.py
over the committed run logs).

## Dated note (2026-10-27, JUN-59 measurement: command-count discriminator)

Session 5's named residual -- WHY the small-B bracket undercounts -- is
tested on the observable axis "bracketed COMMAND COUNT vs bracketed
DISPATCH work" (the BARRIER_N knob: up to 7 empty global execution
barriers between ts1 and the BATCH dispatches; 21 fresh processes; ONE
parameterization edit of the session-5 instrument; custody entirely
before any run). MEASURED at the INSTRUMENT channel: at B=1 the
bracket stays at the 31-tick floor at 18/18 cells for N = 0,1,2,3,7
(host_ns ~354 us unchanged) -- empty bracketed commands do not lift
the floor; at EQUAL total bracketed command count (6 commands) the
arms split by >300x: 1 dispatch + 3 barriers = 31 ticks, 2 + 2 = 31,
4 dispatches + 0 barriers = 8,968..11,632 -- the bracket tracks
dispatch content, not command count (observable only; no mechanism
claimed). NAMED, NOT HIDDEN: the frozen C1 capture threshold
(>= 100,000 ticks) was the session-5 B=64 band applied to a
four-dispatch control (session 4's committed B=4 value: 11,674;
session 5's tb B=4: 11,678; measured here: 11,632, reproducing that
point to 0.4%) -- C1 fired branch (b) on the threshold, and per the
frozen protocol C2-C3 are reported but carry NOT EVALUABLE standing;
the defect is in the protocol I froze, disclosed as such, not
retro-fixed. Rule 4 binds: no row moves, no `:measured?` flag moves,
and no vendor optimization exists for Intel. Evidence:
`docs/evidence/gpu/anv-cmdcount-20261027/` (record.txt is the
finding; publication-s6.txt is produced only by analysis-s6.py over
the committed run logs).

## Dated note (2026-10-27, JUN-59 measurement: B-onset localization)

Session 6's named residual -- "why capture turns on between B=2 and
B=4" -- is narrowed on its observable axis: the batch-bracket onset
grid. The instrument is the archived session-6 snapshot used
BYTE-IDENTICAL (zero derivation edits; only the -DBATCH build value
varies, BARRIER_N=0); 21 fresh processes (B in {1,2,3,4,5,6,8}, 3 runs
each); custody entirely before any run. MEASURED at the INSTRUMENT
channel: capture turns on STRICTLY BETWEEN B=2 AND B=3 -- b2n0 sits at
the 31-tick floor (band 31..32) while b3n0 is captured (pooled median
5,520 ticks at (sum,128,S=16), 4,254..5,526 over the 18 cells). The
controls reproduce the committed anchors to +0.05% (B=4: 11,680 vs
11,674) and +0.11% (B=8: 32,951 vs 32,915), and this session's
pre-registered control criteria are numeric per-B agreement (the named
fix for session 6's frozen-threshold defect). The per-dispatch derived
figure is a SEPARATE transition: 1,840 (B=3) and 2,920 (B=4) sit below
the committed flat band 3,455.69..4,369.81 ticks/dispatch, entering it
by B=5 (3,477) and staying inside at B=6,8. Observable only; NO causal
mechanism is claimed or measured. Rule 4 binds: no row moves, no
`:measured?` flag moves, and no vendor optimization exists for Intel.
Evidence: `docs/evidence/gpu/anv-bonset-20261027/` (record.txt is the
finding; publication-s7.txt is produced only by analysis-s7.py over
the committed run logs).

## Dated note (2026-10-27, JUN-59 measurement: work-dose discriminator)

Session 7's named residual -- WHY capture turns on between B=2 and B=3
-- is narrowed on ONE observable axis: is the capture a total-work
threshold at all? The instrument is the archived session-7 snapshot
with a single parameterization edit (the WORK_MUL work-dose knob, 4
hunks, instrument-derivation.diff.txt; WORK_MUL=1 reproduces the
archived behaviour and the controls pin it); 24 fresh processes
(8 (B,M) arms, 3 runs each); custody entirely before any run.
MEASURED at the INSTRUMENT channel: capture at B=2 is NOT reachable by
up to 8x per-dispatch work -- b2m3 (6 work units) and b2m8 (16 work
units, twice the captured b8m1 control's 8) both sit at the 31-tick
floor at all 18 cells while host_ns shows up to 3,143,995 ns of real
work. Equal-total-work pairs split hard by dispatch count: 3 units as
1 dispatch = 31 ticks vs 3 dispatches = 5,546 ticks (captured); 8
units as 1 dispatch = 31 ticks vs 8 dispatches = 32,896 ticks
(captured) -- up to three orders of magnitude apart at equal total
work. On this axis the capture is not a total-work threshold; dispatch
count stays implicated. Observable only; NO causal mechanism is
claimed or measured, and the frozen named limitation stands: one knob
scales work and grid size together. Rule 4 binds: no row moves, no
`:measured?` flag moves, and no vendor optimization exists for Intel.
Evidence: `docs/evidence/gpu/anv-workmul-20261027/` (record.txt is the
finding; publication-s8.txt is produced only by analysis-s8.py over
the committed run logs).

## Dated note (2026-10-27, JUN-59 measurement: per-workgroup-fatness
## discriminator)

Session 9 (INSTRUMENT channel) removes session 8's frozen named
limitation on ONE axis: the new ITERMUL knob is baked into DERIVED
SHADER sources (the reduce body re-runs ITERMUL times per workgroup;
stored values stay bit-identical, VERIFY mismatch 0 over all runs; the
instrument is the byte-identical session-8 snapshot; the grid is the
archived grid at every arm). Custody: base census 6/6 + inverse check
18/18 (strip the 3-line edit -> base bytes) + corpus 16/16 + local-
vs-host all MATCH before any run. 30 fresh processes (10 (B,I) arms,
3 runs each). MEASURED at the INSTRUMENT channel: C1 archived controls
replicate (a3 +0.20%, a8 -0.52% of committed, inside +/-5%); C2 pins
the derivation at I=1 (f1b8 +0.24% of committed 32,915); W1 branch (a)
as frozen (NOMINAL-I): capture at B=2 is not reachable by up to 8
nominal ITERMUL body executions at constant grid (f3b2/f8b2 both at
the 31-tick floor at all 18 cells, 16 nominal units inside f8b2's
bracket -- twice the captured a8b8 control). NAMED, NOT HIDDEN: the
knob's COST realization is marginal and non-monotone (host_ns f3b1
1.57x a1 > f8b1 1.14x a1; f3b2 1.28x a2; f8b2 1.16x a2 for nominal
3x/8x) -- so the frozen W1 wording is nominal-only and a genuinely
cost-8x-heavier workgroup at B=2 stays UNMEASURED; session 8's grid
axis WAS cost-realized (4.63x host growth at nominal 8x). On the two
separated axes: grid-total-work cost-realized and unreachable at B=2
(session 8); per-workgroup-body nominal-only and unreachable at B=2
(this session); dispatch count implicated on both. Observable only; NO
causal mechanism is claimed or measured. Rule 4 binds: no row moves,
no `:measured?` flag moves, and no vendor optimization exists for
Intel. Evidence: `docs/evidence/gpu/anv-itrmul-20261027/` (record.txt
is the finding; publication-s9.txt is produced only by analysis-s9.py
over the committed run logs).

## Dated note (2026-10-27, JUN-59 measurement: GRID x FATNESS
## interaction)

Session 10 (INSTRUMENT channel) tests the GRID x FATNESS interaction
that sessions 8 and 9 both named UNMEASURED: at fixed B=2, is the
capture reachable by the JOINT dose of the two proven knobs (WORK_MUL
grid x ITERMUL per-workgroup fatness)? Everything is a byte-reuse of
committed custody-checked artifacts (instrument = the session-8
snapshot, NO C edit; iter8 sources = session 9's committed derivation,
inverse check re-run 6/6; the rebuilt iter8 spv byte-identical to
session 9's build; all 3 binaries byte-identical to session 8's
same-flag binaries; corpus 16/16 MATCH, custody entirely before any
run). 15 fresh processes (5 arms x 3 runs). MEASURED at the INSTRUMENT
channel: C1 and C2 replicate (c8 -0.62% of committed 32,915; both
knob controls FLOOR at their single-knob readings); X1 branch (a) as
frozen (NOMINAL reading): the joint arm gf (B=2, M=8, I=8 -- 128
nominal work units, 64x the captured control's nominal 8) sits at the
same 31..32-tick FLOOR at all 18 cells while the c8 control (8
nominal units, 8 dispatches) is CAPTURED at 32,710 ticks. With
session 8 (grid axis alone, cost-realized 4.63x, unreachable) and
session 9 (fatness axis alone, nominal, unreachable), the capture is
not a total-work threshold on ANY knob combination tested to date;
dispatch count stays implicated. NAMED, NOT HIDDEN: the joint knob's
cost realization is marginal over the grid knob alone (host_ns gf/c2
5.92x for nominal 64x; gf/g8 = 1.07x -- the fatness knob adds ~7%
realized cost; the grid knob realizes 5.55x here vs session 8's
committed 4.63x), so branch (c) closes the NOMINAL joint axis only
and a genuinely COST-CALIBRATED joint dose at B=2 stays UNMEASURED.
Observable only; NO causal mechanism is claimed or measured. Rule 4
binds: no row moves, no `:measured?` flag moves, and no vendor
optimization exists for Intel. Evidence:
`docs/evidence/gpu/anv-gridfat-20261027/` (record.txt is the finding;
publication-s10.txt is produced only by analysis-s10.py over the
committed run logs).

## Dated note (2026-10-27, JUN-59 measurement: COST-CALIBRATED JOINT
## DOSE, session 11)

Session 11 (INSTRUMENT channel) tests session 10's named residual: at
fixed B=2, is the capture reachable by the joint grid x fatness dose
at COST-CALIBRATED fatness? The itervc8 derivation (session 9's
committed iter8 sources + ONE coherent volatile qualifier edit on the
X buffer, two-level inverse check 6/6 + 6/6, base census 6/6) makes
the ITERMUL loop's per-iteration loads real accesses. 15 fresh
processes (5 arms x 3 runs; custody GO before any build/run; binaries
byte-identical to session 8's same-flag builds; VERIFY mismatch 0).
MEASURED at the INSTRUMENT channel: C1 and C2 replicate (c8 +0.03% of
committed 32,915); V1 fired branch (b) -- THE DERIVATION FAILED ITS
DESIGN CLAIM: f8vc/c2 host_ns = 1.17x, inside the CSE'd/marginal band
(session 9 non-vc 1.14x..1.57x; session 10 f8 1.18x) -- the coherent
volatile qualifier does NOT make the per-workgroup fatness cost-real
on this host; a post-hoc descriptive spv inspection confirms the
Volatile/Coherent decorations ARE in the executed bytes (4
decorations; non-vc contrast 0), so the marginal realization is not
explained by a missing qualifier at the SPIR-V level. K1 branch (b):
cost calibration not achieved (gfvc host_ns 4,080,951 < 2x c8
4,810,712 in-session anchor). K2 branch (a) AS FROZEN, NOMINAL-ONLY:
gfvc (128 nominal units, 2 dispatches) FLOOR (32 ticks) while c8 (8
units, 8 dispatches) CAPTURED (32,926) -- the row residual (a
genuinely cost-calibrated joint dose at B=2) SURVIVES this session,
narrowed: it is not reachable via the volatile-fatness cost route, and
WHY the fatness knob's realization stays marginal is the named next
question. Observable only; NO causal mechanism is claimed or
measured. Rule 4 binds: no row moves, no `:measured?` flag moves, and
no vendor optimization exists for Intel. Evidence:
`docs/evidence/gpu/anv-costcal-20261027/` (record.txt is the finding;
publication-s11.txt is produced only by analysis-s11.py over the
committed run logs).

## Dated note (2026-10-27, JUN-59 measurement: WORK-DOWN LOCALIZER at
## fixed B=8, session 12)

Session 12 (INSTRUMENT channel) runs the reverse axis of sessions
8-11: at fixed dispatch count B=8, is the captured bracket REMOVABLE
by shrinking the per-dispatch work? One C-side derivation (session 8's
snapshot + the 3-hunk NDIV knob, inverse check -> snapshot bytes
EXACT; NO shader derivation -- the corpus is byte-identical) gives 8
dispatches of n = 125,000 / 3,906 / 244 against the captured c8
control's n = 1,000,003. 15 fresh processes (5 arms x 3 runs; custody
GO before any build/run; VERIFY mismatch 0; n identity exact per the
frozen L2 values). MEASURED at the INSTRUMENT channel: C1 replicates
(c2 FLOOR 31; c8 -0.75% of committed 32,915). W1 fired branch (a) as
frozen: d8 (1/8 per-dispatch work, 1.0 total nominal unit -- HALF the
floored c2 control's 2.0) is CAPTURED (5,465 ticks). W2 (pre-
registered, descriptive) BOUNDS that reading: the capture DIES between
NDIV=8 and NDIV=256 -- d256 (n=3,906, a real 31/16-workgroup grid) is
FLOOR (34 ticks) and d4096 (n=244, protocol-L4 near-empty ambiguity
named) is FLOOR. So the capture requires per-dispatch work ABOVE a
threshold inside the (3,906..125,000] element band at B=8 (2 grid
points; no interpolation): NEITHER dispatch count alone (this
session's removal) NOR work alone (sessions 8-11) suffices; dispatch
count >= 3 is necessary but not sufficient, and the per-dispatch work
dependence was invisible from the B<=2 side. W3 (descriptive): d8
(1.0 total unit, 8 dispatches) 5,465 ticks CAPTURED vs c2 (2.0 units,
2 dispatches) 31 FLOOR (ratio 176.3). Observable only; NO causal
mechanism is claimed or measured. Rule 4 binds: no row moves, no
`:measured?` flag moves, and no vendor optimization exists for Intel.
Evidence: `docs/evidence/gpu/anv-workdown-20261027/` (record.txt is
the finding; publication-s12.txt is produced only by analysis-s12.py
over the committed run logs).

## Dated note (2026-10-27, JUN-59 measurement: WORK-THRESHOLD BISECT at
## fixed B=8, session 13)

Session 13 (INSTRUMENT channel) bisects session 12's named residual
("the exact per-dispatch work threshold location inside the
(3,906..125,000] element band at B=8"): three new ladder rungs NDIV
{32,64,128} (n = 31,250 / 15,625 / 7,812) between session 12's d8
(CAPTURED) and d256 (FLOOR). ZERO derivation edits -- the instrument is
session 12's committed NDIV-derived source byte-identical (digest
a5e539f0...; the four rebuilt arms reproduce session 12's binaries
byte-for-byte -- extra build pin); the new arms are new -D values only.
21 fresh processes (7 arms x 3 runs; custody GO before any build/run;
VERIFY mismatch 0; n identity exact per the frozen L2 values). MEASURED
at the INSTRUMENT channel: C1 and C2 replicate (c8 -0.03% of committed
32,915; d8 -0.62% of session 12's 5,465; d256 FLOOR). W1 fired branch
(c) AS FROZEN -- ALL THREE bisect rungs are INTERMEDIATE/MIXED (d32
1,050, d64 403, d128 167 ticks at (sum,128,S=16)): the ladder descends
d8 CAPTURED -> d32/d64/d128 INTERMEDIATE -> d256 FLOOR, so at class
granularity the capture is NOT killed at a single ladder step; the
CAPTURED-class boundary narrows to (31,250..125,000] and the
FLOOR-class boundary to (3,906..7,812] (one named adjacent rung pair
each; no interpolation). W2 (pre-registered, descriptive): the B=8
bracket descends monotonically with per-dispatch work (32,906 / 5,431 /
1,050 / 403 / 167 / 34 at NDIV 1/8/32/64/128/256), within -22%..+32%
of the linear-work comparison c8/NDIV at the top rungs and below it at
the bottom two -- descriptive over 6 grid points, NO linearity claim.
W3 (descriptive): total-work parity inverts at every rung (d128: 1/32
of c2's total work in 8 dispatches = 5.2x c2's floored bracket).
Observable only; NO causal mechanism is claimed or measured. Rule 4
binds: no row moves, no `:measured?` flag moves, and no vendor
optimization exists for Intel. Evidence:
`docs/evidence/gpu/anv-workthresh-20261027/` (record.txt is the
finding; publication-s13.txt is produced only by analysis-s13.py over
the committed run logs).

## Dated note (2026-10-27, JUN-59 measurement: FLOOR-BOUNDARY BISECT at
## fixed B=8, session 14)

Session 14 (INSTRUMENT channel) bisects session 13's FLOOR-class
boundary residual ("the class boundaries' exact locations inside
(31,250..125,000] and (3,906..7,812]", lower half): three new fine
ladder rungs NDIV {160,192,224} (n = 6,250 / 5,208 / 4,464) between
session 13's d128 (INTERMEDIATE/MIXED) and d256 (FLOOR). ZERO
derivation edits -- the instrument is session 13's committed
NDIV-derived source byte-identical (digest a5e539f0...; the four
rebuilt anchors reproduce session 13's binaries byte-for-byte -- extra
build pin); the new arms are new -D values only. 21 fresh processes
(7 arms x 3 runs; custody GO 15:24:51Z before any build/run; VERIFY
mismatch 0; n identity exact per the frozen L2 values). MEASURED at
the INSTRUMENT channel: C1 replicates (c2 FLOOR 31; c8 +0.13% of
committed 32,915) but C2 FIRED BRANCH (b) -- THE BOUNDING ANCHORS DID
NOT REPLICATE at session 13's own settings: d128 192 vs committed 167
(+14.97%, outside the frozen +/-5%) and d256 CHANGED CLASS (committed
FLOOR 34 -> INTERMEDIATE/MIXED 55 ticks at (sum,128,S=16); 18-cell
spread 55..123). W1 is therefore FLAGGED / NOT EVALUABLE at its
letter; the measured classes stand as content: ALL FIVE fine-ladder
rungs are INTERMEDIATE/MIXED this session, so no FLOOR rung exists on
the ladder and NO boundary narrowing is claimed. W2 (pre-registered,
descriptive): the fine-ladder dose curve is NOT monotone in these runs
(d128 192 -> d160 285 UP with a tight 279..292 run-median band ->
d192 84 -> d224 56 -> d256 55); session 13's monotone descent does
not extend to the fine ladder at d160 here. THE FINDING OF THE TICK:
the FLOOR-class boundary at B=8 is not reproducible at class
granularity across two same-day sessions ~31 minutes apart under
byte-identical instrument/manifest/corpus/binaries -- any boundary
claim narrower than the (3,906..7,812] band is unsupported, and the
class-threshold reading of this boundary is itself session-sensitive
(bottom-rung host_ns moved +13%..+48% in the same setup; cause
UNMEASURED). Observable only; NO causal mechanism is claimed or
measured. Rule 4 binds: no row moves, no `:measured?` flag moves, and
no vendor optimization exists for Intel. Evidence:
`docs/evidence/gpu/anv-floorbisect-20261027/` (record.txt is the
finding; publication-s14.txt is produced only by analysis-s14.py over
the committed run logs).

## Dated note (2026-10-27, JUN-59 measurement: THE SESSION-REPLICATION
## TRIPLE at the boundary anchors, session 15)

Session 15 (INSTRUMENT channel) is the THIRD same-day replication
point of the boundary-anchor series (session 13 14:53Z, session 14
15:24Z, session 15 15:55Z -- all UTC 2026-10-27; session 14's named
residual "cross-day replication" is NOT reachable this tick and stays
UNMEASURED -- protocol L8). ZERO derivation edits -- the instrument is
session 14's committed NDIV-derived source byte-identical (digest
a5e539f0...), the same seven (BATCH,NDIV) arms, the same manifest
bytes; the build replication pin is 7/7 (every rebuilt binary
byte-identical to session 14's same-flag binary), so the realization
is byte-stable across sessions 13-15. 21 fresh processes (7 arms x 3
runs; custody GO 15:54:29Z before any build/run; VERIFY mismatch 0;
forcing reality 378/378). MEASURED at the INSTRUMENT channel: C1
replicates (c2 FLOOR 32; c8 32,950 = +0.11% of committed 32,915); C2
lands EXACTLY ON SESSION 13'S COMMITTED READINGS at both anchors --
d256 FLOOR (34 ticks, +0.00%) and d128 167 (+0.00%) -- so W1 fires
branch (a) S13-LIKE: session 14's divergence (d128 192, d256
INTERMEDIATE 55) is the OUTLIER at 2 of 3 same-day sessions, and the
session-sensitivity finding is confirmed but ASYMMETRIC (now centered:
2 of 3 sessions agree at both anchors). W2: the d160 spike SHAPE
reproduces at 2/2 sessions that ran it (177 > d128 167 and > d192 56
here; 285 > 192 and > 84 in s14) but its magnitude is session-variable
(285 -> 177, -37.89%). W3 (descriptive): this session's lower ladder
is monotone with FLOOR from d192 down (d192 56 / d224 35 / d256 34),
which at these rungs alone would place the FLOOR-class boundary inside
(5,208..6,250] -- NO boundary narrowing is claimed, because the class
picture of the band differs in ALL THREE sessions (s13: boundary
inside (3,906..7,812]; s14: no FLOOR rung at all; s15: FLOOR from
d192 down): the boundary's class reading is confirmed
session-sensitive, and any FLOOR-boundary claim at B=8 remains
session-unsupported. X1 (descriptive): the bottom rungs' host_ns
returned to session 13's values (d128 80,330 vs 80,501; d256 82,374
vs 82,303) after session 14's +13%/+48% excursion (0.68x..0.88x of
s14), c8's rose to 1.26x -- the movement sits in the run
environment/host state, cause UNMEASURED. Observable only; NO causal
mechanism is claimed or measured. Rule 4 binds: no row moves, no
`:measured?` flag moves, and no vendor optimization exists for Intel.
Evidence: `docs/evidence/gpu/anv-sessrepl-20261027/` (record.txt is
the finding; publication-s15.txt is produced only by analysis-s15.py
over the committed run logs).

## Dated note (2026-10-27, JUN-59 measurement: THE DISPATCH-COUNT
## LADDER at fixed per-dispatch work, session 16)

Session 16 (INSTRUMENT channel) takes session 15's named residual "any
B outside {2,8}": at fixed per-dispatch work (NDIV=1, the same
n=1,000,003 grid in every arm) the whole dispatch-count ladder B=2..8
is measured -- the first measurement of B in {3,4,5,6,7} anywhere in
the series (the "dispatch count >= 3" reading had been an inference
from the two endpoints only). ZERO derivation edits -- the instrument
is session 15's committed NDIV-derived source byte-identical (digest
a5e539f0...); the new arms are NEW -D BATCH values only; the c2/c8
rebuilt binaries reproduce session 15's binaries byte-for-byte (2/2
build pins; b3..b7 are new knob values with no prior binary -- named).
21 fresh processes (7 arms x 3 runs; custody GO 16:26:58Z before any
build/run; VERIFY mismatch 0; forcing reality 378/378). MEASURED at
the INSTRUMENT channel: C1 replicates (c2 FLOOR 32; c8 32,955 =
+0.12% of committed 32,915) and W1 fires branch (a) CAPTURE-AT-3 --
ALL FIVE new rungs are CAPTURED-class (b3 5,555 / b4 11,656 / b5
17,251 / b6 22,762 / b7 28,037 ticks at (sum,128,S=16), all 18 cells
>= 1000): with the committed c2 FLOOR endpoint at the same
per-dispatch work, the capture-class transition at full work sits at
the DISCRETE B=2 -> B=3 step -- B=2 does not capture, B=3 already
does. W2 (pre-registered, descriptive) the B-dose curve is monotone
non-decreasing (32 / 5,555 / 11,656 / 17,251 / 22,762 / 28,037 /
32,955 over B=2..8), below the named linear-in-B comparison at every
new rung (0.450x..0.973x) and converging at the top (1.001x) --
descriptive, NO linearity claim. Protocol L4 names the remaining
ambiguity: B and total nominal work co-vary in this design, so whether
the threshold is on dispatch count or on total work is UNMEASURED and
needs a crossing design. Observable only; NO causal mechanism is
claimed or measured. Rule 4 binds: no row moves, no `:measured?` flag
moves, and no vendor optimization exists for Intel. Evidence:
`docs/evidence/gpu/anv-dispatchcount-20261027/` (record.txt is the
finding; publication-s16.txt is produced only by analysis-s16.py over
the committed run logs).

CORRECTION (named, not hidden; supersedes the framing claims of the
session-16 note above): the claim "the first measurement of B in
{3,4,5,6,7} anywhere in the series (the 'dispatch count >= 3' reading
had been an inference from the two endpoints only)" is WRONG against
the chain's own history -- session 7 (anv-bonset-20261027) already
measured B in {1,2,3,4,5,6,8} at full work and already narrowed the
capture onset to the discrete B=2 -> B=3 step (committed b3 5,520 /
b4 11,680 / b5 17,386 / b6 22,730). The measured numbers stand
unchanged; the corrected finding is: B=7 (28,037 ticks, CAPTURED-class
-- session 7's own named residual "B=7") completes the integer ladder
B=1..8 at full per-dispatch work, and session 16's b3..b6 readings
independently replicate session 7's committed values same-day at all
four (+0.63% / -0.21% / -0.78% / +0.14%, inside the frozen +/-5%;
c8 +0.01% of session 7's 32,951). The onset step is a REPLICATED
reading (session 7 first), not a new finding. record.txt section 8
carries the full correction; publication-s16.txt was regenerated by
the corrected analysis-s16.py (twice byte-identical).

## Dated note (2026-10-27, JUN-59 measurement: THE CONSTANT-TOTAL-WORK
## CROSSING at NDIV=B, session 17)

Session 17 (INSTRUMENT channel) takes session 16's named residual
(L4: "whether the threshold is on dispatch count or on total work ...
needs a design that crosses them"): for the first time TOTAL nominal
work is HELD CONSTANT (~1.0 = B*n/1,000,003 with n = 1,000,003//B)
across the whole dispatch-count ladder B=2..8 (the x2..x8 rungs), with
the archived c2/c8 controls pinning the environment. ZERO derivation
edits -- the instrument is session 16's committed NDIV-derived source
byte-identical (digest a5e539f0...); the crossing rungs are new
(BATCH,NDIV=B) pairs of its existing knobs. Custody GO 16:58:38Z
before any build/run (corpus 16/16 + 3/3 local-vs-host MATCH); the
rebuilt x8 is BYTE-IDENTICAL to session 13's committed d8 binary and
c2/c8 to session 16's (3/3 build pins). 27 fresh processes
16:58:50Z..16:58:58Z, VERIFY mismatch 0, forcing 486/486. MEASURED at
the INSTRUMENT channel: C1 replicates (c2 FLOOR 31; c8 32,868 =
-0.14% of committed 32,915) and C2 replicates (x8 = d8's knob pair:
5,458 vs committed d8 5,431 = +0.50%, CAPTURED as committed -- the
crossing and work-down ladders join at that grid point). W1 fires
branch (a) RISE-AT-3: the class vector at constant total work is
(FLOOR, CAPTURED x6) over x2..x8 (x2 32 ticks FLOOR; x3..x8 1,578 /
3,108 / 4,012 / 4,738 / 5,191 / 5,458 ticks, all 18 cells >= 1000) --
the capture-class transition sits at the SAME discrete B=2 -> B=3 step
as the NDIV=1 ladder even at constant total work, so among the three
named hypotheses (dispatch count / total work / per-dispatch work+grid)
the class vector carries the DISPATCH-COUNT signature: the flat
(total-work) and falling (per-dispatch-work) signatures are refuted at
class granularity on this ladder, and "B=2 never captures" extends to
n=500,001. W2 (descriptive) the constant-total dose curve is monotone
non-decreasing (32 -> 5,458), sitting at 0.166x..0.286x of the
committed NDIV=1 same-B values for B=3..8 (a named cross-total-work
comparison only). Protocol L2 binds: per-dispatch work and grid size
co-vary with B BY CONSTRUCTION at constant total, so the discrimination
is among the three named hypotheses only; observable only, NO causal
mechanism is claimed or measured. NAMED, NOT HIDDEN: protocol L1's
stated total range is an arithmetic slip (computed totals
0.999996..0.999999 govern -- record.txt section 6); the first recorded
analysis run mis-dispatched W1 to branch (c) via an all-vector
all-CAPTURED test (fixed before commit against the frozen protocol
letters; measured numbers unchanged). Rule 4 binds: no row moves, no
`:measured?` flag moves, and no vendor optimization exists for Intel.
Evidence: `docs/evidence/gpu/anv-consttotal-20261027/` (record.txt is
the finding; publication-s17.txt is produced only by analysis-s17.py
over the committed run logs).

## Dated note (2026-10-27, JUN-59 measurement: THE NDIV=8 DISPATCH
## LADDER at fixed per-dispatch work, session 18)

Session 18 (INSTRUMENT channel) takes session 17's named residual
(L10: "any (B,NDIV) pair with NDIV != B other than the c2/c8
controls"): the NDIV=8 COLUMN of the (B,NDIV) grid is measured for
the first time (rungs y2..y7 = (B,NDIV=8) pairs never compiled
before; y8 == the committed d8 knob pair) -- the DISPATCH-COUNT
ladder at FIXED per-dispatch work n = 125,000 (1/8 of the full grid,
identical in every y arm), with the archived c2/c8 controls pinning
the environment. ZERO derivation edits -- the instrument is session
17's committed NDIV-derived source byte-identical (digest
a5e539f0...). Custody GO 17:24:45Z before any build/run (corpus
16/16 + 3/3 local-vs-host MATCH); the rebuilt y8 is BYTE-IDENTICAL
to session 17's anv-xt-x8 == session 13's committed d8 binary and
c2/c8 to session 17's (3/3 build pins). 27 fresh processes
17:25:31Z..17:25:39Z, VERIFY mismatch 0, forcing 486/486. MEASURED
at the INSTRUMENT channel: C1 replicates (c2 FLOOR 32, band 31..32;
c8 32,830 = -0.26% of committed 32,915) and C2 replicates (y8 =
d8's knob pair: 5,419 vs committed d8 5,431 = -0.22%, CAPTURED as
committed -- the two ladders join at that grid point). W1 fires
branch (c) RISE-GRADIENT / LATER-ONSET: the class vector at fixed
per-dispatch work 0.125 units is (FLOOR, INTERMEDIATE/MIXED,
CAPTURED, CAPTURED, CAPTURED, CAPTURED) over y2..y7 (y2 31 FLOOR; y3
599 INTERMEDIATE/MIXED, 18-cell range 515..606; y4..y7 1,497 /
2,496 / 3,476 / 4,463 CAPTURED-class at all 18 cells; y8 5,419 the
C2 anchor) -- THE CAPTURE-CLASS TRANSITION DOES NOT SIT AT THE
DISCRETE B=2 -> B=3 STEP AT 1/8 PER-DISPATCH WORK: B=3 is
INTERMEDIATE here where NDIV=1 (5,520) and NDIV=B (1,578) are both
CAPTURED-class at B=3, and full CAPTURED arrives at B=4. The
session-17 "dispatch-count signature" does NOT extend unmodified to
this column of the grid: the onset's position on the B ladder
depends on per-dispatch work -- per-dispatch work INTERACTS with the
dispatch count among the named hypotheses (L2 binds: dispatch count
and total work co-vary BY CONSTRUCTION at fixed per-dispatch work;
observable only, NO causal mechanism is claimed or measured). "B=2
never captures" extends to n=125,000 at total work 0.25 (y2 FLOOR
31). W2 (descriptive) the NDIV=8 dose curve is non-decreasing (31 ->
5,419 over B=2..8); W3's named equal-total shape comparison splits
at equal nominal total 0.25: y2 (2 x 125,000) 31 FLOOR measured vs
d32 (8 x 31,250) 1,050 INTERMEDIATE committed (quote-only). NAMED,
NOT HIDDEN: protocol.txt section 2's "10 arms ... = 30 fresh
processes" is an arithmetic slip in the frozen text (the arm table's
9 rows govern: 27 runs -- record.txt section 6). Rule 4 binds: no
row moves, no `:measured?` flag moves, and no vendor optimization
exists for Intel.
Evidence: `docs/evidence/gpu/anv-ndiv8ladder-20261027/` (record.txt is
the finding; publication-s18.txt is produced only by analysis-s18.py
over the committed run logs).

## Dated note (2026-10-27, JUN-59 measurement: THE NDIV=4 DISPATCH
## LADDER at fixed per-dispatch work, session 19)

Session 19 closes the NDIV=4 column of the (B,NDIV) grid at fixed
per-dispatch work (n = 250,000 = 1/4 grid in every z arm; B ladder
z2..z8 + archived c2/c8 controls). ZERO derivation edits -- the
instrument is session 18's committed NDIV-derived source byte-identical
(digest a5e539f0...). Custody GO 17:55:10Z before any build/run
(corpus 16/16 + 3/3 local-vs-host MATCH); z4's rebuilt binary is
BYTE-IDENTICAL to session 17's anv-xt-x4 (== the committed x4 knob
pair) and c2/c8 to session 18's/17's (3/3 build pins). 27 fresh
processes 17:55:50Z..17:55:59Z, VERIFY mismatch 0, forcing 486/486.
MEASURED at the INSTRUMENT channel: C1 replicates (c2 FLOOR 31, band
31..32; c8 32,830 = -0.26% of committed 32,915) and C2 replicates (z4
= x4's knob pair: 3,112 vs committed x4 3,108 = +0.13%, CAPTURED as
committed -- the NDIV=4 column and the NDIV=B ladder join at that grid
point). W1 fires branch (c) RISE-GRADIENT / LATER-ONSET: the class
vector at fixed per-dispatch work 0.25 units is (FLOOR,
INTERMEDIATE/MIXED, CAPTURED, CAPTURED, CAPTURED, CAPTURED, CAPTURED)
over z2..z8 (z2 31 FLOOR; z3 1,140 INTERMEDIATE/MIXED, 18-cell range
991..1,414; z4..z8 3,112 / 5,021 / 7,065 / 9,008 / 10,988
CAPTURED-class at all 18 cells; z4 the C2 anchor) -- THE
CAPTURE-CLASS TRANSITION DOES NOT SIT AT THE DISCRETE B=2 -> B=3 STEP
AT 1/4 PER-DISPATCH WORK EITHER: B=3 is INTERMEDIATE here, where
NDIV=1 (5,520) and NDIV=B (1,578) are CAPTURED-class at B=3 and
NDIV=8 (599) is INTERMEDIATE/MIXED. Among the measured grid points
the B=3 capture threshold in per-dispatch work sits ABOVE 1/4 --
between 1/4 (INTERMEDIATE, measured here) and 1/3 (CAPTURED, session
17) -- and nothing between grid points is interpolated (L5). Session
18's later-onset shape REPRODUCES at a second per-dispatch-work
level: per-dispatch work INTERACTS with the dispatch count among the
named hypotheses at two grid points now; the session-17
"dispatch-count signature" holds only at per-dispatch work >= 1/3
among measured grid points (observable only, NO causal mechanism is
claimed or measured). "B=2 never captures" extends to n=250,000 at
total work 0.5 (z2 FLOOR 31). W2 (descriptive) the NDIV=4 dose curve
is non-decreasing (31 -> 10,988 over B=2..8); W3's named equal-total
shape comparisons split across the FLOOR/CAPTURED divide at totals
0.5, 1.0 and 2.0 (quote-only vs measured). Rule 4 binds: no row
moves, no `:measured?` flag moves, and no vendor optimization exists
for Intel.
Evidence: `docs/evidence/gpu/anv-ndiv4ladder-20261027/` (record.txt is
the finding; publication-s19.txt is produced only by analysis-s19.py
over the committed run logs).

## Dated note (2026-10-27, JUN-59 measurement: THE NDIV=2 DISPATCH
## LADDER at fixed per-dispatch work, session 20)

Session 20 closes the NDIV=2 column of the (B,NDIV) grid at fixed
per-dispatch work (n = 500,001 = 1/2 grid in every w arm; B ladder
w2..w8 + archived c2/c8 controls). ZERO derivation edits -- the
instrument is session 19's committed NDIV-derived source byte-identical
(digest a5e539f0...). Custody GO 18:24:57Z before any build/run
(corpus 16/16 + 3/3 local-vs-host MATCH); w2's rebuilt binary is
BYTE-IDENTICAL to session 17's anv-xt-x2 (== the committed x2 knob
pair) and c2/c8 to session 19's/18's/17's (3/3 build pins). 27 fresh
processes 18:25:31Z..18:25:45Z, VERIFY mismatch 0, forcing 486/486.
MEASURED at the INSTRUMENT channel: C1 replicates (c2 FLOOR 31; c8
32,874 = -0.12% of committed 32,915) and C2 replicates (w2 = x2's
knob pair: 31 vs committed x2 32 = -3.12%, FLOOR as committed -- the
NDIV=2 column and the NDIV=B ladder join at that grid point). W1
fires branch (a) ONSET-AT-3: the class vector at fixed per-dispatch
work 0.5 units is (FLOOR, CAPTURED, CAPTURED, CAPTURED, CAPTURED,
CAPTURED, CAPTURED) over w2..w8 (w2 31 FLOOR; w3 2,739; w4..w8 6,227
/ 9,907 / 13,456 / 16,919 / 20,254 CAPTURED-class at all 18 cells; w2
the C2 anchor) -- AT PER-DISPATCH WORK 1/2 THE CAPTURE-CLASS
TRANSITION SITS AT THE SAME DISCRETE B=2 -> B=3 STEP as at NDIV=1
(sessions 7/16) and NDIV=B (session 17). The later-onset shape of
sessions 18/19 is specific to per-dispatch work <= 1/4 among the
measured grid points; the B=3 capture threshold in per-dispatch work
sits in (1/4, 1/3] with 1/2 above it -- five B=3 grid points now
stand: 1.0 (5,520), 1/2 (2,739) and 1/3 (1,578) CAPTURED, 1/4
(1,140) and 1/8 (599) INTERMEDIATE/MIXED, a monotone picture across
the measured grid points (L5: nothing between grid points is
interpolated; observable only, NO causal mechanism is claimed or
measured). "B=2 never captures" extends to n=500,001 at total work
1.0 (w2 FLOOR 31). W2 (descriptive) the NDIV=2 dose curve is
non-decreasing (31 -> 20,254 over B=2..8); W3's named equal-total
shape comparisons split across the FLOOR/CAPTURED divide at totals
1.0 and 2.0 (quote-only vs measured). NAMED, NOT HIDDEN: X1's
host-side proxy excursion at the two B=2 arms (c2 host_ns 828,254 =
1.22x sessions 17-19; w2 563,461 = 1.43x session-17's x2) while their
GPU brackets replicate in-band and c8's host_ns is flat -- host_ns is
not a C criterion (L3), cause UNMEASURED. Rule 4 binds: no row moves,
no `:measured?` flag moves, and no vendor optimization exists for
Intel.

Evidence: `docs/evidence/gpu/anv-ndiv2ladder-20261027/` (record.txt is
the finding; publication-s20.txt is produced only by analysis-s20.py
over the committed run logs).

## 2026-10-27 -- session 21 (JUN-59): the B=3 per-dispatch-work threshold bisect

The session-20 residual "the B=3 per-dispatch threshold BETWEEN grid
points" is taken at the bracket's EXACT floor midpoint: n = 291,667 =
(1,000,003\*7)//24 (the (WORK_MUL,NDIV) = (7,24) knob pair of the
byte-identical NDIV-derived instrument; ZERO derivation edits). With
both bracket ends replicating IN-SESSION at byte-identical rebuilt
binaries (lo == committed z3 knob 1,162 vs 1,140 INTERMEDIATE/MIXED;
hi == committed x3 knob 1,567 vs 1,578 CAPTURED), mid is CAPTURED
(1,330; 18-cell min 1,151), so THE B=3 CLASS FLIP SITS IN (250,000,
291,667] n-units = (0.2499993, 0.2916657] work-units -- the (1/4, 1/3]
bracket is HALVED. "B=2 never captures" extends to n=291,667 (b2m
FLOOR 31). C3 measures the first WORK_MUL!=1 + NDIV!=1 compilation
anywhere in the series ((2,2) at n == c2's grid): FLOOR, class-
identical to (1,1) at the same n. The B=3 class-vs-per-dispatch-work
row now stands at six monotone grid points (class granularity only).
NAMED, NOT HIDDEN: X1's host-side proxy excursion at lo (966,683 =
3.167x session 19's same-knob z3) while its GPU bracket replicated
in-band -- host_ns is not a C criterion (L3), cause UNMEASURED.
Rule 4 binds: no row moves, no `:measured?` flag moves, and no vendor
optimization exists for Intel.

Evidence: `docs/evidence/gpu/anv-b3bisect-20261027/` (record.txt is
the finding; publication-s21.txt is produced only by analysis-s21.py
over the committed run logs).

## 2026-10-27 -- session 22 (JUN-59): the B=3 threshold bisect, second cut

The session-21 residual "the flip location inside (250,000, 291,667]"
is taken at n = 270,834 = (1,000,003\*13)//48 -- the nearest reachable
grid point to the exact floor midpoint 270,833 (unreachable at the
knob; session 21's record parenthetical "(1,000,003\*9)//33" is an
arithmetic slip, 272,728 != 270,833 -- named, not erased). With both
bracket ends replicating IN-SESSION at byte-identical rebuilt binaries
(lo == committed z3 knob 1,141 vs 1,140 INTERMEDIATE/MIXED; hi ==
session 21's (7,24) knob 1,320 vs 1,330 CAPTURED -- the pair's first
cross-session replication), mid is CAPTURED (1,224; 18-cell min
1,061), so THE B=3 CLASS FLIP SITS IN (250,000, 270,834] n-units =
(0.2499993, 0.2708332] work-units -- the session-21 bracket is cut to
its lower half. "B=2 never captures" extends to n=270,834 (b2m FLOOR
32). C3 (branch (a)): the same-ratio pair (26,96) is behaviourally
equivalent to (13,48) at the bisect grid (1,218 vs 1,224). The B=3
class-vs-per-dispatch-work row now stands at seven monotone grid
points (class granularity only). NAMED, NOT HIDDEN: X1's lo host_ns
excursion of session 21 (966,683) has reverted here (302,655 =
0.992x session 19's z3) -- host_ns is not a C criterion (L3), cause
UNMEASURED. Rule 4 binds: no row moves, no `:measured?` flag moves,
and no vendor optimization exists for Intel.

Evidence: `docs/evidence/gpu/anv-b3bisect2-20261027/` (record.txt is
the finding; publication-s22.txt is produced only by analysis-s22.py
over the committed run logs).

## 2026-10-27 -- session 23 (JUN-59): the B=3 threshold bisect, third cut

The session-22 residual "the flip location inside (250,000, 270,834]"
is taken at n = 260,417 = (250,000+270,834)//2 -- this time the EXACT
floor midpoint of the bracket IS reachable at the knob (81
(1,000,003\*WORK_MUL)//NDIV == 260,417 pairs; smallest (25,96), its
double (50,192) the eq3 arm). With both bracket ends replicating
IN-SESSION at byte-identical rebuilt binaries (lo == committed z3 knob
1,129 vs 1,140 INTERMEDIATE/MIXED; hi == session 22's (13,48) knob
1,229 vs 1,224 CAPTURED -- the pair's first cross-session replication),
mid is CAPTURED (1,186; 18-cell min 1,026), so THE B=3 CLASS FLIP
SITS IN (250,000, 260,417] n-units = (0.2499993, 0.2604162]
work-units -- the session-22 bracket is cut to its lower half.
"B=2 never captures" extends to n=260,417 (b2m FLOOR 31). C3 (branch
(a)): the same-ratio pair (50,192) is behaviourally equivalent to
(25,96) at the bisect grid (1,190 vs 1,186). The B=3
class-vs-per-dispatch-work row now stands at eight monotone grid
points (class granularity only). Rule 4 binds: no row moves, no
`:measured?` flag moves, and no vendor optimization exists for Intel.

Evidence: `docs/evidence/gpu/anv-b3bisect3-20261027/` (record.txt is
the finding; publication-s23.txt is produced only by analysis-s23.py
over the committed run logs).

## 2026-10-27 -- session 24 (JUN-59): the B=3 threshold bisect, fourth cut

The session-23 residual "the flip location inside (250,000, 260,417]"
is taken at n = 255,208 = (250,000+260,417)//2 -- the exact floor
midpoint (bracket midpoint 255,208.5, not an integer) IS reachable at
the knob (18 (1,000,003\*WORK_MUL)//NDIV == 255,208 pairs in the
sessions 21-23 search box; smallest (1213,4753); ZERO of the 18 have
their same-ratio double in-box, so the eq3 arm uses the double
(2426,9506) outside that box -- a search convenience, not a source
limit). With both bracket ends replicating IN-SESSION at
byte-identical rebuilt binaries (lo == committed z3 knob 1,141 vs
1,140 INTERMEDIATE/MIXED; hi == session 23's (25,96) knob 1,186 vs
1,186 CAPTURED -- the pair's first cross-session replication), mid is
CAPTURED (1,166; 18-cell min 1,000 -- exactly at the frozen >=1000
threshold), so THE B=3 CLASS FLIP SITS IN (250,000, 255,208] n-units
= (0.2499993, 0.2552072] work-units -- the session-23 bracket is cut
to its lower half. NAMED, NOT HIDDEN: the pre-registered C3
pair-representation check fired branch (b) -- the same-ratio twin
(2426,9506) at the identical grid classifies INTERMEDIATE/MIXED
(18-cell min 994) while mid classifies CAPTURED (18-cell min EXACTLY
1,000) at medians within 0.8% (1,157 vs 1,166): the same-ratio
representation flips the class AT the frozen 1000-tick boundary at
this grid and B; the contradiction stands as measured content, is not
resolved here, and mid/b2m carry the frozen letter's flagged risk.
"B=2 never captures" extends to n=255,208 (b2m FLOOR 31). The B=3
class-vs-per-dispatch-work row now stands at nine grid points (class
granularity only). Rule 4 binds: no row moves, no `:measured?` flag
moves, and no vendor optimization exists for Intel.

Evidence: `docs/evidence/gpu/anv-b3bisect4-20261027/` (record.txt is
the finding; publication-s24.txt is produced only by analysis-s24.py
over the committed run logs).

## 2026-10-27 -- session 25 (JUN-59): the B=3 threshold bisect, fifth cut

The session-24 residual "the flip location inside (250,000, 255,208]"
is taken at n = 252,604 = (250,000+255,208)//2 -- the exact floor
midpoint (bracket midpoint 252,604.0, an integer) IS reachable at the
knob (41 (1,000,003\*WORK_MUL)//NDIV == 252,604 pairs in the sessions
21-24 search box; smallest (97,384); 13 of the 41 have their
same-ratio double in-box, so the eq3 arm uses the in-box double
(194,768)). With both bracket ends replicating IN-SESSION at
byte-identical rebuilt binaries (lo == committed z3 knob 1,159 vs
1,140 INTERMEDIATE/MIXED; hi == session 24's (1213,4753) knob 1,166 vs
1,166 CAPTURED -- the pair's first cross-session replication, exact at
the median), mid is INTERMEDIATE/MIXED (1,153; 18-cell range
994..1,411), so THE B=3 CLASS FLIP SITS IN (252,604, 255,208] n-units
= (0.2526032, 0.2552072] work-units -- the session-24 bracket is cut
to its UPPER half (the first cut in this bisect that moves the lower
bound up). The pre-registered C3 pair-representation check fired
branch (a): the same-ratio twin (194,768) is class-identical to mid
(97,384) at this grid (1,147 vs 1,153) -- session 24's same-grid
class split did NOT recur here and its threshold-artifact-vs-
representation question stays unresolved. NAMED, NOT HIDDEN: the
mid/hi class split at this bracket is a frozen-1000-tick-threshold
split within a narrow 18-cell min band (994..1,005) at overlapping
medians. "B=2 never captures" extends to n=252,604 (b2m FLOOR 31).
The B=3 class-vs-per-dispatch-work row now stands at ten grid points
(class granularity only). Rule 4 binds: no row moves, no `:measured?`
flag moves, and no vendor optimization exists for Intel.

Evidence: `docs/evidence/gpu/anv-b3bisect5-20261027/` (record.txt is
the finding; publication-s25.txt is produced only by analysis-s25.py
over the committed run logs).

## 2026-10-27 -- session 26 (JUN-59): the B=3 threshold bisect, sixth cut

The session-25 residual "the flip location inside (252,604, 255,208]"
is taken at n = 253,906 = (252,604+255,208)//2 -- the exact floor
midpoint (bracket midpoint 253,906.0, an integer) IS reachable at the
knob (18 (1,000,003\*WORK_MUL)//NDIV == 253,906 pairs in the sessions
21-25 search box; smallest (1024,4033); exactly 1 of the 18 has its
same-ratio double in-box -- and it is the smallest -- so the eq3 arm
uses the in-box double (2048,8066)). With both bracket ends
replicating IN-SESSION at byte-identical rebuilt binaries (lo ==
session 25's (97,384) knob 1,141 vs 1,153 INTERMEDIATE/MIXED -- the
pair's first cross-session replication; hi == session 25's
(1213,4753) knob 1,156 vs 1,166 CAPTURED), mid is CAPTURED (1,129;
18-cell range 1,001..1,435), so THE B=3 CLASS FLIP SITS IN (252,604,
253,906] n-units = (0.2526032, 0.2539052] work-units -- the
session-25 bracket is cut to its LOWER half. NAMED, NOT HIDDEN: the
pre-registered C3 pair-representation check fired branch (b) AGAIN --
the same-ratio twin (2048,8066) is INTERMEDIATE/MIXED (1,145) while
mid (1024,4033) is CAPTURED (1,129) at identical n and B, the 18-cell
minima splitting AT the frozen 1000-tick threshold (1,001 vs 985) at
overlapping medians -- the second same-grid class split in three
sessions (session 24's split, session 25's agreement), so the
threshold-artifact-vs-representation question stays unresolved and
W1's narrowing rides on the min-1,001 side of the split. The
session-25 systematic host_ns excursion reverted (lo 0.621x its
same-knob value, hi 0.666x) while every GPU bracket replicated
in-band. "B=2 never captures" extends to n=253,906 (b2m FLOOR 32).
The B=3 class-vs-per-dispatch-work row now stands at eleven grid
points (class granularity only). Rule 4 binds: no row moves, no
`:measured?` flag moves, and no vendor optimization exists for Intel.

Evidence: `docs/evidence/gpu/anv-b3bisect6-20261027/` (record.txt is
the finding; publication-s26.txt is produced only by analysis-s26.py
over the committed run logs).

## 2026-10-27 -- session 27 (JUN-59): the B=3 threshold bisect, seventh cut

The session-26 residual "the flip location inside (252,604, 253,906]"
is taken at n = 253,255 = (252,604+253,906)//2 -- the exact floor
midpoint (bracket midpoint 253,255.0, an integer) IS reachable at the
knob (35 (1,000,003\*WORK_MUL)//NDIV == 253,255 pairs in the sessions
21-26 search box; smallest (214,845); 9 of the 35 have their
same-ratio double in-box -- including the smallest -- so the eq3 arm
uses the in-box double (428,1690)). The cut is FLAGGED at its frozen
letter: the upper bracket anchor ((1024,4033) at n=253,906, rebuilt
BYTE-IDENTICAL to session 26's binary) flipped class ACROSS SESSIONS
-- CAPTURED in session 26 (18-cell min 1,001) to INTERMEDIATE/MIXED
here (min 976) at medians within 0.27% (1,129 vs 1,132) -- so the
pre-registered C2 letter fired (b) exactly as written and W1 is (d)
FLAGGED: NO bracket narrowing is claimed and the flip location stays
inside (252,604, 253,906]. The measured classes stand as content:
mid (B=3, n=253,255) INTERMEDIATE/MIXED (1,136; 18-cell 988..1,446);
the same-ratio twin (428,1690) agrees at that grid (C3 (a), 1,134 vs
1,136) -- the threshold-artifact-vs-representation scoreboard is now
two splitting grids (sessions 24, 26) and two agreeing grids
(sessions 25, 27), UNRESOLVED; "B=2 never captures" extends to
n=253,255 (b2m FLOOR 32). NAMED, NOT HIDDEN: the same grid n=253,906
now carries two readings of different class across sessions at a
byte-identical binary, and the frozen-1000-tick-threshold class
instability near the boundary is measured both as a same-ratio twin
split (session 26) and as a cross-session single-pair flip (this
session). The B=3 class-vs-per-dispatch-work row stands at twelve
grid points (class granularity only). Rule 4 binds: no row moves, no
`:measured?` flag moves, and no vendor optimization exists for Intel.

Evidence: `docs/evidence/gpu/anv-b3bisect7-20261027/` (record.txt is
the finding; publication-s27.txt is produced only by analysis-s27.py
over the committed run logs).

## 2026-10-27 -- session 28 (JUN-59): the (1024,4033) anchor-class
recurrence read

The session-27 residual "the recurrence rate of the (1024,4033)
cross-session class flip -- one flip observed, no rate measured" is
taken at the pair's THIRD reading (n=253,906 = (1,000,003\*1024)//4033,
B=3, binary rebuilt BYTE-IDENTICAL to session 26's), with the
same-ratio twin (2048,8066)'s SECOND reading alongside and ZERO
derivation edits / ZERO new knob pairs. THE FLIP RECURS: the reading
sequence at a byte-identical binary and indistinguishable medians
(1,129 / 1,132 / 1,131 -- a 0.27% span) is CAPTURED (session 26,
18-cell min 1,001) / INTERMEDIATE/MIXED (session 27, min 976) /
INTERMEDIATE/MIXED (this session, min 991), so the pre-registered C2
letter fired (b) and W1 is (b): the anchor's class is UNSTABLE across
sessions at the frozen 1000-tick boundary (all three minima within 25
ticks of it) and NO bracket narrowing is claimed -- the flip location
stays inside (252,604, 253,906]. NAMED, NOT HIDDEN: one session adds
one reading; the recurrence RATE stays a multi-session quantity (3
readings: 1 CAPTURED / 2 MIXED -- the sequence, not a rate). The
same-ratio twin agrees at the grid this time (C3 (a), 1,141 vs 1,131,
both INTERMEDIATE/MIXED -- session 26's same-pair split at this grid
did NOT recur), so the threshold-artifact-vs-representation scoreboard
reads two splitting grids (sessions 24, 26) and three agreeing grids
(sessions 25, 27, 28), UNRESOLVED. Controls replicate (C1 (a): c2
FLOOR 32, c8 32,899 vs committed 32,915). Rule 4 binds: no row moves,
no `:measured?` flag moves, and no vendor optimization exists for
Intel.

Evidence: `docs/evidence/gpu/anv-b3anchorrec-20261027/` (record.txt is
the finding; publication-s28.txt is produced only by analysis-s28.py
over the committed run logs).

## 2026-10-27 -- session 29 (JUN-59): the within-session block-variability
read of the (1024,4033) anchor

Session 28's residuals "whether the flips ... are threshold artifacts or
representation effects" and "the anchor-class question is settled at a
pre-registered bar, which three same-day readings do NOT settle" are
taken on their WITHIN-SESSION component (cross-UTC-day replication is
not reachable this tick -- the runs end 23:12:13Z on UTC day
2026-10-27): the (1024,4033) knob pair at n=253,906, B=3 is measured
FOUR times within ONE session as four 3-run blocks (the same estimator
unit every cross-session reading used) of one byte-identical rebuilt
binary (the pair's third cross-session rebuild, a6c31b6c...), with the
archived controls c2/c8 bracketing the hi window and ZERO derivation
edits / ZERO new knob pairs. THE CLASS IS STABLE WITHIN THE SESSION:
all four blocks classify INTERMEDIATE/MIXED at in-band medians (1,130 /
1,144 / 1,143 / 1,151; 18-cell minima 993 / 979 / 985 / 993 -- all
below the frozen 1,000 boundary), so the pre-registered C2 letter fired
(a) and W1 is (a): the cross-session class flip (1,129 CAPTURED /
1,132 MIXED / 1,131 MIXED at byte-identical binaries) is NOT
within-session block-level noise at the frozen 3-run unit, the
anchor-class settling bar (a cross-session bar) is NOT met by
same-UTC-day data, and NO bracket narrowing is claimed -- the flip
location stays inside (252,604, 253,906]. NAMED, NOT HIDDEN: the 12
per-run minima (descriptive; the per-run unit is 25 rounds per cell,
not the frozen unit) span 971..1,001 with ONE per-run minimum at the
boundary (r3, 1,001) -- the minimum statistic wanders at run
granularity inside a session whose every block reads the same class;
what that implies for the cross-session flips is UNMEASURED and the
threshold-artifact-vs-representation question's REPRESENTATION side is
not probed (the twin (2048,8066) did not run; scoreboard carried, not
advanced). Four blocks give four readings; no flip rate and no causal
mechanism is claimed. Controls replicate (C1 (a): c2 FLOOR 31, c8
32,903 vs committed 32,915); the session-28 c8 host_ns excursion
reverted (0.785x, back in the sessions 26/27 band; cause UNMEASURED).
Rule 4 binds: no row moves, no `:measured?` flag moves, and no vendor
optimization exists for Intel.

Evidence: `docs/evidence/gpu/anv-b3blockvar-20261027/` (record.txt is
the finding; publication-s29.txt is produced only by analysis-s29.py
over the committed run logs).

## 2026-10-27 -- session 30 (JUN-59): the anchor-class settling bar
(design slice -- nothing measured)

Session 29's named next row is taken as a DESIGN decision, and it is
taken BEFORE the readings it judges exist: the bar is frozen
pre-registration at 2026-10-27T23:40:56Z, on the same UTC day as
sessions 2-29, while the first cross-UTC-day tick becomes reachable at
2026-10-28T00:00Z on this profile's 15-minute cron cadence (ticks after
the UTC day roll run natively on day 2026-10-28 -- no tick ever needs
to wait across the roll). A bar written after the readings it judges is
post-hoc; this one names its floor first. THE BAR (accepted design
only): a READING is one 3-run block at the frozen estimator unit at the
anchor (BATCH=3, WORK_MUL=1024, NDIV=4033, n=253,906), byte-identical
build pin, C1 (a), VERIFY 0, custody GO; COUNTED is the FIRST
qualifying reading of each UTC day (the L4 axis must be spanned; later
same-day sessions are named descriptive content and do not advance the
bar; FLAGGED sessions -- C1 (b), VERIFY mismatch, broken pin, missing
GO -- consume no day slot); four COUNTED readings from four distinct
UTC days, one class at the frozen section-4 threshold, every median
within +/-5% of each frozen reference 1,129 / 1,132 / 1,131 and
mutually within 5%, SETTLE the anchor's class; a class split is
UNSETTLED with NO SILENT EXTENSION (an extension is a new pre-registered
bar, never a re-roll), and any FLOOR or out-of-band median is the
pre-named CONTRADICTION. The bar settles ONLY the anchor's class at the
frozen threshold: it never narrows the flip bracket (252,604,
253,906], never interpolates, never judges the (2048,8066) twin, and
moves no Rule 4 row. Its floor is named from measured content
(quote-only here): session 29's four-block within-session stability
(4/4 INTERMEDIATE/MIXED at in-band medians 1,130/1,144/1,143/1,151)
and the min-statistic wander (per-run minima 971..1,001, only r3
at/above the frozen 1,000 boundary -- the class boundary sits inside
the measured noise floor of the minimum statistic). The number FOUR is
a design choice matching the four-block floor, not a measured
constant; whether four days is enough is UNMEASURED (the bar can
return UNSETTLED, in which case the representation-side probe -- the
twin, the open half of the sessions 24/26 C3 (b) splits -- is the
named priority). The decision procedure is committed as the
deterministic evaluator `settle-bar-eval.py` with a frozen fixture set
(38 assertions, 0 failed, run twice byte-identical) -- evidence-scoped
tooling, not compiler code. Rule 4 binds: nothing measured this tick
(every number above is quote-only, re-derived in the committed
census), no row moves, no `:measured?` flag moves, and no vendor
optimization exists for Intel.

Evidence: `docs/evidence/gpu/anv-b3settlebar-20261027/` (settle-bar.txt
is the frozen pre-registration; record.txt is the finding;
derivation-census-s30.txt re-derives every cited measured number from
sessions 26-29's committed run logs).

## 2026-10-28 -- session 31 (JUN-59): the first bar-executing session
-- the first cross-UTC-day anchor reading

The bar's L4 axis is spanned for the first time. This tick runs
natively on UTC day 2026-10-28 (protocol freeze stamp 00:04:50Z, run
window 00:06:33Z..00:06:39Z) -- sessions 2-29 all ran on 2026-10-27 --
and takes ONE reading in the bar's frozen unit: one 3-run block of the
(1024,4033) anchor (BATCH=3, WORK_MUL=1024, NDIV=4033, n=253,906,
B=3) at a byte-identical rebuilt binary (a6c31b6c... -- the pair's
fourth cross-session rebuild), with the archived controls c2/c8
bracketing the window. MEASURED: the reading classifies
INTERMEDIATE/MIXED at (sum,128,S=16) pooled median 1,142 (18-cell
985..1,436) over 3 runs x 25 rounds per cell, IN-BAND vs the frozen
references 1,129 / 1,132 / 1,131; C1 (a) (c2 FLOOR 31; c8 32,688 vs
committed 32,915, -0.69%); VERIFY mismatch 0 everywhere (9 fresh
processes, rc=0 9/9, forcing 162/162, S=8 fail-closed 54/54,
host-mtime cross-check 9/9). QUALIFYING under the bar (B1 (a)): the
reading is COUNTED 1/4 -- the first qualifying reading of its UTC day
-- and the frozen evaluator `settle-bar-eval.py` over the append-only
ledger (created this tick, `docs/evidence/gpu/settle-bar-ledger.txt`)
returns VERDICT: PENDING 1/4 (run twice byte-identical; fixture
self-test pin 38/0). Nothing settles at one day: at least three more
qualifying UTC days are needed and FLAGGED days do not shorten the
count. Named, not hidden: the ledger-construction decision (the ledger
starts with the first bar-executing session; sessions 26-29's readings
are the bar's quote-only reference basis, not backfilled entries --
the alternative reading is arguable and was frozen out before the runs
in protocol section 0) and an X1 host-side excursion (hi host_ns
875,403 = ~2.83x every same-knob prior while both controls and every
GPU-side bracket replicate in band -- host_ns is the L3 proxy, cause
UNMEASURED). The reading's min 985 sits inside the measured
min-statistic wander (971..1,001) -- whether day 28's class is day
structure or that wander is UNMEASURED. Rule 4 binds: the bar moves
nothing; accelerator-targets defaults remain provisional
(`:measured? false`); no row moves and no vendor optimization exists
for Intel.

Evidence: `docs/evidence/gpu/anv-b3xday-20261028/` (protocol.txt is
the frozen pre-registration incl. the ledger-construction decision;
publication-s31.txt is the measurement; bar-eval-s31.txt is the
frozen evaluator's verdict; record.txt is the finding) and
`docs/evidence/gpu/settle-bar-ledger.txt` (the append-only ledger).

## 2026-10-28 -- session 32 (JUN-59): the within-day recurrence read
of the session-31 hi host_ns excursion

The bar's UTC-day 2026-10-28 slot is consumed by session 31 (COUNTED
1/4; next executable day slot 2026-10-29), so this tick takes one of
s31's named residuals instead of bar content: the X1 host-side
excursion (hi host_ns 875,403 = ~2.83x every same-knob prior, cause
UNMEASURED). ONE measurement slice, pre-registered before the runs
(protocol freeze stamp 2026-10-28T00:39:07Z): a second same-UTC-day
3-run block of the (1024,4033) anchor (B=3, n=253,906) at a
byte-identical rebuilt binary (a6c31b6c... -- the pair's fifth
cross-session rebuild; 3/3 pins byte-identical), controls c2/c8
bracketing, custody GO 00:40:34Z before builds and all runs. MEASURED:
the excursion DID NOT RECUR -- hi pooled host_ns 304,999 = frozen X1R
letter (a) REVERTED (0.984x-0.990x every same-knob prior
309,848/310,008/309,647/308,129; 0.348x session-31's 875,403; per-run
304,729..305,961), with C1 (a), VERIFY 0 everywhere (9 fresh
processes, rc=0 9/9, forcing 162/162, host-mtime cross-check 9/9).
Descriptive same-day content: the second 2026-10-28 anchor reading
classifies INTERMEDIATE/MIXED at 1,128 (18-cell 982..1,421), in-band
vs the frozen refs 1,129/1,132/1,131; the F2 min-statistic wander
carries (block min 982, per-run minima 986/972/989 inside 971..1,001).
Under settle-bar.txt section 2 the block is NAMED DESCRIPTIVE CONTENT:
its ledger line (appended after a scratch-copy evaluator test) is
classified descriptive by the frozen evaluator (same-day-duplicate
exclusion) and the verdict is UNCHANGED -- PENDING 1/4 with s31
counted (settle-bar-eval.py run twice byte-identical; fixture pin
38/0). Named, not hidden: one non-recurrence observation bounds
nothing about cause -- the excursion's cause remains UNMEASURED and no
causal mechanism is claimed (two observations of the same knob in one
day: one excursion, one non-recurrence). Rule 4 binds: the bar moves
nothing; accelerator-targets defaults remain provisional
(`:measured? false`); no row moves and no vendor optimization exists
for Intel.

Evidence: `docs/evidence/gpu/anv-b3x1rec-20261028/` (protocol.txt is
the frozen pre-registration incl. the X1R letters; publication-s32.txt is
the measurement; bar-eval-s32.txt is the frozen evaluator's verdict;
record.txt is the finding) and
`docs/evidence/gpu/settle-bar-ledger.txt` (the append-only ledger).

## 2026-10-28 -- session 33 (JUN-59): the representation-side re-read
(the pair-twin class relation at the anchor grid)

The bar's UTC-day 2026-10-28 slot is consumed by session 31 (COUNTED
1/4; next executable day slot 2026-10-29) and the bar never judges
the twin, so this tick takes session 29's named-not-probed residual
("the REPRESENTATION side of threshold-artifact-vs-representation is
NOT probed this session (the twin (2048,8066) did not run; scoreboard
carried, not advanced)"), which session 30 named the priority. ONE
measurement slice, pre-registered before the runs (protocol freeze
stamp 2026-10-28T01:08:56Z): one 3-run block of the (1024,4033) pair
and one of its same-ratio twin (2048,8066), both at the identical
grid n=253,906, B=3, at byte-identical rebuilt binaries (hi
a6c31b6c = the pair's sixth cross-session rebuild; tw bb901eb5 = the
twin triple's second cross-session rebuild; 4/4 pins byte-identical),
controls c2/c8 bracketing, custody GO 01:11:19Z before builds and all
runs. MEASURED: T1 = (a) AGREE -- the pair block classifies
INTERMEDIATE/MIXED 1,124 (18-cell 987..1,456) and the twin block
INTERMEDIATE/MIXED 1,146 (994..1,453), same class at medians 1.96%
apart; the s28 anchor-grid C3 (a) REPEATS and the scoreboard becomes
s24 (b) / s25 (a) / s26 (b) / s27 (a) / s28 (a) / s33 (a) -- three
splitting grids, three agreeing grids. NAMED, NOT HIDDEN: the AGREE
does NOT resolve threshold-artifact-vs-representation -- the 1,000-tick
class boundary sits inside the measured min-statistic wander (F2) and
the letter is an observational discriminator only (L2). Descriptive
same-day content: the twin's class is UNCHANGED across its three
readings (1,145 min 985 / 1,141 min 983 / 1,146 min 994) while the
pair once flipped (1,129 CAPTURED s26 -> MIXED since) -- three twin
readings vs nine pair readings establish no rate difference and none
is claimed; the hi block is day 28's THIRD anchor reading (in-band vs
the frozen refs 1,129/1,132/1,131), appended to the ledger and
classified descriptive by the frozen evaluator -- verdict UNCHANGED,
PENDING 1/4 with s31 counted (settle-bar-eval.py run twice
byte-identical; fixture pin 38/0). Every arm's host_ns in band (hi
308,946 = 0.353x s31's excursion -- a third non-recurrence
observation; cause UNMEASURED). Rule 4 binds: nothing moves;
accelerator-targets defaults remain provisional (`:measured? false`);
no row moves and no vendor optimization exists for Intel.

Evidence: `docs/evidence/gpu/anv-b3repr-20261028/` (protocol.txt is
the frozen pre-registration incl. the T1 letters; publication-s33.txt
is the measurement; bar-eval-s33.txt is the frozen evaluator's
verdict; record.txt is the finding) and
`docs/evidence/gpu/settle-bar-ledger.txt` (the append-only ledger).

## 2026-10-28 -- session 34 (JUN-59): the within-window min-statistic wander probe (the threshold-artifact side)

Session 33's named residual ("NEITHER letter resolves
threshold-artifact-vs-representation -- the frozen 1,000-tick class
boundary sits INSIDE the measured F2 min-statistic wander") is taken
on ONE observable axis: do K=12 independent 3-run blocks of the
(1024,4033) anchor at n=253,906, B=3, in ONE session window at a
byte-identical rebuilt binary (a6c31b6c -- the pair's seventh
cross-session rebuild; 3/3 pins byte-identical, controls c2/c8
bracketing) straddle the frozen 1,000-tick class boundary in their
block-unit min statistics? ONE measurement slice, pre-registered
before the runs (protocol freeze stamp 2026-10-28T01:39:28Z; ledger-
construction decision L12 for multi-block sessions frozen there --
block A is the only bar candidate), custody GO 01:42:47Z before
builds and all runs. MEASURED: T1 = (a) STRADDLE -- block-unit min
statistics A 993 / B 1,003 / C 982 / D 1,000 / E 991 / F 988 /
G 991 / H 986 / I 992 / J 989 / K 989 / L 985 (range 982..1,003):
blocks B (1,003) and D (1,000) classify CAPTURED, ten blocks
INTERMEDIATE/MIXED. THE FINDING: the frozen class boundary IS
crossed by within-window variation alone at byte-identical binaries
-- the cross-session class flip (s26 CAPTURED -> s27 MIXED) needs no
session-level effect to occur. NAMED, NOT HIDDEN: this does NOT
prove threshold artifact (the wander may itself be physical; L2
observational, no causal mechanism claimed) and
threshold-artifact-vs-representation STAYS UNRESOLVED; the C3
scoreboard is untouched. Descriptive: per-run minima 972..1,006
(extends the quote-only band 971..1,001); no rate claim (2 of 12
blocks here vs 1 of 11 prior is not a rate comparison); block A is
day 28's FOURTH anchor reading (INTERMEDIATE/MIXED 1,145 min 993,
in-band vs the frozen refs 1,129/1,132/1,131), appended to the
ledger and classified descriptive by the frozen evaluator -- verdict
UNCHANGED, PENDING 1/4 with s31 counted (settle-bar-eval.py twice
byte-identical; fixture pin 38/0); next executable day slot
2026-10-29. Host-side proxy elevated across all three arms this
window (hi 488,151..618,664 = 1.58x..2.03x non-excursion priors)
while GPU-side medians replicate in band -- named, cause UNMEASURED.
Rule 4 binds: nothing moves; accelerator-targets defaults remain
provisional (`:measured? false`); no row moves and no vendor
optimization exists for Intel.

Evidence: `docs/evidence/gpu/anv-b3minwander-20261028/` (protocol.txt
is the frozen pre-registration incl. the T1 letters and L12;
publication-s34.txt is the measurement; bar-eval-s34.txt is the
frozen evaluator's verdict; record.txt is the finding) and
`docs/evidence/gpu/settle-bar-ledger.txt` (the append-only ledger).

## 2026-10-28 -- session 35 (JUN-59): the wander co-variation read (analysis; no new hardware)

Session 34's named residual ("WHY the block-min statistic wanders
(estimator noise vs physical drift vs both)" is UNMEASURED) is taken
on ONE observable axis, from session 34's COMMITTED measured run logs
only (84 logs; NO new hardware this session -- named): within s34's
single window (12 blocks A..L of the (1024,4033) anchor at n=253,906,
B=3, byte-identical binary), do the 12 block-unit min statistics
co-vary with the 12 block-unit host-side proxy values (host_ns at
(sum,128,S=16))? ONE analysis slice, pre-registered before the
statistic was computed (protocol freeze stamp 2026-10-28T02:10:34Z;
frozen Spearman + permutation letters (a) CO-MOVE |rho| >= 0.60 and
p <= 0.05 / (b) NO-CO-MOVE otherwise; the input vectors are published
s34 content and the freeze guards against letter-shopping, not prior
exposure -- named). DERIVED FROM MEASURED DATA: T1 = (b) NO-CO-MOVE
-- rho = -0.038597, permutation p = 0.907841 (100,000 trials, frozen
seed 20261028); the vectors reproduce publication-s34.txt's published
values exactly (X A 993..L 985; Y A 505,202..L 503,138), C1 (a),
VERIFY 0 over the 84 logs. THE FINDING: the within-window min-
statistic wander does NOT co-vary with the host-side proxy -- the
wander is not explained by host-side variation at this window.
NAMED, NOT HIDDEN: this excludes ONLY this proxy (estimator noise vs
an unmeasured physical variable STAYS UNRESOLVED; L2 observational,
no causal mechanism; n=12 in one window is LOW POWER) and
threshold-artifact-vs-representation STAYS UNRESOLVED. Descriptive:
per-run unit (36 points, NAMED DIFFERENT UNIT) also reads no
co-movement (rho -0.098788, p 0.566724); run-order trend rho
-0.473687, p 0.122189 (not significant, no trend claim). NO reading,
NO ledger line, NO day-slot consumption -- the bar stays PENDING 1/4
with s31 counted (frozen evaluator twice byte-identical; fixture pin
38/0); next executable day slot 2026-10-29. NAMED DEFECT (session
34's commit): build-census-s34.txt was cited as evidence but omitted
from the tree; recovered this tick as the session-35 artifact
build-census-s34-recovered-s35.txt from the host workdir's unchanged
artifacts (mtimes at the s34 build stamps) -- 3/3 digests match the
protocol-declared pins byte-identically, substantiating the s34
"3/3 pins BYTE-IDENTICAL" claim retroactively while the omission
stays named. Rule 4 binds: nothing moves; accelerator-targets
defaults remain provisional (`:measured? false`); no row moves and no
vendor optimization exists for Intel.

Evidence: `docs/evidence/gpu/anv-b3wandercov-20261028/` (protocol.txt
is the frozen pre-registration incl. the T1 letters; publication-
s35.txt is the derived read; bar-eval-s35.txt is the frozen
evaluator's verdict; build-census-s34-recovered-s35.txt is the named
recovery; record.txt is the finding) and
`docs/evidence/gpu/settle-bar-ledger.txt` (the append-only ledger,
untouched this tick).

## 2026-10-28 -- session 36 (JUN-59): the common-mode probe (two interleaved arms, one window)

Session 35's named candidate row ("a common-mode probe across two
interleaved arms in one window (physical drift would move both arms'
minima together, estimator noise would not -- NEW HARDWARE, a named
candidate row for a later session)") is taken on ONE observable
axis: in ONE session window on the ANV host, do the block-unit min
statistics of TWO interleaved arms -- the (1024,4033) pair arm (hi)
and the (2048,8066) twin arm (tw), 12 ADJACENT block-pairs (hi
block k immediately followed by tw block k) at byte-identical
rebuilt binaries -- CO-MOVE across the 12 pairs (Spearman rho
between the hi and tw block-min vectors)? ONE measurement slice,
pre-registered before the runs (protocol freeze stamp
2026-10-28T02:36:45Z; frozen letters (a) CO-MOVE |rho| >= 0.60 and
p <= 0.05 / (b) NO-CO-MOVE otherwise / (c) NOT EVALUABLE; the
s35-frozen Spearman + permutation algorithm reused UNCHANGED).
HARDWARE RAN (MEASURED, aiueos-6600hs Intel BMG G31 ANV): 78 fresh
processes (c2 3 + hi 36 + tw 36 + c8 3) in the frozen interleaved
order, run window 2026-10-28T02:40:49Z..02:41:27Z, rc=0 78/78 +
'# done cells=24' 78/78, stderr 0 bytes 78/78, 450 SAMPLE + 24
VERIFY each, knob fields == arms, forcing 1,404/1,404, S=8
fail-closed 468/468, VERIFY mismatch 0 everywhere, host-mtime
cross-check 78/78 (worst 1s), custody GO 2026-10-28T02:40:47Z
before builds and ALL runs (corpus 16/16 + 3/3 local-vs-host
MATCH); 4/4 build pins BYTE-IDENTICAL (hi a6c31b6c = the pair's
EIGHTH cross-session rebuild / 9th measurement; tw bb901eb5 = the
twin's THIRD cross-session rebuild / 4th measurement; c2/c8 the
sessions 13-35 pins). THE FINDING (MEASURED): T1 = (b) NO-CO-MOVE
-- Spearman rho = -0.251762, permutation p = 0.425076 (100,000
trials, frozen seed 20261028; count 42,507/100,001); hi block-min
A..L 991/989/981/998/993/985/984/997/994/994/980/982 (980..998) vs
tw 988/985/994/993/994/995/992/984/987/984/993/981 (981..995), C1
(a) (c2 FLOOR; c8 32,911 = 0.01% of 32,915). The two arms' block-min
wander does NOT co-move in this window; with session 35's (b) (no
co-move vs the host-side proxy at s34's window) the wander is not
explained by EITHER the host-side proxy OR a common-mode driver at
the probed windows/powers -- consistent with per-arm estimator noise
or arm-specific effects. NAMED, NOT HIDDEN: L2 observational only,
NO causal mechanism; n=12 pairs in ONE window is LOW POWER (a null
is not evidence of independence); only common-mode structure slower
than the ~1s block-pair spacing was probed (L14); the s35 and s36
letters come from DIFFERENT windows (named); estimator noise vs an
unmeasured arm-specific physical variable STAYS UNRESOLVED and
threshold-artifact-vs-representation STAYS UNRESOLVED. Descriptive
(MEASURED here): (D1) per-run minima hi 966..1,023 EXTEND the
quote-only band 971..1,006 on both sides (new extremes; per-run
unit L10), tw 971..1,001 in band; (D2) hi block A is day
2026-10-28's FIFTH anchor reading (INTERMEDIATE/MIXED, median 1,142,
min 991, 18-cell 991..1,438), in-band vs the frozen refs
1,129/1,132/1,131; its ledger line appended as DESCRIPTIVE by the
frozen evaluator (same-day-duplicate exclusion; scratch-copy tested
first) -- VERDICT UNCHANGED PENDING 1/4 with s31 counted
(settle-bar-eval.py twice byte-identical; fixture pin 38/0; next
executable day slot 2026-10-29); (D3) tw block E host_ns 465,709 =
1.50x its non-excursion blocks -- an L3 proxy excursion, cause
UNMEASURED (X1 content). Rule 4 binds: nothing moves;
accelerator-targets defaults remain provisional (`:measured?
false`); no row moves and no vendor optimization exists for Intel.

Evidence: `docs/evidence/gpu/anv-b3commonmode-20261028/` (protocol.txt
is the frozen pre-registration incl. the T1 letters; publication-
s36.txt is the measured read; run-window.txt / build-census-s36.txt
/ host-verify-s36.txt are the custody chain; bar-eval-s36.txt is the
frozen evaluator's verdict; derivation-census-s36.txt is the
independent second parser (53 rows / 0 mismatched); record.txt is
the finding) and `docs/evidence/gpu/settle-bar-ledger.txt` (the
append-only ledger, one line appended -- hi block A, descriptive).

## 2026-10-28 -- session 37 (JUN-59): the same-window joint probe (analysis; no new hardware)

Session 36's named-not-hidden residual ("a same-window joint probe
of the proxy AND the cross-arm axis (s35 and s36 probed different
windows)") is taken on ONE observable axis: at session 36's single
window (the same 12 adjacent (hi,tw) block-pairs, byte-identical
binaries), probe BOTH axes plus the second arm's proxy axis on
three frozen sub-statistics (block unit n=12, Spearman + two-sided
permutation p, 100,000 trials, frozen seed 20261028 -- the
s35-frozen algorithm UNCHANGED): (A) hi min-vs-host_ns, (B) tw
min-vs-host_ns, (C) hi-vs-tw min. ANALYSIS slice over session 36's
78 committed run logs -- NO hardware ran; pre-registered before the
statistics were computed (protocol freeze stamp
2026-10-28T03:06:03Z; joint letter (a) JOINT NO-COUPLE / (b) ANY
COUPLE / (c) NOT EVALUABLE; a coupling reads CO-MOVE iff |rho| >=
0.60 AND p <= 0.05; (C) doubles as an integrity anchor and
reproduces s36's published rho -0.251762 / count 42,507 / p
0.425076 EXACTLY). THE FINDING (DERIVED from s36's measured logs):
T1 = (b) ANY COUPLE, named: (A) THE HI ARM'S PROXY AXIS IS THE ONE
COUPLING -- rho = 0.774082, p = 0.004060 (count 405/100,001);
(B) tw proxy rho 0.017575 / p 0.960310 NO-CO-MOVE; (C) cross-arm
rho -0.251762 / p 0.425076 NO-CO-MOVE. Session 35's (b) DOES NOT
REPLICATE at this window: the proxy-vs-wander coupling is NOT
window-stable and NOT arm-stable across the two probed windows, so
"the wander is not explained by the host-side proxy" binds at s34's
window ONLY. NAMED, NOT HIDDEN: L2 observational only, NO causal
mechanism (direction of coupling UNMEASURED); (A) reads over the hi
arm's NARROW host_ns band at this window (307,113..311,051 = 1.3%
spread, vs s34's 488,151..618,664 excursion window) -- a rank
coupling on a near-flat proxy series whose physical meaning is
UNRESOLVED; n=12 LOW POWER; L14 ~1s resolution; estimator noise vs
an unmeasured arm-specific physical variable STAYS UNRESOLVED and
threshold-artifact-vs-representation STAYS UNRESOLVED. Descriptive
(DERIVED here): (D1) per-run-unit analogs read NO co-movement at
the frozen letters (A1 rho 0.316427 p 0.058799; B1 rho 0.047843 p
0.780062; L10 different unit); (D2) (B) without the s36-named tw
block-E host excursion (465,709, cause UNMEASURED) stays
NO-CO-MOVE (rho -0.164385, p 0.626894). The bar: NO reading -> NO
ledger line, NO day-slot consumption -- VERDICT UNCHANGED PENDING
1/4 (frozen evaluator, twice byte-identical; fixture pin 38/0; next
executable day slot 2026-10-29). Rule 4 binds: nothing moves;
accelerator-targets defaults remain provisional (`:measured?
false`); no row moves and no vendor optimization exists for Intel.

Evidence: `docs/evidence/gpu/anv-b3jointprobe-20261028/` (protocol.txt
is the frozen pre-registration incl. the joint letters; publication-
s37.txt is the derived read over s36's logs; bar-eval-s37.txt is the
frozen evaluator's verdict; derivation-census-s37.txt is the
independent second parser (51 rows / 0 mismatched); record.txt is
the finding).

## 2026-10-28 -- session 38 (JUN-59): the third-window joint probe (measurement; the coupling flips arms)

Session 37's named-not-hidden residual ("a THIRD window probing
both axes (2 windows do not make a pattern)") is taken on ONE
observable axis: at a THIRD session window, repeat the session-36
interleaved design exactly (12 adjacent (hi,tw) block-pairs,
byte-identical rebuilt binaries) and apply the s37-frozen joint
probe statistics there -- (A) hi min-vs-host_ns, (B) tw
min-vs-host_ns, (C) hi-vs-tw min (block unit n=12, Spearman +
two-sided permutation p, 100,000 trials, frozen seed 20261028 --
the s35-frozen algorithm UNCHANGED). MEASUREMENT slice -- NEW
HARDWARE; pre-registered before the runs (protocol freeze stamp
2026-10-28T03:36:21Z; joint letters (a) JOINT NO-COUPLE / (b) ANY
COUPLE / (c) NOT EVALUABLE; CO-MOVE iff |rho| >= 0.60 AND p <=
0.05). HARDWARE RAN (MEASURED, aiueos-6600hs Intel BMG G31 ANV):
78 fresh processes (c2 3 + hi 36 + tw 36 + c8 3), run window
2026-10-28T03:39:14Z..03:39:31Z, rc=0 78/78 + '# done cells=24'
78/78, stderr 0 bytes 78/78, VERIFY mismatch 0 everywhere, forcing
1,404/1,404, S=8 fail-closed 468/468, custody GO
2026-10-28T03:38:24Z before builds and ALL runs (corpus 16/16 +
3/3 local-vs-host MATCH), 4/4 build pins BYTE-IDENTICAL (hi
a6c31b6c = the (1024,4033) pair's NINTH cross-session rebuild /
10th measurement; tw bb901eb5 = the (2048,8066) twin's FOURTH
rebuild / 5th measurement). THE FINDING (MEASURED): T1 = (b) ANY
COUPLE WITH A FLIPPED ARM -- (B) THE TW ARM'S PROXY AXIS IS THE
ONE COUPLING (rho 0.748269 / p 0.007040 / count 703 of 100,001);
(A) the hi proxy axis reads NO-CO-MOVE (rho -0.056141 / p
0.864691) -- session 37's (A) coupling DOES NOT REPLICATE at this
window; (C) cross-arm rho -0.536433 / p 0.074439 NO-CO-MOVE.
Across the three probed windows the proxy-vs-wander coupling is
NOT window-stable and NOT arm-stable in both directions (s34
window neither arm / s36 window hi arm / s38 window tw arm), so
no replicable coupling exists on either arm and no
window-general exclusion or attribution of the wander is
available. NAMED, NOT HIDDEN: L2 observational only, NO causal
mechanism (direction UNMEASURED); this window's (B) coupling
reads over the tw arm's 1.3%-spread host_ns band (306,491..-
310,599) -- the s37 near-flat-band caveat binds here too (rank
coupling on a near-flat proxy series; physical meaning
UNRESOLVED); (C)'s rho -0.536433 is nearer the 0.60 threshold
than prior windows but reads NO-CO-MOVE at the frozen letters and
no strength trend is claimed; n=12 LOW POWER; L14 ~1s resolution;
estimator noise vs an unmeasured arm-specific physical variable
STAYS UNRESOLVED and threshold-artifact-vs-representation STAYS
UNRESOLVED. Descriptive (MEASURED here): (D1) per-run analogs
(A1 rho -0.211887 / p 0.213358; B1 rho 0.477382 / p 0.003360 --
below the letter bar; L10 different unit; per-run minima hi
967..1,010, tw 969..1,001); (D3) hi block A is day 2026-10-28's
SIXTH anchor reading (INTERMEDIATE/MIXED, median 1,132, min 992,
in-band vs the frozen refs 1,129/1,132/1,131), its ledger line
appended as DESCRIPTIVE by the frozen evaluator (same-day
duplicate) -- VERDICT UNCHANGED PENDING 1/4 with s31 counted
(frozen evaluator twice byte-identical; fixture pin 38/0; next
executable day slot 2026-10-29); (D4) all host_ns in band this
window (no excursion). Rule 4 binds: nothing moves;
accelerator-targets defaults remain provisional (`:measured?
false`); no row moves and no vendor optimization exists for Intel.

Evidence: `docs/evidence/gpu/anv-b3joint3-20261028/` (protocol.txt
is the frozen pre-registration; publication-s38.txt is the derived
third-window read over the 78 committed run logs; bar-eval-s38.txt
is the frozen evaluator's verdict; derivation-census-s38.txt is the
independent second parser (51 rows / 0 mismatched); record.txt is
the finding).

## 2026-10-28 -- session 39 (JUN-59): the fourth-window joint probe (measurement; JOINT NO-COUPLE)

Session 38's named-not-hidden residual ("a FOURTH window (three
windows show arm-flipping instability but do not establish what,
if anything, is stable)") is taken on ONE observable axis: at a
FOURTH session window, repeat the session-36/38 interleaved design
exactly (12 adjacent (hi,tw) block-pairs, byte-identical rebuilt
binaries) and apply the s37-frozen joint probe statistics there --
(A) hi min-vs-host_ns, (B) tw min-vs-host_ns, (C) hi-vs-tw min
(block unit n=12, Spearman + two-sided permutation p, 100,000
trials, frozen seed 20261028 -- the s35-frozen algorithm
UNCHANGED). MEASUREMENT slice -- NEW HARDWARE; pre-registered
before the runs (protocol freeze stamp 2026-10-28T04:07:17Z; joint
letters (a) JOINT NO-COUPLE / (b) ANY COUPLE / (c) NOT EVALUABLE;
CO-MOVE iff |rho| >= 0.60 AND p <= 0.05). HARDWARE RAN (MEASURED,
aiueos-6600hs Intel BMG G31 ANV): 78 fresh processes (c2 3 + hi 36
+ tw 36 + c8 3), run window 2026-10-28T04:09:48Z..04:10:05Z, rc=0
78/78 + '# done cells=24' 78/78, stderr 0 bytes 78/78, VERIFY
mismatch 0 everywhere, forcing 1,404/1,404, S=8 fail-closed
468/468, custody GO 2026-10-28T04:09:00Z before builds and ALL runs
(corpus 16/16 + 3/3 local-vs-host MATCH), 4/4 build pins
BYTE-IDENTICAL (hi a6c31b6c = the (1024,4033) pair's TENTH
cross-session rebuild / 11th measurement; tw bb901eb5 = the
(2048,8066) twin's FIFTH rebuild / 6th measurement). THE FINDING
(MEASURED): T1 = (a) JOINT NO-COUPLE -- none of the three axes
reads CO-MOVE at this window: (A) hi proxy rho 0.194011 / p
0.544405; (B) tw proxy rho 0.130749 / p 0.685753; (C) cross-arm rho
-0.158646 / p 0.617304. Across the four probed windows the
proxy-vs-wander coupling now reads s34 window NO-COUPLE (A-axis
only) / s36 window (A) COUPLE / s38 window (B) COUPLE / s39 window
JOINT NO-COUPLE: the two couplings seen so far occurred on TWO
DIFFERENT arms at two windows and neither is present at this fourth
window, so no replicable coupling exists on either arm, and the
wander is not attributed to the host-side proxy at this window
either. NAMED, NOT HIDDEN: L2 observational only, NO causal
mechanism (direction UNMEASURED); n=12 LOW POWER (a null at n=12
is not evidence of independence -- the NO-COUPLE letter is a
fourth-window fact, not an exclusion of physical coupling); L14
~1s resolution; L15 shared blocks; the four-window scoreboard is
descriptive only (four windows are not a rate); estimator noise vs
an unmeasured arm-specific physical variable STAYS UNRESOLVED and
threshold-artifact-vs-representation STAYS UNRESOLVED. Descriptive
(MEASURED here): (D1) per-run analogs (A1 rho 0.126790 / p
0.460595; B1 rho 0.095901 / p 0.576574 -- no letter, L10 different
unit; per-run minima hi 967..995, tw 969..1,002 inside the
quote-only band 966..1,023); this window's block-min wander bands
are the NARROWEST of the four probe windows (hi 981..995, tw
983..991 vs s34 982..1,003 / s36 980..998 / s38 982..1,007 --
descriptive range comparison against quote-only priors, no
variance or rate claim); (D3) hi block A is day 2026-10-28's
SEVENTH anchor reading (INTERMEDIATE/MIXED, median 1,146, min 986,
in-band vs the frozen refs 1,129/1,132/1,131), its ledger line
appended as DESCRIPTIVE by the frozen evaluator (same-day
duplicate) -- VERDICT UNCHANGED PENDING 1/4 with s31 counted (frozen
evaluator twice byte-identical; fixture pin 38/0; next executable
day slot 2026-10-29); (D4) host_ns: c2 671,412 (marginally below
every non-excursion prior, 0.998x of the lowest 672,374 -- within
0.2%, no excursion), c8 2,388,174 in band, hi per-block
304,598..310,559, tw 305,820..310,149 (no excursion this window;
the s31, s34-window and s36 tw block-E excursion causes stay
UNMEASURED). Rule 4 binds: nothing moves; accelerator-targets
defaults remain provisional (`:measured? false`); no row moves and
no vendor optimization exists for Intel.

Evidence: `docs/evidence/gpu/anv-b3joint4-20261028/` (protocol.txt
is the frozen pre-registration; publication-s39.txt is the derived
fourth-window read over the 78 committed run logs; bar-eval-s39.txt
is the frozen evaluator's verdict; derivation-census-s39.txt is the
independent second parser (52 rows / 0 mismatched); record.txt is
the finding).

## 2026-10-28 -- session 40 (JUN-59): the wander-noise repartition probe (analysis; NOISE-CONSISTENT)

Session 39's first-named UNMEASURED item ("WHY the min statistic
wanders (estimator noise vs physical drift vs both)") is taken on
ONE observable axis: at the session-39 window, does the observed
spread T (range of the 12 block-unit min statistics of one arm;
s35/s36-frozen constructions UNCHANGED) EXCEED the spread that
run-repartition resampling of the SAME window's committed runs
produces (null: the 36 runs of one arm within one window are
exchangeable across blocks -- all within-run and fresh-process
run-to-run noise included)? ANALYSIS slice -- NO new hardware;
DERIVED from the 234 committed run logs of the s36/s38/s39 windows
(78 each). Resampling: 20,000 trials, random.Random(20261028)
consumed in the frozen probe order (s39 hi, s39 tw, s36 hi, s36 tw,
s38 hi, s38 tw), p = (1 + count(T* >= T_obs)) / (1 + 20,000);
letters pre-registered (protocol freeze stamp 2026-10-28T04:40:07Z,
BEFORE any statistic was computed): (a) NOISE-CONSISTENT / (b)
EXCEEDS NULL (named which arm) / (c) NOT EVALUABLE. THE FINDING
(DERIVED FROM MEASURED DATA): T1 = (a) NOISE-CONSISTENT -- at the
s39 window neither arm exceeds the null (hi T_obs 14, block-mins
981..995, p 0.827359; tw T_obs 8, 983..991, p 0.986451) and the
pre-registered replications agree (s36 window (a): hi T_obs 18, p
0.649868 / tw T_obs 14, p 0.739563; s38 window (a): hi T_obs 25, p
0.059247 / tw T_obs 21, p 0.328534). Across all three probed
windows and both arms no block-timescale (~3-run / few-second)
structure beyond run-exchangeable sampling noise is detected.
NAMED, NOT HIDDEN: (a) does NOT prove "estimator noise is the
mechanism" -- the null is run-exchangeability at the fresh-process
granularity and a physical driver acting UNIFORMLY within a window
would also read (a); the s38 hi arm's p 0.059247 sits CLOSE ABOVE
the frozen 0.05 threshold at the largest T_obs of the six probes
(25) -- no trend, strength or near-miss claim; exchangeability of
runs is itself an assumption; 20,000 trials (pure-Python cost,
named in the freeze; p resolution 1/20,001); the three windows are
ONE day / ONE host and the cross-window comparison is descriptive
only; L2 observational, NO causal mechanism, direction UNMEASURED;
estimator noise vs an unmeasured within-window-uniform physical
variable STAYS UNRESOLVED and threshold-artifact-vs-representation
STAYS UNRESOLVED. Integrity (DERIVED): 3/3 windows clean (VERIFY
mismatch 0, counts, knobs, S=8 fail-closed, cell map), C1 (a) at
the s39 window (c2 FLOOR; c8 32,829 vs 32,915, 0.26%), and 6/6
block-min vectors reproduce publication-s39.txt section 3 EXACTLY.
Rule 4 binds: nothing moves; accelerator-targets defaults remain
provisional (`:measured? false`); no row moves and no vendor
optimization exists for Intel. The bar: NO reading -> NO ledger
line (byte-identical to HEAD), VERDICT UNCHANGED PENDING 1/4 with
s31 counted (frozen evaluator twice byte-identical; fixture pin
38/0; next executable day slot 2026-10-29).

Evidence: `docs/evidence/gpu/anv-b3wandernoise-20261028/`
(protocol.txt is the frozen pre-registration; publication-s40.txt
is the derived read over the 234 committed run logs of the three
windows; derivation-census-s40.txt is the independent second parser
(90 rows / 0 mismatched); bar-eval-s40.txt is the frozen
evaluator's unchanged verdict; record.txt is the finding).

## 2026-10-28 -- session 41 (JUN-59): the cross-window T-spread repartition probe (analysis; WINDOW-CONSISTENT)

Session 40's first-named candidate row ("whether window-to-window
variation of T itself (8..25 across the six probes) exceeds noise")
is taken on ONE observable axis: per arm, does the cross-window
spread of T, R_obs = max_w T_w - min_w T_w over the three probed
windows (s36, s38, s39), exceed the cross-window run-repartition
null (the 108 runs of one arm across the three windows are
exchangeable; s35/s36-frozen constructions UNCHANGED)? ANALYSIS
slice -- NO new hardware; DERIVED from the 234 committed run logs
of the s36/s38/s39 windows (78 each). Resampling: 20,000 trials,
random.Random(20261028) consumed in the frozen probe order (hi then
tw), per trial one shuffle of the 108 run ids split into three
pseudo-windows of 36 and 12 blocks of 3 in draw order, p = (1 +
count(R* >= R_obs)) / (1 + 20,000); letters pre-registered
(protocol freeze stamp 2026-10-28T05:05:50Z, BEFORE any statistic
was computed): per arm (a) WINDOW-CONSISTENT / (b) EXCEEDS NULL
(named which) / (c) NOT EVALUABLE. THE FINDING (DERIVED FROM
MEASURED DATA): T1 = (a) WINDOW-CONSISTENT -- neither arm's R
exceeds the null (hi T 18/25/14, R_obs 11, p 0.275536; tw T
14/21/8, R_obs 13, p 0.079396; both > 0.05 at the frozen
threshold). The 8..25 spread of the six probe Ts is itself
consistent with run-exchangeable sampling noise. NAMED, NOT HIDDEN:
(a) does NOT prove "no physical window-level driver" -- a driver
acting uniformly within AND across windows is invisible by
construction; R tests the window-to-window variation of the SPREAD
of the 12 block-mins ONLY -- window-level shifts in LEVEL do not
enter R (named limitation of the row question); the tw arm's p
0.079396 sits ABOVE the frozen 0.05 and CLOSER to it than hi's --
no trend, strength or near-miss claim; exchangeability across
windows is a STRONGER assumption than session 40's within-window
one; three windows in ONE day on ONE host is LOW POWER (a null is
not evidence of stationarity); session 40's per-window (a) letters
and this letter are DIFFERENT nulls; 20,000 trials (cost, named in
the freeze; p resolution 1/20,001); L2 observational, NO causal
mechanism, direction UNMEASURED; the wander's MECHANISM STAYS
UNRESOLVED and threshold-artifact-vs-representation STAYS
UNRESOLVED. Integrity (DERIVED): 3/3 windows clean (VERIFY mismatch
0, counts, knobs, S=8 fail-closed, cell map), C1 (a) at the s39
window (c2 FLOOR; c8 32,829 vs 32,915, 0.26%), and 6/6 block-min
vectors plus the six T values reproduce the published values
EXACTLY. Rule 4 binds: nothing moves; accelerator-targets defaults
remain provisional (`:measured? false`); no row moves and no vendor
optimization exists for Intel. The bar: NO reading -> NO ledger
line (byte-identical to HEAD), VERDICT UNCHANGED PENDING 1/4 with
s31 counted (frozen evaluator twice byte-identical; fixture pin
38/0; next executable day slot 2026-10-29).

Evidence: `docs/evidence/gpu/anv-b3xwindt-20261028/` (protocol.txt
is the frozen pre-registration; publication-s41.txt is the derived
read over the 234 committed run logs of the three windows;
derivation-census-s41.txt is the independent second parser (40 rows
/ 0 mismatched); bar-eval-s41.txt is the frozen evaluator's
unchanged verdict; record.txt is the finding).

## 2026-10-28 -- session 42 (JUN-59): the cross-window level-shift repartition probe (analysis; LEVEL-CONSISTENT)

Session 41's first-named candidate row ("a LEVEL-shift probe of the
same three windows (D3's descriptive medians suggest little level
movement, but no letter exists -- R does not test level)") is taken
on ONE observable axis: per arm, does the cross-window LEVEL spread,
S_obs = max_w M_w - min_w M_w over the three probed windows (s36,
s38, s39), where M_w = median of the 12 block-mins of window w,
exceed the cross-window run-repartition null (the 108 runs of one
arm across the three windows are exchangeable; s35/s36-frozen
constructions UNCHANGED; the 12-value median computed in half-tick
integer units, 2*M = 6th + 7th order statistics, so every
comparison is exact)? ANALYSIS slice -- NO new hardware; DERIVED
from the 234 committed run logs of the s36/s38/s39 windows (78
each). Resampling: 20,000 trials, random.Random(20261028) consumed
in the frozen probe order (hi then tw), per trial one shuffle of the
108 run ids split into three pseudo-windows of 36 and 12 blocks of 3
in draw order, p = (1 + count(S* >= S_obs)) / (1 + 20,000),
one-sided; letters pre-registered (protocol freeze stamp
2026-10-28T05:33:45Z, BEFORE any statistic was computed): per arm
(a) LEVEL-CONSISTENT / (b) EXCEEDS NULL (named which) / (c) NOT
EVALUABLE. THE FINDING (DERIVED FROM MEASURED DATA): T1 = (a)
LEVEL-CONSISTENT -- neither arm's S exceeds the null (hi M
990.0/987.0/986.5, S_obs 3.5, p 0.470676; tw M 990.0/991.0/988.0,
S_obs 3.0, p 0.485476; both > 0.05 at the frozen threshold). The
D3 level content needs no window-level effect to occur. NAMED, NOT
HIDDEN: (a) does NOT prove "no physical window-level driver" -- a
driver acting uniformly within AND across windows is invisible by
construction; AND the LEVEL is the median of the 12 BLOCK-MINS,
where block-min is itself a TAIL statistic -- a window-level shift
that moves only the BODY of the gpu_ticks distribution and not the
min-tail is invisible to this construction (named limitation; a
BODY-level probe is a named candidate row); the block-min level
sits near the frozen 1,000-tick class boundary and inherits the
threshold-artifact-vs-representation ambiguity; this letter and
session 41's R (spread) letter are DIFFERENT nulls over the SAME
runs (NOT independent evidence); three windows in ONE day on ONE
host is LOW POWER (a null is not stationarity); 20,000 trials
(cost, named in the freeze; p resolution 1/20,001); L2
observational, NO causal mechanism, direction UNMEASURED; the
wander's MECHANISM STAYS UNRESOLVED and threshold-artifact-vs-
representation STAYS UNRESOLVED. Integrity (DERIVED): 3/3 windows
clean (VERIFY mismatch 0, counts, knobs, S=8 fail-closed, cell
map), C1 (a) at the s39 window (c2 FLOOR; c8 32,829 vs 32,915,
0.26%), and 6/6 block-min vectors plus the six M values reproduce
the published values EXACTLY. Rule 4 binds: nothing moves;
accelerator-targets defaults remain provisional (`:measured?
false`); no row moves and no vendor optimization exists for Intel.
The bar: NO reading -> NO ledger line (byte-identical to HEAD),
VERDICT UNCHANGED PENDING 1/4 with s31 counted (frozen evaluator
twice byte-identical; fixture pin 38/0; next executable day slot
2026-10-29).

Evidence: `docs/evidence/gpu/anv-b3levelshift-20261028/`
(protocol.txt is the frozen pre-registration; publication-s42.txt
is the derived read over the 234 committed run logs of the three
windows; derivation-census-s42.txt is the independent second parser
(40 rows / 0 mismatched); bar-eval-s42.txt is the frozen
evaluator's unchanged verdict; record.txt is the finding).

## 2026-10-28 -- session 43 (JUN-59): the cross-window body-level repartition probe (analysis; BODY-LEVEL-CONSISTENT)

Session 42's first-named candidate row ("a BODY-level probe of the
same three windows (per-cell pooled-median level, not the min-tail
-- body shifts are invisible to the block-min constructions by
this probe's own named-not-hidden)") is taken on ONE observable
axis: per arm, does the cross-window BODY LEVEL spread,
S_obs = max_w L_w - min_w L_w over the three probed windows (s36,
s38, s39), where L_w = median of the 12 block-body values of
window w (block-body = median over the 18 ok cells of the block's
per-cell pooled medians -- the min-tail summary replaced by the
body; every upstream unit s35/s36-frozen and UNCHANGED), exceed
the cross-window run-repartition null (the 108 runs of one arm
across the three windows are exchangeable)? The half-tick
(2*B = 9th + 10th order statistics) and quarter-tick (4*L = 6th +
7th order statistics of the doubled block-bodies) constructions
are computed in integer units, so every comparison is exact.
ANALYSIS slice -- NO new hardware; DERIVED from the 234 committed
run logs of the s36/s38/s39 windows (78 each). Resampling: 20,000
trials, random.Random(20261028) consumed in the frozen probe order
(hi then tw), per trial one shuffle of the 108 run ids split into
three pseudo-windows of 36 and 12 blocks of 3 in draw order,
p = (1 + count(S* >= S_obs)) / (1 + 20,000), one-sided; letters
pre-registered (protocol freeze stamp 2026-10-28T06:07:08Z, BEFORE
any statistic was computed): per arm (a) BODY-LEVEL-CONSISTENT /
(b) EXCEEDS NULL (named which) / (c) NOT EVALUABLE. THE FINDING
(DERIVED FROM MEASURED DATA): T1 = (a) BODY-LEVEL-CONSISTENT --
neither arm's S exceeds the null (hi L 1138.25/1139.50/1137.25,
S_obs 2.25, p 0.683016; tw L 1138.50/1137.25/1136.00, S_obs 2.50,
p 0.610119; both > 0.05 at the frozen threshold). The BODY level
needs no window-level effect to occur. NAMED, NOT HIDDEN: (a) does
NOT prove "no physical window-level driver" -- a driver acting
uniformly within AND across windows is invisible by construction;
AND the BODY statistic is the MEDIAN OVER 18 HETEROGENEOUS CELLS
(different ops/workgroups span 986..1,438 ticks even within one
block) -- a window-level shift that moves only SOME cells' levels
can cancel in the median over cells and is invisible to this
construction (named limitation; a per-cell shift probe is a named
candidate row); the body level (~1,136..1,140 ticks) sits ABOVE
the frozen 1,000-tick class boundary while the min-tail sits AT
it; this letter and sessions 40/41/42's letters are DIFFERENT
nulls over the SAME runs (NOT independent evidence); three windows
in ONE day on ONE host is LOW POWER (a null is not stationarity);
20,000 trials (cost, named in the freeze; p resolution 1/20,001);
L2 observational, NO causal mechanism, direction UNMEASURED; the
wander's MECHANISM STAYS UNRESOLVED and threshold-artifact-vs-
representation STAYS UNRESOLVED. Integrity (DERIVED): 3/3 windows
clean (VERIFY mismatch 0, counts, knobs, S=8 fail-closed, cell
map), C1 (a) at the s39 window (c2 FLOOR; c8 32,829 vs 32,915,
0.26%), 6/6 block-min vectors reproduce the published values
EXACTLY, and the NEW pre-registered anchor reproduction row is
EXACT at all three windows (hi block A's (sum,128,S=16) pooled
median and 18-cell min..max vs the quote-only anchor priors: s36
1,142 / 991..1,438; s38 1,132 / 992..1,443; s39 1,146 /
986..1,432). Rule 4 binds: nothing moves; accelerator-targets
defaults remain provisional (`:measured? false`); no row moves and
no vendor optimization exists for Intel. The bar: NO reading -> NO
ledger line (byte-identical to HEAD), VERDICT UNCHANGED PENDING
1/4 with s31 counted (frozen evaluator twice byte-identical;
fixture pin 38/0; next executable day slot 2026-10-29).

Evidence: `docs/evidence/gpu/anv-b3bodylevel-20261028/`
(protocol.txt is the frozen pre-registration; publication-s43.txt
is the derived read over the 234 committed run logs of the three
windows; derivation-census-s43.txt is the independent second parser
(49 rows / 0 mismatched); bar-eval-s43.txt is the frozen
evaluator's unchanged verdict; record.txt is the finding).

## 2026-10-28 -- session 44 (JUN-59): the per-cell body-shift repartition probe (analysis; PER-CELL-CONSISTENT)

Session 43's first-named candidate row ("a PER-CELL body-shift
probe of the same three windows -- per-cell window-level shifts
cancel in this probe's median-over-18-cells construction") taken
on ONE observable axis: per arm, does ANY of the 18 ok cells show
a cross-window per-cell LEVEL spread S_c = max_w L_{w,c} -
min_w L_{w,c} (per-cell level L_{w,c} = median of the 12 block
per-cell pooled medians of window w; block/per-cell pooled median
units s35/s36-frozen, UNCHANGED) exceeding the cross-window
run-repartition null? The primary per-arm statistic is the MAX-T
M = max_c S_c with the max taken inside each resampling trial
(family-wise over the 18 cells). ANALYSIS slice -- NO new
hardware; inputs are the 234 committed run logs of sessions
36/38/39. Pre-registered (protocol freeze stamp
2026-10-28T06:35:39Z, BEFORE any statistic was computed): per arm
(a) PER-CELL-CONSISTENT / (b) EXCEEDS NULL (named which cell(s))
/ (c) NOT EVALUABLE; resampling 20,000 trials,
random.Random(20261028) consumed in the frozen probe order hi
then tw, p = (1 + count(M* >= M_obs)) / (1 + 20,000), one-sided.
THE FINDING (DERIVED): T1 = (a) PER-CELL-CONSISTENT on both arms
-- hi M_obs 23.0 ticks (max cell (sum,256,S=32)), count 3,205 /
20,001, p 0.160292; tw M_obs 18.5 (same cell), count 10,573 /
20,001, p 0.528674 (both p > 0.05). Session 43's named gap is
closed on this axis: no per-cell LEVEL shift beyond
run-exchangeable sampling noise is visible at these windows/
powers. NAMED, NOT HIDDEN: (a) is not proof of noise (a uniform
driver is invisible by construction; per-cell SPREAD/quantile
shifts are invisible to this LEVEL construction -- a per-cell
wander probe and a per-cell spread probe are named candidate
rows); the 36 UNCORRECTED marginal p values carry no letter --
two hi cells sit below 0.05 ((min,256,S=16) p 0.013949,
(sum,256,S=32) p 0.042248) and NOTHING is claimed from them; the
frozen 1,000-tick class boundary sits INSIDE the per-cell level
range (986..1,443) and threshold-artifact-vs-representation
STAYS UNRESOLVED; three windows in ONE day on ONE host is LOW
POWER; this letter and sessions 40-43's letters are DIFFERENT
nulls over the SAME runs (NOT independent evidence). Integrity
(DERIVED): 3/3 windows clean, C1 (a) at the s39 window (c2 FLOOR;
c8 32,829 vs 32,915, 0.26%), 6/6 block-min vectors reproduce
EXACTLY, anchor row EXACT at all three windows. Rule 4 binds:
nothing moves; accelerator-targets defaults remain provisional
(`:measured? false`); no row moves and no vendor optimization
exists for Intel. The bar: NO reading -> NO ledger line
(byte-identical to HEAD), VERDICT UNCHANGED PENDING 1/4 with s31
counted (frozen evaluator twice byte-identical; fixture pin 38/0;
next executable day slot 2026-10-29).

Evidence: `docs/evidence/gpu/anv-b3percellshift-20261028/`
(protocol.txt is the frozen pre-registration; publication-s44.txt
is the derived read over the 234 committed run logs of the three
windows; derivation-census-s44.txt is the independent second parser
(45 rows / 0 mismatched); bar-eval-s44.txt is the frozen
evaluator's unchanged verdict; record.txt is the finding).

## 2026-10-28 -- session 45 (JUN-59): the per-cell wander repartition probe (analysis; T1 PER-CELL-NOISE-CONSISTENT, s38 replication (b) on hi)

Session 44's first-named candidate row ("a PER-CELL WANDER probe
-- the per-cell analog of session 40 -- does any cell's
within-window block-level wander exceed WITHIN-window
run-repartition noise?") taken on ONE observable axis: per
(window, arm), does ANY ok cell's within-window block-level
wander W_c = max_b V_{b,c} - min_b V_{b,c} (V = the block's
per-cell pooled median, s35/s36-frozen unit, UNCHANGED) exceed
the within-window run-repartition null? The primary per-probe
statistic is the MAX-T M = max_c W_c with the max taken inside
each resampling trial (family-wise over the 18 cells). ANALYSIS
slice -- NO new hardware; inputs are the 234 committed run logs
of sessions 36/38/39. Pre-registered (protocol freeze stamp
2026-10-28T07:15:00Z, BEFORE any statistic was computed): per
probe (a) PER-CELL-NOISE-CONSISTENT / (b) EXCEEDS NULL (named
which cell(s)) / (c) NOT EVALUABLE; per-window letter (session
40's rule); T1 = the s39 window letter; resampling 20,000 trials
per probe, random.Random(20261028) consumed in the frozen probe
order s39 hi / s39 tw / s36 hi / s36 tw / s38 hi / s38 tw,
p = (1 + count(M* >= M_obs)) / (1 + 20,000), one-sided; exact
INTEGER arithmetic. THE FINDING (DERIVED): T1 = (a)
PER-CELL-NOISE-CONSISTENT at the s39 window (hi M_obs 72, count
9,423 / 20,001, p 0.471176; tw M_obs 70, count 9,877, p
0.493875); replication s36 = (a) (hi 84, p 0.154792; tw 68, p
0.644518); replication s38 = (b) EXCEEDS NULL on the hi arm --
s38 hi M_obs 84 at cell (sum,256,S=32), count 947 / 20,001,
p 0.047398 (marginals (sum,256,S=32) p 0.035348 and
(min,256,S=default) p 0.042298, UNCORRECTED, no letter); s38 tw
(a) p 0.994550. Session 44's named gap is closed on this axis at
the primary window, while the pre-registered s38 replication
reads (b) on hi. NAMED, NOT HIDDEN: six probe p values / three
window letters are UNCORRECTED across probes/windows (one (b)
among six uncorrected probes at p 0.047398 is within what
multiple uncorrected tests produce; NO replication of the s38 hi
cell exists -- descriptive co-location only: s40's block-min
wander at s38 hi was the closest of its six probes to threshold,
p 0.059247); the 108 UNCORRECTED marginal p values carry no
letter; (a) is not proof of noise (a uniform driver is invisible
by construction; W_c is a tail-to-tail range, not a scale
estimate; per-cell SPREAD is a named candidate row) and (b) names
no mechanism (thermal/scheduling/memory/driver state all
UNMEASURED); the frozen 1,000-tick class boundary sits INSIDE the
per-cell level range (986..1,443) and threshold-artifact-vs-
representation STAYS UNRESOLVED; three windows in ONE day on ONE
host is LOW POWER; this letter and sessions 40-44's letters are
DIFFERENT statistics over the SAME runs (NOT independent
evidence). Integrity (DERIVED): 3/3 windows clean, C1 (a) at the
s39 window (c2 FLOOR; c8 32,829 vs 32,915, 0.26%), 6/6 block-min
vectors reproduce EXACTLY, anchor row EXACT at all three windows.
Rule 4 binds: nothing moves; accelerator-targets defaults remain
provisional (`:measured? false`); no row moves and no vendor
optimization exists for Intel. The bar: NO reading -> NO ledger
line (byte-identical to HEAD), VERDICT UNCHANGED PENDING 1/4 with
s31 counted (frozen evaluator twice byte-identical; fixture pin
38/0; next executable day slot 2026-10-29).

Evidence: `docs/evidence/gpu/anv-b3percellwander-20261028/`
(protocol.txt is the frozen pre-registration; publication-s45.txt
is the derived read over the 234 committed run logs of the three
windows; derivation-census-s45.txt is the independent second
parser (87 rows / 0 mismatched); bar-eval-s45.txt is the frozen
evaluator's unchanged verdict; record.txt is the finding).

## 2026-10-28 -- session 46 (JUN-59): the per-cell within-block spread repartition probe (analysis; all six probes PER-CELL-SPREAD-NOISE-CONSISTENT)

Session 45's first-named candidate row -- "a PER-CELL SPREAD probe
of the same three windows (per-cell within-run/within-block scale
is untested)" -- taken on one observable axis: per (window, arm),
does any ok cell's within-block sample spread (D = max - min of
the block's 75 samples; the s35/s36-frozen block unit unchanged)
wander across the 12 blocks beyond the within-window
run-repartition null? Max-T over the 18 cells (the max taken
inside each trial), 20,000 trials per probe, frozen probe order,
exact integer arithmetic; letters pre-registered at freeze stamp
2026-10-28T07:51:32Z before any statistic was computed.

THE FINDING (DERIVED from the 234 committed run logs measured in
sessions 36/38/39; ANALYSIS slice, no hardware): T1 = (a)
PER-CELL-SPREAD-NOISE-CONSISTENT at the s39 window -- hi M_obs
295 (max cell (min,256,S=default)), count 14,383/20,001, p
0.719164; tw M_obs 360 (max cell (max,128,S=32)), count 13,881,
p 0.694065 -- and the pre-registered replications agree:
s36 (a) (hi 474, p 0.196340; tw 360, p 0.682666), s38 (a) (hi
356, p 0.728164; tw 290, p 0.403480). All SIX probes read (a) --
the first probe family in this campaign with no (b) anywhere:
at these windows/powers no cell's within-block sample-scale
wander exceeds run-exchangeable sampling noise, family-wise over
the 18 cells. NAMED, NOT HIDDEN: (a) is not proof of noise (a
within-window-uniform driver is invisible by construction); D is
a tail-to-tail range, a scale surrogate -- IQR/MAD, spread LEVEL
shifts uniform across blocks, and within-run (25-sample) scale
are invisible to this construction (named candidate rows); the
108 uncorrected marginal p values carry no letter (four probes
carry cells with marginal p <= 0.05 -- within chance, nothing
claimed); six probes / three windows are UNCORRECTED and LOW
POWER (three windows in one day, one host); this letter and
sessions 40-45's are DIFFERENT statistics over the SAME runs (NOT
independent evidence); threshold-artifact-vs-representation
STAYS UNRESOLVED. Integrity (DERIVED): 3/3 windows clean, C1 (a)
at the s39 window (c2 FLOOR; c8 32,829 vs 32,915, 0.26%), 6/6
block-min vectors reproduce EXACTLY, anchor row EXACT at all
three windows. Rule 4 binds: nothing moves; accelerator-targets
defaults remain provisional (`:measured? false`); no vendor
optimization exists for Intel. The bar: NO reading -> NO ledger
line (byte-identical to HEAD), VERDICT UNCHANGED PENDING 1/4 with
s31 counted (frozen evaluator twice byte-identical; fixture pin
38/0; next executable day slot 2026-10-29).

Evidence: `docs/evidence/gpu/anv-b3percellspread-20261028/`
(protocol.txt is the frozen pre-registration; publication-s46.txt
is the derived read over the 234 committed run logs of the three
windows; derivation-census-s46.txt is the independent second
parser (126 rows / 0 mismatched); bar-eval-s46.txt is the frozen
evaluator's unchanged verdict; record.txt is the finding).

## 2026-10-28 -- session 47 (JUN-59): the per-cell within-block robust-scale (IQR) repartition probe (analysis; all six probes PER-CELL-IQR-NOISE-CONSISTENT)

Session 46's first-named candidate row -- "a PER-CELL ROBUST-SCALE
probe (IQR/MAD of the block's 75 -- the range's named blind spot)"
-- taken on one observable axis: per (window, arm), does any ok
cell's within-block robust scale (D = x_(57) - x_(19) of the
block's 75 samples -- the frozen Tukey exclusive hinges; the
s35/s36-frozen block unit unchanged) wander across the 12 blocks
beyond the within-window run-repartition null? Max-T over the 18
cells (the max taken inside each trial), 20,000 trials per probe,
frozen probe order, exact integer arithmetic; letters
pre-registered at freeze stamp 2026-10-28T08:20:41Z before any
statistic was computed.

THE FINDING (DERIVED from the 234 committed run logs measured in
sessions 36/38/39; ANALYSIS slice, no hardware): T1 = (a)
PER-CELL-IQR-NOISE-CONSISTENT at the s39 window -- hi M_obs 197
(max cell (min,128,S=16)), count 15,784/20,001, p 0.789211; tw
M_obs 190 (max cell (max,128,S=16)), count 19,754, p 0.987701 --
and the pre-registered replications agree: s36 (a) (hi 213,
p 0.657217; tw 231, p 0.573471), s38 (a) (hi 219, p 0.191390;
tw 210, p 0.783511). All SIX probes read (a) -- the second
consecutive probe family with no (b) anywhere: at these
windows/powers no cell's within-block robust-scale wander exceeds
run-exchangeable sampling noise, family-wise over the 18 cells.
NAMED, NOT HIDDEN: (a) is not proof of noise (a
within-window-uniform driver is invisible by construction); D is
ONE robust scale -- the IQR at the frozen exclusive hinges --
while MAD, other quantile pairs and spread changes keeping
x_(19)/x_(57) fixed are invisible (named candidate rows); a
robust-scale LEVEL shift uniform across blocks cancels in W_c
(descriptive D1 only); six probes / three windows are UNCORRECTED
and LOW POWER (three windows in one day, one host); this letter
and sessions 40-46's are DIFFERENT statistics over the SAME runs
(NOT independent evidence); threshold-artifact-vs-representation
STAYS UNRESOLVED. Integrity (DERIVED): 3/3 windows clean, C1 (a)
at the s39 window (c2 FLOOR; c8 32,829 vs 32,915, 0.26%), 6/6
block-min vectors reproduce EXACTLY, anchor row EXACT at all
three windows. Rule 4 binds: nothing moves; accelerator-targets
defaults remain provisional (`:measured? false`); no vendor
optimization exists for Intel. The bar: NO reading -> NO ledger
line (byte-identical to HEAD), VERDICT UNCHANGED PENDING 1/4 with
s31 counted (frozen evaluator twice byte-identical; fixture pin
38/0; next executable day slot 2026-10-29).

Evidence: `docs/evidence/gpu/anv-b3percelliqr-20261028/`
(protocol.txt is the frozen pre-registration; publication-s47.txt
is the derived read over the 234 committed run logs of the three
windows; derivation-census-s47.txt is the independent second
parser (171 rows / 0 mismatched); bar-eval-s47.txt is the frozen
evaluator's unchanged verdict; record.txt is the finding).

## 2026-10-28 -- session 48 (JUN-59): the per-cell within-block robust-scale (MAD) repartition probe (analysis; all six probes PER-CELL-MAD-NOISE-CONSISTENT)

Session 47's first-named candidate row -- "a PER-CELL MAD probe
(the IQR's named blind spot)" -- taken on one observable axis:
per (window, arm), does any ok cell's within-block robust scale
(D = e_(38) about m = x_(38) of the block's 75 samples -- the
frozen exact-median MAD) wander across the 12 blocks beyond the
within-window run-repartition null? Max-T over the 18 cells (the
max taken inside each trial), 20,000 trials per probe, frozen
probe order, exact integer arithmetic; letters pre-registered at
freeze stamp 2026-10-28T09:04:56Z before any statistic was
computed.

THE FINDING (DERIVED from the 234 committed run logs measured in
sessions 36/38/39; ANALYSIS slice, no hardware): T1 = (a)
PER-CELL-MAD-NOISE-CONSISTENT at the s39 window -- hi M_obs 46
(max cell (sum,128,S=32)), count 4,374/20,001, p 0.218739; tw
M_obs 39 (max cells (sum,128,S=32), (max,128,S=32), a tie),
count 12,056, p 0.602820 -- and the pre-registered replications
agree: s36 (a) (hi 41, p 0.757112; tw 39, p 0.720664), s38 (a)
(hi 45, p 0.328384; tw 33, p 0.990800). All SIX probes read (a)
-- the third consecutive probe family with no (b) anywhere: at
these windows/powers no cell's within-block MAD wander exceeds
run-exchangeable sampling noise, family-wise over the 18 cells.
NAMED, NOT HIDDEN: (a) is not proof of noise (a
within-window-uniform driver is invisible by construction); D is
ONE robust scale -- the MAD about the median -- while other
quantile pairs, other deviation centers and spread/tail-weight
changes keeping e_(38) about x_(38) fixed are invisible (the
s47 IQR and s46 RANGE see DIFFERENT things; none of the three
dominates; other robust scales stay named candidate rows); a
robust-scale LEVEL shift uniform across blocks cancels in W_c
(descriptive D1 only); the 108 marginal p values are UNCORRECTED
and carry NO letter (three cells sit below 0.05 letterless --
s39 hi (sum,128,S=32) p 0.035198, s39 tw (min,256,S=default) p
0.049448, s36 hi (max,128,S=32) p 0.027699 -- within chance,
nothing claimed); six probes / three windows are UNCORRECTED and
LOW POWER (three windows in one day, one host; max-T at n=12
blocks); this letter and sessions 40-47's are DIFFERENT
statistics over the SAME runs (NOT independent evidence);
threshold-artifact-vs-representation STAYS UNRESOLVED. Integrity
(DERIVED): 3/3 windows clean, C1 (a) at the s39 window (c2 FLOOR;
c8 32,829 vs 32,915, 0.26%), 6/6 block-min vectors reproduce
EXACTLY, anchor row EXACT at all three windows. Rule 4 binds:
nothing moves; accelerator-targets defaults remain provisional
(`:measured? false`); no vendor optimization exists for Intel.
The bar: NO reading -> NO ledger line (byte-identical to HEAD),
VERDICT UNCHANGED PENDING 1/4 with s31 counted (frozen evaluator
twice byte-identical; fixture pin 38/0; next executable day slot
2026-10-29).

The slice ran in two ticks (record.txt's sections 4/8 document
the partial first tick; its section 9 the landing tick): the
derivation census (independent second parser) landed on the
second tick -- derivation-census-s48.txt, 231 rows / 0
mismatched, run twice byte-identical -- and the gate artifacts
were re-run fresh at landing, byte-identical to the pinned
artifacts (gate-rerun-s48b.txt).

Evidence: `docs/evidence/gpu/anv-b3percellmad-20261028/`
(protocol.txt is the frozen pre-registration; publication-s48.txt
is the derived read over the 234 committed run logs of the three
windows; derivation-census-s48.txt is the independent second
parser (231 rows / 0 mismatched); bar-eval-s48.txt is the frozen
evaluator's unchanged verdict; record.txt is the finding).

## 2026-10-28 -- session 49 (JUN-59): the per-cell robust-scale (MAD) LEVEL cross-window repartition probe (analysis; T1 (b) EXCEEDS NULL, driven by the tw arm)

Session 48's first-named candidate row -- "a per-cell
robust-scale LEVEL probe (uniform-across-blocks shifts cancel in
W_c; D levels descriptive only in D1, no letter)" -- taken on one
observable axis: per arm, does any ok cell's cross-window
robust-scale LEVEL spread S_c = max_w L_{w,c} - min_w L_{w,c}
over the three windows (s36/s38/s39) exceed the cross-window
run-repartition null (the 108 runs of one arm across the three
windows exchangeable)? L_{w,c} = median of the 12 block D values
of window w (D = e_(38) about m = x_(38) of the block's 75
samples -- the s48-frozen exact-median MAD; the s35/s36-frozen
3-run block unit unchanged), max-T over the 18 cells (the max
taken inside each trial), 20,000 trials per arm, frozen RNG call
order (hi then tw), exact integer arithmetic (2*L in half-tick
units); letters pre-registered at freeze stamp
2026-10-28T10:09:54Z before any statistic was computed.

THE FINDING (DERIVED from the 234 committed run logs measured in
sessions 36/38/39; ANALYSIS slice, no hardware): T1 = (b) EXCEEDS
NULL -- the FIRST (b) row letter of the s40-49 campaign --
driven by the tw arm: tw M_obs 16.0 ticks (max cell
(max,128,S=default)), count 171/20,001, p 0.008600 (<= 0.05 at
the frozen threshold), its per-cell robust-scale level L at that
cell 71.5 / 55.5 / 56.5 ticks across s36/s38/s39 (its spread
16.0); marginal (sum,128,S=default) p 0.020049, letterless. The
hi arm reads (a) PER-CELL-MAD-LEVEL-CONSISTENT (M_obs 10.0, max
cell (min,256,S=16), count 9,468/20,001, p 0.473426).
NAMED, NOT HIDDEN: (b) implicates window-timescale per-cell
robust-scale LEVEL structure on the tw arm but names NO mechanism
(thermal / scheduling / memory / driver state all UNMEASURED) and
NOT whether the shift is physical or estimator structure; the two
arm probes are UNCORRECTED across arms (the row answer is the
pre-registered joint T1); the 36 marginal p values are
UNCORRECTED (3 marginal cells below 0.05 across the two arms,
letterless); this letter and sessions 40-48's are DIFFERENT
nulls over the SAME runs (NOT independent evidence) -- s44's
per-cell LOCATION level probe read (a) over the same windows and
s45-48's within-window wander/spread/IQR/MAD probes read (a) at
their scales; the cross-window null assumes exchangeability
ACROSS WINDOWS, a STRONGER assumption than within-window
exchangeability, and a (b) can also reflect violation of that
assumption rather than a per-cell scale mechanism; three windows
~30-60 min apart in one day, one host is LOW POWER; 20,000
trials (not the s35-frozen 100,000 -- cost, same named deviation
as sessions 40-48); threshold-artifact-vs-representation STAYS
UNRESOLVED. Integrity (DERIVED): 3/3 windows clean, C1 (a) at the
s39 window (c2 FLOOR; c8 32,829 vs 32,915, 0.26%), 6/6 block-min
vectors reproduce EXACTLY, anchor row EXACT at all three windows.
Rule 4 binds: nothing moves; accelerator-targets defaults remain
provisional (`:measured? false`); no vendor optimization exists
for Intel. The bar: NO reading -> NO ledger line (byte-identical
to HEAD), VERDICT UNCHANGED PENDING 1/4 with s31 counted (frozen
evaluator twice byte-identical; fixture pin 38/0; next executable
day slot 2026-10-29).

The slice ran in two ticks (record.txt's sections 4/8 document
the partial first tick; its section 9 the landing tick): the
derivation census (independent second parser) landed on the
second tick -- derivation-census-s49.txt, 59 rows / 0
mismatched, run twice byte-identical -- and the gate artifacts
were re-run fresh at landing, byte-identical to the pinned
artifacts (gate-rerun-s49b.txt).

Evidence: `docs/evidence/gpu/anv-b3percellmadlevel-20261028/`
(protocol.txt is the frozen pre-registration; publication-s49.txt
is the derived read over the 234 committed run logs of the three
windows; derivation-census-s49.txt is the independent second
parser (59 rows / 0 mismatched); bar-eval-s49.txt is the frozen
evaluator's unchanged verdict; record.txt is the finding).

## 2026-10-28 -- session 50 (JUN-59): the per-cell robust-scale (IQR) LEVEL cross-window repartition probe (analysis; T1 (a) PER-CELL-IQR-LEVEL-CONSISTENT on both arms)

Session 49's first-named candidate row -- "an IQR-level
cross-window probe (the other robust scale's LEVEL axis)" -- taken
on one observable axis: per arm, does any ok cell's cross-window
robust-scale LEVEL spread S_c = max_w L_{w,c} - min_w L_{w,c}
over the three windows (s36/s38/s39) exceed the cross-window
run-repartition null (the 108 runs of one arm across the three
windows exchangeable)? L_{w,c} = median of the 12 block D values
of window w (D = x_(57) - x_(19) of the block's 75 samples -- the
s47-frozen exclusive-hinge IQR; the s35/s36-frozen 3-run block
unit unchanged), max-T over the 18 cells (the max taken inside
each trial), 20,000 trials per arm, frozen RNG call order (hi
then tw), exact integer arithmetic (2*L in half-tick units);
letters pre-registered at freeze stamp 2026-10-28T11:02:52Z
before any statistic was computed.

THE FINDING (DERIVED from the 234 committed run logs measured in
sessions 36/38/39; ANALYSIS slice, no hardware): T1 = (a)
PER-CELL-IQR-LEVEL-CONSISTENT -- both arms read (a): hi M_obs
35.5 ticks (max cell (min,256,S=16)), count 1,677/20,001, p
0.083896; tw M_obs 34.0 ticks (max cell (max,128,S=default)),
count 12,239/20,001, p 0.611969 (both p > 0.05 at the frozen
threshold). NAMED, NOT HIDDEN: at these windows/powers NO ok
cell's cross-window IQR-level spread exceeds run-exchangeable
sampling noise family-wise over the 18 cells -- but this (a) does
NOT overturn session 49's MAD-level (b): the two axes are
DIFFERENT robust scales with DIFFERENT null geometries over the
SAME runs (tw's (max,128,S=default) cell shows IQR-level L 151.5
/ 120.5 / 117.5 across s36/s38/s39, spread 34.0 -- larger in
absolute ticks than its s49 MAD-level spread 16.0 -- while the
IQR-level max-T null is far wider than the MAD-level one; the
observed shifts agree in direction, the nulls disagree); the
per-cell MARGINAL p values are UNCORRECTED (2 marginal cells
below 0.05 across the two arms, letterless: tw (max,128,S=default)
p 0.000300, hi (min,256,S=16) p 0.009100 -- hi's max cell is the
same (min,256,S=16) cell that topped s49's hi arm, p 0.083896 at
the arm level is the closest an arm has come to the threshold on
the level axes, descriptive only); this letter and sessions
40-49's are DIFFERENT nulls over the SAME runs (NOT independent
evidence); the cross-window null assumes exchangeability ACROSS
WINDOWS, a STRONGER assumption than within-window exchangeability;
three windows ~30-60 min apart in one day, one host is LOW POWER;
20,000 trials (not the s35-frozen 100,000 -- cost, same named
deviation as sessions 40-49); threshold-artifact-vs-representation
STAYS UNRESOLVED. Integrity (DERIVED): 3/3 windows clean, C1 (a)
at the s39 window (c2 FLOOR; c8 32,829 vs 32,915, 0.26%), 6/6
block-min vectors reproduce EXACTLY, anchor row EXACT at all three
windows. Rule 4 binds: nothing moves; accelerator-targets defaults
remain provisional (`:measured? false`); no vendor optimization
exists for Intel. The bar: NO reading -> NO ledger line
(byte-identical to HEAD), VERDICT UNCHANGED PENDING 1/4 with s31
counted (frozen evaluator twice byte-identical; fixture pin 38/0;
next executable day slot 2026-10-29).

The slice landed in one tick: the derivation census (independent
second parser) -- derivation-census-s50.txt, 55 rows / 0
mismatched, run twice byte-identical -- and all three gate
families ran fresh at the landing tick, byte-identical to the
pinned artifacts (classify 2649/0; scoped GPU gate GREEN
123/12162/0/0 twice; full run-tests.cljk exit 1 RED AT BASE
kotoba.form, named).

Evidence: `docs/evidence/gpu/anv-b3percelliqrlevel-20261028/`
(protocol.txt is the frozen pre-registration; publication-s50.txt
is the derived read over the 234 committed run logs of the three
windows; derivation-census-s50.txt is the independent second
parser (55 rows / 0 mismatched); bar-eval-s50.txt is the frozen
evaluator's unchanged verdict; record.txt is the finding).

## 2026-10-28 -- session 51 (JUN-59): the fourth-window named-cell robust-scale LEVEL replication probe (measurement; T1 (a) REPLICATED-ON-BOTH-LEVEL-AXES)

MEASUREMENT session -- NEW hardware: the s51 window ran on
aiueos-6600hs Intel BMG G31 ANV at 2026-10-28T11:45:26Z..11:46:13Z
(78 fresh processes; byte-pinned builds 4/4). The row question is
session 50's first-named candidate: the PRE-REGISTERED DIRECTIONAL
CONTRAST of one named cell (tw, (max,128,S=default)) between two
named windows (s36 pre-shift vs s51 new), direction L_s51 < L_s36,
on BOTH frozen robust-scale level axes (the s48 exact-median MAD,
the s47 exclusive-hinge IQR), IUT joint rule, letters pre-registered
at freeze stamp 2026-10-28T11:42:02Z (before the first s51 run).

THE FINDING (DERIVED): T1 = (a) REPLICATED-ON-BOTH-LEVEL-AXES --
MAD axis 2*L 143 -> 118 (C_obs 12.5; count 99/20,001; p 0.005000),
IQR axis 2*L 303 -> 240 (C_obs 31.5; count 9/20,001; p 0.000500);
the post-shift regime of s38/s39 continues at s51 rather than the
s36 regime returning, on both axes. NAMED, NOT HIDDEN: the claim is
narrow (one cell, one window pair, one direction, IUT over two
axes, NEW data), the discovery family stays UNCORRECTED and is not
retro-corrected; no mechanism is named (thermal/scheduling/memory/
driver state all UNMEASURED; physical-vs-estimator UNRESOLVED); n=2
windows ~8.5 h apart in ONE day on ONE host is LOW POWER; 20,000
trials (named cost deviation); threshold-artifact-vs-representation
STAYS UNRESOLVED. Integrity: 4/4 windows clean, s51 C1 (a)
(c8 32,890 vs 32,915, 0.08%), prior vectors/anchors reproduce
EXACTLY. The bar: ONE ledger line (s51 hi block A, median 1137
min 988, class INTERMEDIATE/MIXED) -- day=2026-10-28, same-day
duplicate of s31's COUNTED slot -> descriptive, no day-slot
consumption; frozen evaluator 38/0, twice byte-identical ->
VERDICT PENDING 1/4 (next executable day slot 2026-10-29).
Rule 4 binds: nothing moves; accelerator-targets defaults remain
provisional (`:measured? false`); no vendor optimization exists
for Intel.

TWO-TICK LAND: the measurement + analysis tick, then the landing
tick (fresh gate re-runs byte-identical to the pins -- classify
2649/0, scoped GPU gate GREEN 123/12162/0/0 twice, full
run-tests.cljk exit 1 RED AT BASE kotoba.form, named; derivation
census re-run twice byte-identical, 205 rows / 0 mismatched).

Evidence: `docs/evidence/gpu/anv-b3levelrep-20261028/`
(protocol.txt is the frozen pre-registration; publication-s51.txt
is the derived read over the 234 committed run logs of the four
windows; derivation-census-s51.txt is the independent second
parser (205 rows / 0 mismatched); bar-eval-s51.txt is the frozen
evaluator's verdict; gate-rerun-s51b.txt is the landing re-run
record; record.txt is the finding).

## 2026-10-28 -- session 52 (JUN-59): the named-cell DEVIATION-CENTER level probe (analysis; T2 (b) NOT-SHIFTED-CONSISTENT -- the center level does NOT move with the scale level)

ANALYSIS session -- NO new hardware, NO new runs, NO builds: the
four windows s36/s38/s39/s51 are prior sessions' committed logs
only. The row question is session 51's first-named candidate ("a
deviation-center or other-quantile-pair LEVEL probe over the same
windows") taken on the DEVIATION-CENTER axis (the un-taken other-
quantile-pair half stays a named candidate row): D = x_(38) of
each block's pooled 75, the center about which the s48-frozen MAD
deviation is taken; three TWO-SIDED contrasts (s36 vs s38, s36 vs
s39, s36 vs s51) -- no prior letter fixes a center direction --
joint T2 = the pre-registered IUT (all three (a) AND one common
sign; no multiplicity correction), frozen at 2026-10-28T13:38:22Z
before any statistic of the probe was computed.

THE FINDING (DERIVED): T2 = (b) NOT-SHIFTED-CONSISTENT -- the
named cell's deviation-center level is STABLE across the same four
windows where its robust-scale level shifted: 2*L (half-tick) s36
2,833 -> s38 2,845 (C_obs -6.0; count 9,768/20,001; p 0.488426),
-> s39 2,826 (C_obs +3.5; count 13,472/20,001; p 0.673616), ->
s51 2,825 (C_obs +4.0; count 12,176/20,001; p 0.608820); all
three (b) NOT-DIFFERENT [NONZERO-NOT-SIGNIFICANT], sign split
across pairs. NAMED, NOT HIDDEN: (b) is CONSISTENT WITH a scale-
only change (estimator/dispersion structure) and against a whole-
distribution multiplicative shift, but does NOT decide physical-vs-
estimator-structure (a center shift below the noise floor cannot
be excluded -- LOW POWER, n=2 windows per contrast, ONE host, ONE
UTC day); the axis and contrast set were chosen AFTER the scale
results on these windows were known (FOURTH axis on the same
window data; the family stays separate and retro-corrects
nothing); 20,000 trials (named cost deviation); threshold-
artifact-vs-representation STAYS UNRESOLVED. Integrity: 4/4
windows clean (VERIFY mismatch 0), C1 (a) at all four windows
(c2 FLOOR; c8 0.01%/0.53%/0.26%/0.08% delta), vectors/anchors all
four reproduce EXACTLY. The bar: NO ledger line, NO day-slot
consumption (no runs); frozen evaluator 38/0, ledger eval twice
byte-identical -> VERDICT PENDING 1/4 (next executable day slot
2026-10-29). Rule 4 binds: nothing moves; accelerator-targets
defaults remain provisional (`:measured? false`); no vendor
optimization exists for Intel.

Gates (real runs this tick): classify self-test 2649/0
(byte-identical to the s51 pin); scoped GPU gate GREEN
123/12162/0/0 twice, both byte-identical to the s51 pins; full
run-tests.cljk exit 1 RED AT BASE kotoba.form (ADR-0362, outside
this diff -- touches NO .cljk namespace), stderr byte-identical
to the s51 pin -- NO green full suite claimed; derivation census
117 rows / 0 mismatched, run twice byte-identical; find
docs/evidence/gpu -name '*.sh' -> 0.

Evidence: `docs/evidence/gpu/anv-b3centerlevel-20261028/`
(protocol.txt is the frozen pre-registration; publication-s52.txt
is the derived read over the 234 committed run logs of the four
windows; derivation-census-s52.txt is the independent second
parser (117 rows / 0 mismatched); bar-eval-s52.txt is the frozen
evaluator's verdict; record.txt is the finding).

## 2026-10-28 -- session 53 (JUN-59): the named-cell OTHER-QUANTILE-PAIR (inner-quantile-pair) level probe (analysis; T3 (b) NOT-SHIFTED-CONSISTENT -- the inner-pair level does NOT move consistently with the MAD/IQR scale level)

ANALYSIS session -- NO new hardware, NO new runs, NO builds: the
four windows s36/s38/s39/s51 are prior sessions' committed logs
only. The row question is session 51's first-named candidate ("a
deviation-center or other-quantile-pair LEVEL probe over the same
windows") taken on the OTHER-QUANTILE-PAIR half (the deviation-
center half was session 52's, T2 (b)): the NAMED INNER-QUANTILE-
PAIR axis D = x_(48) - x_(28) of each block's pooled 75 (ranks
symmetric about the deviation-center x_(38), strictly inside the
s47-frozen IQR hinges x_(19), x_(57)); the rank pair (28,48) is
NAMED by this tick's pre-registration and is NOT canonical (no
prior publication fixes a second quantile pair; the outer pair
(x_(9),x_(67)) stays a named candidate row); three contrasts
(s36 vs s38, s36 vs s39, s36 vs s51), ONE-SIDED each in the
pre-registered direction C > 0 (scale-drop continuation; fixed by
the prior published MAD/IQR scale letters -- QUOTE-ONLY priors --
NOT by any inner-pair statistic), joint T3 = the pre-registered
IUT (all three (a); no multiplicity correction), frozen at
2026-10-28T14:06:54Z before any statistic of the probe was
computed.

THE FINDING (DERIVED): T3 = (b) NOT-SHIFTED-CONSISTENT -- the
named cell's inner-quantile-pair spread level does NOT
consistently continue the scale-drop regime its MAD/IQR levels
showed on the same four windows: 2*L (half-tick) s36 118 ->
s38 102 (C_obs +8.0, the pre-registered direction; count
1,942/20,001; p 0.097145) -> (b) NOT-DIFFERENT
[NONZERO-NOT-SIGNIFICANT]; -> s39 128 (C_obs -5.0 OPPOSITE
direction; count 16,132/20,001; p 0.806610) -> (b) NOT-DIFFERENT
[OPPOSITE-DIRECTION]; -> s51 113 (C_obs +2.5; count 7,150/20,001;
p 0.357532) -> (b) NOT-DIFFERENT [NONZERO-NOT-SIGNIFICANT]; all
three (b) => joint (b). NAMED, NOT HIDDEN: (b) is CONSISTENT
WITH a change localized at the hinges/edges (estimator structure)
or confined to the outer spread -- the inner pair did not
compress with the MAD/IQR level -- but does NOT decide physical-
vs-estimator-structure (an inner-pair shift below the noise floor
cannot be excluded -- the 12 block D values per window scatter
36..95, LOW POWER, n=2 windows per contrast, ONE host, ONE UTC
day; s38 ran in the pre-registered direction at p 0.097, NOT
significant at the frozen 0.05 threshold); (b) does NOT overturn
s51's T1 (a) and is CONSISTENT WITH s52's T2 (b) (different
axes); the probe is a FIFTH axis on the same window data, chosen
AFTER the scale/center results were known; the family stays
separate and retro-corrects nothing; 20,000 trials (named cost
deviation); threshold-artifact-vs-representation STAYS
UNRESOLVED. Integrity: 4/4 windows clean (VERIFY mismatch 0), C1
(a) at all four windows (c2 FLOOR; c8 0.01%/0.53%/0.26%/0.08%
delta), vectors/anchors all four reproduce EXACTLY. The bar: NO
ledger line, NO day-slot consumption (no runs); frozen evaluator
38/0, ledger eval twice byte-identical -> VERDICT PENDING 1/4
(next executable day slot 2026-10-29). Rule 4 binds: nothing
moves; accelerator-targets defaults remain provisional
(`:measured? false`); no vendor optimization exists for Intel.

Gates (real runs this tick): classify self-test 2649/0
(byte-identical to the s51/s52 pins); scoped GPU gate GREEN
123/12162/0/0 twice, both byte-identical to the s52 pins; full
run-tests.cljk exit 1 RED AT BASE kotoba.form (ADR-0362, outside
this diff -- touches NO .cljk namespace), stdout+stderr
byte-identical to the s52 pins -- NO green full suite claimed;
derivation census 117 rows / 0 mismatched, run twice
byte-identical; find docs/evidence/gpu -name '*.sh' -> 0.

Evidence: `docs/evidence/gpu/anv-b3innerlevel-20261028/`
(protocol.txt is the frozen pre-registration; publication-s53.txt
is the derived read over the committed run logs of the four
windows (78 runs parsed each); derivation-census-s53.txt is the
independent second parser (117 rows / 0 mismatched);
bar-eval-s53.txt is the frozen evaluator's verdict; record.txt is
the finding).

## 2026-10-28 -- session 54 (JUN-59): the named-cell OUTER-QUANTILE-PAIR level probe (analysis; T4 (a) OUTER-SPREAD-LEVEL-SHIFTED-CONSISTENT -- the outer-pair level moves WITH the MAD/IQR scale level, unlike the inner pair)

ANALYSIS session -- NO new hardware, NO new runs, NO builds: the
four windows s36/s38/s39/s51 are prior sessions' committed logs
only. The row question is session 53's first-named candidate
("the OUTER-quantile-pair (x_(9),x_(67)) LEVEL probe over the same
windows"): the NAMED OUTER-QUANTILE-PAIR axis D = x_(67) - x_(9)
of each block's pooled 75 (ranks symmetric about the deviation-
center x_(38), strictly OUTSIDE the s47-frozen IQR hinges
x_(19), x_(57) -- the pair spans the tails and the whole body);
the rank pair (9,67) is NAMED by this tick's pre-registration and
is NOT canonical (no prior publication fixes a quantile pair
beyond the IQR hinges and the s53 inner pair (28,48)); three
contrasts (s36 vs s38, s36 vs s39, s36 vs s51), ONE-SIDED each in
the pre-registered direction C > 0 (scale-drop continuation; fixed
by the prior published MAD/IQR scale letters -- QUOTE-ONLY priors
-- NOT by any outer-pair statistic), joint T4 = the pre-registered
IUT (all three (a); no multiplicity correction), frozen at
2026-10-28T14:35:25Z before any statistic of the probe was
computed.

THE FINDING (DERIVED): T4 = (a) OUTER-SPREAD-LEVEL-SHIFTED-
CONSISTENT -- the named cell's outer-quantile-pair spread level
DOES consistently continue the scale-drop regime its MAD/IQR
levels showed on the same four windows (the FIRST (a) letter of
the quantile-pair-level family): 2*L (half-tick) s36 496 -> s38
429 (C_obs +33.5, the pre-registered direction; count 108/20,001;
p 0.005450) -> (a) OUTER-DIFFERENT-CONTINUED; -> s39 437 (C_obs
+29.5; count 261/20,001; p 0.013099) -> (a); -> s51 446 (C_obs
+25.0; count 618/20,001; p 0.030948) -> (a); all three (a) =>
joint (a). NAMED, NOT HIDDEN: (a) on the outer pair COMBINED WITH
s53's inner-pair (b) is CONSISTENT WITH a change confined to the
outer spread -- the compression reached the tails/whole-body span
x_(9)..x_(67) (496 -> 429/437/446) but did NOT reach the inner
quantile pair x_(28)..x_(48) (118/102/128/113 scattered, s53 (b))
while the center held (2833/2845/2826/2825, s52 (b)) -- but does
NOT decide physical-vs-estimator-structure (no mechanism named by
any letter; LOW POWER, n=2 windows per contrast, the three
contrasts share the s36 window and are dependent, ONE host, ONE
UTC day; s36-specific state alone can produce (a)); the probe is
a SIXTH axis on the same window data, chosen AFTER the scale/
center/inner-pair results were known; the family stays separate
and retro-corrects nothing (the discovery family behind the cell
choice stays uncorrected); 20,000 trials (named cost deviation);
threshold-artifact-vs-representation STAYS UNRESOLVED. Integrity:
4/4 windows clean (VERIFY mismatch 0), C1 (a) at all four windows
(c2 FLOOR; c8 0.01%/0.53%/0.26%/0.08% delta), vectors/anchors all
four reproduce EXACTLY. The bar: NO ledger line, NO day-slot
consumption (no runs); frozen evaluator 38/0, ledger eval twice
byte-identical -> VERDICT PENDING 1/4 (next executable day slot
2026-10-29). Rule 4 binds: nothing moves; accelerator-targets
defaults remain provisional (`:measured? false`); no vendor
optimization exists for Intel.

Gates (real runs this tick): classify self-test 2649/0
(byte-identical to the s51/s52/s53 pins); scoped GPU gate GREEN
123/12162/0/0 twice, both byte-identical to the s53 pins; full
run-tests.cljk exit 1 RED AT BASE kotoba.form (ADR-0362, outside
this diff -- touches NO .cljk namespace), stdout+stderr
byte-identical to the s53 pins -- NO green full suite claimed;
derivation census 117 rows / 0 mismatched, run twice
byte-identical; find docs/evidence/gpu -name '*.sh' -> 0.

Evidence: `docs/evidence/gpu/anv-b3outerlevel-20261028/`
(protocol.txt is the frozen pre-registration; publication-s54.txt
is the derived read over the committed run logs of the four
windows (78 runs parsed each); derivation-census-s54.txt is the
independent second parser (117 rows / 0 mismatched);
bar-eval-s54.txt is the frozen evaluator's verdict; record.txt is
the finding).

## 2026-10-28 -- session 55 (JUN-59): the inner-vs-outer compression-profile read (analysis; T5 (a) COMPRESSION-PROFILE-OUTER-WEIGHTED-CONSISTENT -- the outer-pair level drops MORE than the inner-pair level in all three named contrasts)

ANALYSIS session -- NO new hardware, NO new runs, NO builds: the
four windows s36/s38/s39/s51 are prior sessions' committed logs
only. The row question is session 54's first-named candidate
("the INNER-vs-OUTER COMPRESSION-PROFILE read over the same
windows -- the formal juxtaposition of the two named quantile-
pair level axes"): the PROFILE axis, the difference-in-
differences 2*P_obs = 2*C_out - 2*C_in where 2*C_out =
2*Lout_s36 - 2*Lout_w (the s54-frozen outer pair D_out =
x_(67) - x_(9)) and 2*C_in = 2*Lin_s36 - 2*Lin_w (the s53-frozen
inner pair D_in = x_(48) - x_(28)), both per block over the SAME
pooled 75 of the named cell; three contrasts (s36 vs s38, s36 vs
s39, s36 vs s51), ONE-SIDED each in the pre-registered direction
P > 0 (outer-weighted compression), joint T5 = the pre-registered
IUT (all three (a); no multiplicity correction), frozen at
2026-10-28T15:08:37Z before any statistic of the probe was
computed.

THE FINDING (DERIVED): T5 = (a) COMPRESSION-PROFILE-OUTER-
WEIGHTED-CONSISTENT -- the named cell's quantile-pair spread
compression IS consistently outer-weighted on the three named
contrasts: 2*P_obs s36-vs-s38 51 (OUT 2*L 496 -> 429, IN 118 ->
102; count 473/20,001; p 0.023699) (a) PROFILE-OUTER-WEIGHTED-
DIFFERENT, -> s39 69 (OUT 496 -> 437, IN 118 -> 128; count
103/20,001; p 0.005200) (a), -> s51 45 (OUT 496 -> 446, IN 118
-> 113; count 784/20,001; p 0.039248) (a) -- all three (a).
NAMED, NOT HIDDEN: this is the FIRST probe of the campaign whose
axis is COMPOSED of two already-published axes, and the
juxtaposition/direction were chosen AFTER s53's inner-pair (b)
and s54's outer-pair (a) were published -- it does NOT test a new
prediction (the point estimates 51/69/45 were already known
positive, QUOTE-ONLY) and quantifies whether the outer-vs-inner
gap exceeds the frozen resampling noise; (a) is CONSISTENT WITH a
compression concentrated toward the tails/whole-body span
x_(9)..x_(67) (the formalized outer-weighted profile) but does
NOT decide physical-vs-estimator-structure (no mechanism named
by any letter; LOW POWER n=2 windows per contrast, the three
contrasts share the s36 window and are dependent, ONE host, ONE
UTC day; s36-specific state alone can produce (a)); SEVENTH axis
on the same window data, a SEPARATE named family; retro-corrects
nothing; 20,000 trials (named cost deviation); threshold-
artifact-vs-representation STAYS UNRESOLVED. Integrity: 4/4
windows clean (VERIFY mismatch 0), C1 (a) at all four windows
(c2 FLOOR; c8 0.01%/0.53%/0.26%/0.08% delta), vectors/anchors all
four reproduce EXACTLY; the D1 inner/outer 2*L values reproduce
the s53/s54 priors EXACTLY. The bar: NO ledger line, NO day-slot
consumption (no runs); frozen evaluator 38/0, ledger eval twice
byte-identical -> VERDICT PENDING 1/4 (next executable day slot
2026-10-29). Rule 4 binds: nothing moves; accelerator-targets
defaults remain provisional (`:measured? false`); no vendor
optimization exists for Intel.

Gates (real runs this tick): classify self-test 2649/0
(byte-identical to the s51-s54 pins); scoped GPU gate GREEN
123/12162/0/0 twice, both byte-identical to the s54 pins; full
run-tests.cljk exit 1 RED AT BASE kotoba.form (ADR-0362, outside
this diff -- touches NO .cljk namespace), stdout+stderr
byte-identical to the s54 pins -- NO green full suite claimed;
derivation census 167 rows / 0 mismatched, run twice
byte-identical; find docs/evidence/gpu -name '*.sh' -> 0.

Evidence: `docs/evidence/gpu/anv-b3innerouterprofile-20261028/`
(protocol.txt is the frozen pre-registration; publication-s55.txt
is the derived read over the committed run logs of the four
windows (78 runs parsed each); derivation-census-s55.txt is the
independent second parser (167 rows / 0 mismatched);
bar-eval-s55.txt is the frozen evaluator's verdict; record.txt is
the finding).

## 2026-10-28 -- session 56 (JUN-59): the second named rank-pair set compression-profile read (analysis; T6 (b) NOT-SECONDPAIR-PROFILE-OUTER-WEIGHTED-CONSISTENT -- the outer-weighted profile does NOT consistently replicate at the halving-rule rank pairs)

Session 55's third named candidate row ("any further named
profile pair (other outer/inner rank pairs stay named candidate
rows)") taken on the SECOND NAMED RANK-PAIR SET of the SAME four
windows s36/s38/s39/s51 of the named-cell robust-scale level
campaign (ANALYSIS only): does the outer-weighted compression
profile of s55's T5 (a) replicate when the outer and inner
quantile-pair ranks are moved by the pre-registered HALVING RULE
-- OUTER2 = (x_(5), x_(71)) halfway between s54's (9,67) and the
full range (1,75); INNER2 = (x_(33), x_(43)) halfway between
s53's (28,48) and the center (38,38)? The rank pairs are named
by the rule BEFORE any second-pair statistic was computed
(protocol freeze stamp 2026-10-28T15:41:51Z). PRIMARY STATISTIC:
the difference-in-differences 2*P2_obs = 2*C_out2 - 2*C_in2
(D_out2 = x_(71) - x_(5), D_in2 = x_(43) - x_(33) per block of
the SAME pooled 75; 2*L = 6th+7th order statistics of the 12
block D values); THREE contrasts (s36 vs s38, s36 vs s39, s36 vs
s51), ONE-SIDED each in the pre-registered direction P2 > 0
(outer-weighted compression at the second pair set -- direction
fixed by s55's published T5 (a) reading, QUOTE-ONLY), joint T6 =
the pre-registered INTERSECTION-UNION rule (all three (a); NO
multiplicity correction); 20,000 trials, seed 2026102806, frozen
probe order, both axes on the same pseudo-blocks. NAMED, NOT
HIDDEN: unlike s55, this probe DOES test a FRESH pre-registered
prediction -- the second-pair levels were never published or
computed anywhere.

THE FINDING (DERIVED; publication-s56.txt, analysis-s56.py run
twice byte-identical): T6 = (b) NOT-SECONDPAIR-PROFILE-OUTER-
WEIGHTED-CONSISTENT (named: pair(s) not (a): s39, s51) -- the
outer-weighted profile does NOT consistently replicate at the
second pair set at the frozen threshold: s36-vs-s38 2*P2_obs 98
(P2 +49.0; OUT2 2*L 713 -> 606 (2*C_out2 107), IN2 63 -> 54
(2*C_in2 9); count 436 / 20,001; p 0.021849) (a) SECONDPAIR-
OUTER-WEIGHTED-DIFFERENT, but s36-vs-s39 2*P2_obs 53 (P2 +26.5;
OUT2 713 -> 659 (54), IN2 63 -> 62 (1); count 3,876 / 20,001; p
0.193840) (b) NOT-DIFFERENT [NONZERO-NOT-SIGNIFICANT] and
s36-vs-s51 2*P2_obs 94 (P2 +47.0; OUT2 713 -> 612 (101), IN2 63
-> 56 (7); count 1,116 / 20,001; p 0.055847) (b) NOT-DIFFERENT
[NONZERO-NOT-SIGNIFICANT]. ALL THREE point estimates sit in the
pre-registered direction (98/53/94 all positive) but only the
s38 contrast clears the frozen 0.05 threshold (s51 at p 0.0558
is marginal). NAMED, NOT HIDDEN: (b) is CONSISTENT WITH the s55
outer-weighted profile being rank-pair specific OR a power loss
at the second pair set (the IN2 spreads sit near the center --
2*L 63/54/62/56 -- where block D values are small and noisy);
(b) does NOT overturn s55's T5 (a) (different rank pairs, a
SEPARATE named family) and formally quantifies the rank-choice
fragility that s55's "NAMED, NOT HIDDEN" caveats only asserted;
this is an EIGHTH axis on the same window data, chosen AFTER the
scale/center/inner/outer/profile results were known (the FAMILY
is fresh, retro-corrects nothing); (a) or (b) names NO mechanism
(thermal/scheduling/memory/driver state all UNMEASURED) and NOT
whether any movement is physical or estimator structure; LOW
POWER, n=2 windows per contrast, ONE host, ONE UTC day; the three
contrasts share the s36 window and are dependent (the IUT does
not care); 20,000 trials (NOT the s35-frozen 100,000 -- cost,
same named deviation as sessions 40-55; p resolution 1/20,001
~= 5e-5); threshold-artifact-vs-representation STAYS UNRESOLVED.
Integrity (DERIVED): 4/4 windows clean (78 runs parsed each,
VERIFY mismatch total 0); C1 (a) at ALL FOUR windows (c2 FLOOR;
c8 0.01%/0.53%/0.26%/0.08% delta vs committed 32,915); all four
windows' block-min vectors and anchor rows reproduce their
published/quote-only priors EXACTLY. The bar: NO ledger line, NO
day-slot consumption (no runs this session; the 2026-10-28 slot
is s31's); frozen evaluator 38/0, ledger eval twice byte-
identical -> VERDICT PENDING 1/4 (next executable day slot
2026-10-29). Rule 4 binds: nothing moves; accelerator-targets
defaults remain provisional (`:measured? false`); no vendor
optimization exists for Intel.

Gates (real runs this tick): classify self-test 2649/0
(byte-identical to the s55 pin); scoped GPU gate GREEN
123/12162/0/0 twice, both byte-identical to the s55 pin and to
each other; full run-tests.cljk exit 1 RED AT BASE kotoba.form
(ADR-0362, outside this diff -- touches NO .cljk namespace),
stdout+stderr byte-identical to the s55 pins -- NO green full
suite claimed; derivation census 159 rows / 0 mismatched, run
twice byte-identical; find docs/evidence/gpu -name '*.sh' -> 0.

Named candidate rows for later sessions: (first) a FIFTH-window
replication on another UTC day (needs NEW hardware; the bar's
next day slot 2026-10-29 is then reachable; it can carry both
quantile-pair level axes AND the second-pair profile axis at
once); then the s38 hi (sum,256,S=32) wander replication (needs
NEW hardware at a future window); then any further named profile
pair (other outer/inner rank pairs stay named candidate rows).

Evidence: `docs/evidence/gpu/anv-b3pair2profile-20261028/`
(protocol.txt is the frozen pre-registration; publication-s56.txt
is the derived read over the committed run logs of the four
windows (78 runs parsed each); derivation-census-s56.txt is the
independent second parser (159 rows / 0 mismatched);
bar-eval-s56.txt is the frozen evaluator's verdict; record.txt is
the finding).

## 2026-10-28 (session 57, JUN-59) -- the fifth-window
cross-UTC-day replication PRE-REGISTRATION FREEZE (DESIGN slice;
STARTED, NOT FINISHED)

Session 57 took the queue's FIRST named candidate row to its
design half: the FIFTH-window cross-UTC-day named-cell
robust-scale level replication is now PRE-REGISTERED in
`docs/evidence/gpu/anv-b3w5xdayrep-20261029/protocol.txt` (freeze
stamp 2026-10-28T16:15:35Z), frozen BEFORE any fifth-window run
exists -- no committed file contains any W5 quantity. The row's
MEASUREMENT half is day-slot-gated and was NOT run this tick:
W5 is DEFINED as the window measured at or after
2026-10-29T00:00:00Z (the bar's 2026-10-29 UTC day slot; this
tick ran 7h45m before that slot opened -- NAMED, not skipped
silently; a window run on 2026-10-28 would share the one UTC day
every prior letter already covers and burn the row as a
same-day-descriptive bar line). Frozen contract: T7 = the
pre-registered directional contrast 2*C_obs = 2*L_s36 - 2*L_W5 >
0 of the tw (max,128,S=default) cell on BOTH frozen level axes
(the s48 exact-median MAD e_(38) and the s47 exclusive-hinge IQR
x_(57)-x_(19); block = 3 consecutive runs, 12 blocks, pooled 75;
2*L = 6th+7th order statistics of the 12 block D values), vs the
two-window run-repartition null over the 72 tw runs of s36 and W5
(20,000 trials, ONE random.Random(20261029) in the frozen probe
order MAD then IQR), joint T7 = INTERSECTION-UNION (both axes
(a) = (a) CROSS-DAY-REPLICATED-ON-BOTH-LEVEL-AXES), per-axis
letters (a) REPLICATED-CONTINUED / (b) NOT-REPLICATED (named
sub-cases) / (c) NOT EVALUABLE. NAMED, NOT HIDDEN: every letter
of sessions 40-56 was computed on windows ALL run in the ONE UTC
day 2026-10-28 on ONE host -- T7 is the campaign's FIRST test of
whether the s36-to-post-shift movement survives the UTC-day
boundary; STILL LOW POWER (n=2 windows, 12 blocks, ONE host);
(a) names NO mechanism and NOT physical-vs-estimator-structure;
threshold-artifact-vs-representation STAYS UNRESOLVED. The W5
data additionally carries (each later row keeps its OWN freeze):
the quantile-pair level axes at W5, the second-pair profile axis
at W5, the s38 hi (sum,256,S=32) wander replication on W5's hi
runs (queue row 2), and any further named profile pair (queue
row 3). Gates (real runs this tick): classify self-test 2649/0
(byte-identical to the s56 pin); scoped GPU gate GREEN
123/12162/0/0 twice (byte-identical to the s56 pin and each
other); full run-tests.cljk exit 1 RED AT BASE kotoba.form
(ADR-0362, outside this diff -- touches NO .cljk namespace),
captures byte-identical to the s56 pins -- NO green full suite
claimed; settle-bar evaluator 38/0 + ledger eval twice
byte-identical -> VERDICT PENDING 1/4 unchanged (no runs, no
ledger line, no day slot; next executable slot 2026-10-29); no
derivation census (a freeze-only tick computes no statistics --
named, not omitted); find docs/evidence/gpu -name '*.sh' -> 0.
Rule 4 binds: nothing moves; accelerator-targets defaults remain
provisional (`:measured? false`); no vendor optimization exists
for Intel.

Named candidate rows for later sessions (unchanged order):
(first, now STARTED) the fifth-window measurement + T7 read in
the 2026-10-29 UTC slot (NEW hardware); then the s38 hi
(sum,256,S=32) wander replication (NEW hardware -- W5's hi runs);
then any further named profile pair (other outer/inner rank pairs
stay named candidate rows).

Evidence: `docs/evidence/gpu/anv-b3w5xdayrep-20261029/`
(protocol.txt is the frozen pre-registration -- written once,
never rewritten; freeze-record-s57.txt is this tick's record -- the
W5 measurement session owns record.txt there; the gate
captures are byte-identical to the s56 pins). The measurement
half of the row is UNMEASURED until the 2026-10-29 UTC slot.

## 2026-10-28 -- session 58 (JUN-59): the third named rank-pair set compression-profile read (analysis; T8 (a) THIRDPAIR-PROFILE-OUTER-WEIGHTED-CONSISTENT -- the outer-weighted profile RE-EMERGES at the third halving-ladder rank pairs)

Session 57's queue third named candidate row ("any further named
profile pair (other outer/inner rank pairs stay named candidate
rows)") taken on the THIRD NAMED RANK-PAIR SET of the SAME four
windows s36/s38/s39/s51 of the named-cell robust-scale level
campaign (ANALYSIS only): does the outer-weighted compression
profile of s55's T5 (a) re-emerge when the outer and inner
quantile-pair ranks are moved one more step along the
pre-registered HALVING LADDER -- OUTER3 = (x_(3), x_(73)) halfway
between s56's (5,71) and the full range (1,75); INNER3 =
(x_(35), x_(41)), where the exact halving between s56's (33,43)
and the center (38,38) lands on the HALF-INTEGER k=2.5 and is
rounded half-away-from-zero to k=3 -- a named rule choice,
frozen BEFORE any third-pair statistic existed (protocol freeze
stamp 2026-10-28T16:36:43Z), the alternative rounding (k=2 ->
(36,40)) staying a named candidate row? PRIMARY STATISTIC: the
difference-in-differences 2*P3_obs = 2*C_out3 - 2*C_in3 (D_out3
= x_(73) - x_(3), D_in3 = x_(41) - x_(35) per block of the SAME
pooled 75; 2*L = 6th+7th order statistics of the 12 block D
values); THREE contrasts (s36 vs s38, s36 vs s39, s36 vs s51),
ONE-SIDED each in the pre-registered direction P3 > 0
(outer-weighted compression at the third pair set -- direction
fixed by s55's published T5 (a) reading and the ladder framing,
QUOTE-ONLY; s56's T6 (b) is KNOWN and did NOT change the
direction), joint T8 = the pre-registered INTERSECTION-UNION
rule (all three (a); NO multiplicity correction); 20,000 trials,
seed 2026102808, frozen probe order, both axes on the same
pseudo-blocks. NAMED, NOT HIDDEN: this probe DOES test a FRESH
pre-registered prediction -- the third-pair levels were never
published or computed anywhere.

THE FINDING (DERIVED; publication-s58.txt, analysis-s58.py run
twice byte-identical): T8 = (a) THIRDPAIR-PROFILE-OUTER-
WEIGHTED-CONSISTENT -- all three contrasts (a): s36-vs-s38
2*P3_obs 181 (P3 +90.5; OUT3 2*L 902 -> 721 (2*C_out3 181), IN3
36 -> 36 (2*C_in3 0); count 57 / 20,001; p 0.002900) (a)
THIRDPAIR-OUTER-WEIGHTED-DIFFERENT, s36-vs-s39 2*P3_obs 92 (P3
+46.0; OUT3 902 -> 811 (91), IN3 36 -> 37 (-1); count 770 /
20,001; p 0.038548) (a), and s36-vs-s51 2*P3_obs 119 (P3 +59.5;
OUT3 902 -> 776 (126), IN3 36 -> 29 (7); count 409 / 20,001; p
0.020499) (a). ALL THREE contrasts clear the frozen 0.05
threshold in the pre-registered direction.

NAMED, NOT HIDDEN: (a) at T8 FOLLOWING s56's T6 (b) is
CONSISTENT WITH the s56 (b) having been a POWER LOSS at the
near-center inner2 pair rather than rank-pair specificity -- at
the third ladder step the outer3 level carries the whole signal
(902 -> 721/811/776) while the inner3 level is flat near its
noise floor (2*L 36/36/37/29; the inner3 pair spans only 6
ranks), so P3 ~= C_out3 at this step (2*C_in3 is 0/-1/+7); (a)
is equally CONSISTENT WITH the outer-weighted reading being an
outer-spread phenomenon at every ladder step whose outer pair
carries enough span to measure; NEITHER reading names a
mechanism (thermal/scheduling/memory/driver state all UNMEASURED)
and NOT whether any movement is physical or estimator structure;
(a) does NOT overturn s56's T6 (b) (different rank pairs, a
SEPARATE named family) and does NOT settle the rank-pair
question by itself (ladder steps 2 and 3 disagree; the k=2
inner3 rounding variant and the ladder's fourth pair set stay
named candidate rows); this is a NINTH axis on the SAME window
data and the campaign's SECOND fresh pre-registered prediction
(the third-pair levels had no priors); LOW POWER, n=2 windows
per contrast, ONE host, ONE UTC day; threshold-artifact-vs-
representation and physical-vs-estimator-structure STAY
UNRESOLVED. Integrity (DERIVED): 4/4 windows clean (78 runs
parsed each, VERIFY mismatch total 0); C1 (a) at ALL FOUR
windows (c2 FLOOR; c8 0.01%/0.53%/0.26%/0.08% delta vs committed
32,915); all four windows' block-min vectors and anchor rows
reproduce their published/quote-only priors EXACTLY. BAR: NO
ledger line and NO day-slot consumption (no runs this session;
the 2026-10-28 slot is s31's); frozen evaluator --self-test 38/0,
ledger eval twice byte-identical -> VERDICT PENDING 1/4
unchanged; next executable day slot 2026-10-29. RULE 4
unchanged: NOTHING MOVES -- accelerator-targets defaults remain
provisional (:measured? false); NO vendor optimization exists
for Intel. Gates (real runs; every capture byte-identical to its
pinned s56 artifact): gpu_regime_classify.py --self-test 2649/0;
scoped GPU gate GREEN 123/12162/0/0 run 1 AND run 2 (scratch
runner scratch/scoped-gpu-gate.cljk -- eight GPU-owned
namespaces, created/run/deleted, never committed); FULL
run-tests.cljk LIVE: exit 1, RED AT BASE kotoba.form (ADR-0362,
outside this diff -- touches NO .cljk namespace) -- NO green full
suite claimed; derivation-census-s58.txt: independent second
parser (split-based, no re module, no numpy; pure-Python sorted()
order statistics from ONE shared sort per pooled 75 --
sorted(pooled75)[72] - sorted(pooled75)[2] and
sorted(pooled75)[40] - sorted(pooled75)[34]; independent
pure-Python shuffle loop under the frozen RNG contract
random.Random(2026102808) consumed in the frozen probe order,
BOTH axes on the SAME pseudo-blocks) re-deriving every published
integer, count, p value and letter -- 159 rows / 0 mismatched,
run twice byte-identical; find docs/evidence/gpu -name '*.sh' ->
0.

Named candidate rows for later sessions (unchanged order):
(first, STARTED) the fifth-window measurement + T7 read in the
2026-10-29 UTC slot (NEW hardware); then the s38 hi
(sum,256,S=32) wander replication (NEW hardware -- W5's hi
runs); then any further named profile pair (the halving ladder's
fourth pair set, or the k=2 inner3 rounding variant, stay named
candidate rows).

Evidence: `docs/evidence/gpu/anv-b3pair3profile-20261028/`
(protocol.txt is the frozen pre-registration -- written once,
never rewritten; record.txt is this tick's record; the gate
captures are byte-identical to the s56 pins).

## 2026-10-28 -- session 59 (JUN-59): the fourth named rank-pair set compression-profile read (analysis; T9 (a) FOURTHPAIR-PROFILE-OUTER-WEIGHTED-CONSISTENT -- the outer-weighted profile HOLDS at the fourth halving-ladder rank pairs)

Session 58's queue third named candidate row ("any further named
profile pair (the halving ladder's fourth pair set, or the k=2
inner3 rounding variant, stay named candidate rows)") taken FIRST
on the FOURTH NAMED RANK-PAIR SET of the SAME four windows
s36/s38/s39/s51 of the named-cell robust-scale level campaign
(ANALYSIS only): does the outer-weighted compression profile of
s55's T5 (a) hold when the outer and inner quantile-pair ranks
are moved one more step along the pre-registered HALVING LADDER --
OUTER4 = (x_(2), x_(74)) halfway between s58's (3,73) and the
full range (1,75); INNER4 = (x_(36), x_(40)), where the exact
halving between s58's (35,41) and the center (38,38) lands on
the HALF-INTEGER k=1.5 and is rounded half-away-from-zero to k=2
by the ALREADY-FROZEN s58 tie-break rule, applied UNCHANGED (no
new rule choice at this step), frozen BEFORE any fourth-pair
statistic existed (protocol freeze stamp 2026-10-28T17:06:21Z);
NAMED, NOT HIDDEN: INNER4 (36,40) COINCIDES EXACTLY with the
s58-named k=2 inner3 rounding-variant pair -- this probe's inner
axis IS that variant's inner axis. PRIMARY STATISTIC: the
difference-in-differences 2*P4_obs = 2*C_out4 - 2*C_in4 (D_out4
= x_(74) - x_(2), D_in4 = x_(40) - x_(36) per block of the SAME
pooled 75; 2*L = 6th+7th order statistics of the 12 block D
values); THREE contrasts (s36 vs s38, s36 vs s39, s36 vs s51),
ONE-SIDED each in the pre-registered direction P4 > 0
(outer-weighted compression at the fourth pair set -- direction
fixed by s55's published T5 (a) reading and the ladder framing,
QUOTE-ONLY; s56's T6 (b) and s58's T8 (a) are KNOWN and did NOT
change the direction), joint T9 = the pre-registered
INTERSECTION-UNION rule (all three (a); NO multiplicity
correction); 20,000 trials, seed 2026102809, frozen probe order,
both axes on the same pseudo-blocks. NAMED, NOT HIDDEN: this
probe DOES test a FRESH pre-registered prediction -- the
fourth-pair levels were never published or computed anywhere
(the campaign's THIRD fresh prediction after s56 and s58).

THE FINDING (DERIVED; publication-s59.txt, analysis-s59.py run
twice byte-identical): T9 = (a) FOURTHPAIR-PROFILE-OUTER-
WEIGHTED-CONSISTENT -- all three contrasts (a): s36-vs-s38
2*P4_obs 143 (P4 +71.5; OUT4 2*L 987 -> 846 (2*C_out4 141), IN4
19 -> 21 (2*C_in4 -2); count 7 / 20,001; p 0.000400) (a)
FOURTHPAIR-OUTER-WEIGHTED-DIFFERENT, s36-vs-s39 2*P4_obs 89 (P4
+44.5; OUT4 987 -> 903 (84), IN4 19 -> 24 (-5); count 63 /
20,001; p 0.003200) (a), and s36-vs-s51 2*P4_obs 93 (P4 +46.5;
OUT4 987 -> 895 (92), IN4 19 -> 20 (-1); count 197 / 20,001; p
0.009900) (a). ALL THREE contrasts clear the frozen 0.05
threshold in the pre-registered direction.

NAMED, NOT HIDDEN: (a) at T9 FOLLOWING s56's T6 (b) and s58's
T8 (a) is CONSISTENT WITH an outer-weighted compression that
persists as the outer pair walks toward the full range -- at the
fourth ladder step the outer4 level carries the whole signal (987
-> 846/903/895) while the inner4 level is flat near its noise
floor (2*L 19/21/24/20; the inner4 pair spans only 4 ranks, so
P4 ~= C_out4 at this step (2*C_in4 is -2/-5/-1)) -- and with the
s56 (b) having been a POWER LOSS at the near-center inner2 pair
rather than rank-pair specificity; (a) is equally CONSISTENT
WITH the outer-weighted reading being an outer-spread phenomenon
at every ladder step whose outer pair carries enough span to
measure; NEITHER reading names a mechanism
(thermal/scheduling/memory/driver state all UNMEASURED) and NOT
whether any movement is physical or estimator structure; (a) does
NOT overturn s56's T6 (b) (different rank pairs, a SEPARATE
named family); the ladder letter sequence now reads step1 (a) /
step2 (b) / step3 (a) / step4 (a) and the rank-pair question is
NOT settled by itself (the ladder's fifth pair set, the k=2
inner3 variant's OUTER3-held T8 re-read and any non-ladder rank
pairs stay named candidate rows); this is a TENTH axis on the
SAME window data and the campaign's THIRD fresh pre-registered
prediction (the fourth-pair levels had no priors); LOW POWER,
n=2 windows per contrast, ONE host, ONE UTC day;
threshold-artifact-vs-representation and
physical-vs-estimator-structure STAY UNRESOLVED. Integrity
(DERIVED): 4/4 windows clean (78 runs parsed each, VERIFY
mismatch total 0); C1 (a) at ALL FOUR windows (c2 FLOOR; c8
0.01%/0.53%/0.26%/0.08% delta vs committed 32,915); all four
windows' block-min vectors and anchor rows reproduce their
published/quote-only priors EXACTLY. BAR: NO ledger line and NO
day-slot consumption (no runs this session; the 2026-10-28 slot
is s31's); frozen evaluator --self-test 38/0, ledger eval twice
byte-identical -> VERDICT PENDING 1/4 unchanged; next executable
day slot 2026-10-29. RULE 4 unchanged: NOTHING MOVES --
accelerator-targets defaults remain provisional (:measured?
false); NO vendor optimization exists for Intel. Gates (real
runs; every capture byte-identical to its pinned s58 artifact):
gpu_regime_classify.py --self-test 2649/0; scoped GPU gate GREEN
123/12162/0/0 run 1 AND run 2 (scratch runner
scratch/scoped-gpu-gate.cljk -- eight GPU-owned namespaces,
created/run/deleted, never committed); FULL run-tests.cljk LIVE:
exit 1, RED AT BASE kotoba.form (ADR-0362, outside this diff --
touches NO .cljk namespace) -- NO green full suite claimed;
derivation-census-s59.txt: independent second parser
(split-based, no re module, no numpy; pure-Python sorted() order
statistics from ONE shared sort per pooled 75 --
sorted(pooled75)[73] - sorted(pooled75)[1] and
sorted(pooled75)[39] - sorted(pooled75)[35]; independent
pure-Python shuffle loop under the frozen RNG contract
random.Random(2026102809) consumed in the frozen probe order,
BOTH axes on the SAME pseudo-blocks) re-deriving every published
integer, count, p value and letter -- 159 rows / 0 mismatched,
run twice byte-identical; find docs/evidence/gpu -name '*.sh' ->
0.

Named candidate rows for later sessions (unchanged order):
(first, STARTED) the fifth-window measurement + T7 read in the
2026-10-29 UTC slot (NEW hardware); then the s38 hi
(sum,256,S=32) wander replication (NEW hardware -- W5's hi
runs); then any further named profile pair (the halving ladder's
fifth pair set, or the k=2 inner3 variant's T8 re-read with
OUTER3 held, stay named candidate rows).

Evidence: `docs/evidence/gpu/anv-b3pair4profile-20261028/`
(protocol.txt is the frozen pre-registration -- written once,
never rewritten; record.txt is this tick's record; the gate
captures are byte-identical to the s58 pins).

## 2026-10-28 -- session 60 (JUN-59): the fifth named rank-pair set (terminal halving-ladder step) compression-profile read (analysis; T10 (b) NOT-FIFTHPAIR-PROFILE-OUTER-WEIGHTED-CONSISTENT -- the outer-weighted profile does NOT consistently replicate at the terminal ladder rank pairs; the halving-ladder family is COMPLETE)

Session 59's queue third named candidate row ("any further named
profile pair (the halving ladder's fifth pair set, or the k=2
inner3 variant's T8 re-read with OUTER3 held -- its inner axis is
exactly this probe's IN4 axis -- stay named candidate rows)")
taken FIRST on the FIFTH NAMED RANK-PAIR SET of the SAME four
windows s36/s38/s39/s51 of the named-cell robust-scale level
campaign (ANALYSIS only): does the outer-weighted compression
profile of s55's T5 (a) hold at the TERMINAL step of the
pre-registered HALVING LADDER, where the outer pair reaches the
full range -- OUTER5 = (x_(1), x_(75)), halfway between s59's
(2,74) [k=36] and the full range (1,75) [k=37] landing on
k=36.5 and rounded half-away-from-zero to k=37 by the
ALREADY-FROZEN s58 tie-break rule applied UNCHANGED (no new rule
choice at this step; OUTER5 IS the degenerate full-range
endpoint, so D_out5 is the pooled-75 sample RANGE and the outer
walk is complete); INNER5 = (x_(37), x_(39)), the exact halving
between s59's (36,40) [k=2] and the center (38,38) [k=0] landing
on k=1 exactly (one halving step from the degenerate center),
frozen BEFORE any fifth-pair statistic existed (protocol freeze
stamp 2026-10-28T17:36:53Z). PRIMARY STATISTIC: the
difference-in-differences 2*P5_obs = 2*C_out5 - 2*C_in5 (D_out5
= x_(75) - x_(1), D_in5 = x_(39) - x_(37) per block of the SAME
pooled 75; 2*L = 6th+7th order statistics of the 12 block D
values); THREE contrasts (s36 vs s38, s36 vs s39, s36 vs s51),
ONE-SIDED each in the pre-registered direction P5 > 0
(outer-weighted compression at the fifth pair set -- direction
fixed by s55's published T5 (a) reading and the ladder framing,
QUOTE-ONLY; s56's T6 (b), s58's T8 (a) and s59's T9 (a) are KNOWN
and did NOT change the direction), joint T10 = the pre-registered
INTERSECTION-UNION rule (all three (a); NO multiplicity
correction); 20,000 trials, seed 2026102810, frozen probe order,
both axes on the same pseudo-blocks. NAMED, NOT HIDDEN: this
probe DOES test a FRESH pre-registered prediction -- the
fifth-pair levels were never published or computed anywhere (the
campaign's FOURTH fresh prediction after s56, s58 and s59).

THE FINDING (DERIVED; publication-s60.txt, analysis-s60.py run
twice byte-identical): T10 = (b) NOT-FIFTHPAIR-PROFILE-OUTER-
WEIGHTED-CONSISTENT (named: pair(s) not (a): s39, s51) -- only
s36-vs-s38 clears the frozen threshold: 2*P5_obs 83 (P5 +41.5;
OUT5 2*L 1060 -> 972 (2*C_out5 88), IN5 12 -> 7 (2*C_in5 5));
count 49 / 20,001; p 0.002500) (a) FIFTHPAIR-OUTER-WEIGHTED-
DIFFERENT, while s36-vs-s39 2*P5_obs 30 (P5 +15.0; OUT5 1060 ->
1031 (29), IN5 12 -> 13 (-1)); count 2,110 / 20,001; p 0.105545)
(b) NOT-DIFFERENT [NONZERO-NOT-SIGNIFICANT] and s36-vs-s51 55 (P5
+27.5; OUT5 1060 -> 1003 (57), IN5 12 -> 10 (2)); count 1,174 /
20,001; p 0.058747) (b) NOT-DIFFERENT [NONZERO-NOT-SIGNIFICANT].
ALL THREE point estimates sit in the pre-registered direction
(83/30/55 all positive) but only s38 clears 0.05 (s51 p 0.0587
marginal, the same flavor as s56's T6 (b) where s51 read p
0.0558).

NAMED, NOT HIDDEN: (b) at T10 FOLLOWING s56's T6 (b), s58's T8
(a) and s59's T9 (a) is CONSISTENT WITH the outer-weighted
profile breaking down at the ladder's terminal step -- the
outer5 axis IS the sample range, driven by the single most
extreme sample of each pooled 75 (the OUT5 level carries the
whole signal 1060 -> 972/1031/1003 while the inner5 level is
flat at its noise floor 2*L 12/7/13/10; P5 ~= C_out5 at this
step) and the s39/s51 contrasts lost power against it (p
0.1055/0.0587); (b) is equally CONSISTENT WITH a rank-pair-
dependent outer-weighted compression that holds at ladder steps
1/3/4 and attenuates at steps 2/5; a fifth-pair shift below the
noise floor at s39/s51 cannot be excluded (POWER LOSS reading);
NEITHER reading names a mechanism (thermal/scheduling/memory/
driver state all UNMEASURED) and NOT whether any movement is
physical or estimator structure; (b) does NOT overturn s55's T5
(a), s58's T8 (a) or s59's T9 (a) (different rank pairs,
SEPARATE named families); the ladder letter sequence now reads
step1 (a) / step2 (b) / step3 (a) / step4 (a) / step5 (b) and
the HALVING-LADDER FAMILY IS COMPLETE AT THIS PROBE (both axes
sit at their degenerate endpoints' immediate neighborhood; no
sixth step names a new pair) -- two of five steps dissent and
the rank-pair question is NOT settled by the family; this is an
ELEVENTH axis on the SAME window data and the campaign's FOURTH
fresh pre-registered prediction (the fifth-pair levels had no
priors); LOW POWER, n=2 windows per contrast, ONE host, ONE UTC
day; threshold-artifact-vs-representation and
physical-vs-estimator-structure STAY UNRESOLVED. Integrity
(DERIVED): 4/4 windows clean (78 runs parsed each, VERIFY
mismatch total 0); C1 (a) at ALL FOUR windows (c2 FLOOR; c8
0.01%/0.53%/0.26%/0.08% delta vs committed 32,915); all four
windows' block-min vectors and anchor rows reproduce their
published/quote-only priors EXACTLY. BAR: NO ledger line and NO
day-slot consumption (no runs this session; the 2026-10-28 slot
is s31's); frozen evaluator --self-test 38/0, ledger eval twice
byte-identical -> VERDICT PENDING 1/4 unchanged; next executable
day slot 2026-10-29. RULE 4 unchanged: NOTHING MOVES --
accelerator-targets defaults remain provisional (:measured?
false); NO vendor optimization exists for Intel. Gates (real
runs; every capture byte-identical to its pinned s59 artifact):
gpu_regime_classify.py --self-test 2649/0; scoped GPU gate GREEN
123/12162/0/0 run 1 AND run 2 (scratch runner
scratch/scoped-gpu-gate.cljk -- eight GPU-owned namespaces,
created/run/deleted, never committed); FULL run-tests.cljk LIVE:
exit 1, RED AT BASE kotoba.form (ADR-0362, outside this diff --
touches NO .cljk namespace) -- NO green full suite claimed;
derivation-census-s60.txt: independent second parser
(split-based, no re module, no numpy; pure-Python sorted() order
statistics from ONE shared sort per pooled 75 --
sorted(pooled75)[74] - sorted(pooled75)[0] and
sorted(pooled75)[38] - sorted(pooled75)[36]; independent
pure-Python shuffle loop under the frozen RNG contract
random.Random(2026102810) consumed in the frozen probe order,
BOTH axes on the SAME pseudo-blocks) re-deriving every published
integer, count, p value and letter -- 159 rows / 0 mismatched,
run twice byte-identical; find docs/evidence/gpu -name '*.sh' ->
0.

Named candidate rows for later sessions (the ladder row is
RETIRED, complete): (first, STARTED) the fifth-window
measurement + T7 read in the 2026-10-29 UTC slot (NEW hardware);
then the s38 hi (sum,256,S=32) wander replication (NEW hardware
-- W5's hi runs); then the k=2 inner3 variant's T8 re-read with
OUTER3 held (its inner axis is the retired step-4 IN4 axis) and
any non-ladder rank pairs (both ANALYSIS).

Evidence: `docs/evidence/gpu/anv-b3pair5profile-20261028/`
(protocol.txt is the frozen pre-registration -- written once,
never rewritten; record.txt is this tick's record; the gate
captures are byte-identical to the s59 pins).

## 2026-10-28 -- session 61 (JUN-59): the k=2 inner3 rounding-variant T8 re-read with OUTER3 held (analysis; T11 (a) THIRDPAIR-K2VARIANT-PROFILE-OUTER-WEIGHTED-CONSISTENT -- the s58 T8 letter is ROBUST to the k=2/k=3 rounding tie-break at the third inner pair; a RE-READ, NOT a fresh pre-registered prediction)

Session 60's queue third named candidate row ("the k=2 inner3
variant's T8 re-read with OUTER3 held (its inner axis is the
retired step-4 IN4 axis) and any non-ladder rank pairs (both
ANALYSIS)") taken FIRST on the K=2 INNER3 ROUNDING-VARIANT RE-READ
of s58's third-pair profile probe over the SAME four windows
s36/s38/s39/s51 of the named-cell robust-scale level campaign
(ANALYSIS only): does s58's joint T8 (a) letter survive when the
third inner pair sits at the s58-named ALTERNATIVE rounding k=2
(x_(36), x_(40)) instead of the frozen tie-break k=3 (x_(35),
x_(41)) -- OUTER3 HELD at (x_(3), x_(73)) (the k=2 pair IS
exactly the retired step-4 INNER4 axis named at s59; the s58
freeze named (35,41)/(36,40) as the two candidates and broke the
k=2.5 tie toward k=3; this probe reads the OTHER rounding of that
SAME tie -- no new rule choice, no new rank pair). NAMED, NOT
HIDDEN -- THE HONESTY FRAMING: unlike s56/s58/s59/s60 this probe
is NOT a fresh pre-registered prediction -- BOTH axes' per-window
levels are published priors (publication-s58 D1 OUTER3
902/721/811/776; publication-s59 D1 INNER4 19/21/24/20, QUOTE-
ONLY), so every observed statistic is a deterministic
recombination of published numbers and ONLY the permutation p
values are new (protocol freeze stamp 2026-10-28T18:08:07Z fixed
the null, thresholds and joint rule BEFORE those p values
existed). PRIMARY STATISTIC: the difference-in-differences
2*P3K2_obs = 2*C_out3 - 2*C_in3K2 (D_out3 = x_(73) - x_(3),
D_in3K2 = x_(40) - x_(36) per block of the SAME pooled 75; 2*L =
6th+7th order statistics of the 12 block D values); THREE
contrasts (s36 vs s38, s36 vs s39, s36 vs s51), ONE-SIDED each in
the pre-registered direction P3K2 > 0 (fixed by s55's published
T5 (a) reading and the s58 T8 framing, QUOTE-ONLY; its truth
value is already determined by the published components), joint
T11 = the pre-registered INTERSECTION-UNION rule (all three (a);
NO multiplicity correction); 20,000 trials, seed 2026102811,
frozen probe order, both axes on the same pseudo-blocks.

THE FINDING (DERIVED; publication-s61.txt, analysis-s61.py run
twice byte-identical): T11 = (a) THIRDPAIR-K2VARIANT-PROFILE-
OUTER-WEIGHTED-CONSISTENT -- ALL THREE contrasts (a):
s36-vs-s38 2*P3K2_obs 183 (P3K2 +91.5; OUT3 2*L 902 -> 721
(2*C_out3 181), IN3K2 19 -> 21 (2*C_in3K2 -2)); count 48 /
20,001; p 0.002450) (a) THIRDPAIR-K2VARIANT-OUTER-WEIGHTED-
DIFFERENT, s36-vs-s39 96 (P3K2 +48.0; OUT3 902 -> 811 (91),
IN3K2 19 -> 24 (-5)); count 697 / 20,001; p 0.034898) (a),
s36-vs-s51 127 (P3K2 +63.5; OUT3 902 -> 776 (126), IN3K2 19 ->
20 (-1)); count 291 / 20,001; p 0.014599) (a) -- all three clear
the frozen 0.05 threshold in the pre-registered direction. THE
RE-READ ANSWER: T11 (a) AGREES with s58's published T8 (a)
(QUOTE-ONLY comparison) -- the T8 joint letter is ROBUST to the
k=2/k=3 rounding tie-break at the third inner pair (s58 k=3
reading: 2*P3_obs 181/92/119, p 0.002900/0.038548/0.020499; k=2
variant: 183/96/127, p 0.002450/0.034898/0.014599 -- same letter
at every contrast).

NAMED, NOT HIDDEN: (a) at T11 is CONSISTENT WITH the s58 T8
letter being robust to the third-inner-pair rounding choice (the
k=2 pair spans 4 ranks vs the k=3 pair's 6 and sits at a
different noise floor 2*L 19/21/24/20 vs 36/36/37/29, yet both
readings read (a) at all three contrasts) and with the outer3
axis carrying the whole signal at both roundings (2*C_in3K2 is
-2/-5/-1, so P3K2 ~= C_out3); NEITHER reading names a mechanism
(thermal/scheduling/memory/driver state all UNMEASURED) and NOT
physical-vs-estimator-structure; because the observed levels are
published-prior recombinations the letters rest on the p values
alone and this probe settles NOTHING beyond rounding
sensitivity; it does NOT overturn s56's T6 (b), s58's T8 (a),
s59's T9 (a) or s60's T10 (b) and does NOT resolve the ladder's
(a)/(b) split at steps 2/5; TWELFTH axis on the same window data
and the campaign's FIRST probe that is NOT a fresh pre-registered
prediction; LOW POWER n=2 windows per contrast, the three
contrasts share the s36 window and are dependent, ONE host, ONE
UTC day; 20,000 trials (NOT the s35-frozen 100,000 -- cost, same
named deviation as sessions 40-60); threshold-artifact-vs-
representation STAYS UNRESOLVED. Integrity (DERIVED): 4/4
windows clean (78 runs parsed each, VERIFY mismatch total 0);
C1 (a) at ALL FOUR windows (c2 FLOOR; c8 0.01%/0.53%/0.26%/0.08%
delta vs committed 32,915); all four windows' block-min vectors
and anchor rows reproduce their published/quote-only priors
EXACTLY; D1 prior check: the derived OUT3 levels reproduce
publication-s58 D1 EXACTLY and the IN3K2 levels reproduce
publication-s59 D1 EXACTLY at all four windows. BAR: NO ledger
line and NO day-slot consumption (no runs this session; the
2026-10-28 slot is s31's); frozen evaluator --self-test 38/0,
ledger eval twice byte-identical -> VERDICT PENDING 1/4
unchanged; next executable day slot 2026-10-29. RULE 4 unchanged:
NOTHING MOVES -- accelerator-targets defaults remain provisional
(:measured? false); NO vendor optimization exists for Intel.
Gates (real runs; every capture byte-identical to its pinned s60
artifact): gpu_regime_classify.py --self-test 2649/0; scoped GPU
gate GREEN 123/12162/0/0 run 1 AND run 2 (scratch runner
scratch/scoped-gpu-gate.cljk -- eight GPU-owned namespaces,
created/run/deleted, never committed); FULL run-tests.cljk LIVE:
exit 1, RED AT BASE kotoba.form (ADR-0362, outside this diff --
touches NO .cljk namespace) -- NO green full suite claimed;
derivation-census-s61.txt: independent second parser (split-
based, no re module, no numpy; pure-Python sorted() order
statistics from ONE shared sort per pooled 75 --
sorted(pooled75)[72] - sorted(pooled75)[2] and
sorted(pooled75)[39] - sorted(pooled75)[35]; independent
pure-Python shuffle loop under the frozen RNG contract
random.Random(2026102811) consumed in the frozen probe order,
BOTH axes on the SAME pseudo-blocks) re-deriving every published
integer, count, p value and letter -- 167 rows / 0 mismatched,
run twice byte-identical; find docs/evidence/gpu -name '*.sh' ->
0. CHAIN: lands on the ONE open chain branch
bot/amu-gpu-chain-20261028-3 (chain PR #1643, OPEN), commit +
push only. BLOCKER-FIRST: 0 open kotoba-lang/amu PRs with a
hermes/ head, checked immediately before this push.

Named candidate rows for later sessions: (first, STARTED) the
fifth-window measurement + T7 read in the 2026-10-29 UTC slot
(NEW hardware; the slot opens 2026-10-29T00:00:00Z, ~5h47m after
this tick -- NAMED, not skipped silently); then the s38 hi
(sum,256,S=32) wander replication (NEW hardware -- W5's hi
runs); then any non-ladder rank pairs (ANALYSIS; a NEW named
selection rule is required -- the halving ladder is retired and
the k=2 inner3 variant re-read is DONE at this probe).

Evidence: `docs/evidence/gpu/anv-b3pair3k2reread-20261028/`
(protocol.txt is the frozen pre-registration -- written once,
never rewritten; record.txt is this tick's record; the gate
captures are byte-identical to the s60 pins).

## 2026-10-28 -- session 62 (JUN-59): the non-ladder asymmetric (hinge-to-opposite-extreme, HX) rank-pair spread-compression probe (analysis; T12 (b) NOT-HXPAIR-ASYMMETRIC-SPREAD-COMPRESSION-CONSISTENT -- the s36 -> post-shift compression does NOT consistently replicate under the IUT at the first named ASYMMETRIC rank pairs, though all six point estimates point the same way; a FRESH pre-registered prediction under a NEW named selection rule)

Session 61's queue third named candidate row ("any non-ladder
rank pairs (ANALYSIS; a NEW named selection rule is required --
the halving ladder is retired and the k=2 inner3 variant re-read
is DONE at this probe)") taken on the FIRST non-ladder rank-pair
family under the NEW NAMED SELECTION RULE (this row's design
content, frozen in protocol.txt section 0 BEFORE any statistic
existed, freeze stamp 2026-10-28T18:40:33Z): HINGE-TO-OPPOSITE-
EXTREME (HX) -- cross each s47-frozen exclusive-hinge rank with
the OPPOSITE sample extreme rank (the s60-named ladder
endpoint): SET-L = (x_(1), x_(57)), SET-R = (x_(19), x_(75)).
The rule is RANK-VOCABULARY-CLOSED (only ranks 1/19/57/75, every
one already NAMED by a prior frozen construction), the pair sets
are ASYMMETRIC about x_(38) (rank midpoints 29 and 47 -- the
campaign's FIRST named pairs that are), mirror images of each
other, 56 ranks each, NO data-dependent choice. NAMED, NOT
HIDDEN: (x_(1), x_(75)) is the retired outer5 axis and
(x_(19), x_(57)) is the s47 IQR axis -- NOT in this family; the
vocabulary's remaining two pairs (x_(1), x_(19)) and
(x_(57), x_(75)) (the HINGE-SIDE pair sets) stay named candidate
rows. NAMED, NOT HIDDEN -- THE HONESTY FRAMING: unlike s61 (a
re-read) this probe IS a fresh pre-registered prediction -- the
HX per-window levels were never published or computed anywhere
(the campaign's FIFTH fresh prediction after s56, s58, s59,
s60). PRIMARY STATISTIC: per axis per contrast 2*C_obs =
2*L_s36 - 2*L_w (D_L = x_(57) - x_(1), D_R = x_(75) - x_(19)
per block of the SAME pooled 75; 2*L = 6th+7th order statistics
of the 12 block D values); THREE contrasts (s36 vs s38, s36 vs
s39, s36 vs s51), ONE-SIDED each in the pre-registered direction
C > 0 (asymmetric-pair spread compression; fixed by the
published wide-span SYMMETRIC pair levels dropping s36 ->
s38/s39/s51 at every ladder step, publication-s54/56/58/59/60
D1, QUOTE-ONLY, and NOT by any asymmetric-pair statistic), joint
T12 = the pre-registered INTERSECTION-UNION rule over ALL SIX
axis x contrast letters (NO multiplicity correction); 20,000
trials, seed 2026102812, frozen probe order, both axes on the
same pseudo-blocks.

THE FINDING (DERIVED; publication-s62.txt, analysis-s62.py run
twice byte-identical): T12 = (b) NOT-HXPAIR-ASYMMETRIC-SPREAD-
COMPRESSION-CONSISTENT (named: letter(s) not (a): HXL-s39,
HXR-s39, HXR-s51) -- ALL SIX point estimates sit in the pre-
registered direction but only THREE clear the frozen 0.05
threshold: s36-vs-s38 HXL 2*C_obs 43 (C_obs +21.5; HXL 2*L
864 -> 821); count 697/20,001; p 0.034898) (a), HXR 66 (+33.0;
HXR 2*L 471 -> 405); count 518/20,001; p 0.025949) (a);
s36-vs-s39 HXL 32 (+16.0; 864 -> 832); count 1,584/20,001; p
0.079246 (b) NOT-DIFFERENT [NONZERO-NOT-SIGNIFICANT], HXR 30
(+15.0; 471 -> 441); count 3,254/20,001; p 0.162742 (b);
s36-vs-s51 HXL 60 (+30.0; 864 -> 804); count 205/20,001; p
0.010299 (a), HXR 6 (+3.0; 471 -> 465); count 9,024/20,001; p
0.451227 (b). NAMED, NOT HIDDEN: (b) at T12 is CONSISTENT WITH
the s36 -> post-shift spread compression being symmetry-
dependent (the first named probe where the compression fails the
IUT at asymmetric pairs) AND EQUALLY CONSISTENT WITH a power
loss at these pair sets (the HX pairs span 56 ranks vs the
ladder outer pairs' 70..74; the s39/s51 contrasts again lose
power, the same flavor as s56's T6 (b) and s60's T10 (b); all
six point estimates positive, HXR-s51 nearly flat 2*C_obs 6);
NAMED, NOT HIDDEN: the two mirror pair sets sit at very
different levels (HXL 2*L 864/821/832/804 vs HXR
471/405/441/465 -- mirror rank pairs do NOT produce mirror-
symmetric spreads); NEITHER reading names a mechanism
(thermal/scheduling/memory/driver state all UNMEASURED) and NOT
physical-vs-estimator-structure; (b) does NOT overturn s55's T5
(a), s58's T8 (a), s59's T9 (a) or s61's T11 (a) (different rank
pairs, SEPARATE named families) and does NOT resolve the
ladder's (a)/(b) split at steps 2/5; THIRTEENTH and FOURTEENTH
axes on the same window data; the campaign's FIFTH fresh pre-
registered prediction; LOW POWER n=2 windows per contrast, the
three contrasts share the s36 window and are dependent, ONE
host, ONE UTC day; 20,000 trials (NOT the s35-frozen 100,000 --
cost, same named deviation as sessions 40-61); threshold-
artifact-vs-representation STAYS UNRESOLVED. Integrity
(DERIVED): 4/4 windows clean (78 runs parsed each, VERIFY
mismatch total 0); C1 (a) at ALL FOUR windows (c2 FLOOR; c8
0.01%/0.53%/0.26%/0.08% delta vs committed 32,915); all four
windows' block-min vectors and anchor rows reproduce their
published/quote-only priors EXACTLY; NAMED, NOT HIDDEN: NO D1
prior-reproduction check at this probe (fresh prediction, no
published prior to re-derive); the independent derivation census
re-derives every published number from the logs instead. BAR:
NO ledger line and NO day-slot consumption (no runs this
session; the 2026-10-28 slot is s31's); frozen evaluator
--self-test 38/0, ledger eval twice byte-identical -> VERDICT
PENDING 1/4 unchanged; next executable day slot 2026-10-29. RULE
4 unchanged: NOTHING MOVES -- accelerator-targets defaults
remain provisional (:measured? false); NO vendor optimization
exists for Intel. Gates (real runs; every capture byte-identical
to its pinned s60 artifact): gpu_regime_classify.py --self-test
2649/0; scoped GPU gate GREEN 123/12162/0/0 run 1 AND run 2
(scratch runner scratch/scoped-gpu-gate.cljk -- eight
GPU-owned namespaces, created/run/deleted, never committed);
FULL run-tests.cljk LIVE: exit 1, RED AT BASE kotoba.form
(ADR-0362, outside this diff -- touches NO .cljk namespace) --
NO green full suite claimed; derivation-census-s62.txt:
independent second parser (split-based, no re module, no numpy;
pure-Python sorted() order statistics from ONE shared sort per
pooled 75 -- sorted(pooled75)[56] - sorted(pooled75)[0] and
sorted(pooled75)[74] - sorted(pooled75)[18]; independent
pure-Python shuffle loop under the frozen RNG contract
random.Random(2026102812) consumed in the frozen probe order,
BOTH axes on the SAME pseudo-blocks) re-deriving every published
integer, count, p value and letter -- 161 rows / 0 mismatched,
run twice byte-identical; find docs/evidence/gpu -name '*.sh'
-> 0. CHAIN: lands on the ONE open chain branch
bot/amu-gpu-chain-20261028-3 (chain PR #1643, OPEN), commit +
push only. BLOCKER-FIRST: 0 open kotoba-lang/amu PRs with a
hermes/ head, checked immediately before this push.

Named candidate rows for later sessions: (first, STARTED) the
fifth-window measurement + T7 read in the 2026-10-29 UTC slot
(NEW hardware; the slot opens 2026-10-29T00:00:00Z, ~5h19m after
this tick -- NAMED, not skipped silently); then the s38 hi
(sum,256,S=32) wander replication (NEW hardware -- W5's hi
runs); then the HINGE-SIDE pair sets (x_(1), x_(19)) and
(x_(57), x_(75)) (ANALYSIS; the remaining two pairs of the HX
rule's four-rank vocabulary -- the HX family itself is COMPLETE
and RETIRED at this probe).

Evidence: `docs/evidence/gpu/anv-b3asymhinge-20261028/`
(protocol.txt is the frozen pre-registration -- written once,
never rewritten; record.txt is this tick's record; the gate
captures are byte-identical to the s60 pins).

## 2026-10-28 -- session 63 (JUN-59): the hinge-side (HS) rank-pair spread-compression probe (analysis; T13 (b) NOT-HINGESIDE-PAIR-SPREAD-COMPRESSION-CONSISTENT -- no contrast clears the threshold at the tail-side pairs and two of six estimates point the OPPOSITE way; a FRESH pre-registered prediction; the four-rank vocabulary is EXHAUSTED and the rank-pair program over it RETIRES)

Session 62's queue third named candidate row (the HINGE-SIDE
pair sets (x_(1), x_(19)) and (x_(57), x_(75)), ANALYSIS -- the
remaining two pairs of the HX rule's four-rank vocabulary; the
two rows ahead of it need NEW hardware and the W5 measurement is
day-slot-gated to the 2026-10-29 UTC slot, which opens at
2026-10-29T00:00:00Z, ~4h51m after this tick -- NAMED, not
skipped silently) taken on the LAST unnamed pairs of the
vocabulary (frozen in protocol.txt section 0 BEFORE any
statistic existed, freeze stamp 2026-10-28T19:09:28Z): SET-L =
(x_(1), x_(19)) (sample min to the lower exclusive hinge Q1),
SET-R = (x_(57), x_(75)) (the upper exclusive hinge Q3 to
sample max) -- RANK-VOCABULARY-CLOSED, ASYMMETRIC about x_(38)
(rank midpoints 10 and 66), mirror pair sets, 18 ranks each,
NO data-dependent choice. NAMED, NOT HIDDEN: with this probe
the four-rank vocabulary is EXHAUSTED (all six pairs named) and
the rank-pair program over it is COMPLETE and RETIRES here.
NAMED, NOT HIDDEN -- THE HONESTY FRAMING: this probe IS a fresh
pre-registered prediction -- the HS per-window levels were never
published or computed anywhere (the campaign's SIXTH fresh
prediction after s56, s58, s59, s60, s62); the narrow-span
caveat (HS pairs span 18 ranks like the inner family's 2..20,
whose levels scattered near their noise floors) was registered
in protocol section 0 BEFORE any HS statistic existed. PRIMARY
STATISTIC: per axis per contrast 2*C_obs = 2*L_s36 - 2*L_w
(D_HSL = x_(19) - x_(1), D_HSR = x_(75) - x_(57) per block of
the SAME pooled 75; 2*L = 6th+7th order statistics of the 12
block D values); THREE contrasts (s36 vs s38, s36 vs s39, s36
vs s51), ONE-SIDED each in the pre-registered direction C > 0
(hinge-side-pair spread compression; fixed by the published
wide-span SYMMETRIC pair levels dropping s36 -> s38/s39/s51 at
every ladder step, publication-s54/56/58/59/60 D1, QUOTE-ONLY,
and NOT by any hinge-side statistic), joint T13 = the pre-
registered INTERSECTION-UNION rule over ALL SIX axis x contrast
letters (NO multiplicity correction); 20,000 trials, seed
2026102813, frozen probe order, both axes on the same
pseudo-blocks.

THE FINDING (DERIVED; publication-s63.txt, analysis-s63.py run
twice byte-identical): T13 = (b) NOT-HINGESIDE-PAIR-SPREAD-
COMPRESSION-CONSISTENT (named: letter(s) not (a): ALL SIX) --
NO contrast clears the frozen 0.05 threshold and TWO point
estimates sit in the OPPOSITE direction: s36-vs-s38 HSL 2*C_obs
4 (C_obs +2.0; HSL 2*L 583 -> 579); count 9,121/20,001; p
0.456077 (b), HSR 26 (+13.0; HSR 2*L 195 -> 169); count
2,748/20,001; p 0.137443 (b); s36-vs-s39 HSL 15 (+7.5; 583 ->
568); count 5,629/20,001; p 0.281486 (b), HSR -1 (-0.5; 195 ->
196); count 10,519/20,001; p 0.525974 (b) [OPPOSITE-DIRECTION];
s36-vs-s51 HSL 29 (+14.5; 583 -> 554); count 3,197/20,001; p
0.159892 (b), HSR -22 (-11.0; 195 -> 217); count 14,767/20,001;
p 0.738363 (b) [OPPOSITE-DIRECTION]. NAMED, NOT HIDDEN: (b) --
the campaign's THIRD joint all-(b) read after s52's T2 and s53's
T3, and the FIRST named probe with MORE THAN ONE opposite-
direction point estimate -- is CONSISTENT WITH the compression
NOT reaching the narrow tail-side pairs (HSL drifts down
monotonically 583 -> 579/568/554 but nowhere near the
threshold; HSR scatters and GROWS at s51, 195 -> 217) AND
EQUALLY CONSISTENT WITH power loss at these narrow pair sets
(the pre-registered section-0 caveat); NEITHER reading names a
mechanism (thermal/scheduling/memory/driver state all
UNMEASURED) and NOT physical-vs-estimator-structure; (b) does
NOT overturn s55's T5 (a), s58's T8 (a), s59's T9 (a) or s61's
T11 (a) (different rank pairs, SEPARATE named families) and
does NOT resolve the ladder's (a)/(b) split at steps 2/5 or
s62's T12 (b); the mirror pair sets sit at very different
levels AGAIN (HSL 583/579/568/554 vs HSR 195/169/196/217 --
third consecutive named probe where mirror rank pairs do NOT
produce mirror-symmetric spreads); FIFTEENTH and SIXTEENTH axes
on the same window data; the campaign's SIXTH fresh pre-
registered prediction; LOW POWER n=2 windows per contrast, the
three contrasts share the s36 window and are dependent, ONE
host, ONE UTC day; 20,000 trials (NOT the s35-frozen 100,000 --
cost, same named deviation as sessions 40-62); threshold-
artifact-vs-representation STAYS UNRESOLVED. Integrity
(DERIVED): 4/4 windows clean (78 runs parsed each, VERIFY
mismatch total 0); C1 (a) at ALL FOUR windows (c2 FLOOR; c8
0.01%/0.53%/0.26%/0.08% delta vs committed 32,915); all four
windows' block-min vectors and anchor rows reproduce their
published/quote-only priors EXACTLY; NAMED, NOT HIDDEN: NO D1
prior-reproduction check at this probe (fresh prediction, no
published prior to re-derive); the independent derivation census
re-derives every published number from the logs instead. BAR:
NO ledger line and NO day-slot consumption (no runs this
session; the 2026-10-28 slot is s31's); frozen evaluator
--self-test 38/0, ledger eval twice byte-identical -> VERDICT
PENDING 1/4 unchanged; next executable day slot 2026-10-29. RULE
4 unchanged: NOTHING MOVES -- accelerator-targets defaults
remain provisional (:measured? false); NO vendor optimization
exists for Intel. Gates (real runs; every capture byte-identical
to its pinned s62 artifact): gpu_regime_classify.py --self-test
2649/0; scoped GPU gate GREEN 123/12162/0/0 run 1 AND run 2
(scratch runner scratch/scoped-gpu-gate.cljk -- eight
GPU-owned namespaces, created/run/deleted, never committed);
FULL run-tests.cljk LIVE: exit 1, RED AT BASE kotoba.form
(ADR-0362, outside this diff -- touches NO .cljk namespace) --
NO green full suite claimed; derivation-census-s63.txt:
independent second parser (split-based, no re module, no numpy;
pure-Python sorted() order statistics from ONE shared sort per
pooled 75 -- sorted(pooled75)[18] - sorted(pooled75)[0] and
sorted(pooled75)[74] - sorted(pooled75)[56]; independent
pure-Python shuffle loop under the frozen RNG contract
random.Random(2026102813) consumed in the frozen probe order,
BOTH axes on the SAME pseudo-blocks) re-deriving every published
integer, count, p value and letter -- 161 rows / 0 mismatched,
run twice byte-identical; find docs/evidence/gpu -name '*.sh'
-> 0. CHAIN: lands on the ONE open chain branch
bot/amu-gpu-chain-20261028-3 (chain PR #1643, OPEN), commit +
push only. BLOCKER-FIRST: 0 open kotoba-lang/amu PRs with a
hermes/ head, checked immediately before this push.

Named candidate rows for later sessions: (first, STARTED) the
fifth-window measurement + T7 read in the 2026-10-29 UTC slot
(NEW hardware; the slot opens 2026-10-29T00:00:00Z, ~4h51m after
this tick -- NAMED, not skipped silently); then the s38 hi
(sum,256,S=32) wander replication (NEW hardware -- W5's hi
runs). NAMED, NOT HIDDEN: with this probe the four-rank
vocabulary is EXHAUSTED and the rank-pair program over it is
COMPLETE and RETIRED -- any further rank-pair probe requires a
NEW named vocabulary/selection rule (none exists yet -- naming
one is future design work).

Evidence: `docs/evidence/gpu/anv-b3hingeside-20261028/`
(protocol.txt is the frozen pre-registration -- written once,
never rewritten; record.txt is this tick's record; the gate
captures are byte-identical to the s62 pins).

## 2026-10-28 (session 64, JUN-59) -- the s38 hi
(sum,256,S=32) wander replication PRE-REGISTRATION FREEZE
(DESIGN slice; STARTED, NOT FINISHED)

Session 64 took the s57-frozen W5 carry-forward's queue SECOND
named candidate row to its design half: the s38 hi
(sum,256,S=32) per-cell wander replication at the W5 window's
hi arm is now PRE-REGISTERED in
`docs/evidence/gpu/anv-b3w5hiwander-20261029/protocol.txt`
(freeze stamp 2026-10-28T19:49:29Z), frozen BEFORE any
fifth-window run exists -- no committed file contains any W5
quantity. This is the row named in the s57 carry-forward as
"the only route from one uncorrected (b) to a letter that
survives multiplicity": the campaign's one uncorrected (b) is
the s45 per-cell wander max-T probe letter EXCEEDS NULL at
(s38, hi) (family-wise p 0.047398; the max cell
(sum,256,S=32), marginal p 0.035348 -- uncorrected across the
six s45 probes and three windows, cell identity
data-dependent). The frozen route: ONE named cell
((sum,256,S=32), the s45 max cell fixed by PUBLISHED content
alone), ONE named (window, arm) ((W5, hi)), ONE named
upper-tail test at 0.05 on NEW data -- T14, the named cell's
within-window block-level wander W_obs (range of the 12 block
pooled medians, exact 38th order statistics of the pooled 75;
INTEGER) against the within-window run-repartition null of W5's
36 hi runs (20,000 trials, ONE random.Random(2026102814) --
distinct from T7's 20261029 -- one shuffle per trial).
Letters: (a) WANDER-EXCESS-REPLICATED (p <= 0.05) / (b)
NOT-REPLICATED (named sub-cases) / (c) NOT EVALUABLE; ONE
letter source, no multiplicity correction needed or applied.
NAMED, NOT HIDDEN: the s45-letter-construction max-T probe at
(W5, hi) runs alongside as D2 DESCRIPTIVE ONLY and NEVER
carries a letter under this freeze (running it as a letter
source would reintroduce the within-probe cell family the
pre-registration exists to remove). The row's ANALYSIS half is
day-slot-gated and was NOT run this tick: it needs W5's hi runs,
and W5 is the window whose 78 fresh processes run in the first
measurement session at or after 2026-10-29T00:00:00Z -- this
tick ran ~4h10m before that slot opens (NAMED, not skipped
silently; the queue's first row -- the W5 measurement + T7 read
-- is gated the same way and its freeze was done at s57; the
s63 probe EXHAUSTED the four-rank vocabulary and RETIRED the
rank-pair program, so this row's design half was the one row
available before the slot, and freezing BEFORE any W5 quantity
exists is strictly stronger than freezing later). NAMED, NOT
HIDDEN: STILL LOW POWER (n=12 blocks, ONE window, ONE host,
ONE cell; the wander is a tail-to-tail RANGE statistic, not a
scale estimate; a (b) is NOT evidence of no per-cell
structure); (a) names NO mechanism and NOT
physical-vs-estimator-structure; threshold-artifact-vs-
representation STAYS UNRESOLVED. Gates (real runs this tick):
classify self-test 2649/0 (byte-identical to the s63 pin);
scoped GPU gate GREEN 123/12162/0/0 twice (byte-identical to
the s63 pin and each other); full run-tests.cljk exit 1 RED AT
BASE kotoba.form (ADR-0362, outside this diff -- touches NO
.cljk namespace), captures byte-identical to the s63 pins -- NO
green full suite claimed; settle-bar evaluator 38/0 + ledger
eval twice byte-identical -> VERDICT PENDING 1/4 unchanged (no
runs, no ledger line, no day slot; next executable slot
2026-10-29); no derivation census (a freeze-only tick computes
no statistics -- named, not omitted); find docs/evidence/gpu
-name '*.sh' -> 0. Rule 4 binds: nothing moves;
accelerator-targets defaults remain provisional
(`:measured? false`); no vendor optimization exists for Intel.

Named rows for later sessions: (first, STARTED) the
fifth-window measurement + T7 read in the 2026-10-29 UTC slot
(NEW hardware; the slot opens 2026-10-29T00:00:00Z, ~4h10m
after this tick -- NAMED, not skipped silently); (second, now
STARTED at this freeze) the s38 hi (sum,256,S=32) wander
replication ANALYSIS half (needs W5's hi runs); then the
quantile-pair level axes at W5 and the second-pair profile axis
at W5 (each its own freeze; need W5 data); any further named
profile pair -- which requires a NEW named rank-pair vocabulary
or selection rule (none exists yet -- naming one is future
design work).

Evidence: `docs/evidence/gpu/anv-b3w5hiwander-20261029/`
(protocol.txt is the frozen pre-registration -- written once,
never rewritten; freeze-record-s64.txt is this tick's record --
the analysis session owns record.txt there; the gate captures
are byte-identical to the s63 pins). The analysis half of the
row is UNMEASURED until the W5 runs exist.

## 2026-10-28 (session 65, JUN-59) -- the quantile-pair level
axes (the s53/s54 named pairs) at W5 PRE-REGISTRATION FREEZE
(DESIGN slice; STARTED, NOT FINISHED)

Session 65 took the s57-frozen W5 carry-forward's remaining
analysis-row queue to its first row's design half: the W5 reads
of the two OTHER named quantile-pair level axes -- INNER
(28,48) (the s53-named pair) and OUTER (9,67) (the s54-named
pair) -- of the named cell (max,128,S=default) are now
PRE-REGISTERED in
`docs/evidence/gpu/anv-b3w5qpairevel-20261029/protocol.txt`
(freeze stamp 2026-10-28T20:10:55Z), frozen BEFORE any
fifth-window run exists -- no committed file contains any W5
quantity. The frozen row: T15, the two-axis read at the named
window pair (s36, W5) -- per axis the directional contrast
2*C_obs = 2*L_s36 - 2*L_W5 of the block-level quantile-pair
spread level (block = 3 consecutive tw runs; 2*L = 6th+7th
order statistics of the 12 block D values, INTEGER half-tick
units) against the two-window run-repartition null of the 72 tw
runs of s36 and W5 (20,000 trials per probe, ONE
random.Random(2026102815) -- distinct from T7's 20261029 and
T14's 2026102814 -- frozen probe order inner then outer), the
pre-registered direction C_obs > 0 on BOTH axes fixed by
published MAD/IQR scale letters and the s54 outer drops
(QUOTE-ONLY) and NOT by any W5 statistic; letters per axis
(a) LEVEL-REPLICATED-CONTINUED / (b) NOT-REPLICATED (named
sub-cases) / (c) NOT EVALUABLE; joint T15 = the pre-registered
INTERSECTION-UNION rule (BOTH axes (a); NO multiplicity
correction). NAMED, NOT HIDDEN: the two axes' published priors
DIFFER in kind -- the OUTER level dropped at every post-shift
window (496/429/437/446, s54 T4 (a)) while the INNER level
SCATTERED (118/102/128/113, s53 T3 (b), one contrast
opposite-direction) -- so the joint (a) is demanding on the
inner axis, and a joint (b) driven by the inner axis is
CONSISTENT WITH the s53-era scatter near the inner pair's noise
floor AND EQUALLY CONSISTENT WITH genuine non-replication at
the inner pair (the per-axis letters are named). The row's
ANALYSIS half is day-slot-gated and was NOT run this tick: it
needs W5's tw runs, and W5 is the window whose 78 fresh
processes run in the first measurement session at or after
2026-10-29T00:00:00Z -- this tick ran ~3h50m before that slot
opens (NAMED, not skipped silently; the queue's first row -- the
W5 measurement + T7 read -- is gated the same way and its freeze
was done at s57; the s38-hi wander replication is frozen at
s64). NAMED, NOT HIDDEN: STILL LOW POWER (n=2 windows, 12
blocks each, ONE host, ONE named cell); (a) names NO mechanism
and NOT physical-vs-estimator-structure;
threshold-artifact-vs-representation STAYS UNRESOLVED. Gates
(real runs this tick): classify self-test 2649/0 (byte-identical
to the s64 pin); scoped GPU gate GREEN 123/12162/0/0 twice
(byte-identical to the s64 pin and each other); full
run-tests.cljk exit 1 RED AT BASE kotoba.form (ADR-0362, outside
this diff -- touches NO .cljk namespace), captures byte-identical
to the s64 pins -- NO green full suite claimed; settle-bar
evaluator 38/0 + ledger eval twice byte-identical -> VERDICT
PENDING 1/4 unchanged (no runs, no ledger line, no day slot;
next executable slot 2026-10-29); no derivation census (a
freeze-only tick computes no statistics -- named, not omitted);
find docs/evidence/gpu -name '*.sh' -> 0. Rule 4 binds: nothing
moves; accelerator-targets defaults remain provisional
(`:measured? false`); no vendor optimization exists for Intel.

Named rows for later sessions: (first, STARTED) the
fifth-window measurement + T7 read in the 2026-10-29 UTC slot
(NEW hardware; the slot opens 2026-10-29T00:00:00Z, ~3h50m
after this tick -- NAMED, not skipped silently); (STARTED at
the s64 freeze) the s38 hi (sum,256,S=32) wander replication
ANALYSIS half (needs W5's hi runs); (STARTED at this freeze)
this row's ANALYSIS half (needs W5's tw runs); then the
second-pair profile axis at W5 (the s56 halving-rule pairs;
its own freeze; need W5 data); any further named profile pair
-- which requires a NEW named rank-pair vocabulary or selection
rule (none exists yet -- naming one is future design work).

Evidence: `docs/evidence/gpu/anv-b3w5qpairevel-20261029/`
(protocol.txt is the frozen pre-registration -- written once,
never rewritten; freeze-record-s65.txt is this tick's record --
the analysis session owns record.txt there; the gate captures
are byte-identical to the s64 pins). The analysis half of the
row is UNMEASURED until the W5 runs exist.

## 2026-10-28 (session 66, JUN-59) -- the second-pair profile
axis (the s56 halving-rule pairs) at W5 PRE-REGISTRATION
FREEZE (DESIGN slice; STARTED, NOT FINISHED)

Session 66 took the s57-frozen W5 carry-forward's remaining
analysis-row queue to its LAST row's design half: the W5 read
of the second-pair compression profile axis -- the
difference-in-differences of the s56 HALVING-RULE pairs,
OUTER2 (5,71) and INNER2 (33,43) -- of the named cell
(max,128,S=default) is now PRE-REGISTERED in
`docs/evidence/gpu/anv-b3w5pair2profile-20261029/protocol.txt`
(freeze stamp 2026-10-28T20:38:43Z), frozen BEFORE any
fifth-window run exists -- no committed file contains any W5
quantity. The frozen row: T16, the single difference-in-
differences test at the named window pair (s36, W5) --
2*P2_obs = 2*C_out2 - 2*C_in2 of the block-level second-pair
spread levels (block = 3 consecutive tw runs; 2*L = 6th+7th
order statistics of the 12 block D values, INTEGER half-tick
units; both axes over the SAME pooled 75) against the
two-window run-repartition null of the 72 tw runs of s36 and
W5 (20,000 trials, ONE random.Random(2026102816) -- distinct
from T7's 20261029, T14's 2026102814 and T15's 2026102815 --
both axes on the same shuffles, one shuffle per trial), the
pre-registered direction P2_obs > 0 fixed by published s55
T5 (a) and the s56 second-pair priors (OUT2 drops exceeding
IN2 drops at every post-shift window, all three published
2*P2_obs positive; QUOTE-ONLY) and NOT by any W5 statistic;
letters (a) SECONDPAIR-W5-OUTER-WEIGHTED-DIFFERENT (p <=
0.05) / (b) NOT-DIFFERENT (named sub-cases) / (c) NOT
EVALUABLE; ONE named test, NO multiplicity correction applied
or needed. NAMED, NOT HIDDEN: T6's published joint letter is
(b) (only (s36,s38) cleared 0.05 -- p 0.021849/0.193840/
0.055847), so this row is a SINGLE-CONTRAST read of a profile
axis whose three-contrast IUT failed on the 2026-10-28
windows; a T16 (a) would NOT repair T6's (b), and a T16 (b)
is CONSISTENT WITH the s56-era power loss at this pair set
AND EQUALLY CONSISTENT WITH genuine non-replication of the
outer-weighted profile at the second pair set; P2 is a
difference-in-differences, so the per-axis contrasts
(2*C_out2, 2*C_in2) and levels are named and printed
(descriptive only, NO letter) and visible under any letter.
The row's ANALYSIS half is day-slot-gated and was NOT run this
tick: it needs W5's tw runs, and W5 is the window whose 78
fresh processes run in the first measurement session at or
after 2026-10-29T00:00:00Z -- this tick ran ~3h20m before that
slot opens (NAMED, not skipped silently). With this freeze
EVERY row of the s57 carry-forward queue is pre-registered;
the remaining work is the day-slot-gated W5 measurement plus
four analysis halves. NAMED, NOT HIDDEN: STILL LOW POWER (n=2
windows, 12 blocks each, ONE host, ONE named cell); (a) names
NO mechanism and NOT physical-vs-estimator-structure;
threshold-artifact-vs-representation STAYS UNRESOLVED. Gates
(real runs this tick): classify self-test 2649/0
(byte-identical to the s65 pin); scoped GPU gate GREEN
123/12162/0/0 twice (byte-identical to the s65 pin and each
other); full run-tests.cljk exit 1 RED AT BASE kotoba.form
(ADR-0362, outside this diff -- touches NO .cljk namespace),
captures byte-identical to the s65 pins -- NO green full suite
claimed; settle-bar evaluator 38/0 + ledger eval twice
byte-identical -> VERDICT PENDING 1/4 unchanged (no runs, no
ledger line, no day slot; next executable slot 2026-10-29);
no derivation census (a freeze-only tick computes no
statistics -- named, not omitted); find docs/evidence/gpu
-name '*.sh' -> 0. Rule 4 binds: nothing moves;
accelerator-targets defaults remain provisional
(`:measured? false`); no vendor optimization exists for Intel.

Named rows for later sessions: (first, STARTED) the
fifth-window measurement + T7 read in the 2026-10-29 UTC slot
(NEW hardware; the slot opens 2026-10-29T00:00:00Z, ~3h20m
after this tick -- NAMED, not skipped silently); (STARTED at
the s64 freeze) the s38 hi (sum,256,S=32) wander replication
ANALYSIS half (needs W5's hi runs); (STARTED at the s65
freeze) the T15 quantile-pair level axes ANALYSIS half (needs
W5's tw runs); (STARTED at this freeze) this row's ANALYSIS
half (needs W5's tw runs); any further named profile pair --
which requires a NEW named rank-pair vocabulary or selection
rule (none exists yet -- naming one is future design work).

Evidence: `docs/evidence/gpu/anv-b3w5pair2profile-20261029/`
(protocol.txt is the frozen pre-registration -- written once,
never rewritten; freeze-record-s66.txt is this tick's record --
the analysis session owns record.txt there; the gate captures
are byte-identical to the s65 pins). The analysis half of the
row is UNMEASURED until the W5 runs exist.

## Dated note (2026-10-28, JUN-59 session 67: the W5 route pre-flight)

The W5 measurement row (the s57-frozen queue's first row) taken to its
ROUTE/CUSTODY PRE-FLIGHT half only -- NO runs, NO compiles, NO GO stamp,
no day slot, no ledger line (the frozen protocol forbids builds/runs
before the session's GO stamp and the W5 slot opens
2026-10-29T00:00:00Z, ~2h5x after this tick). VERIFIED this tick: the
local custody inputs reproduce the s51 host-verify digests exactly
(instrument a5e539f0..., corpus census eefba52e..., s51 manifest
c568e32e...); the manifest cell-line digest is FULLY NAMED for the first
time -- 873025d650afae2329ab2c05c2048931a5263976b9bfb585d3665b7018c32200
(sha256 of the 24 non-comment cell lines; the chain's files quote it
truncated) -- and the s36/s51 cell lines are byte-equal; the 16-file
corpus verifies locally 16/16 against the census; the host route
(aiueos-6600hs / 100.98.24.37, user murakumo-ci) is reachable, host
clock sane, the render-group fix holds, gcc and /dev/dri/renderD128 are
present. NAMED: the W5 workdir ~/anv-b3w5xdayrep-20261029 is NOT yet
staged on the host -- staging is the W5 session's own pre-GO custody
step (not done here). FULL run-tests and the settle-bar self-test +
ledger eval were NOT REACHED this tick (runtime budget) and are NOT
claimed. Rule 4 binds: no row moves; accelerator-targets defaults stay
as ADR-0358 set them. Evidence:
`docs/evidence/gpu/anv-b3w5routepreflight-20261028/record.txt`.

## Dated note (2026-10-28, JUN-59 session 68: the deferred-gate batch)

The s67 carry-forward's named "next tick must run these before any
push-equivalent claim" items, all run and verified this tick -- NO runs,
NO compiles, NO GO stamp, no day slot, no ledger line (a verification
slice only; the W5 slot opens 2026-10-29T00:00:00Z, ~2h2x after this
tick). VERIFIED: FULL run-tests.cljk LIVE exit 1, RED AT BASE
`kotoba.form` (ADR-0362, outside this diff -- this tick touches NO
`.cljk` namespace), captures byte-identical to the newest full-suite
pins on disk (s64) -- NO green full suite claimed; the frozen settle-bar
evaluator self-test 38/0 + ledger eval twice byte-identical AND
byte-identical to the s66 pin -> VERDICT PENDING 1/4 unchanged (the
bar's state is VERIFIED again, it was UNVERIFIED at s67);
`find docs/evidence/gpu -name '*.sh'` -> 0. Standing gates re-run and
byte-identical to their pins: classify self-test 2649/0; scoped GPU gate
GREEN 123/12162/0/0 twice (919-byte captures). NAMED, NOT HIDDEN: the
pinned scoped runner shape is ns + the eight accelerator-* requires +
the bare `(t/run-tests ...)` form -- a draft carrying run-tests.cljk's
`:end-run-tests` override produced a 969-byte capture with one extra
summary line (the only diff vs the pin) and was rebuilt to the pinned
shape; both runs re-taken. Rule 4 binds: no row moves;
accelerator-targets defaults remain provisional (`:measured? false`);
no vendor optimization exists for Intel. Queue unchanged: the W5
measurement session (first at/after 2026-10-29T00:00:00Z, its pre-GO
custody steps named at s67) then T7 and the three frozen analysis
halves. Evidence:
`docs/evidence/gpu/anv-b3w5deferredgates-20261028/record.txt`.

## Dated note (2026-10-28, JUN-59 session 69: the W5 analysis pre-build)

The W5 measurement row's implementation preparation half -- the
five-window analysis machinery of the W5 session's `analysis-s<NN>.py`
built and validated BEFORE any W5 run exists (NO runs, NO compiles, NO
GO stamp, NO host writes, no day slot, no ledger line; the measurement
half stays day-slot-gated to 2026-10-29T00:00:00Z, ~2h after this
tick). VERIFIED: the s51-compat run of
`docs/evidence/gpu/anv-b3w5prego-20261028/analysis-prego.py` (real run
2m45s, exit 0) reproduces the committed publication-s51.txt values
EXACTLY -- 44 rows, 0 failed (want values parsed from the publication,
not transcribed): the ENTIRE published RNG stream (T1 counts 99/9; D3
counts 2844/367/3657/12283) plus D1, the full D2 table, C1, vectors,
anchors -- the resampling and estimator code paths are validated
end-to-end against published frozen numbers. NAMED, NOT HIDDEN: the
W5-dependent parts (T7 at (s36, W5), five-window D3, D1/D2/D4 at W5,
w5-mode publication text) are UNVALIDATED until the W5 logs exist; the
determinism double-run and the standing gates were NOT run this tick
(runtime budget) and are carry-forward before any push-equivalent
claim; the bar state is UNVERIFIED this tick (last verified s68:
VERDICT PENDING 1/4). Rule 4 binds: no row moves;
accelerator-targets defaults stay as ADR-0358 set them. Evidence:
`docs/evidence/gpu/anv-b3w5prego-20261028/`.

## Dated note (2026-10-28, JUN-59 session 70: the determinism double-run + deferred-gate batch 2)

The s69 carry-forward's named items, all run and verified this tick --
NO runs, NO compiles, NO GO stamp, no day slot, no ledger line (a
verification slice only; the W5 slot opens 2026-10-29T00:00:00Z, ~1h3x
after this tick). VERIFIED: the analysis-prego.py `--compat-s51`
determinism DOUBLE-RUN (two real runs, 2m44.7s wall each, exit 0) --
run1 == run2 byte-identical AND both reproduce the committed
`compat-s51-validation.txt` byte-identically (git clean) -- so the
generator's DETERMINISM claim is now verified (it was unverified at
s69); FULL run-tests.cljk LIVE exit 1, RED AT BASE `kotoba.form`
(ADR-0362, outside this diff -- this tick touches NO `.cljk`
namespace), captures byte-identical to the s68 pins -- NO green full
suite claimed; the frozen settle-bar evaluator self-test 38/0 + ledger
eval twice byte-identical AND byte-identical to the s68 pin -> VERDICT
PENDING 1/4 unchanged (the bar's state is VERIFIED again, it was
UNVERIFIED at s69); classify self-test 2649/0 and scoped GPU gate GREEN
123/12162/0/0 twice (919-byte captures, pinned runner shape), every
capture byte-identical to its pin; `find docs/evidence/gpu -name '*.sh'`
-> 0. NAMED, NOT HIDDEN: the W5-dependent parts of the pre-build stay
UNVALIDATED until the W5 logs exist, and the derivation-census
second-parser twin is still NOT built (s69's named optional row; not
done here). Rule 4 binds: no row moves; accelerator-targets defaults
remain provisional (`:measured? false`); no vendor optimization exists
for Intel. Queue unchanged: the W5 measurement session (first at/after
2026-10-29T00:00:00Z, its pre-GO custody steps named at s67) then T7
and the three frozen analysis halves. Evidence:
`docs/evidence/gpu/anv-b3w5deferredgates2-20261028/record.txt`.

## Dated note (2026-10-28, JUN-59 session 71: the prego derivation-census second-parser twin)

The s69/s70-named ungated row -- the independent second-parser
twin for the s69 pre-build's s51-compat validation -- taken to its
implementation half (NO runs, NO compiles, NO GO stamp, no day
slot, no ledger line; the W5 measurement half stays day-slot-gated
to 2026-10-29T00:00:00Z, ~1h14m after this tick started). BUILT:
`docs/evidence/gpu/anv-b3w5pregocensus-20261028/derivation-census-
s71.py` -- the s63 census independence contract (no re module, no
numpy, pure-Python sorted() order statistics, independent
pure-Python shuffle loop re-implementing the frozen RNG contract
`random.Random(20261028)` in the frozen probe order) over the four
prior windows' committed logs, in three-way rows (published /
prego report / census). VERIFIED this tick: the CENSUS_SMOKE
plumbing run (TRIALS=20, scratch-only) -- 38/38 deterministic rows
match three-way (integrity, C1, block-min vectors, anchors, T1 2*L
pairs + joint letter, the full D2 18-cell table) and the six RNG
rows match on every non-count field; SECTION B 2/2 (published D1
content re-derived: 143/111/113/118 repro True inpair False;
303/241/235/240 repro True inpair True); hygiene 4/4; standing
gates all byte-identical to their s70 pins (classify 2649/0, bar
self-test 38/0, ledger eval twice -> VERDICT PENDING 1/4, scoped
GPU gate GREEN 123/12162/0/0 twice, `find ... '*.sh'` -> 0). NAMED,
NOT HIDDEN: the census's 20,000-trial DOUBLE-RUN was still in
flight at tick close (the pure-Python repartition is slower than
the prego's numpy batches) -- its RNG-stream counts/p reproduction
(99/9/2844/367/3657/12283) is UNVERIFIED until the double-run
lands, and FULL run-tests.cljk was NOT run this tick (budget) --
both are carry-forward before any push-equivalent claim. NAMED
FINDING: the prego report's 44 rows contain NO D1 row (its D1
regex is single-line against the publication's wrapped text, so
that loop matched 0 rows), and its dormant D1 helper computes the
pair-interval flag with L_s51 among the endpoints, contradicting
the published `{L_s38, L_s39}` semantics -- the census implements
the published semantics and reproduces the published flags. Rule 4
binds: no row moves; accelerator-targets defaults stay as ADR-0358
set them. Queue unchanged: the W5 measurement session (first
at/after 2026-10-29T00:00:00Z, its pre-GO custody steps named at
s67) then T7 and the three frozen analysis halves. Evidence:
`docs/evidence/gpu/anv-b3w5pregocensus-20261028/`.

## Dated note (2026-10-28, JUN-59 session 72: the s71 carry-forward batch)

The census DOUBLE-RUN at the frozen 20,000-trial contract VERIFIED:
run1 == run2 byte-identical (10,611 bytes), TOTAL 44 rows / 0
mismatched three-way (the six RNG count/p rows now reproduce at full
trials -- 99/9/2844/367/3657/12283), SECTION B 2/2, hygiene 4/4;
`derivation-census-s71.txt` committed (was uncommitted until
verified). The s71 in-flight background runs had not survived their
session (named). FULL run-tests.cljk run live: exit 1, RED AT BASE
`kotoba.form` (ADR-0362, outside this diff) -- no green full suite
claimed. Standing gates byte-identical to the s71 pins (classify
2649/0; scoped GPU gate 123/12162/0/0 x2; bar self-test + ledger
eval x2 -> VERDICT PENDING 1/4; `find ... '*.sh'` -> 0). This
session started 2026-10-28T23:30Z, before the W5 slot opens at
2026-10-29T00:00:00Z -- NOT the W5 measurement session (named).
Rule 4 binds: nothing moves; accelerator-targets defaults stay
:measured? false. Chain PR #1643 was merged 23:21:57Z; this tick
starts `bot/amu-gpu-chain-20261028-4` with one fresh PR. Evidence:
`docs/evidence/gpu/anv-b3w5pregocensus-20261028/record-s72-carryforward.txt`.

## Dated note (2026-10-29, JUN-59 session 75: the s73 carry-forward remainder)

analysis-s73.py run 2 (foreground, numpy 2.5.4 interpreter --
the s74 background run's interpreter lacked numpy, named there)
completed rc=0 in 4m07s and is BYTE-IDENTICAL to run 1
(publication-s73.txt sha256 221d5591... == scratch/pub-s73-run1-
pin.txt, cmp exit 0): the w5-mode "run twice, diff exit 0"
determinism claim is VERIFIED and the W5 (s73) T7 values -- (a)
CROSS-DAY-REPLICATED-ON-BOTH-LEVEL-AXES (MAD 143 -> 98, p 0.000050;
IQR 303 -> 223, p 0.000200) -- stand as two byte-identical runs of
the validated generator. Standing gates: FULL run-tests.cljk exit
1, RED AT BASE kotoba.form (ADR-0362, outside this diff) -- no
green full suite claimed; settle-bar self-test 38/0 and pre-line
ledger eval x2 byte-identical to the s72 pins; `find ... '*.sh'`
-> 0. THE BAR: one ledger line appended after the gates verified
(day=2026-10-29 session=s73 class=INTERMEDIATE/MIXED median=1131
min=998 flag=none -- the frozen L12 hi block-A candidate; C1 (a),
VERIFY mismatch 0, GO stamp 00:34:10Z before builds/runs); the
frozen evaluator (run twice, byte-identical) reports s73 COUNTED
(day 2026-10-29's first qualifying reading) and VERDICT: PENDING
2/4. Rule 4 binds: nothing moves; accelerator-targets defaults
stay :measured? false; NO vendor optimization exists for Intel.
Carry-forward to session 76: the five-window derivation census
(second-parser cross-check) and the three frozen analysis halves
(T14/T15/T16). Evidence:
`docs/evidence/gpu/anv-b3w5xdayrep-20261029/record-s75.txt`.

## Dated note (2026-10-29, JUN-59 session 76: the five-window derivation census)

derivation-census-s73.py -- the independent second parser for
publication-s73.txt (s73 carry-forward 3(b), protocol section 0
implementation paths: split-based parsing; observed estimators
pure-Python sorted() cross-checked in-loop vs np.partition kth;
resampling estimators np.partition kth paths, NOT a sort; RNG call
order re-implemented) -- ran twice byte-identical (cmp exit 0,
sha256 9ee77c15...) with "TOTAL: 57 rows, 0 mismatched" both runs:
every published integer, count, p and letter of the W5 (s73) T7
cross-checks, INCLUDING the resampling counts/p (MAD count 0
p 0.000050; IQR count 3 p 0.000200) and the four five-window D3
probes. The s73 T7 values -- (a) CROSS-DAY-REPLICATED-ON-BOTH-
LEVEL-AXES -- are now two byte-identical runs of the validated
generator PLUS an independent-parser cross-check. Standing gates
NOT re-run this tick (named; no .cljk namespace touched). Rule 4
binds: nothing moves; accelerator-targets defaults stay
:measured? false. Evidence:
docs/evidence/gpu/anv-b3w5xdayrep-20261029/record-s76.txt.

## Dated note (2026-10-29, JUN-59 session 77: the T14 hi-wander analysis half)

The s64-frozen pre-registered T14 row -- the s38-hi
(sum,256,S=32) per-cell wander replication at (W5, hi), the
s57 queue's second named candidate and the only route from one
uncorrected (b) to a letter that survives multiplicity -- is
taken to its ANALYSIS half over the committed W5 logs. THE ROW
ANSWER: T14 = (b) NOT-REPLICATED
[ABOVE-NULL-MEDIAN-NOT-SIGNIFICANT] -- the named cell's 12 block
pooled medians V = 1102 1090 1120 1093 1092 1143 1117 1109 1131
1094 1162 1115, W_obs = 72 ticks vs the within-window
run-repartition null (ONE random.Random(2026102814), 20,000
trials, one fresh-list shuffle per trial): count 3019 / 20,001,
p = 0.150992 one-sided upper, null median 61.0 -- W_obs is ABOVE
the null median but NOT significant at the pre-registered 0.05,
so the s45 s38-hi (b) wander-excess does NOT replicate on NEW
cross-day data (a (b) is NOT evidence of no per-cell structure;
frozen caveats unchanged). DOUBLE-RUNS: analysis-s77.py run twice
byte-identical (publication-s77.txt 9,491 bytes, sha256
f49d51f0..., cmp exit 0) and derivation-census-s77.py -- the
independent second parser (split-based parsing, no regex;
observed medians pure-Python sorted()[37] cross-checked vs
np.partition kth=37; resampling np.partition kth=37, NOT
np.median; RNG re-implemented) -- run twice byte-identical with
"TOTAL: 57 rows, 0 mismatched | B: 0 | C: 0" (sha256
5fa5633a...), every published integer/count/p/letter of the T14
publication cross-checked including the RNG rows. Standing
gates: classify --self-test 2649/0 == pin; scoped GPU gate GREEN
123/12162/0/0 twice == pin; FULL run-tests.cljk exit 1, RED AT
BASE kotoba.form (ADR-0362, outside this diff) with the 879-byte
.err byte-identical to the s64 pin -- no green full suite
claimed; settle-bar self-test 38/0 == pin and ledger eval twice
== pin -> VERDICT: PENDING 2/4 unchanged; `find ... '*.sh'` ->
0. THE BAR: NO hardware runs at this analysis session -> NO
ledger line, NO day-slot consumption (settle-bar-ledger.txt ==
HEAD). Rule 4 binds: nothing moves; accelerator-targets defaults
stay :measured? false; NO vendor optimization exists for Intel.
Carry-forward to session 78: the T15 quantile-pair level axes
and T16 second-pair profile axis analysis halves. Evidence:
docs/evidence/gpu/anv-b3w5hiwander-20261029/record.txt.

## Dated note (2026-10-29, JUN-59 session 78: the T15 quantile-pair level axes analysis half)

The s65-frozen T15 row (the s53/s54 named quantile-pair level
axes at W5) taken to its ANALYSIS half over the 390 committed
run logs (the W5 tw arm's 36 runs + the four prior windows'
integrity machinery; NO hardware runs, NO builds, NO GO stamp,
NO day-slot consumption, NO settle-bar-ledger line). T15 =
(b) NOT-CROSS-DAY-REPLICATED-ON-BOTH-AXES: the named cell
(max,128,S=default) tw arm, s36 vs W5 -- INNER (28,48) 2*L
118 -> 100 (2*C_obs 18, direction-consistent -- NARROWER at
W5), count 1477/20,001, p = 0.073896 one-sided ->
DIRECTION-CONSISTENT-NOT-SIGNIFICANT; OUTER (9,67) 2*L 496 ->
502 (2*C_obs -6), count 11,558/20,001, p = 0.577921 ->
DIRECTION-REVERSED (the outer-pair level is WIDER at W5 than
at s36 -- the s54 T4 (a) post-shift outer-level drop does NOT
hold at W5). Both axes read (b) under the pre-registered IUT
joint rule. D1 descriptive (NO letter): the five-window level
vectors reproduce the quote-only s53/s54 four-window priors
EXACTLY (INNER 118/102/128/113/100; OUTER
496/429/437/446/502); W5 sits OUTSIDE-BELOW the post-shift band
on the inner pair (2*L_W5 100 vs 102..113) and OUTSIDE-ABOVE
it on the outer pair (502 vs 429..437) -- opposite sides of
the band, named not hidden, mechanism UNMEASURED. A (b) is NOT
evidence of no per-cell structure; threshold-artifact-vs-
representation and physical-vs-estimator-structure STAY
UNRESOLVED. DOUBLE-RUNS: analysis-s78.py run twice byte-
identical (publication-s78.txt 13,471 bytes, sha256
501b9d0a...) and derivation-census-s78.py -- the independent
second parser (split-based parsing, no regex; observed block
spreads pure-Python sorted() cross-checked vs np.partition kth
paths; resampling np.partition, NOT np.sort; RNG re-implemented
in the frozen probe order) -- run twice byte-identical with
"TOTAL: 79 rows, 0 mismatched | B: 0 | C: 0" (sha256
a6985446...), every published integer/count/p/letter cross-
checked including the RNG rows; section B 2,160 block-D
cross-checks 0 mismatched. Standing gates: classify --self-test
2649/0 == pin; scoped GPU gate GREEN 123/12162/0/0 twice ==
pins; FULL run-tests.cljk exit 1, RED AT BASE kotoba.form
(ADR-0362, outside this diff) with the 879-byte .err == pin --
no green full suite claimed; settle-bar self-test 38/0 == pin
and ledger eval twice == pin -> VERDICT: PENDING 2/4 unchanged;
`find ... '*.sh'` -> 0. THE BAR: NO hardware runs -> NO ledger
line, NO day-slot consumption (settle-bar-ledger.txt == HEAD).
Rule 4 binds: nothing moves; accelerator-targets defaults stay
:measured? false; NO vendor optimization exists for Intel.
Carry-forward to session 79: the T16 second-pair profile axis
analysis half. Evidence:
docs/evidence/gpu/anv-b3w5qpairevel-20261029/record.txt.

## Dated note (2026-10-29, JUN-59 session 79: the T16 second-pair profile axis analysis half)

The s66-frozen T16 row (the second-pair profile axis -- the s56
halving-rule pairs OUTER2 (5,71) / INNER2 (33,43) -- at W5) taken
to its ANALYSIS half over the 390 committed run logs (the W5 tw
arm's 36 runs + the four prior windows' integrity machinery; NO
hardware runs, NO builds, NO GO stamp, NO day-slot consumption,
NO settle-bar-ledger line). T16 = (b)
NOT-SECONDPAIR-PROFILE-W5-OUTER-WEIGHTED-CONSISTENT
[OPPOSITE-DIRECTION]: the named cell (max,128,S=default) tw arm,
s36 vs W5 -- OUTER2 (5,71) 2*L 713 -> 715 (2*C_out2 -2 -- the
outer2 level slightly WIDER at W5); INNER2 (33,43) 2*L 63 -> 54
(2*C_in2 9 -- the inner2 level narrows); the primary
difference-in-differences 2*P2_obs = -11 (P2_obs = -5.5), count
11,211/20,001, p = 0.560572 one-sided in the pre-registered
direction P2_obs > 0 -- REVERSED. The (b) [OPPOSITE-DIRECTION]
is CONSISTENT WITH the s56-era power loss at this pair set AND
EQUALLY CONSISTENT WITH genuine non-replication of the
outer-weighted profile at the second pair set; the T6 (b) prior
stands unrepaired; both named levels MOVED (composition
structure named), mechanism UNMEASURED. D1 descriptive (NO
letter): the five-window second-pair level vectors reproduce the
quote-only s56 D1 four-window priors EXACTLY (OUTER2
713/606/659/612/715; INNER2 63/54/62/56/54); W5 sits
OUTSIDE-ABOVE the post-shift band on OUTER2 (715 vs 606..612)
and INSIDE it on INNER2 (54 vs 54..56). A (b) is NOT evidence of
no per-cell structure; threshold-artifact-vs-representation and
physical-vs-estimator-structure STAY UNRESOLVED. DOUBLE-RUNS:
analysis-s79.py run twice byte-identical (publication-s79.txt
10,166 bytes, sha256 4f140b19...) and derivation-census-s79.py
-- the independent second parser (split-based parsing, no regex;
observed block spreads pure-Python sorted() cross-checked vs
np.partition kth paths; resampling np.partition, NOT np.sort;
RNG re-implemented with both axes on the same shuffles) -- run
twice byte-identical with "TOTAL: 47 rows, 0 mismatched | B: 0 |
C: 0" (sha256 f564d6dd...), every published integer/count/p/
letter cross-checked including the RNG rows; section B 2,160
block-D cross-checks 0 mismatched. Standing gates: classify
--self-test 2649/0 == pin; scoped GPU gate GREEN
123/12162/0/0 twice == pins; FULL run-tests.cljk exit 1, RED AT
BASE kotoba.form (ADR-0362, outside this diff) with the 879-byte
.err == pin -- no green full suite claimed; settle-bar self-test
38/0 == pin and ledger eval twice == pin -> VERDICT: PENDING 2/4
unchanged; `find ... '*.sh'` -> 0. THE BAR: NO hardware runs ->
NO ledger line, NO day-slot consumption (settle-bar-ledger.txt ==
HEAD). Rule 4 binds: nothing moves; accelerator-targets defaults
stay :measured? false; NO vendor optimization exists for Intel.
With this row the s57 W5 carry-forward queue is COMPLETE;
carry-forward to session 80: the bar needs two more counted day
slots (NEW pre-registered hardware measurements on future UTC
days -- future design+measurement work) and any further named
profile pair needs a NEW named rank-pair vocabulary (future
design work). Evidence:
docs/evidence/gpu/anv-b3w5pair2profile-20261029/record.txt.

## Dated note (2026-10-29, JUN-59 session 80: the W6 counted-day measurement pre-registration)

The s79 carry-forward item (a) taken to its DESIGN half: the
pre-registration freeze of the hardware measurement the anchor-
class settling bar's THIRD counted day slot needs (protocol.txt
of docs/evidence/gpu/anv-b3w6daybar-20261030/, freeze stamp
2026-10-29T04:23:51Z, before any W6 quantity exists). W6 = the
window whose 78 fresh processes run in the first measurement
session that starts at or after 2026-10-30T00:00:00Z on the ANV
host; ONE ledger line -- hi block A of W6 (the frozen L12 single
bar candidate) at the settle-bar section-2 reading (class at the
frozen section-4 threshold, (sum,128,S=16) pooled median, 18-cell
pooled-median min), COUNTED iff the first qualifying reading of
its UTC day, FLAGGED construction (C1 (b) / VERIFY / pin / GO)
named and consuming no slot; the s57 section-6 route UNCHANGED
(custody host-verify 3/3 + corpus 16/16 before the GO stamp; the
four s51-frozen build pins 4/4 BYTE-IDENTICAL; the 78 runs in the
frozen run order). 2026-10-29's slot is consumed (s73), so the
slice runs NO hardware (NO reading, NO ledger line, NO day-slot
consumption; the bar stays PENDING 2/4). NAMED, NOT HIDDEN: no
analysis row rides this freeze (the W5 queue is COMPLETE; any
further named profile pair needs the NEW named rank-pair
vocabulary, which does not exist); the alternative minimal 9-run
bar-only session was CONSIDERED AND REJECTED with reasons in the
freeze; the FOURTH day slot is NOT frozen here (no silent
extension). Standing gates (real runs): classify --self-test
2649/0 == pin; scoped GPU gate GREEN 123/12162/0/0 twice == pins;
FULL run-tests.cljk exit 1, RED AT BASE kotoba.form (ADR-0362,
outside this diff -- touches NO .cljk namespace) with the 879-byte
.err == pin -- no green full suite claimed; settle-bar self-test
38/0 == pin and ledger eval twice == pin -> VERDICT: PENDING 2/4
unchanged; `find ... '*.sh'` -> 0. Rule 4 binds: nothing moves;
accelerator-targets defaults stay :measured? false; NO vendor
optimization exists for Intel. Carry-forward to session 81: the
W6 measurement half (the first session at/after
2026-10-30T00:00:00Z), then the fourth day slot (its own future
freeze) and the named rank-pair vocabulary (unfrozen design
work). Evidence:
docs/evidence/gpu/anv-b3w6daybar-20261030/freeze-record-s80.txt.

## Dated note (2026-10-29, JUN-59 session 81: the doubling-ladder named rank-pair vocabulary)

The s80 carry-forward item (c) taken to its DESIGN half: the NEW
named rank-pair vocabulary / selection rule -- the only route back
for the rank-pair program retired at s62/s63 (vocabulary.txt of
docs/evidence/gpu/anv-b3dladder-20261029/, written once at freeze
stamp 2026-10-29T04:58:52Z, before any statistic of its pairs
exists). THE DOUBLING LADDER (DL): DL4 (x_(34), x_(42)) k=4 span
8, DL8 (x_(30), x_(46)) k=8 span 16, DL16 (x_(22), x_(54)) k=16
span 32, DL32 (x_(6), x_(70)) k=32 span 64 -- k = half-distance
from the pooled-75 deviation-center rank x_(38); the frozen rule
is data-independent: k runs over the powers of two <= 37 that no
committed record has named ({1,2} named at s58-s61 -> free
{4,8,16,32}); each k sits strictly between consecutive named k
(spacing repair 3<4<5, 5<8<10, 10<16<19, 29<32<33). Future rows
name pairs ONLY from this vocabulary, each in its own protocol
freeze before any statistic (estimators/nulls/thresholds stay
per-row); no silent extension. NAMED, NOT HIDDEN: every DL pair is
self-mirror (tail-side asymmetry is out of scope -- the s61/s62/
s63 mirror-pair asymmetry needs a separate future vocabulary);
DL4 (span 8) sits in the pre-registered narrow-span noise band, so
a (b) at DL4 is uninformative; the freshness claim is exactly a
grep -F over docs/evidence/gpu (0 hits outside the new directory);
the alternative free-k and asymmetric-vocabulary designs were
CONSIDERED AND REJECTED with reasons in the freeze. The slice
computes NO statistic (the DL levels are UNMEASURED), runs NO
hardware, writes NO ledger line (settle-bar-ledger.txt == HEAD);
the bar stays PENDING 2/4. Standing gates (real runs):
classify --self-test 2649/0 == pin; scoped GPU gate GREEN
123/12162/0/0 twice == pins; FULL run-tests.cljk exit 1, RED AT
BASE kotoba.form (ADR-0362, outside this diff -- touches NO
.cljk namespace) with the 879-byte .err == pin -- no green full
suite claimed; settle-bar self-test 38/0 == pin and ledger eval
twice == pin -> VERDICT: PENDING 2/4 unchanged; `find ... '*.sh'`
-> 0. Rule 4 binds: nothing moves; accelerator-targets defaults
stay :measured? false; NO vendor optimization exists for Intel.
Carry-forward to session 82: the W6 measurement half (first
session at/after 2026-10-30T00:00:00Z), the fourth day slot (its
own future freeze), any DL rank-pair row (its own pre-
registration), and the tail-side vocabulary (named limitation).
Evidence: docs/evidence/gpu/anv-b3dladder-20261029/
(freeze-record-s81.txt).

## Dated note (2026-10-29, JUN-59 session 82: the DL level-axis descriptive reference row)

The s81-frozen DOUBLING LADDER vocabulary's FIRST STATISTIC (the
s81 carry-forward item "any DL rank-pair row" taken to its
descriptive-reference half; protocol.txt of
docs/evidence/gpu/anv-b3dlprofile-20261029/ frozen at stamp
2026-10-29T05:22:05Z BEFORE any statistic of the row existed;
the pre-freeze freshness greps were 0/0 hits). T17, DESCRIPTIVE
ONLY -- NO letter, NO null, NO direction (the DL pairs carry no
pre-existing directional hypothesis; the honest first statistic
is the reference vectors a future inferential DL row quotes as
priors): the tw arm's named cell (max,128,S=default), per-block
D = x_(b)-x_(a) over each block's pooled 75 gpu_ticks, 2*L =
6th+7th order statistics of the 12 block D values, five
committed windows s36/s38/s39/s51/W5 -- DL4 (x_(34),x_(42)) 2*L
46/47/48/38/40 (W5 INSIDE the post-shift band 38..47); DL8
(x_(30),x_(46)) 97/84/99/79/83 (INSIDE 79..84); DL16
(x_(22),x_(54)) 238/187/201/188/178 (W5 OUTSIDE-BELOW 187..188);
DL32 (x_( 6),x_(70)) 655/537/572/564/658 (W5 OUTSIDE-ABOVE
537..564). Span-dependent picture, named not hidden, NO letter:
the two NARROW self-mirror pairs sit inside the post-shift band
at W5 while the two WIDE pairs leave it in OPPOSITE directions
-- the narrow-vs-wide opposition of T15's INNER/OUTER set, now
visible inside one data-independent vocabulary; mechanism
UNMEASURED; n=12 blocks x 5 windows, ONE host. VERIFIED (real
tool output): analysis-s82.py (deterministic, no RNG) run twice
BYTE-IDENTICAL (7,870 bytes, sha256 d858cc17..., cmp exit 0);
parser validity pins EXACT (the published s78 INNER
118/102/128/113/100 and OUTER 496/429/437/446/502 vectors and
both W5 block-D vectors reproduced byte-for-value); integrity
390 logs / VERIFY 0 / 8-8 block-min vectors / 4-4 anchors / C1
(a). Standing gates (real runs == the s81 pins): classify
2649/0; scoped GPU gate GREEN 123/12162/0/0 twice; FULL
run-tests.cljk exit 1 RED AT BASE kotoba.form (ADR-0362, outside
this diff -- touches NO .cljk namespace) -- no green full suite
claimed; settle-bar self-test 38/0 + ledger eval twice == pins
-> VERDICT: PENDING 2/4 unchanged; `find ... '*.sh'` -> 0. The
bar: NO reading -> NO ledger line, NO day-slot consumption
(settle-bar-ledger.txt == HEAD). Rule 4 binds: nothing moves;
accelerator-targets defaults stay :measured? false; NO vendor
optimization exists for Intel. Carry-forward to session 83: the
W6 measurement half (first session at/after
2026-10-30T00:00:00Z), the fourth day slot (its own future
freeze), an inferential DL row or this publication's derivation
census (each its own pre-registration), and the tail-side
vocabulary (named limitation). Evidence:
docs/evidence/gpu/anv-b3dlprofile-20261029/
(freeze-record-s82.txt).

## Dated note (2026-10-29, JUN-59 session 83: the T17 derivation census)

The s82 carry-forward item "this publication's derivation census
(independent second parser)" taken as a verification slice; NO
hardware runs, NO compiles, NO GO stamp, NO ledger line.
derivation-census-s82.py re-derives every published value of
publication-s82.txt from the 390 committed run logs on a
genuinely different path (split-based parsing, no regex; pure-
Python sorted() estimators cross-checked in-loop against
np.partition kth paths; NO RNG) and matches the committed bytes
on EVERY row -- 49/49 two-way rows, 0 mismatched; section B
6,480 pair-spread + 2,255 pooled-median + 30 2*L dual-
computation cross-checks, 0 mismatched; section C hygiene 0
mismatched. DOUBLE-RUN BYTE-IDENTICAL (14,721 bytes, sha256
7ecc3ef4..., cmp exit 0). ONE FINDING NAMED, NOT HIDDEN: the
published section-5 band lines print sorted[0]..sorted[1] (min..
MEDIAN) of the three {s38,s39,s51} 2*L values under the label
"closed interval spanned by {s38,s39,s51}" -- the printed
interval tops are understated (DL4 38..47 vs min..max 38..48;
DL8 79..84 vs 79..99; DL16 187..188 vs 187..201; DL32 537..564
vs 537..572); ALL FOUR BAND VERDICTS are UNCHANGED under
min..max (INSIDE/INSIDE/OUTSIDE-BELOW/OUTSIDE-ABOVE), so the
narrow-vs-wide descriptive picture does not move; a future
inferential DL row's freeze must name its convention explicitly.
Standing gates (real runs == the s82 pins): classify 2649/0;
scoped GPU gate GREEN 123/12162/0/0 twice; FULL run-tests.cljk
exit 1 RED AT BASE kotoba.form (ADR-0362, outside this diff --
touches NO .cljk namespace) -- no green full suite claimed;
settle-bar self-test 38/0 + ledger eval twice == pins ->
VERDICT: PENDING 2/4 unchanged; `find ... '*.sh'` -> 0. The
bar: NO reading -> NO ledger line, NO day-slot consumption
(settle-bar-ledger.txt == HEAD). Rule 4 binds: nothing moves;
accelerator-targets defaults stay :measured? false; NO vendor
optimization exists for Intel. Carry-forward to session 84: the
W6 measurement half (first session at/after
2026-10-30T00:00:00Z), the fourth day slot (its own future
freeze), an inferential DL row (its own pre-registration), and
the tail-side vocabulary (named limitation). Evidence:
docs/evidence/gpu/anv-b3dlprofile-20261029/ (record-s83.txt).

## Dated note (2026-10-29, JUN-59 session 84: the T18 inferential
## DL row pre-registration)

The s83 record section-9(c) carry-forward item "an INFERENTIAL
DL row (its own pre-registration; the s82 vectors are its
quote-only priors; its freeze names its convention)" taken to
its DESIGN half; NO hardware runs, NO compiles, NO GO stamp,
NO ledger line; the row's ANALYSIS half is day-slot-gated
behind the W6 measurement half -- STARTED, NOT FINISHED.
protocol.txt (freeze stamp 2026-10-29T06:14:31Z, before any
statistic of the row exists and before any W6 quantity exists)
pre-registers T18 at the fresh W6 window: per-pair contrast
2*C_obs = 2*L_s36 - 2*L_W6 over the WHOLE closed DL vocabulary
(DL4/DL8/DL16/DL32, named only from the s81 freeze),
pre-registered direction C_obs > 0 per pair fixed by the s82
quote-only priors alone (DL8 3/4 post-s36 windows below s36;
DL16 4/4; DL32 3/4 with the W5 exception named -- the demanding
axis; DL4 2/4 and uninformative per the s81 section-4(c)
caveat), the s78/T15 two-window run-exchangeability null
verbatim (72 tw runs, ONE random.Random(2026102918), probe
order DL4/DL8/DL16/DL32, 20,000 trials per probe, p =
(1+count(C* >= C_obs))/(1+20,000) one-sided), per-pair letters
(a)/(b)/(c), joint T18 = IUT over the three informative steps
DL8/DL16/DL32 (s81 rule 3(d): the row's own multiplicity
convention). THE CONVENTION IS NAMED EXPLICITLY (the s83
requirement): the post-shift band is the closed interval
[MIN, MAX] of {2*L_s38, 2*L_s39, 2*L_s51} -- MIN..MAX, NOT the
s82 publication's printed min..median (the s83 correction
record) -- and every band placement is descriptive, never a
test. Standing gates (real runs == the s83 pins): classify
2649/0 (17,925 bytes == pin); scoped GPU gate GREEN
123/12162/0/0 twice (919 bytes == pins); FULL run-tests.cljk
exit 1 RED AT BASE kotoba.form (ADR-0362, outside this diff --
touches NO .cljk namespace) -- no green full suite claimed;
settle-bar self-test 38/0 + ledger eval twice == pins ->
VERDICT: PENDING 2/4 unchanged; `find ... '*.sh'` -> 0. The
bar: NO reading -> NO ledger line, NO day-slot consumption
(settle-bar-ledger.txt == HEAD). Rule 4 binds: nothing moves;
accelerator-targets defaults stay :measured? false; NO vendor
optimization exists for Intel. Carry-forward to session 85:
the W6 measurement half (first session at/after
2026-10-30T00:00:00Z) -- now the only gate between this freeze
and its analysis half --, then the T18 analysis half, the
fourth day slot (its own future freeze), and the tail-side
vocabulary (named limitation). Evidence:
docs/evidence/gpu/anv-b3w6dlrep-20261030/ (protocol.txt,
freeze-record-s84.txt).

## Dated note (2026-10-29, JUN-59 session 85: the fourth
## counted-day bar measurement pre-registration (W7))

The s84 record section-6(c) carry-forward item "the fourth
counted-day bar measurement (its own future freeze; its day
follows W6's actual run day)" taken to its DESIGN half; NO
hardware runs, NO builds, NO compiles, NO GO stamp, NO ledger
line; the row's MEASUREMENT half is slot-gated behind W6's
ledger line -- STARTED, NOT FINISHED. protocol.txt (freeze
stamp 2026-10-29T06:39:16Z, before any W6 quantity exists and
before any W7 quantity exists; pre-freeze freshness greps over
docs/evidence/gpu: "anv-b3w7daybar"/"20261031"/"2*L_W7"/
whole-word "W7"/"W7 =" all 0 hits) pre-registers W7 = the
window whose 78 fresh processes run in the first measurement
session that starts at or after 00:00:00Z of the first UTC day
STRICTLY AFTER the UTC day named on W6's ledger line (planned
2026-10-31 if W6's line takes 2026-10-30; follows W6's actual
run day if the runs slip): ONE ledger line = hi block A (the
frozen L12 single bar candidate) at the settle-bar.txt
section-2 READING, COUNTED iff the first qualifying reading of
its UTC day, FLAGGED construction named and consuming no slot;
the s57 section-6 route UNCHANGED (custody 3/3 + corpus 16/16
before the GO stamp; the four s51-frozen build pins 4/4
BYTE-IDENTICAL; the 78 runs in the frozen run order). THE
THREE CONTINGENCIES FROZEN (named, not hidden): (i) W6 slips
-> W7's day follows W6's actual line day; (ii) W6 FLAGGED ->
 W7's line delivers the THIRD counted reading and the rest is
NEW pre-registered work (no silent extension); (iii) W6's
ledger line ABSENT -> this freeze STANDS DOWN (fail-closed).
NO analysis row rides this freeze (T18 binds only (s36, W6);
W7 is in no frozen pair or contrast); the minimal 9-run
bar-only alternative RE-REJECTED on the s80 4(b) reasons
adopted here. Standing gates (real runs == the s84 pins):
classify 2649/0 (17,925 bytes == pin); scoped GPU gate GREEN
123/12162/0/0 twice (919 bytes == pins); FULL run-tests.cljk
exit 1 RED AT BASE kotoba.form (ADR-0362, outside this diff --
touches NO .cljk namespace) -- no green full suite claimed;
settle-bar self-test 38/0 + ledger eval twice == pins ->
VERDICT: PENDING 2/4 unchanged; `find ... '*.sh'` -> 0. The
bar: NO reading -> NO ledger line, NO day-slot consumption
(settle-bar-ledger.txt == HEAD). Rule 4 binds: nothing moves;
accelerator-targets defaults stay :measured? false; NO vendor
optimization exists for Intel. Carry-forward to session 86:
the W6 measurement half (first session at/after
2026-10-30T00:00:00Z) -- the gate for T18's analysis half and
this freeze's measurement half --, then the T18 analysis half,
the W7 measurement half (behind W6's ledger line), any further
counted-day slot (its own freeze), and the tail-side
vocabulary (named limitation). Evidence:
docs/evidence/gpu/anv-b3w7daybar-20261031/ (protocol.txt,
freeze-record-s85.txt).

## Dated note (2026-10-29, JUN-59 session 86: the tail-side
## half-pair vocabulary)

The s81 DL freeze's named limitation 4(b) ("probing which tail
moves needs a SEPARATE future vocabulary (asymmetric pairs)"),
queued at s85 carry-forward (e), taken to its DESIGN half; NO
hardware runs, NO builds, NO compiles, NO GO stamp, NO ledger
line, NO statistic of any run log. vocabulary.txt (freeze
stamp 2026-10-29T07:22:17Z; pre-freeze freshness greps
07:18:55Z-07:19:25Z: 24 tokens x 0 hits -- pair forms, name
tokens TS-L4..TS-R32, pair tokens; bare rank tokens NOT
claimed fresh, named not hidden) freezes the TAIL-SIDE
HALF-PAIRS: per k in the DL k set {4,8,16,32} (named ONLY
from s81 -- no new k selection), TS-Lk = (x_(38-k), x_(38))
and TS-Rk = (x_(38), x_(38+k)); span control (the s81 4(a)
conflation objection answered by construction), mirror
closure (r <-> 76-r), DL decomposition (HL_k + HR_k = D_k
exactly), disjoint from all 20 named pairs, closed at eight
pairs. The selection rule for future rows is frozen (s81
rule 3 adopted). NAMED, NOT HIDDEN: NO direction is
pre-registered (the s61/s62/s63 asymmetry is quote-only
motivation); the narrow-span caveat (s81 4(c)) extends to
half-pairs (TS-L4/TS-R4 and TS-L8/TS-R8 in the noise band;
informative families k=16/32); estimators/contrast stay
per-row. Standing gates (real runs == the s85 pins):
tailpair-vocab-s86.py run twice byte-identical (3,188 bytes,
sha256 7c9d9892... both) + self-test 271/0; classify
2649/0 (17,925 bytes == pin); scoped GPU gate GREEN
123/12162/0/0 twice (919 bytes == pins); FULL run-tests.cljk
exit 1 RED AT BASE kotoba.form (ADR-0362, outside this diff
-- touches NO .cljk namespace) -- no green full suite
claimed; settle-bar self-test 38/0 + ledger eval twice ==
pins -> VERDICT: PENDING 2/4 unchanged; `find ... '*.sh'` ->
0. The bar: NO reading -> NO ledger line, NO day-slot
consumption (settle-bar-ledger.txt == HEAD). Rule 4 binds:
nothing moves; the ADR-0358 row states are unchanged; NO
vendor optimization exists for Intel. Carry-forward to
session 87: the W6 measurement half (first session at/after
2026-10-30T00:00:00Z) -- the gate for T18's analysis half
and W7's measurement half --, then the T18 analysis half,
the W7 measurement half (behind W6's ledger line), any
further counted-day slot (its own freeze), any tail-side row
(this vocabulary is the route; a NEW pre-registration).
Evidence: docs/evidence/gpu/anv-b3tailvocab-20261029/
(vocabulary.txt, tailpair-vocab-s86.py/.txt,
tailvocab-s86-selftest.txt/.err, freeze-record-s86.txt, the
s86 gate captures).

## Dated note (2026-10-29, JUN-59 session 87: the tail-side
## half-pair descriptive reference row)

The s86 tail-side vocabulary's FIRST STATISTIC (T19) taken to
its DESCRIPTIVE half over the 390 committed run logs of the
five fixed windows; NO hardware runs, NO builds, NO compiles,
NO GO stamp, NO ledger line, NO letter, NO null, NO direction.
protocol.txt (freeze stamp 2026-10-29T07:40:02Z, file finalized
07:40:27Z; pre-freeze freshness greps
2026-10-29T07:38:25Z-07:38:39Z: 0 hits on every row-name token;
bare "T19"'s 64 hits are all UTC-hour timestamps -- named not
hidden) freezes the row; analysis-s87.py (pure stdlib, no RNG)
run twice byte-identical (publication-s87.txt 13,188 bytes,
sha256 ebe4daa7... both, cmp exit 0). The five-window 2*L
vectors (s36/s38/s39/s51/s73) at the tw arm's named cell
(max,128,S=default): TS-L4 23/30/21/24/20; TS-R4
19/16/22/18/19; TS-L8 50/51/52/47/42; TS-R8 48/32/49/38/41;
TS-L16 118/103/115/103/90; TS-R16 94/82/100/85/77; TS-L32
418/342/397/362/439; TS-R32 213/186/183/204/214. The s86
decomposition identity HL_k+HR_k = D_k verified EXACT at all
240 block checks. DESCRIPTIVE PICTURE, NAMED NOT HIDDEN, NO
LETTER: at the two INFORMATIVE families (k=4/8 tagged
UNINFORMATIVE-BY-S86-CAVEAT) the LEFT half-spread level
exceeds the RIGHT at all five windows (k=16 R-L level
difference -24/-21/-15/-18/-13; k=32 -205/-156/-214/-158/
-225) -- the direction of the s61/s62/s63 quote-only
motivation is visible in these descriptive vectors; NOT a
test, mechanism UNMEASURED, no tail is claimed to move. The
2*L levels do NOT add (published section 5b names it). Parser
validity pins EXACT 6/6 (publication-s78 INNER/OUTER +
publication-s82 DL vectors). Standing gates (real runs == the
s86 pins): classify 2649/0 (17,925 bytes == pin); scoped GPU
gate GREEN 123/12162/0/0 twice (919 bytes == pins); FULL
run-tests.cljk exit 1 RED AT BASE kotoba.form (ADR-0362,
outside this diff -- touches NO .cljk namespace) -- no green
full suite claimed; settle-bar self-test 38/0 + ledger eval
twice == pins -> VERDICT: PENDING 2/4 unchanged; `find ...
'*.sh'` -> 0. The bar: NO reading -> NO ledger line, NO
day-slot consumption (settle-bar-ledger.txt == HEAD). Rule 4
binds: NOTHING MOVES; the ADR-0358 row states are unchanged;
NO vendor optimization exists for Intel. Carry-forward to
session 88: the W6 measurement half (first session at/after
2026-10-30T00:00:00Z) -- the gate for T18's analysis half and
W7's measurement half --, then the T18 analysis half, the W7
measurement half (behind W6's ledger line), any further
counted-day slot (its own freeze), and a future inferential
tail-side row (the s86 vocabulary + T19's vectors are the
route; its own pre-registration). Evidence:
docs/evidence/gpu/anv-b3tailprofile-20261029/ (protocol.txt,
analysis-s87.py, publication-s87.txt, freeze-record-s87.txt,
the s87 gate captures).

## Dated note (2026-10-29, JUN-59 session 88: the inferential
## tail-side row's pre-registration -- T20)

The s87 carry-forward's item 6(e) -- "a FUTURE inferential
tail-side row (the s86 vocabulary + T19's vectors are the
route; its own pre-registration)" -- taken to its DESIGN half
(the s84/s85/s86 pattern: freeze before any target-window
quantity exists). NO hardware runs, NO builds, NO compiles, NO
GO stamp, NO ledger line, NO statistic of any run log; the
row's ANALYSIS half is gated behind the W6 measurement half
(first session at/after 2026-10-30T00:00:00Z; this tick runs
2026-10-29T08:1xZ, ~15.7h before the slot opens) -- STARTED,
NOT FINISHED. protocol.txt (freeze stamp 2026-10-29T08:16:54Z;
pre-freeze freshness greps 08:16:12Z-08:16:22Z: 0 hits on all
eight row-name tokens; "2^12"/"4,096" hits unrelated, bare
"T20" hits UTC-hour timestamps -- named not hidden) freezes
T20 = the tail-side half-pair asymmetry replication at W6: does
the LEFT-greater-RIGHT asymmetry the T19 quote-only
five-window vectors show at all five windows at the two
INFORMATIVE families (k=16: 118/103/115/103/90 vs
94/82/100/85/77; k=32: 418/342/397/362/439 vs
213/186/183/204/214) replicate at the fresh window? Per family
C_obs = 2*L({HL_k}) - 2*L({HR_k}) (the T19 estimator held
fixed) at the named cell (max,128,S=default), tw arm, 12
blocks of 3. NULL: WITHIN-BLOCK SIDE-EXCHANGEABILITY (the s86
mirror closure r <-> 76-r swaps HL_k/HR_k per block); EXACT
randomization over all 2^12 = 4,096 whole-block side-swap
assignments, p = count(C* >= C_obs)/4,096 one-sided, NO RNG
(the T15/T18 seeded Monte Carlo convention considered and
rejected -- 2^12 is exactly enumerable). Letters per family (a)
ASYMMETRY-LEFT-GREATER-REPLICATED (C_obs > 0 AND p <= 0.05) /
(b) NOT-REPLICATED / (c) NOT EVALUABLE; JOINT T20 = IUT over
k=16/k=32 (k=4/8 excluded by the s86 section-4(c) caveat,
tagged UNINFORMATIVE-BY-S86-CAVEAT, never in the joint).
NAMED, NOT HIDDEN: direction fixed by T19's committed vectors
alone (quote-only priors, the s53/s54/s82 pattern -- no
double-dipping: the test data is W6 alone and does not exist at
freeze); which tail MOVES across days is NOT claimed (a
cross-day tail-movement row is its own future pre-registration,
not queued); still low power (n=12 blocks, one window, one
host, one cell); a (b) is not evidence of tail symmetry;
mechanism UNMEASURED. STATE: ACCEPTED DESIGN ONLY (protocol.txt
+ freeze-record-s88.txt + this note); every T20 quantity is
UNMEASURED. Standing gates (real runs == the s87 pins):
classify 2649/0 (17,925 bytes == pin); scoped GPU gate GREEN
123/12162/0/0 twice (919 bytes == pins); FULL run-tests.cljk
exit 1 RED AT BASE kotoba.form (ADR-0362, outside this diff --
touches NO .cljk namespace) -- no green full suite claimed;
settle-bar self-test 38/0 + ledger eval twice == pins ->
VERDICT: PENDING 2/4 unchanged; `find ... '*.sh'` -> 0. The
bar: NO reading -> NO ledger line, NO day-slot consumption
(settle-bar-ledger.txt == HEAD). Rule 4 binds: NOTHING MOVES;
the ADR-0358 row states are unchanged; NO vendor optimization
exists for Intel. Carry-forward to session 89: the W6
measurement half (first session at/after 2026-10-30T00:00:00Z)
-- the gate for T18's analysis half, T20's analysis half and
W7's measurement half --, then the T18 analysis half, T20's
analysis half, the W7 measurement half (behind W6's ledger
line), any further counted-day slot (its own freeze), and a
cross-day tail-movement row (not queued). Evidence:
docs/evidence/gpu/anv-b3w6tailrep-20261030/ (protocol.txt,
freeze-record-s88.txt, the s88 gate captures).

## Dated note (2026-10-29, JUN-59 session 89: the T19
## derivation census)

The publication-s87.txt section-5 queued item ("the 12 W5 block
values (for a future census)") taken as a verification slice --
the s82->s83 census precedent, applied to the T19 vectors the
frozen T18/T20 rows quote at W6. NO hardware runs, NO builds,
NO compiles, NO GO stamp, NO ledger line, NO day-slot
consumption. derivation-census-s87.py (the INDEPENDENT second
parser: no re module; estimators on the numpy np.partition kth
paths -- analysis-s87.py is pure stdlib sorted()-based -- cross-
checked in-loop against pure-Python sorted(); NO RNG, no clock)
re-derives every published computed value from the 390 committed
run logs and matches the committed bytes on EVERY row: 92/92
two-way rows, 0 mismatched; run twice byte-identical (29,790
bytes, sha256 ebf261dd...1463c both). Section B: 1,080 pair-
spread + 2,255 pooled-median + 90 2*L cross-check comparisons
and 240 decomposition block checks, 0 mismatched everywhere.
THE ONE SUBSTANTIVE FINDING, NAMED NOT HIDDEN: the publication's
band lines print sorted[0]..sorted[1] (min..median) of
{s38,s39,s51} and judge W5 vs sorted[1] while protocol.txt
section 5 AND the printed label freeze [MIN,MAX] -- all 8
interval tops understated; under the frozen convention 2 of 8
verdicts CHANGE (TS-R4 OUTSIDE-ABOVE -> INSIDE in 16..22; TS-R8
OUTSIDE-ABOVE -> INSIDE in 32..49), BOTH in the
UNINFORMATIVE-BY-S86-CAVEAT k=4/8 families; the four
informative-family verdicts (TS-L16/TS-R16/TS-L32/TS-R32) are
INVARIANT (0 changed). IMPACT ON FROZEN ROWS: NONE -- T20's
direction rests only on the five-window 2*L vectors (verified
EXACT) and T18's freeze already names [MIN,MAX]; the band
subsection is descriptive, quoted by NO frozen row.
publication-s87.txt stands as published bytes; record-s89.txt
is its correction record; any future band placement uses
[MIN,MAX] and names it. Standing gates (real runs == the s88
pins): classify 2649/0 (17,925 bytes == pin); scoped GPU gate
GREEN 123/12162/0/0 twice (919 bytes == pins); FULL run-tests
.cljk exit 1 RED AT BASE kotoba.form (ADR-0362, outside this
diff -- touches NO .cljk namespace) -- no green full suite
claimed; settle-bar self-test 38/0 + ledger eval twice == pins
-> VERDICT: PENDING 2/4 unchanged; `find ... '*.sh'` -> 0. The
bar: NO reading -> NO ledger line, NO day-slot consumption
(settle-bar-ledger.txt == HEAD). Rule 4 binds: NOTHING MOVES;
the ADR-0358 row states are unchanged; NO vendor optimization
exists for Intel. Carry-forward to session 90: the W6
measurement half (first session at/after 2026-10-30T00:00:00Z)
-- the gate for T18's analysis half, T20's analysis half and
W7's measurement half --, then the T18 analysis half, T20's
analysis half, the W7 measurement half (behind W6's ledger
line), any further counted-day slot (its own freeze), and a
cross-day tail-movement row (not queued). Evidence:
docs/evidence/gpu/anv-b3tailprofile-20261029/
(derivation-census-s87.py/.txt, record-s89.txt, the s89 gate
captures).

## Dated note (2026-10-29, JUN-59 session 90: the W6 reading
## pre-build)

The s89 carry-forward item (a) (the W6 measurement half, the s80
freeze) taken to its IMPLEMENTATION preparation half (the s69
pre-build precedent): reading-prego.py + derivation-census-prego.py,
the s80 protocol section-6 bar-reading path (hi block A anchor
reading -- (sum,128,S=16) pooled median, 18-cell min..max, bar class
vs the frozen refs 1,129/1,132/1,131 -- plus the section-3 integrity
rows), pre-built BEFORE any W6 quantity exists (the W6 run logs do
not exist; the measurement half stays day-slot-gated, first session
at/after 2026-10-30T00:00:00Z). The W6 session adopts the pair as
reading-s<NN>.py / derivation-census-s<NN>.py. VALIDATED at the five
committed windows against publication-s73.txt: 14/14 two-way rows
EXACT under BOTH parsers independently (the generator: regex +
stdlib statistics.median; the census twin: NO re module,
split()/find-split parsing, numpy np.partition kth estimators
cross-checked in-loop against sorted() explicit order statistics --
124 dual computations, 0 mismatched); both run twice byte-identical
(2,930 bytes sha256 8509d52a...00e9; 3,246 bytes sha256
395f4dda...ff51). NO W6 quantity computed; the W6-dependent parts
stay UNVALIDATED until the W6 logs exist. Standing gates (real runs
== the s88 pins): classify 2649/0 (17,925 bytes == pin); scoped GPU
gate GREEN 123/12162/0/0 twice (919 bytes == pins); FULL run-tests
.cljk exit 1 RED AT BASE kotoba.form (ADR-0362, outside this diff --
touches NO .cljk namespace) -- no green full suite claimed; settle-
bar self-test 38/0 + ledger eval twice == pins -> VERDICT: PENDING
2/4 unchanged; `find ... '*.sh'` -> 0. The bar: NO reading -> NO
ledger line, NO day-slot consumption (settle-bar-ledger.txt ==
HEAD). Rule 4 binds: NOTHING MOVES; the ADR-0358 row states are
unchanged; NO vendor optimization exists for Intel. Carry-forward
to session 91: the W6 measurement half (first session at/after
2026-10-30T00:00:00Z) -- the gate for T18's analysis half, T20's
analysis half and W7's measurement half --, then the T18 analysis
half, T20's analysis half, the W7 measurement half (behind W6's
ledger line), any further counted-day slot (its own freeze), and a
cross-day tail-movement row (not queued). Evidence:
docs/evidence/gpu/anv-b3w6prego-20261029/ (reading-prego.py +
compat-prego-validation.txt, derivation-census-prego.py +
derivation-census-prego.txt, record.txt, the s90 gate captures).

## Dated note (2026-10-29, JUN-59 session 91: the W6 route/custody
## pre-flight)

The s90 carry-forward item (a) (the W6 measurement half, the s80
freeze) taken to its ROUTE/CUSTODY PRE-FLIGHT half (the s67
precedent -- the W5 row's preparation half was exactly this
pre-flight): the W6 route's local custody inputs re-verified
against the s51 host-verify digests BEFORE the slot opens (this
tick runs 2026-10-29T10:0xZ, ~13.8h before the first session
at/after 2026-10-30T00:00:00Z; the measurement half stays
day-slot-gated -- STARTED, NOT FINISHED). LOCAL CUSTODY INPUTS
(shasum -a 256 over the committed bytes): instrument source
gpu-subgroup-reduce-anv-ndiv.c a5e539f0ad1c5d73... MATCH (==
s51 host-verify local=/host=); expected-corpus.sha256
eefba52e7be052d6... MATCH; manifest cases-s51-a.txt
c568e32ef0363165... MATCH; the 24 non-comment cell lines digest
873025d650afae2329ab2c05c2048931a5263976b9bfb585d3665b7018c32200
reproduces the chain's 873025d650afae23... prefix EXACTLY and the
cell lines are byte-equal to cases-s36-a.txt's (the fresh-header
manifest rule the W6 session must reproduce); corpus 16/16 local
verify (8 OK + 8 OK across the two corpus dirs). HOST ROUTE PROBE
(read-only ssh, NO GPU submission): route reachable
(murakumo-ci-6600hs -> aiueos-6600hs, user murakumo-ci), host
clock sane, render group holds, gcc present, /dev/dri/card0 +
renderD128 present; the W6 workdir ~/anv-b3w6daybar-20261030 is
NOT YET STAGED (NO-WORKDIR, named not hidden -- staging is the W6
session's own pre-GO custody step). NAMED LIMITS: no host-side 3/3
comparison, no corpus sha256sum -c host-side, no GO stamp, no
builds, no runs, no statistics of any kind (a pre-flight computes
no statistics). Standing gates (real runs == the s88 pins):
classify 2649/0 (17,925 bytes == pin); scoped GPU gate GREEN
123/12162/0/0 twice (919 bytes == pins); FULL run-tests.cljk exit
1 RED AT BASE kotoba.form (ADR-0362, outside this diff -- touches
NO .cljk namespace) -- no green full suite claimed; settle-bar
self-test 38/0 + ledger eval twice == pins -> VERDICT: PENDING 2/4
unchanged; `find ... '*.sh'` -> 0. The bar: NO reading -> NO ledger
line, NO day-slot consumption (settle-bar-ledger.txt == HEAD).
Rule 4 binds: NOTHING MOVES; the ADR-0358 row states are
unchanged; NO vendor optimization exists for Intel. Carry-forward
to session 92: the W6 measurement half (first session at/after
2026-10-30T00:00:00Z) -- the gate for T18's analysis half, T20's
analysis half and W7's measurement half --, then the T18 analysis
half, T20's analysis half, the W7 measurement half (behind W6's
ledger line), any further counted-day slot (its own freeze), and a
cross-day tail-movement row (not queued). Evidence:
docs/evidence/gpu/anv-b3w6routepreflight-20261029/ (record.txt +
the s91 gate captures).

## Dated note (2026-10-29, JUN-59 session 92: the T18 analysis
## pre-build)
The T18 row's ANALYSIS machinery preparation half (the s69/s90
pre-build precedent applied to the s84-frozen analysis path;
NO hardware runs, NO builds, NO compiles, NO GO stamp, NO host
writes, NO day-slot consumption, NO ledger line). The analysis
half itself REMAINS day-slot-gated behind the W6 measurement half
(first session at/after 2026-10-30T00:00:00Z; this tick runs
2026-10-29T10:4xZ-11:0xZ, ~12.9h before the slot opens) --
STARTED, NOT FINISHED. analysis-t18-prego.py implements the
complete frozen T18 row -- the construction (named cell
(max,128,S=default), tw arm, 12 blocks of 3, per-block pooled-75
EXACT-INTEGER D at the closed DL vocabulary), the frozen null
(the s78 two-window run-exchangeability machinery verbatim, ONE
random.Random(2026102918), 20,000 trials per probe, probe order
DL4/DL8/DL16/DL32), the letters and the IUT joint (DL4 excluded
per the s81 section-4(c) caveat), the invalidation machinery and
the D-family (D3 band under the s83/s89 corrected [MIN,MAX]
convention). Full mode is unreachable under the pre-build name;
the T18 session adopts it as analysis-s<NN>.py. PROVENANCE
(named): the file arrived as this bot's own interrupted-run
scaffold (mtime 2026-10-29T10:40Z) and was reviewed line by line
and repaired this tick -- four real defects found by running it
(pair-table construction crash; missing s73 block-min constants +
wrong anchor-loop width; two wrong self-test fixtures), all named
in record.txt section 2. VERIFIED (real tool output): --self-test
99/0 run-twice byte-identical (fixture suite; MOCK numbers are
fixtures, never measurements); --compat 37 rows / 0 mismatched
run-twice byte-identical -- the s84 section-6 parser validity
pins recomputed over the five committed windows (390 logs) and
two-way-checked against committed publication bytes (want
PARSED, never transcribed), INCLUDING the s78 NULL REPRODUCTION:
the same frozen engine reproduces publication-s78.txt's PUBLISHED
T15 counts/p EXACTLY (INNER count 1477 p 0.073896; OUTER 11558 p
0.577921). NO T18 quantity exists or is computed. Standing gates
== the s88 pins: classify 2649/0 (17,925 bytes); scoped GPU gate
GREEN 123/12162/0/0 twice (919 bytes); FULL run-tests.cljk exit 1
RED AT BASE kotoba.form (ADR-0362, outside this diff -- touches
NO .cljk namespace) -- no green full suite claimed; settle-bar
self-test 38/0 + ledger eval twice == pins -> VERDICT: PENDING
2/4 unchanged; `find ... '*.sh'` -> 0; settle-bar-ledger.txt ==
HEAD. The bar: NO reading -> NO ledger line, NO day-slot
consumption. Rule 4 binds: NOTHING MOVES; the ADR-0358 row
states are unchanged; NO vendor optimization exists for Intel.
Carry-forward to session 93: the W6 measurement half (first
session at/after 2026-10-30T00:00:00Z) -- the gate for T18's
analysis half, T20's analysis half and W7's measurement half --,
then the T18 analysis half (this pre-build + the s84 freeze
bind), T20's analysis half (the s88 freeze binds), the W7
measurement half (behind W6's ledger line), any further
counted-day slot (its own freeze), and a cross-day tail-movement
row (not queued). Evidence:
docs/evidence/gpu/anv-b3t18prego-20261029/ (record.txt +
analysis-t18-prego.py + compat-prego-validation.txt +
t18prego-selftest.txt/.err + the s92 gate captures).

## Dated note (2026-10-29, JUN-59 session 93: the T20 analysis
## pre-build)
The T20 row's ANALYSIS machinery preparation half (the s69/s90/s92
pre-build precedent applied to the s88-frozen analysis path;
NO hardware runs, NO builds, NO compiles, NO GO stamp, NO host
writes, NO day-slot consumption, NO ledger line). The analysis
half itself REMAINS day-slot-gated behind the W6 measurement half
(first session at/after 2026-10-30T00:00:00Z; this tick runs
2026-10-29T11:2xZ-11:4xZ, ~12.4h before the slot opens) --
STARTED, NOT FINISHED. analysis-t20-prego.py implements the
complete frozen T20 row -- the construction (named cell
(max,128,S=default), tw arm, 12 blocks of 3, per-block pooled-75
EXACT-INTEGER HL_k/HR_k at the closed s86 vocabulary), the frozen
null (WITHIN-BLOCK SIDE-EXCHANGEABILITY: all 2^12 = 4,096
whole-block side-swap assignments enumerated EXACTLY, one shared
mask across the four families, NO RNG, p = count(C* >= C_obs) /
4,096 one-sided, identity included), the letters and the IUT joint
(k=4/8 excluded per the s86 section-4(c) caveat), the invalidation
machinery (incl. the s86 decomposition identity) and the D-family
(D3 band under the s83/s89 corrected [MIN,MAX] convention). Full
mode is unreachable under the pre-build name; the T20 session
adopts it as analysis-s<NN>.py. VERIFIED (real tool output):
--self-test 184/0 run-twice byte-identical (fixture suite; hand-
computable exact cases at the full 4,096 assignments -- the
identical-block fixture count 1,586 = sum_{m=0..5} C(12,m) -- plus
an independent pure-Python twin cross-checked in-loop; MOCK numbers
are fixtures, never measurements); --compat 52 rows / 0 mismatched
run-twice byte-identical -- the s88 section-6 parser validity pins
recomputed over the five committed windows (390 logs) and
two-way-checked against committed publication bytes (want PARSED,
never transcribed), INCLUDING the eight TS five-window vectors and
W5 block value vectors EXACT against publication-s87.txt and the
decomposition identity's 240 prior checks "EXACT everywhere".
NAMED, NOT HIDDEN: the exact-enumeration null has NO published
reproduction target (T19 is descriptive-only) -- no p is computed
on any real window in this pre-build. NO T20 quantity exists or is
computed. Standing gates == the s88 pins: classify 2649/0 (17,925
bytes); scoped GPU gate GREEN 123/12162/0/0 twice (919 bytes);
FULL run-tests.cljk exit 1 RED AT BASE kotoba.form (ADR-0362,
outside this diff -- touches NO .cljk namespace) -- no green full
suite claimed; settle-bar self-test 38/0 + ledger eval twice ==
pins -> VERDICT: PENDING 2/4 unchanged; `find ... '*.sh'` -> 0;
settle-bar-ledger.txt == HEAD. The bar: NO reading -> NO ledger
line, NO day-slot consumption. Rule 4 binds: NOTHING MOVES; the
ADR-0358 row states are unchanged; NO vendor optimization exists
for Intel. Carry-forward to session 94: the W6 measurement half
(first session at/after 2026-10-30T00:00:00Z) -- the gate for T18's
analysis half, T20's analysis half and W7's measurement half --,
then the T18 analysis half (the s92 pre-build + the s84 freeze
bind), the T20 analysis half (this pre-build + the s88 freeze
bind), the W7 measurement half (behind W6's ledger line), any
further counted-day slot (its own freeze), and a cross-day
tail-movement row (not queued). Evidence:
docs/evidence/gpu/anv-b3t20prego-20261029/ (record.txt +
analysis-t20-prego.py + compat-prego-validation.txt +
t20prego-selftest.txt/.err + the s93 gate captures).

## Dated note (2026-10-29, JUN-59 session 94: the W7 route/custody
## pre-flight)
The W7 measurement row's ROUTE preparation half (the per-window
precedent: s67 -> W5, s91 -> W6, this tick -> W7; NO runs, NO
builds, NO compiles, NO GO stamp, NO host writes, NO day-slot
consumption, NO ledger line). The measurement half itself REMAINS
day-slot-gated behind W6's ledger line (STARTED, NOT FINISHED):
W7's run day is UNKNOWN at this tick (W7 = the first measurement
session at/after 00:00:00Z of the first UTC day strictly after
W6's ledger-line day; W6's line does not exist -- the W6 slot
opens 2026-10-30T00:00:00Z and this tick runs ~12.0h before it).
LOCAL CUSTODY INPUTS re-verified this tick against the s51/s57-
frozen digests (tool: shasum -a 256): instrument source
a5e539f0ad1c5d73..., expected-corpus.sha256 eefba52e7be052d6...,
manifest cases-s51-a.txt c568e32ef0363165..., the 24-cell-line
digest 873025d650afae23... (reproduces the chain prefix; diff vs
cases-s36-a.txt cell lines EMPTY), corpus 16/16 LOCAL (8 OK in
anv-subgroupsize-81632-20261027/shaders + 8 OK in
anv-subgroupsize-batch64-20261027/shaders). HOST ROUTE PROBE
(read-only ssh, verbatim in the record; NO GPU submission, NO
vulkaninfo): 2026-10-29T12:02:58Z / aiueos-6600hs / murakumo-ci
nix-users render kvm / NO-WORKDIR / /usr/bin/gcc / by-path card0
renderD128, ssh_rc=0 -- route reachable, host clock sane, the s27
render-group fix holds, gcc present (no compile before GO), dri
nodes present; the W7 workdir (~/anv-b3w7daybar-<ACTUAL-RUN-DAY,
default 20261031>) is NOT YET STAGED (probed by glob because the
day component is unknown before W6's line day) -- staging is the
W7 session's own pre-GO custody step (s51/s73 precedent). NAMED
LIMITS: no host-side 3/3 or corpus 16/16 (local halves only), no
GO stamp, no build-census, no run-window, no publication, NO
STATISTICS OF ANY KIND; the s85 contingencies bind unchanged
(W6 slips -> W7's day follows W6's actual line day; W6 FLAGGED ->
W7 delivers the bar's THIRD counted reading and the remaining slot
is NEW pre-registered work; W6's line ABSENT -> s85 STANDS DOWN
and this pre-flight stands inert with it). Reading machinery stays
s90's pre-build; the W7 adoption edit is named (reading-prego.py's
single window constant W6_DIR, line 65). VERIFIED (real tool
output, byte-compared to the s88 committed pins): classify
2649/0 (17,925 bytes == pin); scoped GPU gate GREEN
123/12162/0/0 twice (919 bytes == pins); FULL run-tests.cljk exit
1 RED AT BASE kotoba.form (ADR-0362, outside this diff -- touches
NO .cljk namespace) -- no green full suite claimed; settle-bar
self-test 38/0 + ledger eval twice == pins -> VERDICT: PENDING
2/4 unchanged; `find ... '*.sh'` -> 0; settle-bar-ledger.txt ==
HEAD. The bar: NO reading -> NO ledger line, NO day-slot
consumption. Rule 4 binds: NOTHING MOVES; the ADR-0358 row
states are unchanged; NO vendor optimization exists for Intel.
Carry-forward to session 95: the W6 measurement half (first
session at/after 2026-10-30T00:00:00Z) -- the gate for T18's
analysis half, T20's analysis half and W7's measurement half --,
then the T18 analysis half (the s92 pre-build + the s84 freeze
bind), the T20 analysis half (the s93 pre-build + the s88 freeze
bind), the W7 measurement half (behind W6's ledger line; its
route/custody preparation half is this pre-flight), any further
counted-day slot (its own freeze), and a cross-day tail-movement
row (not queued). Evidence:
docs/evidence/gpu/anv-b3w7routepreflight-20261029/ (record.txt +
the s94 gate captures).

## Dated note (2026-10-29, JUN-59 session 95: the W6 run-window
## driver pre-build)
The W6 measurement row's RUN-PATH IMPLEMENTATION preparation half
(the s69/s90 pre-build precedent applied to the s80 protocol
section-2 RUN path; NO hardware runs, NO builds, NO compiles, NO
GO stamp, NO host writes, NO day-slot consumption, NO ledger
line). The measurement half itself REMAINS day-slot-gated (first
session at/after 2026-10-30T00:00:00Z; this tick runs
2026-10-29T12:1xZ-12:4xZ, ~11.5h before the slot opens) -- STARTED,
NOT FINISHED. run-window-prego.py (pure stdlib, NO RNG, no clock;
submits nothing to any GPU): --plan emits the frozen 78-run order
(c2 r1-3, k=1..12 hi block k then tw block k, c8 r1-3) with per-run
artifact names and the invocation ./anv-bb-<arm> <manifest>; --rebuild
constructs run-window.txt's 78 per-run lines + the frozen 3-line
trailer from run logs + the LIVE-FIELDS capture (rc and host-date are
live-only, quoted as input at compat time, named not hidden; every
other field re-derived from committed bytes). FAIL-CLOSED: single-
quote tail, non-uniform trailer, missing/extra runs are hard errors.
VERIFIED (real tool output): --compat over the three committed 78-run
run-window transcripts (s36/s51/W5 -- s38/s39 committed none): plan
order == committed order 78/78 all three; rebuilt bytes BYTE-EQUAL
78/78 at s36 and 81/81 (table+trailer) at s51 and W5 -- TOTAL 243
rows 0 mismatched, twice byte-identical; --self-test TOTAL 18/0
twice byte-identical (MOCK fixtures, never measurements). NAMED, NOT
HIDDEN: s36's transcript predates the s57 route freeze (session-prose
trailer); the trailer comparison covers the s57-route windows s51/W5
only. ADOPTION: the frozen route names no driver filename -- the W6
session adopts this file as its run-window driver and owns its record;
the execution path (ssh, live capture, staging, GO) stays session-
owned as at s51/s73. Standing gates == the s88 pins: classify 2649/0
(17,925 bytes); scoped GPU gate GREEN 123/12162/0/0 twice (919
bytes); FULL run-tests.cljk exit 1 RED AT BASE kotoba.form (ADR-0362,
outside this diff -- touches NO .cljk namespace) -- no green full
suite claimed; settle-bar self-test 38/0 + ledger eval twice == pins
-> VERDICT: PENDING 2/4 unchanged; find docs/evidence/gpu -name '*.sh'
-> 0; settle-bar-ledger.txt == HEAD. The bar: NO reading -> NO ledger
line, NO day-slot consumption. Rule 4 binds: NOTHING MOVES; the
ADR-0358 row states are unchanged; NO vendor optimization exists for
Intel. Carry-forward to session 96: the W6 measurement half (first
session at/after 2026-10-30T00:00:00Z) -- the gate for T18's analysis
half, T20's analysis half and W7's measurement half --, then the T18
analysis half (s92 pre-build + s84 freeze), the T20 analysis half
(s93 pre-build + s88 freeze), the W7 measurement half (behind W6's
ledger line), any further counted-day slot (its own freeze), and a
cross-day tail-movement row (not queued). Evidence:
docs/evidence/gpu/anv-b3w6runprego-20261029/ (run-window-prego.py +
runwindow-prego-selftest.txt/.err + compat-prego-validation.txt/.err +
runwindow-prego-plan.txt/.err + record.txt + the s95 gate captures).
(JUN-55, JUN-59; Linear tracking JUN-499)

## Dated note (2026-10-29, JUN-59 session 96: the W6 pre-GO custody
## checker pre-build)
The W6 measurement row's CUSTODY-PATH IMPLEMENTATION preparation
half (the s69/s90/s95 pre-build precedent applied to the s80
protocol section-2 CUSTODY surface and the settle-bar.txt section-2
FLAGGED criteria's custody/build half; NO hardware runs, NO builds,
NO compiles, NO GO stamp, NO host writes, NO network connections,
NO day-slot consumption, NO ledger line). The measurement half
itself REMAINS day-slot-gated (first session at/after
2026-10-30T00:00:00Z; this tick runs 2026-10-29T13:4xZ-14:0xZ,
~10.0h before the slot opens) -- STARTED, NOT FINISHED.
custody-prego.py (pure stdlib, NO RNG, no clock; submits nothing to
any GPU) checks the eight named custody surfaces of a window's
record text (host-verify MATCH lines + chain digests, manifest cell
chain 873025d6..., corpus census 16/16 both committed shapes, GO
ordering vs builds/runs, the four pinned compiles at the frozen knob
sets, the s51-frozen build pins BYTE-IDENTICAL, the 78-run window,
VERIFY 1872/mismatch total) and derives the frozen FLAGGED criteria
(2)(3)(4) fail-closed in frozen precedence ((1) C1 is the s90
reading pair's surface -- named scope cut); any other failing row
refuses with REFUSED-RECORD-INCONSISTENT, never a qualifying line.
VERIFIED (real tool output): --compat over the three committed 78-run
windows (s36/s51/W5) TOTAL 81 rows 0 mismatched, flags none none
none, twice byte-identical (7,716 bytes, sha256 54bd8175...);
--self-test TOTAL 42/0 twice byte-identical (2,404 bytes, sha256
1f757c19...; MOCK fixtures, never measurements). NAMED, NOT HIDDEN:
the source draft (this session's earlier interrupted segment,
13:39Z) had never run -- first execution found three defects, fixed
and named in the record (chain parameter computed but unused
[engine]; fixture row count 28 vs the engine's 27 [fixture]; the
loader assumed per-window artifact bytes where W5 committed none --
now a named canonical-copy fallback with artifact-provenance lines,
manifest absence still a hard error). ADOPTION: the W6 session
adopts this file as its custody checker (custody-s<NN>.py), re-runs
--compat in its own record and checks its fresh records BEFORE the
ledger line; W7 the same (surface window-generic per s80/s85). The
execution path (ssh, staging, GO) stays session-owned as at s51/s73.
Standing gates == the s88 pins: classify 2649/0 (17,925 bytes);
scoped GPU gate GREEN 123/12162/0/0 twice (919 bytes); FULL
run-tests.cljk exit 1 RED AT BASE kotoba.form (ADR-0362, outside
this diff -- touches NO .cljk namespace) -- no green full suite
claimed; settle-bar self-test 38/0 + ledger eval twice == pins ->
VERDICT: PENDING 2/4 unchanged; find docs/evidence/gpu -name '*.sh'
-> 0; settle-bar-ledger.txt == HEAD. The bar: NO reading -> NO
ledger line, NO day-slot consumption. Rule 4 binds: NOTHING MOVES;
the ADR-0358 row states are unchanged; NO vendor optimization exists
for Intel. Carry-forward to session 97: the W6 measurement half
(first session at/after 2026-10-30T00:00:00Z) -- the gate for T18's
analysis half, T20's analysis half and W7's measurement half --,
then the T18 analysis half (s92 pre-build + s84 freeze), the T20
analysis half (s93 pre-build + s88 freeze), the W7 measurement half
(behind W6's ledger line), any further counted-day slot (its own
freeze), and a cross-day tail-movement row (not queued). Evidence:
docs/evidence/gpu/anv-b3w6custodyrego-20261029/ (custody-prego.py +
custody-prego-selftest-run1/2.txt/.err + custody-prego-compat-run1/2
.txt/.err + record.txt + the s96 gate captures).
(JUN-55, JUN-59; Linear tracking JUN-499)

## Dated note (2026-10-29, JUN-59 session 97: the W6 ledger-line
## pre-build)
The W6 measurement row's LEDGER-PATH IMPLEMENTATION preparation half
(the s69/s90/s95/s96 pre-build precedent applied to the
settle-bar-ledger.txt line surface of the s80 protocol sections 1/5;
NO hardware runs, NO builds, NO compiles, NO GO stamp, NO host
writes, NO day-slot consumption, NO ledger line; the measurement half
REMAINS day-slot-gated -- first session at/after 2026-10-30T00:00:00Z;
this tick runs 2026-10-29T14:4xZ-15:0xZ, ~9h before the slot opens)
-- STARTED, NOT FINISHED.  ledger-prego.py (pure stdlib, NO RNG, no
clock; emits text, appends nothing) derives the one s80 section-5
ledger line (day from run-window host-date= fields, single distinct
day; class/median/min from hi block A under the frozen F3 estimator;
flag from the frozen FLAGGED join in frozen precedence c1-b >
verify-mismatch > pin-missing > custody-go) -- closing s96's named
scope cut: criterion (1) C1 is re-derived from the run logs here;
criteria (3)/(4) are the s96 custody checker's surface, explicit
inputs that REFUSE fail-closed when undecided.  VERIFIED (real tool
output): --compat over the NINE committed bar-executing windows
(5 shapes: 9/9/12/42/78 runs) TOTAL 9 rows 0 mismatched -- all nine
committed settle-bar-ledger.txt lines re-derived BYTE-EXACT from
committed run-log bytes (want parsed from the ledger, never
transcribed; day derived from run-window host-dates at 7 windows,
quoted for s38/s39 which committed no run-window.txt; pin/go quoted
inputs, named) -- twice byte-identical (3,038 bytes, sha256
818ac303...); --self-test (MOCK fixtures, never measurements) TOTAL
27/0 twice byte-identical (2,656 bytes, sha256 4d1394cf...) -- every
criterion alone, precedence at every overlap, fail-closed refusals
(undecided input, missing anchor run, two-day window, day
missing/unparseable, cell-map drift, short sample census, no
(sum,128,S=16) cell), line-grammar conformance.  Standing gates == the
s88 pins: classify 2649/0 (17,925 bytes); scoped GPU gate GREEN
123/12162/0/0 twice (919 bytes); FULL run-tests.cljk exit 1 RED AT
BASE kotoba.form (ADR-0362, outside this diff -- touches NO .cljk
namespace) -- no green full suite claimed; settle-bar self-test 38/0 +
ledger eval twice == pins -> VERDICT: PENDING 2/4 unchanged; find
docs/evidence/gpu -name '*.sh' -> 0; settle-bar-ledger.txt == HEAD.
The bar: preparation session -> NO reading -> NO ledger line, NO
day-slot consumption.  Rule 4 binds: NOTHING MOVES; NO vendor
optimization exists for Intel.  ADOPTION: the W6 session adopts this
file as ledger-s<NN>.py (name-gated --emit path emits the one line,
never appends; the append follows the standing gates -- s80 section
5) and wires the custody checker's (3)/(4) + its own C1 cross-check
into the line; W7 the same.  Carry-forward to session 98: the W6
measurement half (the s80 freeze; the W6 session adopts s90's reading
pair, s91's custody baseline, s95's run-window driver, s96's custody
checker and this emitter) -- the gate for T18's analysis half (s92 +
s84), T20's analysis half (s93 + s88) and W7's measurement half
(s85) --, then any further counted-day slot (its own freeze) and a
cross-day tail-movement row (not queued).  Evidence:
docs/evidence/gpu/anv-b3w6ledgerrego-20261029/ (ledger-prego.py +
selftest/compat run1/2 .txt/.err + record.txt + the s97 gate
captures).
(JUN-55, JUN-59; Linear tracking JUN-499)

## Dated note (2026-10-29, JUN-59 session 98: the W6 pre-GO custody
## fresh-entry pre-build)
The W6 measurement row's CUSTODY-CHECK IMPLEMENTATION preparation half
(the s69/s90/s95/s96/s97 pre-build precedent applied to the surface
the adoption contracts assumed but no code path served; NO hardware
runs, NO builds, NO GO stamp, NO host writes, NO day-slot consumption,
NO ledger line; the measurement half REMAINS day-slot-gated -- first
session at/after 2026-10-30T00:00:00Z; this tick runs
2026-10-29T15:1xZ-15:5xZ, ~8.4h before the slot) -- STARTED, NOT
FINISHED.  custody-check-prego.py (the s96 checker + this session's
extension; the s96 original committed unchanged) adds the fresh-window
entry --check <dir> <tag> <manifest> (the s96 main() served only
--self-test and the hardwired three-window --compat) and
decide_ledger_inputs -- the pin/go explicit inputs of
ledger-s<NN>.py --emit, derived from the checker's own rows alone,
ROW-BASED (a verify-mismatch flag never masks a bad pin row).
REFUSED-RECORD-INCONSISTENT -> both halves UNDECIDED, fail-closed: the
ledger emitter refuses and NO line derives from the record -- a NAMED
tightening of the s96 prose ("can only lead to a FLAGGED ledger line"):
the frozen FLAGGED list is exhaustive-four, the ledger grammar admits
no fifth token, and a false-token FLAGGED line would misattribute inside
the bar's own data; a refused record that also fired C1 loses its c1-b
line (named conservative loss; the mapping cannot see C1).  VERIFIED
(real tool output): --check over the three committed 78-run windows
exits 0 (flag none, pin=ok go=ok) at all three, twice byte-identical,
its 27 rows BYTE-EQUAL to the --compat blocks at each window and flags
EQUAL (check-vs-compat-proof.txt, twice byte-identical); --self-test
TOTAL 68/0 twice byte-identical (4,528 bytes; the s96 42-line prefix
BYTE-EQUAL to the s96 capture) incl. every mapping case and the
UNDECIDED-iff-REFUSED equivalence; --compat twice byte-identical AND
byte-identical to the s96 pin (7,716 bytes).  Standing gates == the
s88 pins: classify 2649/0 (17,925 bytes); scoped GPU gate GREEN
123/12162/0/0 twice (919 bytes); FULL run-tests.cljk exit 1 RED AT
BASE kotoba.form (ADR-0362, outside this diff -- touches NO .cljk
namespace) -- no green full suite claimed; settle-bar self-test 38/0 +
ledger eval twice == pins -> VERDICT: PENDING 2/4 unchanged; find
docs/evidence/gpu -name '*.sh' -> 0; settle-bar-ledger.txt == HEAD.
The bar: preparation session -> NO reading -> NO ledger line, NO
day-slot consumption.  Rule 4 binds: NOTHING MOVES; NO vendor
optimization exists for Intel.  ADOPTION (amended): the W6 session
adopts this copy as custody-s<NN>.py and feeds --check's ledger-pin/
ledger-go to ledger-s<NN>.py --emit verbatim (UNDECIDED -> no line);
W7 the same.  Carry-forward to session 99: the W6 measurement half
(the s80 freeze; the W6 session adopts s90's reading pair, s91's
custody baseline, s95's run-window driver, this checker and s97's
emitter) -- the gate for T18's analysis half (s92 + s84), T20's
analysis half (s93 + s88) and W7's measurement half (s85) --, then any
further counted-day slot (its own freeze) and a cross-day
tail-movement row (not queued).  Evidence:
docs/evidence/gpu/anv-b3w6custodycheckrego-20261029/ (custody-check-
prego.py + selftest/compat/check run1/2 captures + check-vs-compat-
proof.txt + record.txt + the s98 gate captures).
(JUN-55, JUN-59; Linear tracking JUN-499)

## Dated note (2026-10-29, JUN-59 session 99: the W6 adoption-chain
## reconciliation pre-build)
The W6 measurement row's CROSS-TOOL RECONCILIATION preparation half
(the s90/s95/s96/s97/s98 pre-build precedent applied to the surface
between the adopted tools -- the residual the s98 note named and left
session-owned: "the W6 session cross-checks this checker's verify-
mismatch-total row against the ledger emitter's own criterion-(2)
derivation (two parsers over the same run logs)"; NO hardware runs, NO
builds, NO compiles, NO GO stamp, NO host writes, NO day-slot
consumption, NO ledger line; the measurement half REMAINS day-slot-
gated -- first session at/after 2026-10-30T00:00:00Z; this tick runs
2026-10-29T15:4xZ-16:2xZ, ~7.6h before the slot) -- STARTED, NOT
FINISHED.  reconcile-prego.py runs the five adopted W6 tools (reading,
census twin, run-window driver, custody checker --check, ledger
emitter --compat) over the three common committed 78-run windows
(s36/s51/W5=s73) and cross-checks their overlapping derived
quantities: reading-vs-ledger median/min/class (the two published
artifacts' shared fields), reading-vs-census median/min/max (the s90
independence pair, cross-compared), the s98-named verify-mismatch
residual at the numeric level, the 78-run census four ways, the
decide_ledger_inputs flag join end-to-end, the day derivation
(host-date vs emitted), and the C1 boolean; plus --line
<publication> <ledger> <tag> for the W6-fresh pair and a fixture
--self-test.  VERIFIED (real tool output): --compat run twice
BYTE-IDENTICAL (3,591 bytes) -- STAGE 7/0, CROSS 31 rows 0
mismatched, VERDICT CONSISTENT (median/min 1142/991, 1137/988,
1131/998; census == reading at all three windows); --line on the
committed publication-s73.txt vs the s73 ledger line twice
byte-identical (469 bytes) CONSISTENT, and a MOCK negative fixture
(perturbed median) rc 1 MISMATCH detected; --self-test 17/0 twice
byte-identical (708 bytes).  One engine defect found by first
execution and named: the row comparator conflated equality with join
semantics (15 false MISMATCH on consistent data) -- fixed with
explicit per-row predicates at source before capture.  Standing
gates == the s88 pins: classify 2649/0 (17,925 bytes); scoped GPU
gate GREEN 123/12162/0/0 twice (919 bytes); FULL run-tests.cljk
exit 1 RED AT BASE kotoba.form (ADR-0362, outside this diff --
touches NO .cljk namespace) -- no green full suite claimed;
settle-bar self-test 38/0 + ledger eval twice == pins -> VERDICT:
PENDING 2/4 unchanged; find docs/evidence/gpu -name '*.sh' -> 0;
settle-bar-ledger.txt == HEAD.  The bar: preparation session -> NO
reading -> NO ledger line, NO day-slot consumption.  Rule 4 binds:
NOTHING MOVES; NO vendor optimization exists for Intel.  ADOPTION:
the W6 session adopts this file as reconcile-s<NN>.py, re-runs
--compat/--self-test in its own record and reconciles its fresh
publication against its ledger line with --line; W7 the same.
Carry-forward to session 100: the W6 measurement half (the s80
freeze; the W6 session adopts s90's reading pair, s91's custody
baseline, s95's run-window driver, s98's checker, s97's emitter and
this reconciler) -- the gate for T18's analysis half (s92 + s84),
T20's analysis half (s93 + s88) and W7's measurement half (s85) --,
then any further counted-day slot (its own freeze) and a cross-day
tail-movement row (not queued).  Evidence:
docs/evidence/gpu/anv-b3w6reconcilerego-20261029/ (reconcile-prego.py
+ compat/selftest/line/negative captures + record.txt + the s99 gate
captures).
(JUN-55, JUN-59; Linear tracking JUN-499)

## Dated note (2026-10-29, JUN-59 session 100: the W6 reading-block
## reconciliation pre-build)
The W6 measurement row's READING-SHAPE preparation half (the s90
reading w6-block extension closing the reconciliation surface s99's
--line exposed; NO hardware runs, NO builds, NO compiles, NO GO
stamp, NO host writes, NO day-slot consumption, NO ledger line; the
measurement half REMAINS day-slot-gated -- first session at/after
2026-10-30T00:00:00Z; this tick runs 2026-10-29T17:46Z-18:0xZ,
~6.2h before the slot) -- STARTED, NOT FINISHED (the fresh-window
census-check duty stays queued).  Provenance named not hidden (the
s92 precedent): the slice was drafted by an interrupted tick of
this same job (reading-s1000.py + rehearsal captures + the final
reading-s1001.py edit, never run to completion, never committed)
and completed by this continuation tick.  FINDING (verified by
real tool output): the s90 w6 block printed its five section-4
prior rows WITH class tokens, and reconcile-prego.py --line's
parse_pub_tuples treats every class-bearing "median N min..max
N..N" row as a bar tuple -- a fully consistent pair parsed 6
tuples / 5 distinct -> pub-rows-agree=False -> FALSE INCONSISTENT
at the W6 session's own reconciliation gate (demonstrated on the
W5-stand-in rehearsal pair, rehearsal-line-unfixed captures, twice
byte-identical).  The fix (reading-s1001.py / reading-
prego-fixed.py, the s98 provenance pattern; the s90 original
committed UNCHANGED): (a) prior rows in the frozen
publication-s73 section-3b row shape, want values PARSED from the
committed publication-s73.txt bytes, NO class token on a prior
row; (b) a section-6 D4-shape bar row equal to section 3's fresh
row by construction; (c) the ok-map label names its 0-based index
base; (d) the verifier-twin note corrected -- derivation-census-
prego.py is --compat-only, the fresh-window "every published
integer cross-checked" duty is a NAMED gap (queued).  VERIFIED:
reading-prego-fixed.py --compat twice byte-identical AND
byte-identical to the s90 pin (2,930 bytes) -- the edits touch w6
mode only; the fixed w6 rehearsal (W5 stand-in; every number a
FIXTURE, never a measurement) twice byte-identical (4,009 bytes),
five prior rows all reproduction EXACT: True; reconcile-prego
--line on the fixed pair twice byte-identical (469 bytes)
CONSISTENT (rows parsed 2, agree True, median/min/class MATCH) and
byte-identical to the s99 committed-pair capture -- the defect is
closed at the rehearsal level.  Standing gates == the s88 pins:
classify 2649/0 (17,925 bytes); scoped GPU gate GREEN
123/12162/0/0 twice (919 bytes); FULL run-tests.cljk exit 1 RED AT
BASE kotoba.form (ADR-0362, outside this diff -- touches NO .cljk
namespace) -- no green full suite claimed; settle-bar self-test +
ledger eval twice == pins -> VERDICT: PENDING 2/4 unchanged; find
docs/evidence/gpu -name '*.sh' -> 0; settle-bar-ledger.txt ==
HEAD.  The bar: preparation session -> NO reading -> NO ledger
line, NO day-slot consumption.  Rule 4 binds: NOTHING MOVES; NO
vendor optimization exists for Intel.  ADOPTION: the W6 session
adopts reading-prego-fixed.py as reading-s<NN>.py (superseding the
s90 copy; provenance named) with the s90 census twin, s91's
custody baseline, s95's run-window driver, s98's checker, s97's
emitter and s99's reconciler; W7 the same (the s94 W7_DIR
repoint).  Carry-forward to session 101: the W6 measurement half
(the s80 freeze) -- the gate for T18's analysis half (s92 + s84),
T20's analysis half (s93 + s88) and W7's measurement half (s85)
--; if a tick runs before the slot opens, the queued fresh-window
census-check pre-build is the honest preparation row; then any
further counted-day slot (its own freeze) and a cross-day tail-
movement row (not queued).  Evidence:
docs/evidence/gpu/anv-b3w6censuscheckrego-20261029/ (reading-
s1000.py + reading-s1001.py + reading-prego-fixed.py + the
rehearsal run captures + record.txt + the s100 gate captures).
(JUN-55, JUN-59; Linear tracking JUN-499)

## Dated note (2026-10-29, JUN-59 session 101: the W6 fresh-window
## census-check pre-build)
The W6 measurement row's FRESH-RECORD-CHECK preparation half (the
s100 named gap "the fresh-window 'every published integer
cross-checked' duty is QUEUED" now closed; NO hardware runs, NO
builds, NO compiles, NO GO stamp, NO host writes, NO day-slot
consumption, NO ledger line; the measurement half REMAINS
day-slot-gated -- first session at/after 2026-10-30T00:00:00Z;
this tick runs 2026-10-29T19:16Z-19:4xZ, ~4.5h before it) --
STARTED, NOT FINISHED.  Provenance named not hidden (the s92/s100
precedent): fresh-census-prego.py was DRAFTED by an interrupted
tick of this same job (created 19:13Z, never run to completion,
never committed) and COMPLETED by this continuation tick.
FINDING (verified by real tool output): the duty exists as
machinery -- fresh-census-prego.py --w6 re-derives EVERY published
integer of the publication body from the six windows' run logs
plus named committed want sources (parsed from committed bytes,
never transcribed) in two-way claim rows and enforces digit-SPAN
COVERAGE (every body digit run inside a claim or a NAMED
structural span), fail-closed; NO re module (split()/find
parsing), numpy estimators cross-checked in-loop against
pure-Python order statistics, NO RNG, no clock.  Thirteen defects
found by first execution (the draft had never run -- an
unreachable note-line branch, seven unregistered/over-wide
coverage spans, a delta extraction from the wrong "(", the
distinct-count/day parse, the "(NEW)" prior tag, unregistered
sec1 spans, the report written to argv[3] instead of argv[4],
two miscounted fixtures), all fixed at source and named in the
record.  VERIFIED: --self-test 51/0 twice byte-identical (7,400
bytes); --w6 rehearsal (W5 stand-in + the committed s100 rehearsal
publication; every number a FIXTURE, never a measurement) twice
byte-identical (9,240 bytes): 66 claim rows 0 mismatched, 125
body digit runs 0 UNCLAIMED, 530 dual computations 0 mismatched,
VERDICT CONSISTENT; a MOCK negative (median 1131 -> 1132 in a
scratch copy) rc 1 twice byte-identical, caught at the claim row
(sec3 median 1132 vs 1131) -> INCONSISTENT.  Standing gates == the
s88 pins: classify 2649/0 (17,925 bytes); scoped GPU gate GREEN
123/12162/0/0 twice (919 bytes); FULL run-tests.cljk exit 1 RED AT
BASE kotoba.form (ADR-0362, outside this diff -- touches NO .cljk
namespace) -- no green full suite claimed; settle-bar self-test +
ledger eval twice == pins -> VERDICT: PENDING 2/4 unchanged; find
docs/evidence/gpu -name '*.sh' -> 0; settle-bar-ledger.txt ==
HEAD.  The bar: preparation session -> NO reading -> NO ledger
line, NO day-slot consumption.  Rule 4 binds: NOTHING MOVES; NO
vendor optimization exists for Intel.  ADOPTION: the W6 session
adopts this file as fresh-census-s<NN>.py alongside
reading-prego-fixed.py (as reading-s<NN>.py), the s90 census twin,
s91's custody baseline, s95's run-window driver, s98's checker,
s97's emitter and s99's reconciler; VERDICT INCONSISTENT => no
ledger line derives from the reading; W7 the same.  Carry-forward
to session 102: the W6 measurement half (the s80 freeze) -- the
gate for T18's analysis half (s92 + s84), T20's analysis half (s93
+ s88) and W7's measurement half (s85) --; then any further
counted-day slot (its own freeze) and a cross-day tail-movement
row (not queued).  Evidence:
docs/evidence/gpu/anv-b3w6freshcensusprego-20261029/
(fresh-census-prego.py + selftest/rehearsal/negative run captures
+ record.txt + the s101 gate captures).
(JUN-55, JUN-59; Linear tracking JUN-499)

2026-10-29 session 102 (JUN-59): the W6 ADOPTION-MANIFEST PRE-BUILD
-- the adoption surface (eight prose contracts, two supersession
chains) bound to exact committed bytes: adoption-manifest.txt (7
tool slots + 4 frozen s91 custody rows, digests from committed
bytes; the cell-line chain 873025d6... re-derived by the named
construction, reproduced exactly) + adoption-check-prego.py
(fail-closed --check; pure stdlib).  Verified: --self-test 42/0
twice byte-identical (MOCK fixtures only); --check over the real
tree VERDICT CONSISTENT (matched 25, mismatched 0) twice
byte-identical -- the s100-named line-95 relation holds
mechanically; MOCK negative rc 1 twice byte-identical (row 3 named)
-> INCONSISTENT.  Three first-execution defects fixed and named
(format-arg arity; two fixture refits).  Standing gates == the s88
pins: classify 2649/0 (17,925 bytes); scoped GPU gate GREEN
123/12162/0/0 twice (919 bytes); FULL run-tests.cljk exit 1 RED AT
BASE kotoba.form (ADR-0362, outside this diff -- touches NO .cljk
namespace) -- no green full suite claimed; settle-bar self-test +
ledger eval twice == pins -> VERDICT: PENDING 2/4 unchanged; find
docs/evidence/gpu -name '*.sh' -> 0; settle-bar-ledger.txt == HEAD.
The bar: preparation session -> NO reading -> NO ledger line, NO
day-slot consumption.  Rule 4 binds: NOTHING MOVES; NO vendor
optimization exists for Intel.  Named limits: provenance is
presence-checked (no positional binding); the manifest guards
adoption mistakes, not repository compromise.  Carry-forward to
session 103: the W6 measurement half (the s80 freeze; the first
measurement session at/after 2026-10-30T00:00:00Z adopts the seven
tools manifest-checked) -- the gate for T18's analysis half (s92 +
s84), T20's analysis half (s93 + s88) and W7's measurement half
(s85) --; then any further counted-day slot (its own freeze) and a
cross-day tail-movement row (not queued).  Evidence:
docs/evidence/gpu/anv-b3w6adoptionprego-20261029/.
(JUN-55, JUN-59; Linear tracking JUN-499)

2026-10-29 session 103 (JUN-59): the W6 CUSTODY-TO-LEDGER
WIRING REHEARSAL -- the s97/s98 contracts' one hand-wired
composition (decide_ledger_inputs ledger-pin/ledger-go VERBATIM
into ledger-s<NN>.py --emit) executed on real committed window
bytes for the first time (previously MOCK-only): the three
committed 78-run windows each re-derive their committed
settle-bar-ledger.txt line BYTE-EXACT through the full
checker-to-emitter path (s36 1142/991, s51 1137/988, s73
1131/998), and the frozen precedence (pin-missing over custody-go)
and fail-closed REFUSED-INPUT-UNDECIDED refusals hold on real
bytes.  ZERO defects found.  Verified: composition run twice
BYTE-IDENTICAL (25 capture pairs, 0 differing; 31 claim rows, 0
mismatched); adoption gate CONSISTENT (matched 25, mismatched 0)
twice byte-identical; adoption copies sha256 == the manifest
ledger token (scratch, created/run/deleted).  Standing gates ==
the s88 pins: classify 2649/0 (17,925 bytes); scoped GPU gate
GREEN 123/12162/0/0 twice (919 bytes); FULL run-tests.cljk exit 1
RED AT BASE kotoba.form (ADR-0362, outside this diff -- touches
NO .cljk namespace) -- no green full suite claimed; settle-bar
self-test + ledger eval twice == pins -> VERDICT: PENDING 2/4
unchanged; find docs/evidence/gpu -name '*.sh' -> 0;
settle-bar-ledger.txt == HEAD.  The bar: preparation session ->
NO reading -> NO ledger line, NO day-slot consumption.  Rule 4
binds: NOTHING MOVES; NO vendor optimization exists for Intel.
Named limits: flag=none is the only positive flag path with
committed data (the flagged input paths replayed as explicit
--emit inputs on the s73 stand-in); driver and adoption copies
were scratch and are deleted.  Carry-forward to session 104: the
W6 measurement half (the s80 freeze; the first measurement
session at/after 2026-10-30T00:00:00Z adopts the seven tools
manifest-checked) -- the gate for T18's analysis half (s92 +
s84), T20's analysis half (s93 + s88) and W7's measurement half
(s85) --; then any further counted-day slot (its own freeze) and
a cross-day tail-movement row (not queued).  With s102+s103 no
honest pre-slot preparation row remains; a pre-slot tick should
say so rather than pad.  Evidence:
docs/evidence/gpu/anv-b3w6wiringrehearsal-20261029/.
(JUN-55, JUN-59; Linear tracking JUN-499)
