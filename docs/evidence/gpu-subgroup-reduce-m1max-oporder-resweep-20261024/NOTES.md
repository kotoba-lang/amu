# gpu-subgroup-reduce-m1max-oporder-resweep-20261024/w1024-sum-last -- the W = 1024 fast-level ratio at the LAST block (JUN-58)

Tick: amu-gpu chain (bot/amu-gpu-chain). Tracking: JUN-58 (the Apple vendor
row; Linear AWAI-41), parent JUN-55 (AWAI-35). One row of work: ONE
MEASUREMENT -- the cell the previous op-order record's Honest LEFT named
UNMEASURED ("the W = 1024 fast-regime ratio at a late block position ...
no session schedules a regime"), hunted with the same op-order instrument
(:sum LAST) on the only vendor this host has (Apple Silicon).

## What this is a check OF

The regime term at W = 1024 at the LAST dispatch block. The previous
sessions at this cell shape left the question open:

- wsweep-20261023/w1024 and resweep-20261023/w1024 (sum,max,min order):
  the fresh-process clock ramp put :max/:min (later blocks) in the fast
  regime (1.167-1.175) while :sum (first block) stayed slow (1.185) --
  regime confounded with block position;
- oporder-20261024/w1024-sum-last (max,min,sum order, 6 runs): the
  position confound was ruled out AT THE SLOW REGIME (1.185 at the last
  block) -- but the session saw no ramp at all, so the ratio at the fast
  level at ANY block position stayed UNMEASURED.

This session runs the same instrument and captures the ramp.

## What ran (real hardware, real emitted bytes)

- Driver:
  `python3 scripts/gpu-subgroup-reduce-metal-measure.py --runs 12
  --workgroup 1024 --elements 1000003 --op-order max,min,sum --out
  docs/evidence/gpu-subgroup-reduce-m1max-oporder-resweep-20261024/w1024-sum-last`
  (explicit --out; the driver's named FOOTGUN avoided; no historical
  record rewritten). Ran 2026-10-24 ~18:52 JST.
- Device: Apple M1 Max; reported simdgroup size 32 in every fresh
  process's header. n = 1000003, W = 1024.
- NAMED DEVIATION, one only: 12 fresh-process runs, not the cell
  protocol's 6. Reason, stated as design: 6-run sessions at this cell
  shape have produced zero ramp in two of three sessions; doubling the
  session's process count doubles the window the intra-session clock
  ramp can appear in and the processes it can land in. Everything else
  is the cell protocol unchanged: 20 interleaved AB/BA pairs per
  operator per run, 2 warmup submits per arm discarded, Metal GPU
  timestamps around one reduce dispatch, verified read-back. The
  statistic (ADR-0358's: median of per-run paired ratios) is
  run-count-agnostic. The first-6 subset is reported below for direct
  comparability with the 6-run cells.
- Determinism: `diff -r` of this run's shaders/ against BOTH earlier
  W = 1024 cells (oporder-20261024/w1024-sum-last/shaders,
  wsweep-20261023/w1024/shaders): BYTE-IDENTICAL (empty diff, both).
- Verified read-back: 72 verify lines (12 runs x 3 ops x 2 arms), ok=1
  on every one; :max/:min bit-identical to ref and between arms; :sum
  within 6.10e-5 (arm-vs-arm) / 3.27e-5 (vs CPU ref) -- the historical
  cells' f32 :sum low-bit movement, unchanged.

## The numbers (summary.md full tables; paired statistic = ADR-0358's)

The session RAMPED: :sum's baseline per-run medians fall 128k ->
40.5k across the twelve processes; :min's too (but with the onset
moving between runs); :max NEVER ramped (its block runs first).

Rule-1 levels (GAP-1.15, fastest first):

| op | level 1 (fastest) | level 2 | level 3 | level 4 (slowest) |
|---|---|---|---|---|
| sum | 40,500..40,750 (runs 8-12) | 52,667 (run 7) | 77,708 (run 6) | 128,229..128,396 (runs 1-5) |
| min | 40,500..41,958 (runs 9-11) | 52,854 (run 7) | 90,480 (run 6) | 127,396..128,396 (runs 1-5, 8, 12) |
| max | -- | -- | -- | 127,458..128,562 (all 12) |

Level-conditioned per-run paired ratios (the finding's table):

| op / block | level (baseline) | per-run ratios | median |
|---|---|---|---|
| sum / LAST | 4 (128k, runs 1-5) | 1.187, 1.185, 1.184, 1.186, 1.184 | **1.185** |
| sum / LAST | 3 (77.7k, run 6) | 1.177 | 1.177 |
| sum / LAST | 2 (52.7k, run 7) | 1.180 | 1.180 |
| sum / LAST | 1 (40.5k, runs 8-12) | 1.171, 1.169, 1.170, 1.169, 1.170 | **1.170** |
| min / 2nd | 4 (128k, runs 1-5, 8, 12) | 1.186, 1.187, 1.184, 1.185, 1.184, 1.185, 1.186 | 1.185 |
| min / 2nd | 1 (40.5k-42k, runs 9-11) | 1.137, 1.170, 1.169 | 1.169 |
| max / 1st | 4 (128k, all 12) | 1.183..1.186 (12) | 1.1845 |

- First-6 subset (comparability with the 6-run cells): sum 1.185,
  max 1.1845, min 1.1845 -- reproducing the 6-run op-order cell's
  1.185/1.184/1.184 and the sum-first sessions' slow-level values.
- All-12 medians (summary.md's headline row): sum 1.179, max 1.184,
  min 1.184. The :sum 1.179 is a MIXED-regime statistic (5 slow runs +
  2 transition + 5 fast); it is NOT a replacement for any
  single-regime cell median and must not be compared as one.
- Rule 2: regime-invariant slower at every operator (12/12 per-run
  ratios above 1.0 each; 36/36 pooled). The sign is stable across the
  ramp; only the magnitude moves.
- Cross-operator level identity: REFUTED (52 of 66 run pairs diverge).
  min's and sum's partitions refine max's; min and sum cross-cut. This
  record is the THIRD member of the corpus's :sum-refines-:max set --
  see the pin note below.

## FINDING

**The named gap is filled at the resweep's regime level: at the LAST
block position, the W = 1024 paired ratio at the fastest observed
rule-1 level is 1.170** (:sum, runs 8-12, 1.169..1.171), against
1.185 at the slow level for the SAME operator at the SAME block
position in the SAME session (runs 1-5). The 1.170 sits inside the
resweep's fast band 1.167-1.175 (measured at :max/:min at their
later blocks in sum-first sessions). The ratio follows the clock
level, not the dispatch block's position -- now corroborated AT the
fast level, where the previous op-order session had zero samples.

Second finding, new structural data (harness reads no clock; this is
level structure only): the ramp is BLOCK-ORDERED WITHIN a process --
in runs 8-12 :max's first block sat at the slow level while :sum's
third block was already at the fast level in the same fresh process;
in runs 8 and 12 :min's second block was still slow when :sum's third
block was fast. The ramp onset moves within the process (min captured
it in runs 9-11 only). This is the third distinct regime structure in
four sessions at this cell shape (resweep: ramp across processes with
the first-block operator never ramping "throughout"; oporder 6-run:
no ramp at all; this: intra-process onset drifting).

## NAMING TENSION, named (the "fast" word, twice)

- The claim protocol's regime naming is rule 1 (GAP-1.15 clustering of
  per-run baseline medians): this session's capture is level 1 =
  "fastest observed", 40,500..40,750 for :sum. The resweep's prose
  "fast regime" names the same level (its fast runs carried per-run
  medians 40,625). Under the operative regime definition the gap is
  filled, and the two records' "fast" words agree.
- The W = 32 pair-level analyzer's bins (analyze-oporder.py,
  unchanged: slow > 80k, middle 40k..80k, fast <= 40k) put ZERO pairs
  in the fast bin in this session too (fastest pair baseline 40,375
  :sum / 40,292 :min -- just above the 40k line; middle-bin medians
  sum 1.172 / min 1.170). If "fast" is read strictly as the analyzer's
  <= 40k pair bin, that bin's ratio at any block position remains
  UNMEASURED at this W in every session to date -- no session has
  produced one pair there. Both readings are stated; nothing is
  silently upgraded.

