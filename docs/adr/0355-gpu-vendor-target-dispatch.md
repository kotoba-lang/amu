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
