# gpu-subgroup-reduce-m1max-oporder-fastbin-20261024/w1024-sum-last -- the W = 1024 <= 40k pair-bin hunt (JUN-58)

Tick: amu-gpu chain (bot/amu-gpu-chain). Tracking: JUN-58 (the Apple vendor
row), parent JUN-55. One row of work: ONE MEASUREMENT -- the previous
record's (oporder-resweep-20261024/w1024-sum-last) Honest LEFT named it
"the <= 40k pair-bin ratio at this W" -- the pair-level analyzer's strict
fast bin (pair baseline <= 40,000 ns) that ZERO pairs landed in at
W = 1024 in every session so far. This session hunts that bin with the
same instrument.

## What this is a check OF

The pair-level analyzer's strict bins are ABSOLUTE on the pair's baseline
gpu-ns (fast 0 < b <= 40000, middle 40000 < b <= 80000, slow b > 80000 --
scripts/gpu_regime_classify.py `in_bucket`). At W = 1024 no committed
session has put a pair in the fast bin: the resweep's 720 pairs bottomed
out at a 40,375 ns pair baseline (fastest observed rule-1 level 40,500..40,750
per-run medians). Under the analyzer's strict reading the <= 40k bin's
ratio at this W is UNMEASURED at every block position. Filling it needs
pairs whose BASELINE arm lands <= 40,000 ns -- either a faster clock level
than any observed at this W, or a dip inside the fastest level.

## What ran (real hardware, real emitted bytes)

- Driver (the same instrument as the record whose left row this fills --
  W, shape, op-order, run count all unchanged, so the pair populations are
  directly comparable):
  `python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 12
  --workgroup 1024 --elements 1000003 --op-order max,min,sum --out
  docs/evidence/gpu-subgroup-reduce-m1max-oporder-fastbin-20261024/w1024-sum-last`
  (explicit --out; the driver's named FOOTGUN avoided; no historical
  record rewritten). Ran 2026-10-24 ~19:24 JST -- the same calendar day
  as, and ~30 minutes after, the resweep session (this is a same-day
  re-session at this cell; the resweep's same-day naming decision governs:
  named in record prose, never in the flip/selection lists -- and this
  record kind is outside the flip contract's rows anyway).
- Device: Apple M1 Max; reported simdgroup size 32 in every fresh
  process's header. n = 1000003, W = 1024.
- NAMED DEVIATION, one only, inherited unchanged from the resweep: 12
  fresh-process runs, not the cell protocol's 6. Reason, stated as
  design: the intra-session clock ramp is the only route to fast-level
  pairs at all, 6-run sessions have produced zero ramp in two of three
  sessions at this cell shape, and doubling the process count doubles the
  window the ramp can appear in. The statistic (ADR-0358's: median of
  per-run paired ratios) is run-count-agnostic. The first-6 subset is
  reported below for direct comparability.
- Host condition, named: load averages 27.23 / 18.08 / 16.97 at run start
  (uptime, 2026-10-24 19:24 JST) -- busy, but nothing like the resweep
  session's load 99. The harness times Metal GPU timestamps, not host
  wall time (host submit->completion ns recorded as secondary only).
- Classpath: the driver's named route 2 (AMU_KBB_TEST_CLASSPATH) -- route
  1 (`kbb -Spath -M:test`) still fails at the tree root ("no deps.edn";
  the merge retired it). The value used is the closure recorded verbatim
  in the resweep cell's compile-log.txt (identical dependency closure,
  same tree state); this cell's own compile-log records the route again.
- Determinism: `diff -r` of this run's shaders/ against BOTH earlier
  W = 1024 cells (oporder-resweep-20261024/w1024-sum-last/shaders,
  wsweep-20261023/w1024/shaders): BYTE-IDENTICAL (empty diff, both).
- Verified read-back: 72 verify lines (12 runs x 3 ops x 2 arms), ok=1 on
  every one; :max/:min bit-identical to ref and between arms; :sum within
  6.10e-5 (arm-vs-arm) / 3.27e-5 (vs CPU ref) -- the historical cells'
  f32 :sum low-bit movement, unchanged.

## THE FINDING (real measurement, this host, this tick)

**The session never ramped.** Every one of the 720 pairs sits at the slow
plateau or slower; the <= 40k pair-bin got ZERO pairs again -- and this
session put no pair anywhere near ANY fast level (the fastest pair
baseline this session is 126,875 ns).

