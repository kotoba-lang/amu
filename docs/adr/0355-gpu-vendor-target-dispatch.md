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