## The corpus pin (code touched by this record's arrival)

scripts/gpu_regime_classify.py's identity corpus self-test pins the
corpus-wide ":sum-refines-:max record set" and says so in its own
contract: "A future record entering this set fails this pin on
purpose: the corpus fact must be re-stated with its own story, never
drift silently." This record entered the set (it ran the self-test as
its gate, so the red surfaced immediately -- the finest-sum-corpus-pin
record's go-forward rule held). The pin is re-stated in this slice:
the set is THREE records (shape-2 W = 1024, the 6-run op-order cell,
this re-session), and this record's own per-record pin carries its
story (12 runs, :sum LAST refining :max's single level). Self-test
after the re-statement: 1954 assertions passed, 0 failed (corpus
54 -> 55 with this record).

## What this slice does NOT license (named so nothing is silently upgraded)

- No `:measured?` flag, no `:measured-cell` :shapes extension, no
  selection answer and no workgroup row (ADR-0355/0358) moves -- the
  summary's rule-1/2/3 text is publication machinery, not a flip.
- The all-12 mixed-regime medians (sum 1.179) are not cell medians and
  replace nothing.
- The analyzer's <= 40k pair bin stays UNMEASURED at this W (above).
- This is an op-order check record kind (its own kind, outside the
  flip contract's rows): it fills none of the nine pending
  `:simdgroup-reduce` cross-day rows (2026-10-25+) and claims nothing
  about them. Per the 2026-10-24 same-day re-session naming decision,
  this same-day session is named in record prose but NOT added to the
  flip note's basis evidence lists (it flips nothing, extends no
  shape); the flip note prose is untouched here because this record
  kind is not a flip-contract cell.
- UNMEASURED scope unchanged elsewhere: shapes beyond the two contract
  cells; every Apple device but this M1 Max; the GLSL arm (blocked on
  a wire-42 route, ADR 0371); the NVIDIA/Intel/ARM/AMD variant rows
  entirely (no hardware; fleet hosts tailnet-SSH-blocked to this
  session, verified 2026-10-24).

## Gate (real runs, this host, kbb --backend sci, route-2 classpath,
2026-10-24, run for THIS record)

