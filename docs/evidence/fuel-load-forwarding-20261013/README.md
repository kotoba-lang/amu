# Fuel-load forwarding (kaizen K1) — 13 October 2026

Status: **candidate, not adopted**. Parallel kaizen work (Claude) next to the Codex
total-C goal thread. It does not change any Codex candidate, loader, ABI or fuel rule.

## Why this pass

A sampling profile (SIGPROF, 100 µs, PC histogram inside the guest image) of all 19
round86 timer images on an M1 Max showed that the context fuel counter is the largest
cross-cutting cost. Every charge is `ldr x16,[x7,#8]; subs; b.hs; brk; str x16,[x7,#8]`,
so in a loop the counter travels through memory: store → store-to-load forward → load.
Share of samples on `[x7,#8]` loads and stores (skid included, so an upper bound):

| workload | fuel ld/st | workload | fuel ld/st |
|---|---:|---|---:|
| crc32 | 81.0% | nettle-aes | 19.4% |
| md5sum | 38.5% | picojpeg | 18.6% |
| aha-mont64 | 34.3% | nsichneu | 18.2% |
| statemate | 29.5% | matmult-int | 17.8% |
| wikisort | 21.7% | tarfind | 17.2% |
| slre | 21.6% | ud | 16.4% |

(The remaining workloads are 1–15%.) Codex's existing leaf mode keeps fuel in `x8`, but
non-leaf functions and the boundaries between them still reload the counter from memory
right after storing it.

## What the pass does

`seed/42-layout.kotoba`, prefix `flf-`, runs after every fixup and `scn-run` (all branch
displacements are final). It is a forward *available-register* analysis over the finished
AArch64 words:

* state = set of registers known to equal the published counter `[x7,#8]`;
* `str xS,[x7,#8]` sets the state to `{xS}`; `ldr xD,[x7,#8]` adds `xD`;
* any write of a register removes it (`scn-defs` must-def masks); a write of `x7`, any other
  `x7`-based store, `BLR` and every encoding `scn-defs` does not model empty the state;
* `BL` carries the caller's state (minus `x30`) to its destination; its return point starts
  empty;
* roots (empty state): the `FF-CODE` of every function that is exported or not `FK-PRIV`
  (the loader, other modules and link stubs may enter it), every `FX-FADDR` target and every
  `ADR` destination (including `adr x30` return labels). Private functions are therefore
  analysed with the meet of their real `BL`/`B` callers;
* greatest fixed point, states AND-ed in place, at most 64 forward sweeps (3 in practice).

Every reached `ldr xD,[x7,#8]` whose state is non-empty becomes `mov xD,xS`, or `nop` when
`xD` is already in the state. Nothing else changes.

### Why the observable behaviour cannot change

* Every fuel **store**, charge, trap, call and return is untouched, so the published counter
  has the same value at every instant (including asynchronous CPU/wall interruption and every
  trap edge). Only a memory read is replaced by a copy of a register proved equal to it.
* Same-size rewrite: no instruction, label, fixup, `FF-CODE`, export or literal moves. The
  KSEED header, image length and the non-code tail are identical.
* Only words reached from the roots are examined or rewritten, so data words are never
  touched. A reached `BR`, `ADRP`, `LDR (literal)` or a branch leaving the code refuses the
  whole image unchanged (none occurs in the compiler or the 39 programs).
* Stores through other base registers are assumed not to address the context; the adopted
  leaf `x8` fuel caching already relies on exactly this property.

## Evidence (local, macOS arm64)

Workspace: `/Users/junkawasaki/github/workspaces/claude/kaizen-20261013/`.

The branch was first qualified on main `a81ba220` (two-argument v7, bootstrap `c0687a55…`,
fixed point `e241b0c9…`), then on `d5596291` (one-call descriptor, bootstrap `bd57c7e2…`,
fixed point `a65eda7d…`), and finally rebased onto main `4d733753` (sequential zero scans,
bootstrap `9ce5f89a…`). The checks below were repeated after each rebase; numbers are for
the final base unless marked otherwise. `build/regen.py` in the workspace reinstalls the
fixed point and pins after a rebase.

* **Native self-build**: main bootstrap `9ce5f89a…` → G1 `c23e6dfc…` → G2 = G3
  `692b5653…` (1,750,712 bytes), now `seed/bootstrap/adopted-20261012.bin`. The main
  bootstrap is kept as `previous-main-bootstrap.bin` (pinned in the receipt as
  `fuelLoadForwardingQualification.offBootstrap`) for the OFF arm of the check.
* **Baseline identity**: the main bootstrap reproduces the committed sequential-scan golden
  (`seed/main-sequential-scan-native19.json`) for all 19 original sources.