Rule-1 levels (GAP-1.15; baseline per-run medians): ONE level per
operator -- max 128,208..128,583 (all 12 runs), min 128,208..128,521
(all 12), sum 128,125..128,500 (all 12).

Paired statistic (ADR-0358's), the whole session at the one level:

| operator | per-run paired ratios | median |
|---|---|---|
| sum | 1.183, 1.185, 1.186, 1.185, 1.185, 1.183, 1.185, 1.185, 1.186, 1.186, 1.186, 1.185 | 1.185 |
| max | 1.185, 1.183, 1.183, 1.184, 1.184, 1.182, 1.185, 1.183, 1.185, 1.185, 1.182, 1.183 | 1.183 |
| min | 1.184, 1.184, 1.185, 1.184, 1.183, 1.182, 1.182, 1.184, 1.185, 1.185, 1.183, 1.182 | 1.184 |

First-6 subset medians: 1.185 / 1.184 / 1.184 (sum/max/min) -- the
6-run cells' statistic reproduced inside this session.

Rule 2 at this cell (the session's own single observed level): all 36
per-run ratios above 1.0 -- REGIME-INVARIANT SLOWER for the
`:subgroup-reduce` arm at the slow level.

Slow-level reproduction, named: :sum at the LAST block measures 1.185
again -- the third max,min,sum session in a row at this level (the 6-run
op-order cell: 1.185; the resweep's slow runs 1-5: 1.185; this session:
1.185). The slow-level ratio at this block position is stable across
three sessions on one day.

Pair-level section (the instrument of the question; ANALOGUE only, it
never amends rule 2 and cannot choose a variant):

| operator | level | pairs | baseline gpu-ns range | median pair ratio | sides |
|---|---|---|---|---|---|
| max | 1 (fastest observed) | 237 | 126875..151083 | 1.184 | 237/237 slower |
| max | 2 (slowest observed) | 3 | 175167..212167 | 0.773 | 0/3 slower, 3/3 faster |
| min | 1 (fastest observed) | 236 | 126917..132875 | 1.184 | 236/236 slower |
| min | 2 (slowest observed) | 4 | 203667..244625 | 0.695 | 1/4 slower, 3/4 faster |
| sum | 1 (fastest observed) | 236 | 126917..132917 | 1.185 | 236/236 slower |
| sum | 2 | 2 | 192458..198667 | 0.776 | 0/2 slower, 2/2 faster |
| sum | 3 (slowest observed) | 2 | 238083..247875 | 0.626 | 0/2 slower, 2/2 faster |

The nine pairs at 175k..248k baselines are contention stragglers in
micro-levels of 2-4 pairs; their sub-1.0 ratios are named as structural
noise and CLAIM NOTHING (the pair-level analogue is explicitly not rule
2; a 2-pair level is not a regime finding).

Pair-level cross-operator identity: REFUTED -- 2563 of 28,680 key pairs
diverge (max/min, max/sum, min/sum all cross-cut), driven by which
operator's block caught a straggler pair. The run-level identity
section says "identity holds" -- but that is DEGENERATE here (one level
per operator, nothing to disagree about) and licenses no cross-operator
pair naming. Both facts printed by the machine; the tension is named,
not resolved.

## NEW STRUCTURAL DATA (level structure only; the harness reads no clock)

Five sessions now exist at this cell shape (W = 1024, n = 1000003):

| session | date | runs | ramped? |
|---|---|---|---|
| wsweep-20261023/w1024 (sum,max,min) | 10-23 | 6 | yes (:max/:min later blocks fast) |
| resweep-20261023/w1024 (sum,max,min) | 10-23 | 6 | yes (same shape) |
| oporder-20261024/w1024-sum-last (max,min,sum) | 10-24 | 6 | no |
| oporder-resweep-20261024/w1024-sum-last (max,min,sum) | 10-24 | 12 | yes (runs 8-12) |
| THIS (oporder-fastbin-20261024, max,min,sum) | 10-24 | 12 | NO |

The fresh-process ramp is therefore NOT guaranteed even at 12 runs:
2 of 5 sessions saw none. Host load does not decide it -- the resweep
ramped at load ~99, this session stayed flat at load ~27. What governs
the ramp is UNMEASURED (the harness reads no clock).

## NAMING TENSION, extended (NOTHING silently upgraded)

The resweep named the two regime readings (rule 1's GAP-1.15 "fastest
observed level" vs the pair analyzer's strict absolute bins). This
session adds reachability evidence for the strict reading: at W = 1024
the strict fast bin (pair baseline <= 40,000) sits BELOW every fast-level
pair ever captured (resweep floor 40,375 ns over its fast-level pairs;
this session captured zero fast-level pairs). Under the strict reading
the <= 40k bin's ratio at this W stays UNMEASURED, and the accumulated
evidence says the bin may be unreachable at this W's observed levels.
Whether the strict-bin reading at this W is reachable AT ALL is a
design question for its own slice -- nothing here moves either reading,
and no fill claim is made under the strict one.

## What this slice does NOT LICENSE

- no `:measured?` flag, no `:measured-cell` :shapes, no selection
  answer, no workgroup row (ADR-0355/0358) moves;
- the <= 40k pair-bin ratio at W = 1024 remains UNMEASURED (the bin is
  empty in this session too);
- it fills none of the nine pending `:simdgroup-reduce`/`:subgroup-reduce`
  cross-day rows (2026-10-25+) and claims nothing about them; the
  shape-2 W = 512 later-day DATA run stays 2026-10-25+;
- UNMEASURED unchanged elsewhere: shapes beyond the two contract cells;
  every Apple device but this M1 Max; the GLSL arm (blocked on the
  wire-42 route, ADR 0371); the NVIDIA/Intel/ARM/AMD variant rows
  entirely.

## Gate (real runs, this host, for THIS record)

1. gpu_regime_classify.py --self-test -> exit 0, TOTAL: 2003 assertions
   passed, 0 failed. This record entered the corpus (its verdict is
   printed like every record's: "identity-holds (0 divergent pairs;
   levels max 1, min 1, sum 1)"); the corpus is now 56 multi-operator
   records -- 20 identity-holds (3 multi-level), 36 identity-refuted
   (36 with refinement structure). NO pinned set changed membership --
  this record carries no refinement edge and enters no pinned relation
   set (the :sum-refines-:max exact pin still lists exactly its three
   named records), so no pin needed re-statement; the record's facts are
   covered by the corpus-wide assertions (shared run set, tally floors).
2. gpu-subgroup-reduce-metal-measure.py --self-test -> exit 0, 12
   assertions passed, 0 failed.
3. Scoped GPU gate (8 GPU-owned namespaces, scratch runner
   gpu_scoped_gate.cljk): Ran 102 tests containing 9774 assertions.
   0 failures, 0 errors (no .cljk namespace in this diff).
4. Full run-tests.cljk: RED AT BASE at `kotoba.form` ("Could not find
   namespace: kotoba.form", the W3 port path, outside this diff),
   re-verified live this tick. No green full suite is claimed.

## HONESTY STATE

IMPLEMENTED -- nothing in code moved (this diff is evidence prose only;
the record's own arrival is asserted by the classifier self-test as
above). MEASURED -- this session's numbers: the level structure (one
slow level, 128,125..128,583), the paired ratios (1.185/1.183/1.184),
the 36/36 slower roll-up, and the slow-level third reproduction of
1.185 at :sum's last block -- all on this host, this date, this
session. UNMEASURED -- the <= 40k pair-bin ratio (the bin is empty;
this session adds zero fast-level pairs), the ramp's governing
conditions, and everything in the NOT LICENSED list. PROPOSED --
nothing new.

## HONEST LEFT

- the <= 40k pair-bin ratio at W = 1024: STILL UNMEASURED after this
  hunt session (started, not finished -- the row moves to the next
  tick, with a design sub-row now named: strict-bin reachability at
  this W);
- the nine cross-day rows and the shape-2 W = 512 later-day DATA run
  (2026-10-25+);
- SOUL.md backlog item 3 (blocked on hardware / ADR-0371; `:arm` /
  `:unknown` rows stay `:measured? false`);
- the W3 `string-ascii-lower` residue.

## NOT PUSHED

Blocker-first rule in force -- kotoba-lang/amu open PRs with `hermes/`
heads re-checked this tick (gh pr list): #1553
(hermes/jun31-pe-shim-align) is OPEN, so this commit is kept locally on
bot/amu-gpu-chain and pushes on the first tick after the blocker PR
clears. Chain PR #1455 (bot/amu-gpu-chain) stays the one open chain PR
(MERGEABLE/CLEAN at tick start).