1. python3 scripts/gpu_regime_classify.py --self-test
   -> exit 0. TOTAL: 1954 assertions passed, 0 failed.
      (corpus 54 -> 55 with this record; the first run at the raw
      record was RED on the identity corpus pin's stale two-member
      set -- AssertionError, exit 1 -- recorded, not hidden; the pin
      re-statement above is what turned it green.)
2. python3 scripts/gpu-subgroup-reduce-metal-measure.py --self-test
   -> exit 0. driver auto-wiring self-test: 12 assertions passed,
      0 failed.
3. Scoped GPU gate (the 8 GPU-owned test namespaces, scratch runner
   gpu_scoped_gate.cljk, not in the repo):
     kbb --backend sci --classpath "src:test:<resolved closure>" \
       /Users/junkawasaki/.hermes/profiles/amu-gpu/cache/scratch/gpu_scoped_gate.cljk
   -> exit 0. Ran 102 tests containing 9774 assertions.
      0 failures, 0 errors. (no .cljk namespace in this diff.)
4. Full suite (run-tests.cljk), same classpath substitution:
   -> exit 1. RED AT BASE, outside this diff, at namespace load on
      `kotoba.form` ("Error: Could not find namespace: kotoba.form";
      the W3 port path documented red at base in ADR 0362), verified
      live this tick. No green full suite is claimed.

## HONEST LEFT (the real remainder after this row)

- The W = 1024 ratio in the analyzer's <= 40k pair bin at any block
  position: UNMEASURED (naming tension above).
- The nine `:simdgroup-reduce` cross-day replication rows (runnable
  2026-10-25+ per their own session dates) and the shape-2 W = 512
  later-day DATA run: date-blocked today.
- SOUL.md backlog item 3 (per-vendor workgroup sweeps replacing the
  provisional rows) stays BLOCKED on hardware / the ADR-0371 provider
  route; `:arm` and `:unknown` workgroup rows remain `:measured?
  false`.
- The W3 `string-ascii-lower` residue (reading-level, unverified)
  stays open on the W3 track.

## Push state

NOT pushed: blocker-first rule in force -- kotoba-lang/amu open PR
#1553 (hermes/jun31-pe-shim-align, head `hermes/...`) verified open
this tick (gh pr list), so this commit is kept locally on
bot/amu-gpu-chain and pushes on the first tick after the blocker PR
clears. Chain PR #1455 (bot/amu-gpu-chain) stays the one open chain
PR.