* **39 images** (the stable corpus of `compare-priority-v7/all39-stable-v1`): candidate
  images have identical length, KSEED header and tail; every differing word is an exact fuel
  load turned into `mov`/`nop` (705 words: 276 `mov`, 429 `nop`; e.g. statemate 98,
  picojpeg 74, wikisort 45, nettle-aes 23). The count is the same before and after the
  rebase. `rewrites-39.txt` lists them per image.
* **Differential execution (39 images)**: every arity-1 export of all 39 images (173
  exports) with 11 inputs (−1, 0, 1, 2, 3, 5, 8, 17, 64, 255, 1000) = 1,903 cases. Each case
  runs with 2^31 fuel to learn its charge F, then at fuel 0..40, geometric points up to F
  and F−1, F, F+1, so exhaustion traps occur at many distinct program points, including
  the function entries and loop heads the pass rewrites; each run has a 30 s CPU / 60 s wall
  limit. Exit status, stdout and stderr (status, result, remaining fuel, trap kind, all 17
  arena counters) are compared byte for byte. On the two earlier bases all 196,730 runs were
  identical. On the final base 196,736 of 196,740 runs were identical; the other four are
  input −1 at fuel 2^31 (official depthconv ×3, sglib-combined ×1), interrupted by the
  time limit (SIGALRM) at speed-dependent points on the busy host. Re-run with 1800 s limits,
  both arms exhaust the 2^31 budget with identical exit, stdout and stderr
  (`differential-39.json`, `timeLimitInterruptions`). CPU/wall interruption is outside the
  language's fuel semantics, and the time-limited remaining fuel is not a stable observable.
* **CI-equivalent checks, all PASS locally**: source/bootstrap pins; two-generation native
  self-build to the pinned fixed point; `check-bounded-lookup`; `check-certified-scalar-calls`
  (54 exact pairs); `check-twoarg-comparisons` (480 exact pairs, previous main vs new);
  `check-sequential-scan`; `verify-preserved-integration` (preserved and `--main`: three
  generations, 34 policy refusals, smoke 42, original 19 images equal to the new golden
  `seed/main-flf-native19.json`).
* `scripts/seed/check-fuel-load-forwarding.py` (new, CI job `adopted-seed-native`) compiles
  the original 19 sources with the previous main compiler and the self-built one, proves the
  layout identity and forwarding-only word differences (353 words), and compares 4,012
  export × input × fuel pairs byte for byte.
* The original 483 qualification observations are not re-run here; the 39-image
  differential run above covers the same images with a wider fuel grid.

## Measurement

Exploratory only. Local M1 Max that was **not quiet** (load average median 82 during the
rebased run, 25 during the first), so per `AGENTS.md` these are not publishable benchmark
results; the Joseph protocol and the official driver are still required. Both arms use the
round86 timer packets: the main images (identical to the timers except the two images the
one-call change touched, slre and sglib-combined) and the candidate images are embedded at
the same offsets. Six rounds alternate the arm order; each run executes LSF×8192/4 bodies;
the metric is the child's user+system CPU time (`RUSAGE_CHILDREN`); wall time is recorded
too. Benchmark and verify fuel are identical between arms in all 228 runs.

Rebased (main `d5596291` vs candidate `a65eda7d`) — `measurement-cpu-abab-v3.jsonl`,
`measurement-cpu-abab-v3.txt`, script `abab3.py`, sampler `sigprof-sampler.h`:

| workload | cand/main CPU | rounds faster | workload | cand/main CPU | rounds faster |
|---|---:|:-:|---|---:|:-:|
| wikisort | 0.828 | 6/6 | aha-mont64 | 0.997 | 3/6 |
| slre | 0.849 | 6/6 | ud | 0.998 | 5/6 |
| statemate | 0.874 | 6/6 | edn, huffbench, tarfind | 0.998 | 3/6 |
| nettle-aes | 0.950 | 6/6 | qrduino | 1.002 | 3/6 |
| nettle-sha256 | 0.983 | 5/6 | depthconv | 1.004 | 3/6 |
| picojpeg | 0.984 | 5/6 | md5sum | 1.004 | 3/6 |
| nsichneu | 0.993 | 3/6 | crc32 | 1.007 | 1/6 |
| matmult-int | 0.994 | 5/6 | xgboost | 1.011 | 2/6 |
| sglib-combined | 0.996 | 2/6 | | | |

Geometric mean of the 19 CPU ratios: **0.970** (wall 0.968). The pre-rebase run (main
`a81ba220` vs `e241b0c9`, `measurement-cpu-abab-v2.*`) gave 0.969 with the same three
large gains (wikisort 0.818, slre 0.862, statemate 0.876). Applied naively to Codex's round
88 Kotoba/C ratio 2.946 this would be about 2.86; that product is an estimate, not a
measurement. crc32 and xgboost (+0.7%, +1.1%) are small observed slowdowns this cycle
cannot explain (crc32's forwarded loads leave its hot loop bound by the table load and the
multiply chain); they need the Joseph protocol before any claim. The final rebase onto
`4d733753` changes only picojpeg's main image; six rounds against it gave a median CPU ratio
of 0.976 with per-round values 0.875–1.037 at load average ~400, which is inconclusive
(`measurement-cpu-abab-v4-picojpeg.jsonl`). The other 18 images are unchanged from the
`d5596291` comparison above. The total-C goal remains
unmet.

## Next kaizen candidates (design, not implemented)

The profile also shows where K1 cannot reach:

* **K2 – private callee entry specialisation.** `aha-mont64` spends ~38% in `u-ge`, a
  one-line private predicate with a full non-leaf frame, called from `modul64` (counter in
  `x16`) and `montmul` (state empty after a call). The meet at the entry kills forwarding.
  A second entry after the fuel load, chosen per call site in `41-a64gen` when the caller's
  state is known, removes the load without a meet. Needs emission-time support (layout moves).
* **K3 – inlining: measured, rejected in its generic form.** An upper-bound experiment
  (`k3-experiment/`) inlined helpers at the source level (`srcinline.py`; it drops the
  callee's entry charge, so it overstates any gain) and compiled with the current main
  compiler. Auto-selected private scalar leaf helpers (`select.py`: `:i64`/`:bool`
  signature, no vectors/strings/loops, at most 40 tokens) in 13 workloads, four alternating
  rounds, child CPU time, load ~235:

  | workload | inlined/main | workload | inlined/main |
  |---|---:|---|---:|
  | aha-mont64 | **0.594** | sglib-combined | 1.060 |
  | crc32 | 0.989 | slre | 1.139 |
  | edn | 0.996 | md5sum | 1.520 |
  | ud | 1.008 | nettle-sha256 | 1.599 |
  | wikisort | 1.042 | nettle-aes | 2.396 |
  | | | picojpeg | 2.495 |
  | | | qrduino | 2.876 |
  | | | statemate | 3.330 |

  Inlining nsichneu's vector transition helpers (`t1`/`t2`/`demark2`/`put-output`) into the
  126 step functions grew the image 8× and ran 2.6× slower. The code generator is a set of
  exact call-shape recognisers (`gn-call-wrapper`, `gn-sign-wrapper`, scalar-mask, clamp,
  `qi`/`pi`/`ti`/`rp`/`rc`/`mr`/`aw`/`tb`/`tc`/`di` admits): a helper *call* such as
  statemate's `s8` becomes one `sxtb`, rotations become `extr`, threshold trees become a
  table lookup. Inlining destroys those shapes and falls back to generic lowering. A SIR- or
  source-level inliner is therefore not adopted.

  The profitable subset is **frame elision**: aha-mont64's `u-ge` already has its `u-lt`
  call machine-inlined, yet the SIR `CALL` makes prescan clear `gn-f-leaf`, so the function
  keeps a full non-leaf frame (17.7% of aha-mont64 samples are frame instructions in that
  27-instruction function). Hot framed functions that emit no `bl`/`blr` at all also cost
  frame time in matmult-int (13.3%), nettle-aes (4.9% + 2.2% + 1.6%), ud (2.4%) and edn
  (1.3%) — an estimated ~3% geometric-mean gain. It requires prescan to know which calls
  each admit will emit inline *and* every such emitter to be valid in leaf mode (several
  admits require `gn-f-leaf = 0` today); a trial emission with rollback would have to undo
  the per-function entry hooks (`trg-*`, `gn-tree-entry`, `eq-chain-entry`, `vl-entry`,
  `pf-entry`, `ve-entry`). This belongs with the owner of `41-a64gen`'s admit set.
* **K4 – non-leaf fuel register: measured, not worth implementing.** Upper-bound prototype
  (`k4-experiment/k4proto.py`, measurement only) on the K1 images of main `4d733753`: a
  backward liveness analysis turns every fuel store into `nop` when the counter is stored
  again before any reader (an unforwarded fuel load, another `x7`-based load, `bl`/`blr`/`ret`
  or an unmodelled word). Trap paths are treated as non-readers, as a real K4 would publish in
  a trap stub, so the rewrite is only valid for non-trapping runs. It removes 993 of 3,088
  reached fuel stores (statemate 476, picojpeg 254). Against K1, six alternating rounds at
  `nice 19` on a host at load ~383: geometric mean **0.999**; statemate 0.961 (5/6 rounds
  faster), md5sum **1.178** (6/6 rounds slower), every other workload within the ±10%
  round-to-round noise. The cost K1 removes — the store-to-load dependency — dominates;
  dropping the remaining publication stores buys nothing measurable, and a real K4 would need
  invasive `41-a64gen` changes. Not pursued.

Each candidate keeps the qualification rules of this repository: exact result, fuel, trap
and all arena counters on the original corpus, a native fixed point, and no percentage cutoff.
