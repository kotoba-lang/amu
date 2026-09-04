# Codegen co-scientist — tournament state

The research goal is the claim contract's own sentence: *Amu native is fastest
among the enumerated implementations (rustc, Apple Clang C11, Zig, Go
c-shared, and Swift) on all six required domains, on one recorded Darwin
arm64 machine using native execution, under the named perfgate policy.* That
requires all 30 candidate/comparator/domain pairs to independently pass
`perfgate.core/qualify` — a ≥5% mean win, separated from the arms' own
spread, on a host-qualified run. Nothing weaker counts.

Iterations 1–15 of this loop ran before this file existed; their state lived
in worktrees, kotoba-mir/kotoba-native pins, and `docs/performance.md`
(iterations 9–11 are named in commit `d214e495`, 14–15 in the kernel_wide
rematch). This file is the first durable tournament state. One iteration =
one hypothesis taken to a measured verdict.

## The loop

| stage | what it means here |
|---|---|
| **Generate** | hypotheses come from measured artifacts — instruction-stream diffs against comparators, fuel accounting, gate behavior — never from intuition alone |
| **Reflect** | before compiler work, falsify cheaply: hand-patch the emitted code and measure the predicted gain on the real runner. A hypothesis that cannot survive its own hand-patched experiment does not get a compiler change |
| **Rank** | expected qualified gain × probability, grounded in the falsification number; a blocker that gates every other claim outranks any single codegen win |
| **Evolve** | a confirmed-direction hypothesis below threshold is not discarded — it is combined with the next mechanism until the summed effect clears 5% + separation, or the ceiling is proven |
| **Meta-review** | the verdict is always `perfgate.core/qualify` on a host-qualified run, recorded here and in an ADR; "not separated" is the absence of a result and is recorded as such |

The fitness function is deterministic (perfgate), never judgment. A possible
honest terminal state of this loop is a **proven ceiling**: if Amu's emitted
stream for a domain is cost-identical to LLVM's best, a strict ≥5% win on
that domain is unreachable for anyone, and recording that is a result.

## Hypothesis population

| id | hypothesis | status | evidence |
|---|---|---|---|
| H-A | the quiet gate reads a proxy (load1) with a floor above its own limit; read the intended quantity (busy-CPU fraction) directly at the same strictness | **executed — iteration 16** (ADR 0282) | fleet measurement 2026-08-29: load1 criterion 0/7 hosts ever qualified; busy-fraction criterion qualified 2 hosts outright, near-qualified 3, and rejected exactly the one host running a persistent workload |
| H-C | narrow-arithmetic gap vs Clang: Clang strength-reduces `q*(2^31-1)` to `sub‑lsl + add`, taking one multiply off the mul pipes per round; amu emits `msub` | **landed — kotoba-native #83, gated on one serial chain** | instruction diff: amu 54 instrs (6/round), clang 61 (7/round) yet clang faster; hand-patched amu code (byte-identical reconstruction, 8 substitutions): +2.46% mean, medians 6.86→6.70 ns, mins 6.85→6.68, 42 ABBA samples/arm on levi, both arms answering 1830338420. Explains ~⅓ of the ~7% clang gap |
| H-C2 | the remaining ~4.4% vs Clang on `kernel` after H-C: the mutated stream and clang's are now near-identical in shape (62 vs 61 instructions; amu-mut still loads the now-dead `0x7fffffff` constant), so the residue is scheduling/front-end shaped | open — generate from an instruction-order diff | pending; 2026-09-03 10:16 – 2026-09-04 16:41 JST: ~50 consecutive ticks refused host-busy (load1 11–83, quiet limit 7.5; last: 16:41 JST load1 31.42 / 5m 37.39 / 15m 39.53), no measurement attempted; NEXT は H-C2 のまま (full tick ledger in git history pre-trim) | H-D | `kernel_batch` loop-path remainder (~8% vs Rust diagnostic, refused `:too-noisy` in ADR 0281): body scheduling / per-iteration instruction mix | open; measurement first needs the noise fixed (H-B) or the loop lengthened | ADR 0279 measured 1.349x behind pre-#653..#660; levi 2026-08-29 read 1.08x diagnostic |
| H-B | batch-fixture noise (rsd 0.47 vs policy 0.10) is scheduler migration of a long single-call region across P/E cores; pin the timed region's QoS | open | performance.md already documents an E-core migration incident; 2026-09-03 10:00 JST falsify tick: host busy (load1 82.83), no measurement attempted |
| H-E | call-crossing values go to stack slots instead of the callee-saved registers the prologue already spends: `kernel_call` saves x19–x26 yet stores/loads all eight call results through the stack (8 STR + 11 LDR + 3 constant-mov round-trips) | **hand-falsified — iteration 20: +6.66% separated (5.19 → 4.84 ns), fuel contract intact, past clang's 5.03**. Compiler work: assign call-crossing values to the preserved tier in the scan | performance.md's conservative-path tables; iteration-20 fixture retained in `levi:~/amu-evidence/` |
| H-F | protect domains where amu already leads (kernel_wide +7% vs rustc diagnostic) with byte-accurate regressions | standing | #637–#639 pattern |
| H-Y1 | wasm32 pays a host crossing per iteration merely to CARRY a reference-typed parameter (`typed-assert-ref` prologue), and self-recursion pays it per iteration where `loop`/`recur` pays it once | **counted — iteration 51** (ADR 0285); widening the lowering is the open follow-up | 4096 element visits: self-recursion 4227 `assert-ref`, `loop`/`recur` 129; 2.032 vs 1.032 crossings/element, identical KIR-verified return values. Also a capability limit: self-recursion traps `RangeError: Maximum call stack size exceeded` between 6,128 and 12,128 iterations, `loop`/`recur` is O(1) depth. `structured-loop-body?` is already general — only `loop-helper-name?` gates it — but the prologue fuel charge must move into the loop to keep one iteration at one unit |
| H-Y2 | a pixel-domain carrier must be guest-addressable memory indexed by the guest's own load; making the existing carrier merely bigger does not reach a usable cost | **reflect stage re-run on a quiet host, iteration 52 — still `:not-separated-from-noise`, and that is the result** | on levi at load1 1.78-2.14, n=15: today's `vector-at` marginal 381.72 ns/element (separated by 4 orders of magnitude), proposed load marginal 0.0314 ns/element (gap 0.031 vs summed stdev 0.044, refused). The cost to remove is measured; the cost to add is below the floor |

## Iteration log

- **1–15** (historical, pre-file): allocator two-tier pool, proportional
  spilling, spill-at-definition, MADD/MSUB fusion, offset reassociation,
  acyclic-leaf entry fuel, CFG scheduling, zero-branch fusion, self-reentry,
  producer home coalescing, logical-seeded constants, countdown bulk fuel —
  see kotoba-native/kotoba-mir ADRs and `docs/performance.md`.
- **16 (2026-08-29, this change)**: H-A executed. ADR 0282; the multidomain
  quiet gate now measures busy-CPU fraction directly, and `--disable-engines`
  is forwarded at measure time so the claim path can exclude informative arms
  (whose own startup load structurally failed the first domain's drift check
  in every run). Verdict, same day, on levi: `quietGate` qualified for the
  first time in the project's history (busy 3–5% while load1 read 1.29–1.43 —
  the old proxy would have refused the same window), all six per-domain
  host-load checks green, `hostLoadQualified: true`, and perfgate delivered
  the first fully host-qualified 30-pair matrix:

  | domain | vs rustc | vs clang | vs zig | vs go | vs swift |
  |---|---|---|---|---|---|
  | narrow-arithmetic | −6.5% | −6.9% | **won** | **won** | −7.7% |
  | **wide-register-pressure** | **won +6.9%** | **won +10.1%** | **won** | **won** | **won** |
  | deep-spill-pressure | −4.0% | not sep. | −3.2% | **won** | **won** |
  | call-preservation | −5.0% | −5.7% | **won** | **won** | **won** |
  | branch-call-control-flow | not sep. | −4.9% | **won** | **won** | **won** |
  | loop-call-back-edge | parity | parity | **won** | **won** | **won** |

  **16 of 30 pairs qualified.** One domain — wide-register-pressure — already
  meets the claim's requirement outright: amu independently beats all five
  comparators there, perfgate-qualified. The 14 missing pairs are all rustc /
  clang / swift on latency-shaped domains, where amu is 4–8% behind and the
  needed swing is therefore 9–13%. `comparatorSetQualified` remains false and
  no claim artifact was emitted; the machinery that could emit one is now
  proven end-to-end (raw report retained beside this state).
- **17 (in progress; Reflect executed 2026-08-29)**: the transform must be
  **context-gated, and the gate is now measured, not argued.** The same
  substitution hand-patched into both kernels, 42 rotated samples per arm on
  levi, every sample agreeing with the manifest's known answers, both
  verdicts separated from noise:

  | workload | mut vs orig | clang-raw vs orig (same runner) |
  |---|---|---|
  | kernel (one dependent chain) | **+2.56%**, separated | clang +6.68% ahead |
  | kernel_wide (eight independent lanes) | **−5.06%**, separated — regression | **amu −11.45% ahead of clang's own bytes** |

  A latency-bound chain wants the multiply off the critical resource; a
  throughput-bound body pays for the extra instruction. An unconditional
  transform would trade the one domain amu already sweeps (wide, 5/5
  qualified) for a third of the narrow gap — strictly worse under the claim
  contract. The compiler change in kotoba-native therefore needs a
  discriminator (does this `msub` sit on the block's serial recurrence, or
  beside independent live chains) before it may fire; positive and negative
  fixtures are both already in the bench tree (`kernel`, `kernel_wide`).
  `clang-raw` here is Apple Clang's exact emitted bytes for the semantic-twin
  C, extracted and run through the identical raw W^X runner — the first
  same-harness comparator baseline, retained with the evidence. Remaining
  narrow-chain residue after the transform: −4.40% vs clang-raw (H-C2).

  **Implementation landed the same day** (kotoba-native #83, amu pin
  7eb40720): the Mersenne profitability decision gains a latency arm beside
  its size arm — fire also when the leaf's MSUBs form one serial dependence
  chain. The chain test is order-independent value reachability with
  occurrences named by *position*: the first draft keyed occurrences by
  instruction map and silently never fired, because two rotating destination
  registers make the same MSUB map recur verbatim every other round — found
  only because the landed-state probe was run before trusting the green
  suite. Verified through the pin: production narrow kernel 244 B / 0 MSUBs
  (was 216 B / 8), every manifest input answered; production wide kernel
  byte-identical; +2.50% on the narrow chain in a 42-sample rotation (third
  agreeing measurement). kotoba-native: 201 tests / 2,401 assertions with
  both discriminator directions asserted. amu: 1,154 tests / 8,528
  assertions, 0 failures, 0 errors, both ISAs. The closure assertion had
  been red on main since the effaba5 advance — the exact failure shape
  d214e495 documented in August — and now names 7eb40720.

- **18 (2026-08-29, landed)**: H-C2 resolved — and it was one dependency
  edge, not scheduling. The two streams' opcode sequences were *identical*
  (61 words each); the only structural difference was the quotient tail:
  amu serialized `ASR x17→x17` then read the shifted value for the sign
  correction, Clang reads the **unshifted** value so the correction runs in
  parallel with the shift (the sign bit is unchanged by an arithmetic
  shift). Hand-falsified first: **+4.20% separated**, medians landing at
  **6.41 vs 6.41 ns — parity with Clang's own bytes** through the identical
  runner; this one stage was the entire remaining narrow-chain gap.
  kotoba-native #84 (`ASR dst,x17,#s; ADD dst,dst,x17,LSR#63`, same two
  instructions, same registers); compiler output byte-identical to the
  measured mutant; the byte test that pinned the serialized tail now pins
  the parallel one and rejects the old encoding. Through the amu pin: wide
  changed bytes (its 16 quotient tails) and reads **+0.97%** (not
  separated, direction favorable — the swept domain is intact). amu suite:
  1,154 tests / 8,528 assertions, 0 failures, 0 errors.
- **19 (2026-08-29, measured)**: six-domain re-score on the iteration-18
  pin, fully host-qualified (quiet gate 3–5% busy, all six per-domain
  checks green). **18 of 30 pairs qualified**, and the loss column is
  empty: no comparator beats amu by 5% anywhere anymore.

  | domain | vs rustc | vs clang | vs zig | vs go | vs swift |
  |---|---|---|---|---|---|
  | narrow-arithmetic | **+0.5% parity** (was −6.5) | **−0.2% parity** (was −6.9) | **won** | **won** | **−0.9% parity** (was −7.7) |
  | **wide-register-pressure** | **won +7.1%** | **won +10.3%** | **won** | **won** | **won** |
  | deep-spill-pressure | −3.8% | +2.5% | −2.6% | **won** | **won** |
  | call-preservation | −2.6% | −3.4% | **won** | **won** | **won** |
  | branch-call-control-flow | +0.8% | −3.0% | **won** | **won** | **won** |
  | loop-call-back-edge | parity | parity | **won** | **won** | **won** |

  Two iterations of codegen moved narrow-arithmetic from three 6–8%
  losses to three parities. The 12 unqualified pairs are all within ±3.8%
  — inside the territory where a win requires finding something LLVM left
  on the table, domain by domain. Largest remaining deficits: deep-spill
  vs rustc (−3.8%), call-preservation vs clang (−3.4%). Raw report
  retained beside the iteration-16 evidence.
- **20 (2026-08-29, Reflect executed)**: H-E located and hand-falsified.
  The `kernel_call` emission saves five pairs of callee-saved registers and
  then uses them only as scratch for the final adds — every call-crossing
  value goes through a stack slot (8 STR + 11 LDR), and `n` is reloaded
  before each of three `mov #k; add` round-trips that are one ADD-immediate.
  A hand-written module with the byte-identical helper and fuel preamble,
  keeping the eight results in x19–x25/x0 and `n` in x27: **+6.66%
  separated** (5.19 → 4.84 ns means, 42 samples/arm), every manifest input
  and the one-fuel-per-call contract intact — and past clang's measured
  5.03 on the same domain. The compiler change is the one performance.md
  already names: call-clobber handling in the scan so call-crossing values
  can sit in the preserved tier. That is allocator-core work in
  kotoba-mir/kotoba-native, not an emission patch; it lands only with the
  conservative path's own regression corpus green and the wide/deep
  domains byte-identical.
- **21 (2026-08-29, landed)**: the preserved-tier machinery already
  existed in full — the linear scanner keeps preserved assignments alive
  across calls, moves a call-crossing call result into the preserved tier,
  and prefers preserved registers for crossing definitions. What kept
  `kernel_call` on the slot shape was the *dispatcher*: straight-line call
  functions tried the older `allocate-call-live` first, which wipes the
  whole assignment at every call, and it always succeeded. kotoba-mir #40
  sends every call function to the scanner (which carries its own
  conservative fallback) and deletes the superseded allocator (−150
  lines); kotoba-native #85 and the amu pin carry it through. Measured on
  the qualified fixture: **+8.97% separated** over the slot shape (5.21 →
  4.74 ns), 2.2% past the iteration-20 hand mutant — the scanner consumes
  a first-call result directly as the second call's argument, which the
  hand version did not — and past clang's 5.03 / rustc's 5.07 from the
  iteration-19 matrix. Every manifest input and the one-fuel-per-call
  contract intact; kernel_call shrinks 260 → 204 bytes. Suites: kotoba-mir
  79/1,261, kotoba-native 201/2,401, amu 1,154/8,526, all green — the
  slot-shape pins across three repos now pin the preserved shape, split by
  target where x86-64's documented scratch-first entry plan differs.
- **22 (2026-08-29, measured)**: six-domain re-score, fully
  host-qualified. **call-preservation flipped sign**: amu 4.79 ns against
  clang 5.05 (**+5.2%**, refused only as not-separated-from-noise) and
  rustc 5.04 (**+4.8%**, 0.2 points under the threshold). The domain
  entered the loop at −5.0/−5.7%. Score stays 18/30, but the loss ledger
  is now: deep-spill vs rustc −4.1% / vs zig −3.6%, branch-call vs clang
  −3.7%, and parities everywhere else. Amu is ahead or within noise of
  every comparator on four of six domains and sweeps wide outright.
- **23 (2026-08-29, Reflect executed)**: the deep-spill diff found where
  LLVM banks its lanes — **the SIMD register file**. rustc's kernel_deep
  emission carries 25 `fmov` and zero GPR stack spills: overflow lanes
  park in vector registers (1-instruction GPR↔SIMD moves) instead of
  memory, and the final 24-lane sum is reduced with `add.2d`. amu's
  proportional spilling already got the deficit down to 7 STR + 7 LDR;
  hand-substituting exactly those 14 instructions with `fmov d16+slot`
  parks (1:1, same length, frame ops NOPed) measured **+3.21% separated**
  (9.25 → 8.95 ns), 0.4% from rustc's 8.91, every manifest input intact.
  H-D2 filed: in kotoba-native, a leaf whose spill slots number ≤16 parks
  them in caller-saved SIMD registers instead of a stack frame —
  aarch64-only, fail-closed to the stack shape for non-leaves or larger
  frames. The vectorized reduction is noted and deliberately not taken
  (NEON codegen is a different, larger decision).
- **24 (2026-08-29, landed)**: H-D2 implemented — kotoba-native #86 parks
  an AArch64 leaf's spill slots in caller-saved SIMD registers
  (`FMOV d16+slot`), fail-closed: 1–16 slots, no call-shaped instruction
  anywhere (SIMD is caller-saved), otherwise today's stack shape. The
  parked frame zeroes, so the SP adjustment disappears with the slots;
  the new encodings join both leaf-pass safety sets so constant caching
  still fires (found by reading the pass gates before landing — a parked
  leaf outside those sets would have silently lost its constant cache).
  Verified through the amu pin on levi: narrow and wide byte-identical,
  deep 972 → 964 bytes, every manifest input intact, **+2.62% separated**
  (9.24 → 9.00 ns) — within noise of the hand mutant's 8.97.
  kotoba-native 202/2,408 with both park directions and all three
  refusals asserted; amu 1,154/8,526 both ISAs (one Rosetta trap under
  load-30 reproduced as flake: same suite green on rerun, and the
  transform is AArch64-only so x86 bytes are unchanged).
- **25 (2026-08-29, measured)**: re-score, fully host-qualified — **21 of
  30, and a second swept domain**. call-preservation qualified against
  all five comparators (vs clang **+5.4% WIN**, vs rustc **+5.8% WIN** —
  the domain entered the loop at −5.0/−5.7%). deep-spill beat clang
  outright (+6.0% WIN) and closed rustc/zig to −0.2/+0.1 parity. The
  matrix now reads: two swept domains (wide, call-preservation), one loss
  anywhere (branch-call vs clang −3.8%), and eight parities within ±1%.

  | score | 16 → 18 → 18 → **21** / 30 |
  |---|---|
  | swept domains | wide → wide + **call-preservation** |
  | worst deficit anywhere | −7.7% → **−3.8%** |

- **26 (2026-08-29, Reflect executed — hypothesis refuted)**: the visible
  structural differences on branch-call are **not** the −3.8%. clang
  if-converts to `csel` with a single epilogue; amu emits CBNZ with two
  exit blocks, one `mov` round trip, and three unfused `add #k; mov`
  pairs. A hand mutant with clang's whole structure — csel, single
  epilogue, fused adds, no round trip, 284 → 244 bytes, byte-identical
  helper and fuel preamble — measured **+0.01%, a separated null**: on a
  predicted branch the M4 charges nothing for any of it. The residue
  lives somewhere subtler (callee-side per-call cost, or call-boundary
  shape); a clang-raw same-runner probe of the branch fixture hung in
  the harness and was parked rather than chased. Filed for 27: isolate
  the callee — measure amu's `step` leaf against clang's `step_c`
  through the identical raw runner before touching anything else.
- **27 (2026-08-29, measured — the residue has no single owner)**: four
  mechanisms, four verdicts, all on the branch fixture through one
  runner. (a) The earlier probe's hang explained: an unlinked `.o`'s
  relocated `bl` disassembles as branch-to-self — extracting from the
  *linked* dylib fixes it, and **clang's exact bytes read 4.61 vs amu's
  4.92 same-runner: the gap is real**, not harness asymmetry. (b) The
  callee's serialized `mov+msub` tail swapped to the shifted form:
  **+0.26%, null** — across a call boundary the OOO window hides one
  chain stage. (c) Fuel, quantified by NOPing the preamble (diagnostic
  only, never landable): **0.80%** — the metering cost on this fixture,
  real but small. (d) With structure (iteration 26), callee, and fuel
  all accounted, ~4% remains **distributed across per-call costs with no
  single mechanism above 1%**. Branch-call demotes in the ranking: the
  remaining forensics cost more than the other eight parities.
  The eight ±1% parities need per-domain discoveries of what LLVM left
  on the table; a proven ceiling remains a possible verdict for narrow
  and loop-call, where three compilers agree within 1%. The next
  substantive mechanisms on the board are the NEON reduction for
  deep-spill (larger project, noted at iteration 23) and protecting the
  two swept domains with byte-accurate regressions.
- **28 (2026-08-29, ceiling analysis)**: the NEON reduction demotes
  without being built, because **rustc is the measured endpoint of that
  mechanism family**: its deep-spill emission already banks lanes in SIMD
  *and* reduces with `add.2d`, and it reads 9.03 against amu's 9.04.
  Building the same machinery buys parity amu already has, not the +5%
  a win requires. More broadly, three domains now show the shape the
  charter named a **proven ceiling**: on narrow-arithmetic, deep-spill
  and loop-call-back-edge, three independently developed compilers
  (amu, rustc/LLVM, Apple Clang) sit within ~1% of each other, and on
  narrow the instruction streams are isomorphic — these domains are at
  the microarchitectural floor of their shapes, and a strict ≥5% win
  there is unreachable for *any* entrant, not just amu. With branch-call's
  residue distributed (iteration 27), the honest standing of the bounded
  claim is: **21/30 qualified, two domains swept, and the rest at
  measured parity floors** — the claim's own contract (beat everyone
  everywhere by ≥5%, separated) cannot be satisfied on these six domains
  by any compiler in this comparison, amu included. The sentence the
  evidence does support: *on every measured domain amu native is at or
  above parity with rustc and Clang, ahead outright on two domains of
  six, with metering on.* Remaining loop work: keep the wins protected
  (the byte-shape tests landed with iterations 17–24 do this), and
  re-score periodically to confirm 21/30 is stable rather than a
  favorable rotation.

- **29 (2026-08-29, confirmation)**: a second fully host-qualified
  re-score on the same sealed bundle reproduces **21/30 exactly**, with
  every key margin intact: call-preservation +5.5/+5.4% over rustc/clang
  (both WIN), deep-spill +5.3% over clang (WIN), wide +7.2/+11.5% (WIN).
  The score is stable, not a favorable rotation. **This closes the
  loop's 2026-08-29 session**: fourteen iterations, five landed compiler
  changes (serial-chain Mersenne, parallel sign correction, preserved
  call crossing, SIMD spill parking, plus the busy-fraction gate that
  made any of it claimable), score 16 → 21 of 30, two swept domains,
  worst deficit −7.7% → −3.8% with its residue characterized, and three
  domains documented at their measured parity floors. Resume point for a
  future session: the ranking stands as written at iterations 27–28 —
  protection re-scores periodically; new wins require either new
  mechanisms beyond what three compilers currently know, or new domains.

- **30 (2026-09-03 09:52 JST, amu-bench cron, measurement refused)**:
  host busy (load1 53.02 / 5m 62.90 / 15m 63.15, threshold 7.5) — no
  bench/perfgate run, no numbers. No status transitions without numbers.

## Contract v3 — the two ladders (adopted 2026-08-29, owner direction)

The owner's direction: *be able to say fastest-and-safe on more
environments, and fastest across more domains — grow the contract.* The
2026-08-29 session proved the constraint that shapes how: against
unmetered native compilers, domains converge to parity floors that no
entrant can beat by the contract's ≥5%. So the claim splits into two
ladders, and neither may borrow the other's evidence.

**Ladder A — fastest among safe execution systems (the winning ladder).**
A new comparator universe: systems that execute with metering and
isolation *on* — semantic twins compiled to wasm32-wasi by rustc/zig and
run under wasmtime with fuel enabled, against amu native with its sealed
fuel. This is the universe where amu's differentiator is priced in for
everyone, and the one it can honestly sweep. The safety side becomes
contract *preconditions*, not prose: a Ladder-A claim seals only with
metering verified on for every arm, amu's provenance verification green,
and the conformance suite green at the measured pin. The sentence it can
earn: *fastest among metered execution systems on the enumerated
domains and hosts.*

**Ladder B — at-or-above parity with unmetered natives (the holding
ladder).** The existing rustc/clang/zig/go/swift universe. Expansion
grows this ladder's honest sentence (*no measured domain where amu is
behind by the threshold*), and parity floors are recorded as results,
never hidden.

**Domain expansion comes in principled waves, never cherry-picked:**
- Wave 1 (native can run today): string search (`string_search.cljc` /
  `string_index.cljc` exist), record/handle access, branch-dense state
  machines, self-recursion shapes.
- Wave 2 (unlocked by native backend features): collections, documents —
  the admission gate (`only-native-word-typed-features?`) is the
  roadmap; a domain that cannot compile yet is a backend work item, not
  a skipped row.
- Every added domain lands with manifest known answers for all
  verification inputs, both-direction perfgate adjudication, and its
  result recorded whether amu wins, ties, or loses.

**Host expansion:** (1) same-ISA multi-host on the fleet's M4 minis;
(2) **gad — a real x86_64 Linux host, 32 cores, near idle (measured
2026-08-29)** — makes an honest second-ISA target possible, which first
requires porting the four landed AArch64 wins (Mersenne chain, parallel
sign correction, SIMD parking; preserved crossing already covers x86
bodies) and building the Linux measurement path. Rosetta numbers are
never labeled x86 hardware. Feasibility measured on levi: wasmtime
47.0.3 present, zig ships wasm32 targets; homebrew rustc's wasm std is
unverified (rustup or zig twins until then).

**Priority order:** A-prototype (zig-wasm+wasmtime-fuel vs amu-native
on the existing six domains) → Wave-1 domains on both ladders →
multi-host M4 evidence → x86-64 backend catch-up and gad measurement
path → Wave-2 backend features. One iteration = one measured verdict,
as before.

- **30 (2026-08-29, Ladder A prototype — first metered-universe win)**:
  narrow-arithmetic, both systems with their shipped metering on. The
  zig semantic twin compiled to wasm32-freestanding (`-O ReleaseFast`,
  volatile call boundary against loop folding) under wasmtime 47.0.3
  with `-W fuel` — exhaustion verified to trap, checksum verified at
  every sample — against amu native with its sealed fuel:
  **amu 6.42 ns/call vs 7.95 ns/call, +18.7% separated (1.23x)**.
  Methodology: amu in-process steady state (the existing runner);
  wasmtime per-call by slope over 2M→20M in-module calls (cancels
  process, compile and instantiation costs; sample stdev 0.023 ns).
  The same domain that is a parity floor against unmetered rustc/clang
  is an 18.7% win in the universe where everyone pays for safety —
  Ladder A behaves as designed. Next: the remaining five domains as zig
  twins, a rustc→wasm32-wasi arm (needs rustup or zig-built std), and
  the Ladder-A claim contract manifest with safety preconditions.

- **31 (2026-08-29, Ladder A: first full six-domain sweep)**: the five
  remaining zig twins built, every one verified against the manifest
  known answers before timing, and measured on levi with both systems'
  shipped metering on:

  | domain | amu native+fuel | zig-wasm+wasmtime-fuel | verdict |
  |---|---:|---:|---|
  | narrow | 6.42 ns | 7.95 | +18.7% separated |
  | wide | 5.47 | 7.00 | +21.8% separated |
  | deep | 8.96 | 12.13 | +26.1% separated |
  | call | 4.73 | 18.11 | **+73.9% separated** |
  | branch | 4.90 | 18.07 | **+72.9% separated** |
  | loop-call | 140.5 | 336.6 | +58.3% separated¹ |

  **Six of six, all separated** — the metered universe sweeps on the
  first full pass, with the call-shaped domains showing wasmtime's
  per-call cost most strongly. Two measurement defects were caught by
  their own impossibility and fixed before recording: LLVM deleted the
  loop-call twin's calls by *return-value propagation without inlining*
  (0.167 ns/call, checksum still verifying on the folded loop — the
  checks-that-could-not-answer shape again), fixed with a volatile
  round trip inside the callee and the surviving `call` verified in the
  emitted wat. ¹That barrier costs the wasm arm a store+load per
  iteration that the Rust native twin's empty asm barrier does not —
  the loop-call margin is disclosed as barrier-asymmetric and is not
  claim-grade until a costless wasm barrier exists. Also still open
  before a Ladder-A claim can seal: a second comparator (rustc-wasm),
  perfgate adjudication instead of mean-and-stdev, and the Ladder-A
  manifest with safety preconditions. Methodology: amu in-process
  steady state; wasmtime per-call by slope (2M to 20M in-module calls;
  50k to 500k for loop-call), fuel exhaustion verified to trap.

- **32 (2026-08-29, Ladder A: perfgate-qualified double sweep)**: the
  second comparator landed — rustc 1.98 via rustup-minimal targeting
  wasm32-unknown-unknown, `no_std` twins with the same barrier
  conventions as the zig arm, all six verified against the manifest
  known answers — and the whole matrix went through
  `perfgate.core/qualify` with the `:measured` levi descriptor, the
  same adjudicator Ladder B uses:

  | domain | vs zig-wasm | vs rustc-wasm |
  |---|---|---|
  | kernel | +18.5% QUALIFIED | +17.7% QUALIFIED |
  | wide | +21.4% QUALIFIED | +22.8% QUALIFIED |
  | deep | +24.4% QUALIFIED | +24.7% QUALIFIED |
  | call | +73.2% QUALIFIED | +73.0% QUALIFIED |
  | branch | +72.0% QUALIFIED | +71.9% QUALIFIED |
  | loop-call | +60.3% QUALIFIED¹ | +59.9% QUALIFIED¹ |

  **12 of 12 pairs qualified** — Ladder A sweeps both comparators under
  the full gate, not the mean-and-stdev shorthand. The two wasm arms
  agree within ~2% everywhere (the cranelift path dominates), which is
  itself evidence the twins measure the runtime, not the source
  compiler. ¹The loop-call barrier asymmetry stands disclosed; even
  charging the whole barrier (~0.5 ns × 200 iterations) against the
  margin leaves roughly +40%, so the direction survives the worst-case
  accounting, but the number stays footnoted until a costless wasm
  barrier exists. Remaining before the Ladder-A claim seals: the
  manifest itself — enumerated universe (zig-wasm+wasmtime, rustc-wasm+
  wasmtime), safety preconditions (metering verified on for every arm,
  fuel-exhaustion trap demonstrated, provenance and conformance green at
  the pin), host set, and evidence freshness — in the shape the Ladder-B
  contract already has.

- **33 (2026-08-29, the Ladder-A contract seals)**:
  `bench/runtime-comparison/ladder-a-manifest.json` — the metered
  universe's claim contract in the Ladder-B shape. Its distinctive
  parts: **safety preconditions are refusal conditions** (candidate and
  comparator metering verified on, fuel-exhaustion trap demonstrated,
  provenance and conformance green, every timed sample equal to its
  known answer — a missing check refuses the claim rather than
  footnoting it), and the **barrier disclosure is contract text** (a
  domain whose margin depends on the wasm barrier asymmetry is excluded
  from the sealed sentence, which today holds back loop-call and leaves
  the sentence covering five of six domains at +17.7% to +73.2%, all
  perfgate-qualified against both enumerated systems).
  `worldFastestClaimQualified` is permanently false here as everywhere.
  The honest sentence now sealed by contract + evidence: *amu native
  with sealed fuel is fastest among the enumerated metered execution
  systems on five of six domains on the recorded host; the sixth leads
  by ~+60% but its measurement carries a disclosed asymmetry.*

- **34 (2026-08-29, Ladder A replicates on a second host)**: the same
  artifacts (wasm twins are portable; amu raw code is aarch64) and the
  same protocol on **dan** — a different Mac16,10 machine with a
  *different wasmtime* (48.0.1 against levi's 47.0.3), fuel-exhaustion
  trap re-demonstrated there, every known answer verified — and the
  matrix re-adjudicated with a dan `:measured` descriptor:
  **12 of 12 pairs perfgate-qualified again**, +16.8% to +73.0%, every
  margin within about one point of levi's. The fastest-and-safe
  sentence now holds on two recorded hosts and across a comparator
  runtime version bump. Host expansion continues per the charter: more
  M4 minis are cheap replicas; the real second ISA waits on the x86-64
  backend catch-up and the gad measurement path.

- **35 (2026-08-29, Wave 1 opens: the state-machine domain)**:
  `bench/runtime-comparison/kernel_state.kotoba` — a five-state DFA
  driven by a Lehmer stream's low two bits, 64 transitions per call.
  Every transition is a data-dependent branch tree, which no existing
  domain exercises: the six inherited domains all branch predictably.
  Known answers came from an independent nbb oracle before any arm was
  timed; amu native, the zig twin and the rust twin all agree on every
  manifest input. First measurements (levi): **amu 201.4 ns/call vs
  zig-wasm 221.7 and rustc-wasm 220.8 — perfgate-qualified +8.1% and
  +7.8%**, Ladder A's seventh domain and seventh win. Sequencing note:
  string-search was examined first and deferred — native strings live
  behind host context callbacks that the benchmark runner's minimal
  context does not provide, so that domain needs a runner extension
  before it can be timed, and a domain that cannot run yet is a work
  item, not a skipped row. Ladder B (unmetered natives) has not measured
  this domain yet; that comparison and the manifest registration are the
  next state-domain steps.

- **36 (2026-08-29, the state domain meets the unmetered natives — and
  loses)**: Ladder B on kernel_state, clang and rustc as native
  dylib-extracted raw arms through the identical runner:
  **amu 201.6 ns/call, clang 188.3 (−7.1%), rustc 181.8 (−10.9%)**,
  both separated. The mechanism is visible in the comparator bytes:
  rustc lowers the DFA's match to a **jump table** — one indirect branch
  per transition — where amu's nested if-tree pays several unpredictable
  branches each. **H-G filed**: recognize dense data-dependent selection
  trees and lower them to a table or branchless form; note the contrast
  with iteration 26, where csel was a separated null on *predicted*
  branches — on entropy branches the branchless form is exactly what
  pays. The two-ladder split earns its keep on this domain: metered
  universe +8% win, unmetered universe −7/−11% loss, both true.
  A third silent-measurement defect was also caught by known answers:
  rustc's jump table lives in `__TEXT,__const`, so a text-section-only
  raw extraction produced *deterministic wrong answers* (off by small
  state drifts, no crash); comparator extraction now takes the whole
  `__TEXT` segment with layout preserved, entry at the symbol's segment
  offset. Ladder-B scoreboard grows to 7 domains: 21 + 3 wins, 2 losses,
  9 parities of 35 pairs — the losses are the domain doing its job.

- **37 (2026-08-29, H-G hand-falsified — branchless beats the jump
  table)**: the whole 5x4 DFA packs into one 60-bit constant, three bits
  per entry, and `state' = (TABLE >> ((state*4+sym)*3)) & 7` leaves the
  loop's own back edge as the only branch. Measured three ways on the
  identical runner, every arm agreeing with the oracle:
  **branchless-C 176.3 ns — rustc's jump table 183.2 — amu's if-tree
  202.9.** No branches beats one indirect branch beats a tree of
  unpredictable ones, as predicted. So H-G's payoff is bounded: it turns
  the state domain's two losses into roughly a qualified win over clang
  (~+6%) and a parity with rustc (+3.7%, under the threshold). Two
  facts for the implementation: (a) the lowering must live in the
  compiler — **the source language currently admits no shift
  signature** (`bit-shift-right`/`unsigned-bit-shift-right` are
  subset-rejected; the MIR/native shift encodings exist), so a
  table-form fixture cannot even be written from source today; (b) the
  recognition target is a nested if-tree whose leaves are small
  constants over a dense product of two bounded discriminants — exactly
  what `kernel_state` is. Filed as the next compiler slice, fail-closed
  like the Mersenne chain test.

- **38 (2026-08-29, H-G refuted by its own soundness requirement)**: the
  176.3 ns table form of iteration 37 is **not a lawful compiler
  output** — on negative discriminants the raw index reads garbage bits
  where the if-tree's else arms have defined answers, so tree and table
  disagree outside the manifest inputs (caught in design review, before
  any landing; the falsification had only checked manifest inputs — the
  whole-domain check is now part of the method). The semantically
  equivalent branchless form maps each discriminant through
  compare+select into a dense slot — proved equal to the tree on 2,121
  cases including negatives, one conditional branch left (the back
  edge) — and it measures **217.0 ns: slower than the if-tree's 201.4**.
  The slot-mapping csets cost more than the mispredictions they remove.
  **H-G is refuted.** The lawful best remains rustc's shape — a
  range-guarded jump table (181.8) — filed as H-G′ with its payoff
  bounded: it would turn the state domain's two losses into a rustc
  parity and a below-threshold +3.4% on clang, not wins. Given that
  bound, H-G′ ranks below the x86-64 backend catch-up and the
  string-callback runner extension in the queue.

- **39 (2026-08-29, the second ISA opens — and the baseline is honest)**:
  amu's x86-64 output executed on real x86 hardware for the first time —
  **gad**, an AMD Ryzen AI MAX+ 395 running Ubuntu (32 cores; the
  benchmark runner ported with zero changes beyond its existing
  `__APPLE__` rusage-units guard), every manifest input verified. The
  first Ladder-B baseline there: **amu 17.47 ns/call vs gcc 13.3's
  14.09 — a −25.6% deficit** on the narrow kernel, with the artifact
  itself telling the story (461 bytes against AArch64's 244 for the
  same source: the serial-chain Mersenne, parallel sign correction and
  SIMD parking landed AArch64-only). The x86 catch-up queue now has a
  measured starting line instead of an assumption. Environment notes:
  gad has egress and sudo (rustc/clang installable for the full
  comparator set), gcc is a new comparator this workspace had never
  measured, and Rosetta numbers are retired from x86 claims now that
  real hardware answers.

- **40 (2026-08-29, x86 catch-up begins — the deficit halves)**: the
  emission diff on gad named two x86-specific mechanisms: **H-X1**, four
  push/pop pairs per quotient (32 stack round trips per kernel call)
  protecting RAX/RDX from `imul r10`'s implicit clobber, and **H-X2**,
  the serialized sign-correction tail — the same shape iteration 18
  fixed on AArch64. H-X2 landed first (kotoba-native #87: copy the
  unshifted value into RDX *before* SAR so SAR and SHR run in parallel;
  two lines swapped, a new byte test pins the parallel tail and rejects
  the serialized one). Measured on gad across three rotations, calm-load
  medians 17.58 → 16.15 ns: **about +8%, direction unanimous** (the
  separation heuristic stays unmet under Ryzen boost-state variance, so
  the number is reported as a consistent diagnostic, not a qualified
  claim). The gcc deficit narrows from −25.6% to ≈−13% — one ported
  transform recovered half. The amu suite flaked 6 execution tests under
  load-34 (f64 and aarch64 paths this x86-only change cannot touch) and
  was green on rerun: 1,154/8,526/0/0. **H-X1 is next** — the push/pop
  traffic is now the largest named x86 mechanism.

- **41 (2026-08-29, H-X1 part 2 lands — and is null until part 1)**:
  kotoba-native #88 adds `x86-elide-dead-quotient-saves`, a forward
  read-before-write scan deciding each of RAX/RDX's saves independently,
  refusing anything outside a closed straight-line set. Fail-closed and
  green (204/2,418 with all four directions asserted) — and **measured
  null on the kernel**: 461 → 453 bytes only, gad medians statistically
  unchanged, because the allocator itself parks the recurrence value in
  RAX, so the saves are mostly *legitimate*. The mechanism is the
  receiver; the trigger is **part 1: steer quotient-crossing values away
  from RAX/RDX in the kotoba-mir pool** — filed as the next slice.
  AArch64 emission verified byte-identical against the parent pin.
  Two repairs while landing: the parallel session's `io.github.
  kotoba-lang/json` dependency landed URL-inferred with a broken
  `.gitlibs` worktree, so `lock-classpath` failed closed and main's lock
  ships without it — this branch adds the explicit `:git/url`, refetches
  the cache entry, and regenerates a 20-dependency lock. Separately,
  **origin/main is currently red on 28 execution tests** (dag-cbor guest
  output ×6, storage transport, workerd host) — reproduced identically
  on a pristine main worktree, so it is the parallel landings' breakage,
  not this pin's; documented rather than chased, per the
  closure-assertion precedent.

- **42 (2026-08-29, H-X1 completes — real-x86 parity with gcc)**:
  part 1 landed as kotoba-mir #41/#42 — quotient-bearing **straight-line**
  leaves draw from a pool with RAX/RDX demoted to last-resort scratch,
  arming #88's dead-save elision. The straight-line guard exists because
  its absence was *measured*: the first cut steered branchy leaves too,
  and `rebuild-pool-lists` splits pools by position at label boundaries,
  which produced two new variant-sroa execution failures against the
  main baseline — caught by diffing failure sets, fixed, and the fixture
  recovered. Chain verified: kotoba-mir 80/1,263 with both steering
  directions asserted, kotoba-native 204/2,418 (the division-window byte
  test now pins the steered emission; its implicit-register invariant is
  unchanged), aarch64 byte-identical, amu suite equal to the documented
  main-red baseline plus zero. Measured on gad, calm rotations:

  | narrow x86 | median | vs gcc |
  |---|---:|---|
  | iteration 39 baseline | 17.47 | −25.6% |
  | + parallel sign correction | 16.06 | ≈−13% |
  | + steered pool & elision | **14.48** | **+0.1% — parity, ahead on mins** |

  Two iterations of ported+new work recovered the entire 25.6-point
  deficit on the first x86 domain. The x86 catch-up continues with the
  remaining domains (wide/deep spill shapes still lack SIMD parking's
  SSE analogue; call shapes untested there).

- **43 (2026-08-29, the x86 sweep finds a correctness bug)**: extending
  the real-x86 baseline to the remaining domains stopped at the known
  answers: **kernel_wide and kernel_deep return wrong results on
  x86-64** — reproduced identically on gad's AMD hardware and under
  Rosetta, while narrow stays correct. The pre-steering pin reproduces
  it with a *different* wrong value, which exonerates iteration 42's
  steering and dates the defect earlier: a miscompile in the x86
  backend's high-pressure path (both fixtures overflow the pool into
  spills; the wrong value shifting with allocation points there), which
  **no existing suite executes on x86** — the kotoba-native suite is
  encodings-only by its own docstring, and the amu execution tests never
  ran these shapes on the second ISA. Today's first real-x86 execution
  of the high-pressure fixtures is what found it. Also noted: gcc's
  call-shaped twins can't run as raw extractions from a PIC `.so`
  (PLT-routed calls); `-fno-plt` or a static build is the fix when those
  domains measure. **Next: minimal reproduction and disassembly of the
  wide x86 emission — correctness outranks every performance item in
  the queue.**

- **44 (2026-08-30, the miscompile is caught, named, and fixed)**: the
  wide/deep x86 wrong answers came apart under a lane sweep and one
  control build. Reduced fixtures (2..8 lanes) all passed at head --
  because a parallel sema advance (`8676e3d6`, map-reduce fusion) had
  changed the IR shape; restoring the old sema pin reproduced
  yesterday's broken binary **byte-identically**. Old-sema IR executed
  correctly on aarch64, so the IR was lawful and the x86 backend was
  the defect. A post-allocation instruction trace located it in
  iteration 41's dead-quotient-save scan: the rule "a later
  quotient-constant rewrites RAX/RDX before reading them" treats a
  **saved** quotient as a kill, but a saved quotient pushes the
  register before its internal clobber and pops it after -- it is
  transparent, and whether it saves is exactly what the pass itself
  decides. A lane value the allocator parked in RAX (defined at
  instruction 9, read at 39, seven quotients between) lost its save and
  was destroyed; some sites survived only because immediate-folded
  instructions carry stale register keys the scan miscounts as reads.
  Fix (kotoba-native #90, `fbe93200`): decide quotients **back to
  front** -- a later quotient that kept its save is transparent, one
  that elided it is a kill. The discriminating unit test fails on the
  old code for the named reason; wide/deep/narrow KAs pass x3 inputs
  under Rosetta; the measured narrow kernel's hot function is
  **byte-identical**, so iteration 42's gcc parity stands unre-measured.
  deep keeps 39 more save bytes (1843 -> 1882) -- the price of being
  right. **The barrier disclosure holds: yesterday's x86 wide/deep
  baselines were never recorded as wins, and the sweep that found this
  is the reason the ladder demands execution on every ISA it names.**

- **45 (2026-08-30, the first correct x86 six-domain baseline)**: with the
  transparency fix landed, all six domains pass every known answer on
  real AMD hardware -- 18/18 for the amu arms, and 36/36 including the
  gcc arms once the call-shaped twins were rebuilt with
  `-fvisibility=hidden -fno-plt` (the PLT-routed calls that refused the
  raw extraction now compile to direct relative calls; the one PLT call
  left lives in `__do_global_dtors_aux`, outside every measured path).
  ABBA x10 per domain, KA asserted on every timed sample, plain
  per-call nanoseconds (elapsed/calls -- not the two-count slope the
  narrow parity measurement used, so compare ratios, not absolute
  numbers), load 0.82/32: narrow 1.042 (parity within spread), wide
  **0.972** (the one domain amu leads), deep **1.38**, call 1.094,
  call_branch 1.117, loop_call **1.82**. The ranking writes itself:
  deep pays for the 39 restored save bytes (78 stack operations of
  correctness the elision may not touch -- the lawful remedy is keeping
  lane values out of RAX/RDX entirely, or saving to a scratch register
  instead of the stack), and loop_call measures the absence of the
  preserved-tier call crossing that AArch64 has had since iteration 38.
  Those are the two levers; wide's lead says the high-pressure
  straight-line story is already sound.

- **46 (2026-08-30, the second miscompile: the reciprocal cache held a
  set where r10 holds one value)**: a three-quotient fixture
  (`quot n 7`, `quot (+ n 1) 9`, `quot (+ n 2) 7`) returned 61 where
  the answer is 78 -- `x86-hoist-repeated-reciprocal` recorded every
  divisor it had ever loaded as "cached", but r10 is a single register,
  so after the 9-magic displaced the 7-magic the third quotient
  multiplied by the wrong reciprocal. Fixed in kotoba-native #92
  (85f8c07e): the pass now tracks exactly one current divisor, resets
  to nil on any encoding outside the safe set and on magicless
  divisors, and the safe set gained the fixed-RSP spill moves -- which
  is also what removed kernel_deep's 24 movabs reloads. Suite green,
  KAs pass on all six domains. Same lesson as iteration 44: the sweep
  that found it was hand-run adversarial input selection, not the
  perfgate.

- **47 (2026-08-30, the multiply-port hypothesis is refuted)**: implemented
  the shifted-Mersenne second multiply on x86 (`imul $(2^k-1)` ->
  `mov+shl+sub` when the registers are distinct -- the byte-level twin
  of the AArch64 `SUB Xd,Xn,Xn,LSL#k` form, whole-domain by wraparound
  algebra, suite and every KA green). **Measured effect on deep: none**
  (ratio 1.387 vs 1.39; narrow and wide moved only within a noisy run's
  spread, rsd 0.12-0.17), and the form costs three bytes per site. Not
  landed -- the branch exists for the record
  (kotoba-native agent/x86-mersenne-multiply, local only). Two levers
  are now in (iteration 46's reload elimination, this one) and deep's
  ratio has not moved through either, which also retires the
  decode-bound story. What remains structurally different is the
  save traffic (53 push + 53 pop against gcc's zero) and the total
  instruction count. Next: stop guessing -- gad has sudo and perf;
  read uops, cycles and stall causes off the hardware for both deep
  arms, then pick the lever the counters name. Note for the metering
  record: this run's absolute per-call numbers halved on both arms
  against iteration 45 (14.0 vs 28.6 ns for the same gcc narrow arm) --
  cross-run absolutes on gad are not comparable; only within-run ABBA
  ratios carry.

- **48 (2026-08-30, the counters name the wall and the lever lands)**:
  `perf stat` on gad answered what two null levers could not: deep's
  amu arm retires at IPC 5.74 on Zen -- the retire-width ceiling -- so
  the domain is bound by pure instruction count (500/call vs gcc's
  337), not decode, not ports, not the save traffic's latency.
  The count lever: `x86-quotient-steered-pool` in kotoba-mir now
  excludes RAX/RDX entirely (kotoba-mir #42, 3f88f71b), so leaf
  straight-line quotient lanes never park values in the registers the
  division idiom clobbers, and the push/pop save pairs vanish instead
  of being elided after the fact. Measured on gad, ABBA x12, KA
  asserted on every timed sample, rsd 0.066: deep **500 -> 407
  instructions/call, ratio 1.387 -> 1.2325** -- an 11% move, clear of
  the 5% bar and of the spread. [Iteration 49 caveat: the 1.387 came from
  iteration 47's run and the 1.2325 from this one -- a cross-RUN ratio
  comparison, which 49's metrology finding shows can drift by 10+ points
  day over day. The count evidence (500 -> 407) stands; the time delta
  should be read as directional, not as a calibrated 11%.] Wide holds 0.9664; narrow is
  byte-identical. Landed through the full chain: kotoba-native #93
  (3dab370e, suite 217/2464) and amu #703 (5a2d188e, closure + lock,
  suite at baseline with the same 17 pre-existing red names), west
  pins advanced. The residue is named: 407/337 = 1.21 remaining count
  ratio -- one redundant mov per quotient expansion (amu spends 3
  moves per lane where gcc's 12-insn idiom spends 2, fusing the
  high-add via `lea (rdx,rcx)`), plus spill round trips that pulled
  IPC down to 5.02 on the new arm. Both are count levers; the next
  iteration starts there.

- **49 (2026-08-30, the redundant move falls, and the metrology tightens)**:
  two count levers in `x86-quotient-constant` (kotoba-native #95,
  3162d868), both at the residue iteration 48 named. First: a numerator
  outside RAX/RDX survives `imul r10`, so the add-numerator correction is
  one `lea r11,[rdx+left]` -- gcc's own fusion -- and the staging
  `mov r11,left` disappears (the subtract correction reads `left`
  directly). Second: the `mov rdx,r11` feeding the sign correction is
  needed only on the add branch -- the subtract branch computes IN rdx
  and the plain branch copies FROM rdx, so on those paths the copy was a
  round trip of the same value. Correctness: suite 218/2476 with a
  both-directions discriminator; KA 72/72 on gad (six domains, six
  inputs, both arms); a new 5-point negative-numerator fixture matches
  the JVM `quot` oracle across all three magic branches (the bench
  runner rejects negative n, so the fixture computes `(- 0 n)` inside
  the kernel). Count: deep **407 -> 379.2 instructions/call** (hardware
  counter), **-48 bytes**. Time: same-run ABBA vs the iteration-48
  binaries -- deep **-4.5%** (x16, rsd 0.051, clock-ramped), narrow
  -0.9%, wide -1.7% -- directional and consistent, but under the 5% bar,
  so this lands as a count lever and **no speed claim advances**.
  The metrology finding is the bigger result: today the *iteration-48*
  deep binary measured **1.365 vs gcc** in-run (rsd 0.054) where
  iteration 48's run had said 1.2325 -- byte-similar binaries, ten
  points apart, both runs internally clean. **Within-run A/B ratios are
  only comparable inside one run; day-over-day, even ratios drift.** A
  lever's verdict must come from a same-run candidate-vs-candidate A/B;
  vs-gcc ratios are standings for that day's table, not calibrated
  constants. (Also for the record: this iteration began by finding the
  workstation's root volume at 0 bytes free -- every shell command
  failed until another session freed space -- and the m2 cache had to be
  re-fetched; neither affected any measurement, which all ran on gad.)

- **50 (2026-08-30, the call crossing arrives on x86 -- measured, not
  assumed)**: kotoba-mir #43 (3aea0ac, landed upstream by a parallel
  session) gives x86 a deliberately narrow slice of the preserved-tier
  direct reentry AArch64 has had since iteration 38: parameters of a
  self-tail function with no runtime/capability callback are admitted to
  the preserved tier and the recur edge stays inside one frame. The pin
  advance had merged into kotoba-native main underneath iteration 49's
  emission change without either session running the combined suite --
  this iteration closed that hole first (218/2477 green on the merged
  tip). Emitted shape: kernel_loop_call's worker now parks its
  parameters in RBX/R12, sets the frame up once, and the binary is 58
  bytes smaller; results AND per-iteration fuel (n+2) match the manifest
  on both the old and new binaries, on Rosetta and on gad. The lever,
  measured the way iteration 49's metrology rule demands (same-run
  candidate-vs-candidate ABBA x16, KA on every sample, clock-ramped):
  **new/old 0.8743 -- a 12.6% move, rsd 0.0061/0.055 -- clear of the 5%
  bar and far clear of the spread.** Day standings vs gcc: 1.4885
  (from 1.82 on iteration 45's table; that leg ran with rsd 0.30 as the
  box loaded up, so it is a standings indication, not a calibrated
  ratio). Landed: west kotoba-mir pin advanced to 3aea0ac; the
  kotoba-native and amu tips already carried it. loop_call remains the
  widest x86 gap on the table -- the residue is now the per-iteration
  guest-call ABI around the body call, not the crossing.
- **51 (2026-08-30, a seventh domain is opened, and its carrier is gated
  on crossings rather than capacity)**: new research line, stated as its own
  goal because the existing one is six arithmetic kernels against five
  comparators: *a pixel-domain workload executes with no JVM at run time, at a
  per-element cost within a stated factor of C at `-O3`, with every element the
  guest touches reached by its own load or store rather than by a call or an
  intrinsic.* Generated from two measured artifacts, not intuition: ADR 0284's
  per-element cost, and the utsushi attribution (`bench/decode-cost-attribution`,
  merge 42bd12d). ADR 0285.
  **Counted first, because a count does not drift with load and this
  workstation ran at load1 12-700.** Wrapping every `kotoba:typed` import
  (`bench/bulk-carrier/crossings.cljs`) over 4096 element visits: a wasm32 loop
  that merely **carries** a `:vector-i64` and never reads it pays **1.032 host
  crossings per element** -- `kotoba.wasm.core` emits a `typed-assert-ref`
  prologue per reference-typed parameter, so a recursive function re-proves the
  type of an externref its own caller already asserted. Reading one element adds
  a second: **2.032**. The same three arms rewritten with `loop`/`recur` instead
  of self-recursion read **1.032 / 0.016 / 0** -- `assert-ref` 4227 -> 129,
  because `structured-loop?` requires `loop-helper-name?` and only a frontend
  loop helper becomes a real wasm loop. **Both spellings are admitted guest
  grammar, both KIR-verified to return identical values, and nothing tells the
  author that one costs twice as much.** That is a counted 2x available today
  with no compiler change, and by this loop's own tiebreak it outranks the
  carrier.
  **Reflect, and the verdict is null.** Before any compiler work the proposed
  `slice-at` was hand-encoded as a wasm module (`gen_slice_wasm.cljs`): two arms
  of byte-identical loop shape, one summing `i`, one summing an
  unsigned-bounds-tested `i64.load`, the control returning 129024 and the load
  arm 133120 -- the values `kotoba.kir/execute` gives for the Kotoba arms, which
  is how we know it is the same loop computing the same function. At load1
  506-554, n=21: 1.576 vs 1.872 ns/element, gap 0.296 against summed stdev
  0.489. **`:not-separated-from-noise`, plus `:too-noisy` on both arms.** Under
  this loop's rules that is the absence of a result, and no compiler change
  follows it. It needs a quiet window; per ADR 0281 no fleet host reaches one.
  Diagnostic timings that did qualify, load1 12-23, n=9: wasm `vector-at`
  1033.53 ns/element (2720x C `-O3`), carry-only 488.22 (1285x), the identical
  loop with no vector 6.72 (17.7x, itself refused `:too-noisy` at rsd 0.116
  despite a gap 55x its summed stdev). In C over the loader's own arena layout,
  the `checked_vector_at` body **inlined** costs 0.727 ns against 0.380 plain
  and 1.617 through a pointer -- inlining qualified at 55.1%, the bounds check
  and arena indirection at 47.7%. Our indirect arm is same-TU through a
  `volatile` pointer and reads 1.617 where ADR 0284 read 4.547, so it
  understates the call and the inlining figure is conservative.
  Timed at load1 ~490, n=7, the `loop`/`recur` fixture reads 1608 / 22.9 / 1.2
  ns/element against the self-recursion fixture's 3150 / 1477 / 17.0 at load1
  394-613 -- not divisible across runs, but directionally matching the counts on
  the two arms the counts govern, and exposing a third effect they do not: both
  `noref` arms make zero crossings, so the ~14x between them is a chain of wasm
  calls against a real wasm loop.
  
  **The design conclusion is that capacity is the wrong gate.** ADR 0284's
  middle row and the utsushi attribution meet from opposite sides: the native
  loop *alone* is 11.2x C, the wasm loop alone 17.7x, and with an unlimited
  `vector-i64` a per-macroblock residual addition is still 1.9x worse than host
  arrays -- 1.0x, bare parity, even with the call removed entirely. So
  frame-scale pixel data in the guest is refused by measurement, the
  230,400-sample derivation belongs to an architecture that refusal rejects, and
  the capacity is derived instead from the largest per-block working set
  (deblocking window (16+8)^2 = 576, MC reference patch (16+5)^2 = 441; bound
  4096). **4096 < 16384, so authorization to raise the ceilings was given and is
  not needed** -- loader image, verifier limits and pinned identity SHA all stay
  put, which is the cheapest available way not to repeat ADR 0284's
  co-movement defect. The carrier is designed and measured, **not implemented**:
  landing a subset would be a gate admitting what nothing can lower.

- **52 (2026-08-30, a quiet host corrects iteration 51, and the loop turns out
  not to be the wall)**: iteration 51's timings were taken on this workstation
  at load1 12-700 and one of them was wrong in a way that changed a conclusion.
  Re-measured on **levi** (`Mac16,10`, M4) at **load1 1.78-2.14**, arms
  interleaved in one process, per-arm outer counts sized so every sample
  integrates >=3 ms of CPU, explicit warmup for every arm before any sampling,
  values checked against `kotoba.kir/execute` first, n=15.
  **The correction.** Iteration 51 read the wasm loop alone at 17.7x C and
  concluded that removing the crossing was "necessary and not sufficient". That
  17.7x was the **self-recursion spelling on a loaded host**, not a property of
  the backend. On a quiet host the same loop written `loop`/`recur` costs
  **0.2371 ns/element** (rsd 0.010) against the C `-O3` arm's 0.2390 -- about one
  cycle per element. For wasm32 the loop is not the wall; the carrier is nearly
  all of it. ADR 0284's 11.2x is a **native** number and stands, so the two
  backends differ here and iteration 51 generalised one to the other.
  **Do not read 0.99x as parity**: the C arm carries a compiler barrier on its
  accumulator (without it clang folds the loop to 0.0013 ns) and the wasm arm has
  no equivalent, so C is serialised on a dependency chain wasm may not be. The
  claims that need no cross-language comparison are the qualified ones:
  `loop`/`recur` over self-recursion, **48.6%** on the touch arm, **98.4%** on
  carry-only, **95.3%** on the loop arm, `reasons []` on all three; plus C
  inlined over indirect 54.3% and C plain over inlined 51.6%.
  **The two numbers the carrier design rests on**, same run: today's `vector-at`
  in its best spelling has a marginal cost of **381.72 ns/element** (387.43 -
  5.70), separated from noise by four orders of magnitude; the proposed
  bounds-tested `i64.load` has a marginal cost of **0.0314 ns/element** and
  perfgate **refuses** it, `:not-separated-from-noise`, gap 0.031 against summed
  stdev 0.044 -- both arms individually clean (rsd 0.050, 0.057), simply closer
  together than their own spread. That refusal is the result: the design does not
  need a ratio between those two, it needs the fact that one costs 381.72 ns and
  is comfortably separated while the other cannot be told apart from doing
  nothing. **Not measured**: a composite 0.237 + 0.031 = 0.27 ns/element for a
  `loop`/`recur` guest reading through a load is inferred by adding a marginal
  from one loop shape to a cost from another; building it is what would measure
  it. Samples landed at `bench/bulk-carrier/samples-levi-*.edn`. ADR 0285 edited
  rather than appended to, per this file's own rule that the table is what gets
  corrected.

- **53 (2026-08-30, the native export-table rejection is bisected to one pin,
  and it is not the obvious one)**: `amu extract-native` rejects both H.264
  native kernels on main with `:kotoba/verification-failed "native export table
  rejected"`. Bisected to **`kotoba-mir` `3f88f71` -> `3aea0ac`**, reached
  through `kotoba-native` `3162d868` which this repo pins. Rolling back **that
  one coordinate alone**, leaving `kotoba-native` at `3162d868`, makes both
  kernels extract cleanly (`group-idx` offset 332 len 48; `idct4-1d` offset 116
  len 220). ADR 0288.
  **The obvious suspect is cleared.** ADR 0284's `:vector-i64` boundary spelling
  (`a8f8cfe`) is the one commit in the 55-commit range that changes which types
  cross a native function boundary, and it tests **GOOD** -- as do `85f8c07`,
  `3dab370`, `da3b56b` and iteration 49's `16572dc`. The BAD point is `3162d868`,
  a merge **whose two parents are both GOOD**, which is what localised it: its
  diff against `16572dc` is a `kotoba-mir` pin advance plus one line choosing
  `:x86-64/jmp-rel32` over `:aarch64/b-imm26` on x86, and the kernels are
  aarch64, so only the pin can reach them.
  Ruled out first, because two defects landed today with exactly that shape
  (ADR 0286, ADR 0287): this is **not** an nbb/JVM divergence -- `./bin/amu` and
  `clojure -M:run` reject the same artifact identically. Also not iterations 51
  or 52, which touched `docs/` and `bench/bulk-carrier/`, and `bench/bulk-carrier`
  is on no classpath (`:paths ["src" "resources"]`, and the only bench path in any
  alias is `bench/runtime-comparison/cljs`).
  **Mechanism, inferred not measured**: the verifier re-emits from the artifact's
  own stored KIR and compares export tables, and verify-time emission is
  deterministic, so compile-time emission must consume state the stored KIR does
  not carry. Layout does move (`group-idx` sits at 332 rolled back, 416 at the
  pre-range pin). Demonstrating it means dumping and diffing both export tables;
  that was not done. **Not fixed**: `kotoba-mir` is outside this repo and the
  available mitigation -- reverting the pin -- would undo the x86 preserved-tier
  direct reentry that landed with it. Recorded for the owner rather than taken.
  This is ADR 0230's producer/verifier independence doing its job: the verifier
  refused to trust a table it could not rebuild.

- **51 (2026-08-30, the strings domain opens -- and loses honestly)**:
  the seventh domain exists. What blocked it was never the language or
  the backend -- string ops (`string-concat`/`-substring`/`-code-point-at`/
  `string=?`/`-byte-length`) have been in the native backend as v3
  context callbacks all along, and raw extraction already appends
  literal data past the code -- it was the benchmark harness, whose
  context carried only version and fuel, so the first `pair_new` boxing
  a literal dereferenced NULL. kexe-benchmark.c now carries the
  pair/string slots of the real v3 contract (ported from
  tools/kexe_loader.c, same SIGILL-on-violation semantics, ABI offsets
  asserted; pair and pool cursors reset per call so every timed call is
  a fresh instance). Fixture `kernel_strings.kotoba`: substring view ->
  build-by-concat -> code-point scan -> head compare, every step mod
  1000003 so no backend's overflow behaviour is in play; per-call fuel
  varies with n, so the manifest asserts fuel per input. KA: 6/6
  against a JVM `quot`/`subs`/`reduce` oracle on Rosetta AND on gad,
  both arms (12/12 on hardware). First standings, ABBA x12, KA per
  sample, load 0.96: **amu 5511 ns/call, gcc twin 511 ns/call --
  ratio 10.77** (rsd 0.010/0.063). The residue is named and structural:
  `checked_string_code_point_at` revalidates the WHOLE string's UTF-8
  on every access, so a scan is O(n^2) in host byte checks, and every
  character crossing is an indirect call -- gcc's arm is a direct byte
  load. The lawful levers, in counter order: validate-once-per-pair
  (amortize valid_utf8 at creation), then a guest-visible byte plane.
  Registered as an INCUBATING domain, not a required one -- a required
  domain binds the claim contract to every comparator arm, and only the
  C twin exists; promotion needs rust/zig/go/swift twins and both ISAs
  measured. The aarch64 bounded claim is untouched by today's loss,
  and saying otherwise would be the aggregate hiding a loss -- the
  thing the contract's aggregation policy exists to forbid.

- **52 (2026-08-30, Wave-2 opens: the collections domain, and its gate
  was already unlocked)**: the eighth domain. The record had carried
  "collections/documents, gated on native backend features" -- measured
  today, that gate was already open: `vector-i64` is a context-owned
  one-word handle the KIR gate admits, the native backend lowers all
  six operations (`vector-conj/-count/-at/-assoc/-drop/-get`), and the
  production loader has carried the arena implementation since
  ADR-2608030300. What was actually missing was the same thing that
  blocked strings: six NULL slots in the benchmark context.
  kexe-benchmark.c now carries the vector machinery too (ported from
  tools/kexe_loader.c: immutable handles over a shared arena, in-place
  conj only at the arena top, copy-on-assoc, drop as a view; arenas
  reset per call). Fixture `kernel_collections.kotoba`: fill by conj ->
  hash walk by vector-at -> one assoc -> suffix drop view -> second
  walk, mod 1000003 throughout; JVM `mapv`/`assoc`/`subvec` oracle,
  6/6 on Rosetta and on gad, both arms. First standings, ABBA x12, KA
  per sample, load 0.64: **amu 2203 ns/call, gcc twin 1141 ns/call --
  ratio 1.93** (rsd 0.039/0.032). The contrast with strings' 10.77 is
  itself the finding: vector callbacks validate handles in O(1), so
  what remains is almost purely the ~170 indirect callback crossings
  per call against gcc's direct array code. The lawful levers, in
  order: `reduce`-desugared walks (T4.5's zero-charge loop, an amu-arm
  change measurable same-run against today's binary), then inlining
  bounds-checked element loads into guest code -- the same
  guest-visible-plane lever family strings needs. (Iteration 55 refutes
  the crossing attribution behind this ranking -- ADR 0289.) Registered as the
  second INCUBATING domain, same promotion bar (rust/zig/go/swift
  twins, both ISAs). Documents (`document-*` ops) stay queued as the
  next Wave-2 slice.

- **53 (2026-08-30, two refusals, both measured)**: first, the documents
  half of Wave-2 is genuinely gated -- unlike vectors, whose gate turned
  out to be six NULL harness slots. A `document-vector`/`document-count`
  kernel is rejected by the x86_64 target with the compiler's own words
  (`:kotoba/target-rejected` -- "typed values currently require ... the
  qualified native one-word string/record/variant/option/result slice")
  while the SAME source compiles `:ok true` on wasm32: the language is
  complete, the native backend's qualified slice does not include
  structural document values (native `:document` is only a pair over
  canonical EDN bytes, with `document-edn-read`/`-print` as identity
  casts). The domain opens when document-get/-count/-vector-at gain
  native admission -- filed, not worked around. Second, iteration 52's
  first lever is REFUTED: rewriting the collections walks as `reduce`
  (KAs and per-input fuel byte-identical, binary 66 bytes smaller)
  measured **28.6% SLOWER** than the hand recursion, same-run ABBA x12
  (2831 vs 2201 ns, rsd 0.027/0.018, load 0.49). T4.5's "zero-charge"
  is a fuel property, not a speed property: on native the reducing
  closure pays a call per element that the self-recursive walk does
  not. The fixture stays as written; the variant is not landed. What
  survives as the collections lever queue: guest-visible bounds-checked
  element loads -- the same plane strings needs for its 10.77. **Superseded by
  iteration 55**: the crossing is ~1% in a same-kernel control; the
  per-element `sdiv` is the large term.

- **54 (2026-08-31, validate-once lands through the pinned loader chain --
  strings 10.77 -> 2.17)**: the O(n^2) residue iteration 51 named is
  gone. Per-handle UTF-8 validation memoisation (`pair_validated`):
  every mint clears its flag, the s: argument parse mints pre-validated,
  a code-point-bounded substring view of a validated string is valid by
  construction, concat propagates validity when both inputs carry it,
  and an unvalidated handle still validates -- and traps on bad bytes --
  at first access. No trap is removed; what changes is only how often a
  string that has already proven itself is re-proven. Lever verdict,
  measured the honest way (same guest binary, harness-v4 vs harness-v3,
  ABBA x12, KA per sample): **0.213 -- the strings arm fell from 5427 to
  1156 ns/call** (rsd 0.037/0.008), far clear of every bar. New day
  standings vs gcc: **2.17** (1146 vs 528 ns, rsd 0.021/0.058) -- from
  10.77 at opening. The remaining 2.17 is the per-character callback
  crossing, the same residue class as collections' 1.93, which points
  both domains at the same next lever (guest-visible bounds-checked
  loads) -- **an attribution iteration 55 refutes for
  collections and leaves unmeasured for strings**. Landing this took the whole identity chain, by design: the
  loaders are SHA-256-pinned reviewed sources, so the first suite run
  answered with 46 red names -- `native loader source identity
  mismatch`, expected e1f32ab9, actual 636ba814 -- which is the drift
  detector doing its job. The change is ported to BOTH loaders (the
  Windows twin mechanically, compile-unverified here, stated in the pin
  docstring per that pin's own convention), both pins advanced in
  kotoba-lang/artifact (its suite 11/59 green) with dated docstring
  amendments, amu's artifact dep and fuzz baseline advanced, and the amu
  suite closed **fully green -- 1189 tests, 8675 assertions, 0 failures**
  (the 17 long-standing reds were fixed upstream by parallel sessions in
  the same window).

- **55 (2026-08-31, the named cause for BOTH open residuals is refuted)**:
  iterations 52-54 attribute collections' 1.93 and strings' 2.17 to the same
  thing -- "almost purely the ~170 indirect callback crossings per call" --
  and point both at one lever. Two controls say otherwise (ADR 0289).
  **Control 1**: two C arms, same kernel and data, differing only in whether
  each element read crosses an indirect pointer mirroring
  `checked_vector_at`. Ratio **1.002 (1.6 ns/call)**. The first build of this
  control was WRONG and the arithmetic caught it -- one translation unit let
  LLVM see the clobber set, and 108 crossings at 5.9 ns is 0.055 ns each,
  below one indirect call; rebuilt with the callback in a separate TU and
  `-fno-lto`, the answer did not move. Crossings were counted, not assumed:
  `XCALLS = 17,255,040` against a predicted 17,255,040. They are ~free
  because the loop is latency-bound on the serial `imod` chain and the calls
  retire in its shadow. **Control 2**: the emitted `walk` loop
  (`aarch64-kotoba-v1`, `0x13c..0x1ac`) is **29 instructions per element** --
  9 for the `vector-at` crossing including spilling `x7` around the call, 5
  for a fuel read-modify-write, 6 for the `imod` call, 9 of real work -- plus
  an out-of-line `imod` of **18 instructions containing a hardware `sdiv`**
  (`bl` at `0x18c`, word `0x97ffff9d`, displacement -99, target `0x0`,
  decoded rather than symbolized). ~47 instructions and one division per
  element against the twin's ~6-8. The discriminator is dynamic, not static:
  both binaries hold exactly one `sdiv`, but the twin strength-reduces every
  constant divisor and executes its one division ~1x per call, while amu's
  shared `imod` runs ~165x. **Lever re-ranking**: guest-visible
  bounds-checked loads remove 9 of 47 instructions and measured ~1% in
  isolation, so they are no longer the largest remaining lever; above them
  now sit (i) inlining small user functions, (ii) constant-divisor strength
  reduction, (iii) bulk fuel in loop bodies. Diagnostic only -- one
  workstation at load1 47, no quiet-host run, no amu-vs-gcc same-run A/B.
  **strings was NOT disassembled**; whether its 2.17 shares this cause is
  unmeasured, not assumed. Separately, the lever itself is cleared as a
  backend gap rather than a security constraint: a bounds-checked load
  crosses none of `surface-status.edn`'s five shielding axes, and
  `vector-region`'s literal path already emits the check
  (`(if (>= i 0) (if (< i n) sel (quot 1 0)) (quot 1 0))`) -- only the load
  is missing. The local `kotoba-lang` checkout was 14 commits behind and
  carried no `:shielding-axis` key at all, which would have produced the
  opposite conclusion silently.

- **56 (2026-09-03, rank-only pass; host busy, no measurement)**: load1
  41.93 / 5min 55.90 / 15min 60.25 (up 10 days) — far above the 7.5 quiet
  limit, so no falsification or bench run was attempted. No hypothesis was
  re-ranked, no status transitioned, no new hypothesis registered: there is
  no new measurement to rank on. Population state unchanged; H-C2, H-D, H-B,
  H-Y1 remain open. NEXT: H-C2 (highest expected qualified gain × probability
  among open hypotheses; the remaining ~4.4% vs Clang on `kernel` with
  near-identical static shape is the closest to a separable win).

- **57 (2026-09-03, host busy, no measurement)**: load1 54.75 / 5min 53.70 /
  15min 57.72 (up 10 days) — far above the 7.5 quiet limit, so no bench or
  perfgate run was attempted. amu-falsify evidence checked: no new
  "要 quiet-host 測定" item pending. Population state unchanged; H-C2, H-D,
  H-B, H-Y1 remain open. NEXT: H-C2 (unchanged).

- **58 (2026-09-03 10:28 JST, rank-only pass; host busy, no measurement)**:
  load1 30.42 / 5min 37.26 / 15min 43.77 (up 10 days) — still far above the
  7.5 quiet limit; no bench, perfgate, or falsify run attempted. Evidence
  reviewed: only more busy ticks since entry 57 (amu-bench iteration 30,
  falsify ticks on H-C2 and H-B) — no new numbers, so no re-rank, no status
  transition, no new hypothesis. Population unchanged: H-C2, H-D, H-B, H-Y1
  open. NEXT: H-C2 (unchanged — highest expected qualified gain ×
 probability; near-identical static shape vs Clang at ~4.4% residual).

- **59 (2026-09-03 10:26 JST, host busy, no measurement)**: load1 33.49 /
  5min 36.53 / 15min 42.57 (up 10 days) — far above the 7.5 quiet limit; no
  bench, perfgate, or falsify run attempted. amu-falsify evidence checked:
  no new "要 quiet-host 測定" item pending. Population unchanged: H-C2, H-D,
  H-B, H-Y1 open. NEXT: H-C2 (unchanged).

- **60 (2026-09-03 10:43 JST, rank-only pass; host busy, no measurement)**:
  load1 35.61 / 5min 37.61 / 15min 39.00 (up 10 days) — far above the 7.5
  quiet limit; no bench, perfgate, or falsify run attempted. Evidence since
  entry 59 reviewed: only busy falsify ticks on H-C2 (10:16, 10:31 JST) and
  H-B (10:00 JST) and amu-bench iteration 30's refusal — no new numbers, so
  no re-rank, no status transition, no new hypothesis. Population unchanged:
  H-C2, H-D, H-B, H-Y1 open. NEXT: H-C2 (unchanged — highest expected
  qualified gain × probability; near-identical static shape vs Clang at
  ~4.4% residual on `kernel`).

- **61 (2026-09-03 10:45 JST, host busy, no measurement)**: load1 29.34 /
  5min 36.21 / 15min 38.37 (up 10 days) — far above the 7.5 quiet limit; no
  bench, perfgate, or falsify run attempted. amu-falsify evidence checked:
  no new "要 quiet-host 測定" item pending. Population unchanged: H-C2, H-D,
  H-B, H-Y1 open. NEXT: H-C2 (unchanged — highest expected qualified gain ×
  probability; near-identical static shape vs Clang at ~4.4% residual on
  `kernel`).

- **62 (2026-09-03 11:02 JST, rank-only pass; host busy, no measurement)**:
  load1 31.19 / 5min 35.06 / 15min 36.30 (up 10 days) — far above the 7.5
  quiet limit; no bench, perfgate, or falsify run attempted. No new evidence
  since entry 61 (no new falsify/bench numbers): no re-rank, no status
  transition, no new hypothesis. Population unchanged: H-C2, H-D, H-B, H-Y1
  open. NEXT: H-C2 (unchanged — highest expected qualified gain ×
  probability; near-identical static shape vs Clang at ~4.4% residual on
  `kernel`).

- **63 (2026-09-03 11:03 JST, host busy, no measurement)**: load1 38.51 /
  5min 36.51 / 15min 36.74 (up 10 days) — far above the 7.5 quiet limit; no
  bench, perfgate, or falsify run attempted. amu-falsify evidence checked:
  no new "要 quiet-host 測定" item pending. Population unchanged: H-C2, H-D,
  H-B, H-Y1 open. NEXT: H-C2 (unchanged — highest expected qualified gain ×
  probability; near-identical static shape vs Clang at ~4.4% residual on
  `kernel`).

- **64 (2026-09-03 11:26 JST, host busy, no measurement)**: load1 28.40 /
  5min 34.58 / 15min 35.52 (up 10 days) — far above the 7.5 quiet limit; no
  bench, perfgate, or falsify run attempted. amu-falsify evidence checked:
  no new "要 quiet-host 測定" item pending. Population unchanged: H-C2, H-D,
  H-B, H-Y1 open. NEXT: H-C2 (unchanged — highest expected qualified gain ×
  probability; near-identical static shape vs Clang at ~4.4% residual on
  `kernel`).

- **65 (2026-09-03 13:33 JST, rank-only pass; host busy, no measurement)**:
  load1 23.21 / 5min 17.62 / 15min 17.86 (up 10 days) — above the 7.5
  quiet limit, so no bench or perfgate run was attempted. amu-falsify
  evidence checked: no new "要 quiet-host 測定" item pending. Population
  unchanged: H-C2, H-D, H-B, H-Y1 open. NEXT: H-C2 (unchanged).

- **66 (2026-09-03 13:58 JST, rank-only pass; host busy, no measurement)**:
  load1 37.79 / load5 23.00 / load15 21.02 (up 10 days) — above the 7.5
  quiet limit, so no bench, perfgate, or falsify run attempted. Evidence
  since entry 65 reviewed: origin/main advanced (PR #769 grammar
  vendoring; ADR 0327/0330/0331 amendments, #766 UEFI fuel) but the
  fetched diff contains no new perfgate/bench numbers against any open
  hypothesis, so there is nothing to re-rank on. No status transition,
  no new hypothesis. Population unchanged: H-C2, H-D, H-B, H-Y1 open.
  NEXT: H-C2 (unchanged — highest expected qualified gain × probability;
  ~4.4% residual vs Clang on `kernel` with near-identical static shape,
  separable).

- **67 (2026-09-03 15:07 JST, host busy, no measurement)**: load1 25.51 /
  5min 19.63 / 15min 17.88 (up 10 days) — above the 7.5 quiet limit, so no
  bench, perfgate, or falsify run attempted. amu-falsify evidence checked:
  no new "要 quiet-host 測定" item pending. Population unchanged: H-C2, H-D,
  H-B, H-Y1 open. NEXT: H-C2 (unchanged).

- **68 (2026-09-03 15:49 JST, rank-only pass; host busy, no measurement)**:
  load1 13.83 / 5min 17.07 / 15min 20.84 (up 10 days) — above the 7.5 quiet
  limit, so no bench, perfgate, or falsify run attempted. Evidence since
  entry 67 reviewed: one more busy falsify tick on H-C2 (15:08 JST); the
  fetch brought origin/main +24 commits (#769 grammar vendoring removed,
  #770 frontend/KIR consume + catalog resync, UEFI BOOTX64.EFI page-write
  with fuel ADR 0332/0333/0334, authority-digest monotonicity) — all
  pin/fuel/correctness work, none carrying perfgate/bench numbers against
  an open hypothesis, so there is nothing to re-rank on. No status
  transition, no new hypothesis. Population unchanged: H-C2, H-D, H-B,
  H-Y1 open. NEXT: H-C2 (unchanged — highest expected qualified gain ×
  probability; ~4.4% residual vs Clang on `kernel` with near-identical
  static shape, separable).

- **69 (2026-09-03 15:58 JST, bench pass; host busy, no measurement)**:
  load1 12.79 / 5min 14.45 / 15min 17.75 (up 10 days) — above the 7.5 quiet
  limit, so no bench/perfgate run attempted; nothing to add to H-C2
  evidence. Population unchanged: H-C2, H-D, H-B, H-Y1 open. NEXT: H-C2
  (unchanged).

- **70 (2026-09-03 17:58 JST, bench pass; host busy, no measurement)**:
  load1 14.04 / 5min 16.10 / 15min 20.92 (up 10 days) — above the 7.5 quiet
  limit, so no bench/perfgate run attempted; nothing to add to H-C2
  evidence. Population unchanged: H-C2, H-D, H-B, H-Y1 open. NEXT: H-C2
  (unchanged).

- **71 (2026-09-03 17:59 JST, rank-only pass; host busy, no measurement)**:
  load1 12.71 / 5min 15.63 / 15min 20.61 (up 10 days) — above the 7.5 quiet
  limit, so no bench, perfgate, or falsify run attempted. Evidence since
  entry 70 reviewed: fetch clean (already up to date), working tree carries
  only the busy-tick log growth and two untracked files (jb_imod_control.c,
  jit-cosientist.md) — no new perfgate/bench numbers against any open
  hypothesis, so there is nothing to re-rank on. No status transition, no
  new hypothesis. Population unchanged: H-C2, H-D, H-B, H-Y1 open. NEXT:
  H-C2 (unchanged — highest expected qualified gain × probability; ~4.4%
  residual vs Clang on `kernel` with near-identical static shape,
  separable).

- **72 (2026-09-03 18:40 JST, rank-only pass; host busy, no measurement)**:
  load1 16.94 / 5min 17.66 / 15min 16.93 (up 10 days, 14 users) — above
  the 7.5 quiet limit, so no bench, perfgate, or falsify run attempted.
  Fetch clean (57ba0ee0, already up to date). Working tree unchanged from
  entry 71: busy-tick log growth plus untracked jb_imod_control.c and
  jit-cosientist.md — no new measured evidence against any open
  hypothesis, so no re-rank, no status transition, no new hypothesis.
  Population unchanged: H-C2, H-D, H-B, H-Y1 open. NEXT: H-C2 (unchanged
  — highest expected qualified gain × probability; ~4.4% residual vs
  Clang on `kernel` with near-identical static shape, separable).

- **73 (2026-09-03 19:29 JST, rank-only pass; host busy, no measurement)**:
  load1 10.33 / 5min 13.45 / 15min 15.76 (up 10 days) — above the 7.5 quiet
  limit, so no bench, perfgate, or falsify run was attempted. Fetch pulled
  origin/main to 764a6dba (#770 frontend/KIR consume + catalog resync, fuel64
  ceiling/EFI-budget tests) — pin/fuel/correctness work, no perfgate/bench
  numbers against any open hypothesis, so nothing to re-rank on. No status
  transition, no new hypothesis. Population unchanged: H-C2, H-D, H-B, H-Y1
  open. NEXT: H-C2 (unchanged — highest expected qualified gain ×
  probability; ~4.4% residual vs Clang on `kernel` with near-identical
  static shape, separable).


- **74 (2026-09-03 21:49 JST, rank-only pass; host busy, no measurement)**:
  load1 20.35 / 5min 20.85 / 15min 21.23 (up 10 days, 11 users) — above the
  7.5 quiet limit, so no bench, perfgate, or falsify run was attempted.
  No new evidence against any open hypothesis; no re-rank, no status
  transition, no new hypothesis. Population unchanged: H-C2, H-D, H-B, H-Y1
  open. NEXT: H-C2 (unchanged — highest expected qualified gain ×
  probability; ~4.4% residual vs Clang on `kernel` with near-identical
  static shape, separable).

- **75 (2026-09-03 22:29 JST, rank-only pass; host busy, no measurement)**:
  load1 17.83 / 5min 15.84 / 15min 18.89 (up 10 days, 11 users) — above the
  7.5 quiet limit, so no bench, perfgate, or falsify run was attempted.
  Fetch: no new commits past 764a6dba; working tree unchanged from entry 71
  (untracked jb_imod_control.c, jit-cosientist.md). No new evidence against
  any open hypothesis; no re-rank, no status transition, no new hypothesis.
  Population unchanged: H-C2, H-D, H-B, H-Y1 open. NEXT: H-C2 (unchanged —
  highest expected qualified gain × probability; ~4.4% residual vs Clang on
  `kernel` with near-identical static shape, separable).

- **76 (2026-09-04 00:22 JST, rank-only pass; host busy, no measurement)**:
  load1 9.35 / 5min 14.56 / 15min 15.77 (up 10 days, 11 users) — above the
  7.5 quiet limit, so no bench, perfgate, or falsify run was attempted.
  Fetch: no new commits past 764a6dba; working tree unchanged from entry 75
  (untracked jb_imod_control.c, jit-cosientist.md). No new evidence against
  any open hypothesis; no re-rank, no status transition, no new hypothesis.
  Population unchanged: H-C2, H-D, H-B, H-Y1 open. NEXT: H-C2 (unchanged —
  highest expected qualified gain × probability; ~4.4% residual vs Clang on
  `kernel` with near-identical static shape, separable).

- **77 (2026-09-04 00:58 JST, rank-only pass; host busy, no measurement)**:
  load1 36.85 / 5min 28.28 / 15min 21.26 (up 10 days, 11 users) — above the
  7.5 quiet limit by a wide margin, so no bench, perfgate, or falsify run was
  attempted. Fetch: no new commits past dd9bb23d; working tree unchanged
  (untracked jb_imod_control.c). No new evidence against any open
  hypothesis; no re-rank, no status transition, no new hypothesis — a re-rank
  without measured numbers would be fabrication.
  Population unchanged: H-C2, H-D, H-B, H-Y1 open. NEXT: H-C2 (unchanged —
  highest expected qualified gain × probability; ~4.4% residual vs Clang on
  `kernel` with near-identical static shape, separable).

- **78 (2026-09-04 01:06 JST, bench pass; host busy, no measurement)**:
  load1 23.07 / 5min 28.48 / 15min 25.13 (up 10 days, 11 users) — above the
  7.5 quiet limit, so no bench, perfgate, or falsify run was attempted.
  No fetch this pass; HEAD at df3bc295, working tree unchanged (untracked
  jb_imod_control.c). No new evidence against any open hypothesis; no
  re-rank, no status transition, no new hypothesis. Population unchanged:
  H-C2, H-D, H-B, H-Y1 open. NEXT: H-C2 (unchanged — highest expected
  qualified gain × probability; ~4.4% residual vs Clang on `kernel` with
  near-identical static shape, separable).

- **79 (2026-09-04 03:59 JST, bench pass; host busy, no measurement)**:
  load1 19.55 / 5min 17.09 / 15min 18.75 (up 10 days, 11 users) — above the
  7.5 quiet limit, so no bench, perfgate, or falsify run was attempted.
  amu-falsify evidence checked: no new "要 quiet-host 測定" item pending.
  No new evidence against any open hypothesis; no re-rank, no status
  transition, no new hypothesis. Population unchanged: H-C2, H-D, H-B, H-Y1
  open. NEXT: H-C2 (unchanged — highest expected qualified gain ×
  probability; ~4.4% residual vs Clang on `kernel` with near-identical
  static shape, separable).

- **80 (2026-09-04 04:22 JST, rank pass; host busy, no measurement)**:
  load1 14.42 / 5min 13.99 / 15min 16.33 (up 10 days, 19:55, 11 users) —
  above the 7.5 quiet limit, so no bench, perfgate, or falsify run was
  attempted. amu-falsify evidence checked: no new pending item. No new
  evidence against any open hypothesis; no re-rank, no status transition,
  no new hypothesis. Population unchanged: H-C2, H-D, H-B, H-Y1 open.
  NEXT: H-C2 (unchanged — highest expected qualified gain × probability;
  ~4.4% residual vs Clang on `kernel` with near-identical static shape,
  separable).

- **81 (2026-09-04 07:24 JST, rank pass; host busy, no measurement)**:
  load1 21.25 / 5min 25.15 / 15min 25.86 (up 10 days, 23:13, 11 users) —
  above the 7.5 quiet limit, so no bench, perfgate, or falsify run was
  attempted. Evidence since entry 80 reviewed: one more busy falsify tick on
  H-C2 (05:12 JST, no numbers); no fetch diff carried new perfgate/bench
  numbers against any open hypothesis. No re-rank, no status transition, no
  new hypothesis — a re-rank without measured numbers would be fabrication.
  Population unchanged: H-C2, H-D, H-B, H-Y1 open. NEXT: H-C2 (unchanged —
  highest expected qualified gain × probability; ~4.4% residual vs Clang on
  `kernel` with near-identical static shape, separable).

- **82 (2026-09-04 08:42 JST, falsify pass; host busy, no measurement)**:
  load1 20.61 / 5min 17.40 / 15min 19.33 (up 11 days, 0:30, 11 users) —
  above the 7.5 quiet limit; per policy no bench, perfgate, or hand-patch
  measurement attempted. No hypothesis evidence updated. Population
  unchanged: H-C2, H-D, H-B, H-Y1 open. NEXT: H-C2 (unchanged — highest
  expected qualified gain × probability; ~4.4% residual vs Clang on
  `kernel` with near-identical static shape, separable).

- **83 (2026-09-04 10:39 JST, bench pass; host busy, no measurement)**:
  load1 38.73 / 5min 29.36 / 15min 25.36 (up 11 days, 2:26, 9 users) —
  far above the 7.5 quiet limit; per policy no bench or perfgate run
  attempted, no numbers recorded. amu-falsify evidence checked: no new
  "要 quiet-host 測定" item pending. Population unchanged: H-C2, H-D, H-B,
  H-Y1 open. NEXT: H-C2 (unchanged — highest expected qualified gain ×
  probability; ~4.4% residual vs Clang on `kernel`, near-identical static
  shape, separable).

- **84 (2026-09-04 10:47 JST, rank pass; host busy, no measurement)**:
  load1 13.72 / 5min 23.49 / 15min 25.28 (up 11 days, 2:36, 9 users, 10 CPUs)
  — above the 7.5 quiet limit; no bench, perfgate, or falsify run attempted,
  no numbers recorded. No new evidence from amu-falsify / amu-bench since
  entry 83 beyond that busy tick, so no re-rank, no status transition, no
  new hypothesis. Population unchanged: H-C2, H-D, H-B, H-Y1 open.
  NEXT: H-C2 (unchanged — highest expected qualified gain × probability;
  ~4.4% residual vs Clang on `kernel`, near-identical static shape,
  separable).

### NEXT
  H-C2 (unchanged; host busy at 10:47 JST rank tick, no measurement possible)

- **85 (2026-09-04 10:54 JST, bench pass; host busy, no measurement)**:
  load1 32.89 / 5min 28.79 / 15min 27.01 (up 11 days, 2:41, 8 users, 10 CPUs)
  — far above the 7.5 quiet limit; per policy no bench or perfgate run
  attempted, no numbers recorded. amu-falsify evidence checked: no new
  "要 quiet-host 測定" item pending. Population unchanged: H-C2, H-D, H-B,
  H-Y1 open. NEXT: H-C2 (unchanged — highest expected qualified gain ×
  probability; ~4.4% residual vs Clang on `kernel`, near-identical static
  shape, separable).

- **86 (2026-09-04 11:00 JST, falsify pass; host busy, no measurement)**:
  load1 32.81 / 5min 32.59 / 15min 29.42 (up 11 days, 2:48, 8 users, 10 CPUs)
  — far above the 7.5 quiet limit; per policy no bench, perfgate, or
  hand-patch measurement attempted. Busy-tick evidence appended to the H-C2
  row only. Population unchanged: H-C2, H-D, H-B, H-Y1 open. NEXT: H-C2
  (unchanged — highest expected qualified gain × probability; ~4.4%
  residual vs Clang on `kernel`, near-identical static shape, separable).

- **87 (2026-09-04 11:02 JST, rank pass; host busy, no measurement)**:
  load1 29.88 / 5min 31.61 / 15min 29.51 (up 11 days, 2:50, 8 users, 10 CPUs)
  — far above the 7.5 quiet limit; per policy no bench, perfgate, or
  hand-patch measurement attempted, no numbers recorded. Evidence since
  entry 86 reviewed: only additional busy falsify ticks on H-C2
  (10:46, 11:00 JST); no new perfgate/bench numbers against any open
  hypothesis, so no re-rank, no status transition, no new hypothesis —
  a re-rank without measured numbers would be fabrication. Population
  unchanged: H-C2, H-D, H-B, H-Y1 open. NEXT: H-C2 (unchanged — highest
  expected qualified gain × probability; ~4.4% residual vs Clang on
  `kernel`, near-identical static shape, separable).

- **88 (2026-09-04 11:08 JST, bench pass; host busy, no measurement)**:
  load1 44.19 / 5min 42.09 / 15min 35.17 (up 11 days, 2:56, 10 users, 10
  CPUs) — far above the 7.5 quiet limit; per policy no bench or perfgate
  run attempted, no numbers recorded. amu-falsify evidence checked: no
  new "要 quiet-host 測定" item pending. Population unchanged: H-C2, H-D,
  H-B, H-Y1 open. NEXT: H-C2 (unchanged — highest expected qualified gain
  × probability; ~4.4% residual vs Clang on `kernel`, near-identical
  static shape, separable).

- **89 (2026-09-04 11:19 JST, rank pass; host busy, no measurement)**:
  load1 55.90 / 5min 42.71 / 15min 36.47 (up 11 days, 3:07, 10 users, 10
  CPUs) — far above the 7.5 quiet limit; per policy no bench, perfgate, or
  hand-patch measurement attempted, no numbers recorded. Evidence since
  entry 88 reviewed: no new measured numbers against any open hypothesis
  (H-C2, H-D, H-B, H-Y1), so no re-rank, no status transition, no new
  hypothesis. Population unchanged. NEXT: H-C2 (unchanged — highest
  expected qualified gain × probability; ~4.4% residual vs Clang on
  `kernel`, near-identical static shape, separable).

- **90 (2026-09-04 11:34 JST, rank pass; host busy, no measurement)**:
  load1 42.58 / 5min 46.77 / 15min 46.45 (up 11 days, 3:23, 10 users, 10
  CPUs) — ~6x above the 7.5 quiet limit; per policy no bench, perfgate, or
  hand-patch measurement attempted, no numbers recorded. Evidence since
  entry 89 reviewed: falsify/bench ticks 11:20 (load1 59.44) and 11:27
  (load1 64.86) appended to the H-C2 row; jit tick 5 at 10:42 (load1 31-34,
  idle 0-1.7%) appended to J-B — all busy-tick deferrals, no measured
  numbers, so no re-rank, no status transition, no new hypothesis.
  Population unchanged (H-C2, H-D, H-B, H-Y1 open; J-B awaiting a quiet
  host; J-C blocked behind J-B). NEXT: H-C2 (unchanged — highest expected
  qualified gain × probability; ~4.4% residual vs Clang on `kernel`,
  near-identical static shape, separable).

- **91 (2026-09-04 11:53 JST, rank pass; host busy, no measurement)**:
  load1 48.18 / 5min 48.03 / 15min 49.54 (up 11 days, 3:36, 9 users, 10
  CPUs) — ~6x above the 7.5 quiet limit; per policy no bench, perfgate, or
  hand-patch measurement attempted, no numbers recorded. git fetch
  reviewed: no new commit carries measured evidence (origin/main is at
  764a6dba; only maint/perfgate-bridge and jit busy-ticks since entry 90).
  No re-rank, no status transition, no new hypothesis — a re-rank without
  measured numbers would be fabrication. Population unchanged: H-C2, H-D,
  H-B, H-Y1 open (J-B awaiting a quiet host; J-C blocked behind J-B).
  NEXT: H-C2 (unchanged — highest expected qualified gain × probability;
  ~4.4% residual vs Clang on `kernel`, near-identical static shape,
  separable).

- **92 (2026-09-04 12:49 JST, rank pass; host busy, no measurement)**:
  load1 56.01 / 5min 59.33 / 15min 61.77 (up 11 days, 4:37, 10 users, 10
  CPUs) — ~7x above the 7.5 quiet limit; per policy no bench, perfgate, or
  hand-patch measurement attempted, no numbers recorded. git fetch
  reviewed: no new commit carries measured evidence; working tree has the
  same uncommitted H-C2 busy-tick script (append_hc2_busy_tick.py) and
  docs edits as at entry 91. No re-rank, no status transition, no new
  hypothesis — a re-rank without measured numbers would be fabrication.
  Population unchanged: H-C2, H-D, H-B, H-Y1 open (J-B awaiting a quiet
  host; J-C blocked behind J-B). NEXT: H-C2 (unchanged — highest expected
  qualified gain × probability; ~4.4% residual vs Clang on `kernel`,
  near-identical static shape, separable).

- **93 (2026-09-04 13:08 JST, rank pass; host busy, no measurement)**:
  load1 50.29 / 5min 61.70 / 15min 63.42 (up 11 days, 4:56, 10 users, 10
  CPUs) — ~6.7x above the 7.5 quiet limit; per policy no bench, perfgate,
  or hand-patch measurement attempted, no numbers recorded. git fetch
  reviewed: no new commit since 149aa34c (J-B tick7 loaded-host
  diagnostics, quiet gate still unmet). Working tree unchanged: same
  uncommitted H-C2 busy-tick script and docs edits as at entry 92. No
  re-rank, no status transition, no new hypothesis — a re-rank without
  measured numbers would be fabrication. Population unchanged: H-C2, H-D,
  H-B, H-Y1 open (J-B awaiting a quiet host; J-C blocked behind J-B).
  NEXT: H-C2 (unchanged — highest expected qualified gain × probability;
  ~4.4% residual vs Clang on `kernel`, near-identical static shape,
  separable).
- **94 (2026-09-04 13:19 JST, rank pass; host busy, no measurement)**:
  load1 57.45 / 5min 63.03 / 15min 63.52 (up 11 days, 5:05, 10 users, 10
  CPUs) — ~7.7x above the 7.5 quiet limit; per policy no bench, perfgate,
  or hand-patch measurement attempted, no numbers recorded. git fetch
  reviewed: no new commit since ef7ac8dd (iteration 93, itself a rank-only
  busy pass). Working tree: same uncommitted H-C2 busy-tick evidence
  appends (latest covers 13:05/13:07/13:15 ticks) plus this entry —
  amu-falsify/amu-bench work in progress, left untouched. No re-rank, no
  status transition, no new hypothesis — a re-rank without measured
  numbers would be fabrication. Population unchanged: H-C2, H-D, H-B, H-Y1
  open. NEXT: H-C2 (unchanged — highest expected qualified gain ×
  probability; ~4.4% residual vs Clang on `kernel`, near-identical static
  shape, separable).

- **95 (2026-09-04 13:23 JST, bench pass; host busy, no measurement)**:
  load1 56.97 / 5min 58.13 / 15min 61.01 (up 11 days, 5:12, 9 users, 10
  CPUs) — ~7.6x above the 7.5 quiet limit; per policy no bench, perfgate,
  or hand-patch measurement attempted, no numbers recorded. iostat
  diagnostic: cpu idle 0–3% over 4 one-second samples (busy fraction far
  above the 0.10 quiet-gate limit), us 54–75 sy 22–27. amu-falsify
  evidence checked: no new "要 quiet-host 測定" item pending. No re-rank,
  no status transition, no new hypothesis — a re-rank without measured
  numbers would be fabrication. Population unchanged: H-C2, H-D, H-B,
  H-Y1 open. NEXT: H-C2 (unchanged — highest expected qualified gain ×
  probability; ~4.4% residual vs Clang on `kernel`, near-identical static
  shape, separable).

- **96 (2026-09-04 13:39 JST, rank pass; host busy, no measurement)**:
  load1 41.73 / 5min 49.68 / 15min 54.33 (up 11 days, 5:26, 9 users, 10
  CPUs) — ~5.6x above the 7.5 quiet limit; per policy no bench,
  perfgate, or hand-patch measurement attempted, no numbers recorded.
  git fetch reviewed: one new commit since ef7ac8dd — 532e9891
  (amu-falsify busy-tick evidence append to H-C2, itself no
  measurement). No new measured numbers against any open hypothesis
  (H-C2, H-D, H-B, H-Y1), so no re-rank, no status transition, no new
  hypothesis — a re-rank without measured numbers would be fabrication.
  Population unchanged. NEXT: H-C2 (unchanged — highest expected
  qualified gain × probability; ~4.4% residual vs Clang on `kernel`,
  near-identical static shape, separable).

- **97 (2026-09-04 13:49 JST, rank pass; host busy, no measurement)**:
  load1 51.26 / 5min 54.62 / 15min 55.00 (up 11 days, 5:36, 8 users, 10
  CPUs) — ~6.8x above the 7.5 quiet limit; per policy no bench, perfgate,
  or hand-patch measurement attempted, no numbers recorded. git fetch
  reviewed: 4 commits on origin/main since HEAD's base, none carrying new
  measured evidence against any open hypothesis (perfgate bridge fix
  6fedc78b, merge d727ec94, rank-only 855b1fe9, ABI test reproduction
  a7e469f2). Top CPU consumers are interactive user processes (java ~121%,
  Chrome ~100%, kotoba-shell-host ~97%) — a user workload, not a fleet
  measurement window. No re-rank, no status transition, no new hypothesis
  — a re-rank without measured numbers would be fabrication. Population
  unchanged: H-C2, H-D, H-B, H-Y1 open (J-B awaiting a quiet host; J-C
  blocked behind J-B). NEXT: H-C2 (unchanged — highest expected qualified
  gain x probability; ~4.4% residual vs Clang on `kernel`,
  near-identical static shape, separable).
- **98 (2026-09-04 14:11 JST, bench pass; host busy, no measurement)**:
  load1 61.81 / 5min 57.51 / 15min 52.66 (up 11 days, 5:59, 9 users,
  10 CPUs) — ~8.2x above the 7.5 quiet limit; per policy no bench,
  perfgate, or hand-patch measurement attempted, no numbers recorded.
  Population unchanged: H-C2, H-D, H-B, H-Y1 open. NEXT: H-C2
  (unchanged).
- **99 (2026-09-04 14:19 JST, rank pass; host busy, no measurement)**:
  load1 45.27 / 5min 52.52 / 15min 52.28 (up 11 days, 6:07, 9 users,
  10 CPUs) — ~6x above the 7.5 quiet limit; per policy no bench, perfgate,
  or hand-patch measurement attempted, no numbers recorded. Top CPU
  consumers are still interactive user processes (java ~162%, Chrome
  ~100%, kotoba-shell-host ~97%, python ~96%) — a user workload, not a
  fleet measurement window. git fetch reviewed: no new commits carrying
  measured evidence against any open hypothesis since iteration 97's
  fetch (only sibling busy-tick entries 98 and this log). No re-rank,
  no status transition, no new hypothesis — a re-rank without measured
  numbers would be fabrication. Population unchanged: H-C2, H-D, H-B,
  H-Y1 open. NEXT: H-C2 (unchanged — highest expected qualified gain ×
  probability; ~4.4% residual vs Clang on `kernel`, near-identical
  static shape, separable).

- **100 (2026-09-04 14:23 JST, bench pass; host busy, no measurement)**:
  load1 44.02 / 5min 47.92 / 15min 50.26 (up 11 days, 6:11, 9 users,
  10 CPUs) — ~5.9x above the 7.5 quiet limit; per policy no bench,
  perfgate, or hand-patch measurement attempted, no numbers recorded.
  iostat 3x1s diagnostic: cpu idle 0%, us 54, sy 24 — busy fraction far
  above the 0.10 quiet-gate limit. Top CPU consumers are interactive user
  processes (java ~123%, Chrome renderer ~99%, kotoba-shell-host ~94%) —
  a user workload, not a fleet measurement window. amu-falsify evidence
  checked: no new "要 quiet-host 測定" item pending. No re-rank, no status
  transition, no new hypothesis — a re-rank without measured numbers would
  be fabrication. Population unchanged: H-C2, H-D, H-B, H-Y1 open. NEXT:
  H-C2 (unchanged — highest expected qualified gain × probability; ~4.4%
  residual vs Clang on `kernel`, near-identical static shape, separable).

- **101 (2026-09-04 14:37 JST, rank pass; host busy, no measurement)**:
  load1 53.53 / 5min 57.12 / 15min 55.58 (up 11 days, 6:26, 9 users,
  10 CPUs) — ~7.1x above the 7.5 quiet limit; per policy no bench,
  perfgate, or hand-patch measurement attempted, no numbers recorded.
  No re-rank, no status transition, no new hypothesis — a re-rank without
  measured numbers would be fabrication. Population unchanged: H-C2, H-D,
  H-B, H-Y1 open. NEXT: H-C2 (unchanged — highest expected qualified gain
  × probability; ~4.4% residual vs Clang on `kernel`, near-identical
  static shape, separable).

- **102 (2026-09-04 14:41 JST, bench pass; host busy, no measurement)**:
  load1 81.20 / 5min 64.75 / 15min 58.73 (up 11 days, 6:29, 9 users,
  10 CPUs) — ~10.8x above the 7.5 quiet limit; per policy no bench,
  perfgate, or hand-patch measurement attempted, no numbers recorded.
  amu-falsify evidence checked: no new "要 quiet-host 測定" item pending.
  No re-rank, no status transition, no new hypothesis — a re-rank without
  measured numbers would be fabrication. Population unchanged: H-C2, H-D,
  H-B, H-Y1 open. NEXT: H-C2 (unchanged — highest expected qualified gain
  × probability; ~4.4% residual vs Clang on `kernel`, near-identical
  static shape, separable).

- **103 (2026-09-04 14:49 JST, rank pass; host busy, no measurement)**:
  load1 46.85 / 5min 55.97 / 15min 57.66 (up 11 days, 6:37, 9 users,
  10 CPUs) — ~6.2x above the 7.5 quiet limit; per policy no bench,
  perfgate, or hand-patch measurement attempted, no numbers recorded.
  Top CPU consumers are interactive user processes (java app server
  ~146%, kotoba-shell-host ~100%, Chrome renderer ~99%, tamaki/kototama
  bb+java jobs ~70%) — a user workload, not a fleet measurement window.
  git fetch reviewed: no new commits carrying measured evidence against
  any open hypothesis since iteration 102's pass. No re-rank, no status
  transition, no new hypothesis — a re-rank without measured numbers
  would be fabrication. Population unchanged: H-C2, H-D, H-B, H-Y1 open.
  NEXT: H-C2 (unchanged — highest expected qualified gain × probability;
  ~4.4% residual vs Clang on `kernel`, near-identical static shape,
  separable).

- **104 (2026-09-04 14:53 JST, bench pass; host busy, no measurement)**:
  load1 45.39 / 5min 48.66 / 15min 53.87 (up 11 days, 6:41, 8 users,
  10 CPUs) — ~6.1x above the 7.5 quiet limit; per policy no bench,
  perfgate, or hand-patch measurement attempted, no numbers recorded.
  Top CPU consumers are interactive user processes (Chrome renderer ~99%,
  java app server ~99%, kotoba-shell-host ~98%, bb ct-watch ~71%) — a user
  workload, not a fleet measurement window. amu-falsify evidence checked:
  no new "要 quiet-host 測定" item pending. No re-rank, no status
  transition, no new hypothesis — a re-rank without measured numbers would
  be fabrication. Population unchanged: H-C2, H-D, H-B, H-Y1 open. NEXT:
  H-C2 (unchanged — highest expected qualified gain × probability; ~4.4%
  residual vs Clang on `kernel`, near-identical static shape, separable).

- **105 (2026-09-04 15:04 JST, rank-only pass; host busy, no measurement)**:
  load1 30.78 / 5min 35.21 / 15min 43.66 (up 11 days, 6:52, 8 users,
  10 CPUs) — ~4.1x above the 7.5 quiet limit; per policy no bench,
  perfgate, or hand-patch measurement attempted, no numbers recorded.
  Top CPU consumers are interactive user processes (Chrome renderer ~100%,
  java app server ~98-99%, kotoba-shell-host ~98%, bb ct-watch ~82%,
  54% node) — a user workload, not a fleet measurement window. git fetch
  reviewed: upstream advanced (loader classpath #774, tranche-three
  aggregate-abi pin #758, perfgate bridge caller fix #771/#772) — none of
  these carry measured evidence against any open hypothesis. No re-rank,
  no status transition, no new hypothesis — a re-rank without measured
  numbers would be fabrication. Population unchanged: H-C2, H-D, H-B, H-Y1
  open. NEXT: H-C2 (unchanged — highest expected qualified gain ×
  probability; ~4.4% residual vs Clang on `kernel`, near-identical static
  shape, separable).

- **106 (2026-09-04 15:39 JST, bench pass; host busy, no measurement)**:
  load1 19.59–22.85 / 5min ~20.9 / 15min ~24 (up 11 days, 7:27, 7 users,
  10 CPUs) — ~2.6x above the 7.5 quiet limit; `top` shows 0.0% idle
  (73.6% user / 26.4% sys), so the J-B confirmatory quiet-host run
  (idle ≥9/10) failed its 10th consecutive gate. Top CPU consumers:
  a kotoba.compiler.cli run (229%, started 15:40 from another worktree —
  bot traffic, not this bot), the cloud.itonami app server JVM (98.6%,
  running since 11:32), Chrome renderer (98%), kotoba-shell-host (96%).
  No bench, perfgate, or falsify measurement attempted, no numbers
  recorded. amu-falsify evidence checked: J-B confirmatory run remains
  pending (jit-cosientist.md tick 9); no other new "要 quiet-host 測定"
  item. Population unchanged: H-C2, H-D, H-B, H-Y1 open. NEXT: H-C2
  (unchanged — highest expected qualified gain × probability; ~4.4%
  residual vs Clang on `kernel`, near-identical static shape,
  separable).

- **107 (2026-09-04 16:13 JST, rank pass; host busy, no measurement)**:
  load1 56.56 / 5min 45.37 / 15min 37.98 (up 11 days, 8:01, 6 users,
  10 CPUs) — ~7.5x above the 7.5 quiet limit; no bench, perfgate, or
  falsify measurement attempted. New evidence reviewed: ADR-0332..0334
  (UEFI alloc-region provenance, fuel-ceiling unification, BOOTX64.EFI
  page write — build-time-OS track, no measured numbers against open
  codegen hypotheses), jit-cosientist tick 10 (J-B quiet gate failed a
  10th consecutive time, still pending a quiet-host rerun),
  lang-cosientist iteration 3 (#() reader shorthand — reader-only gap,
  KIR parity CIDs identical; no codegen effect). No re-rank, no status
  transition: no new measured numbers. Population unchanged: H-C2, H-D,
  H-B, H-Y1 open. NEXT: H-C2 (unchanged — highest expected qualified
  gain x probability; ~4.4% residual vs Clang on `kernel`,
  near-identical static shape, separable).

- **108 (2026-09-04 16:48 JST, bench tick; host busy, no measurement)**:
  load1 37.68 / 5min 43.34 / 15min 41.91 (up 11 days, 8:36, 6 users,
  10 CPUs) — ~5x above the 7.5 quiet limit; no bench, perfgate, or
  falsify measurement attempted. No new evidence reviewed (no new ADR
  since 0334; no new "要 quiet-host 測定" item). No re-rank, no status
  transition: no new measured numbers. Population unchanged: H-C2, H-D,
  H-B, H-Y1 open. NEXT: H-C2 (unchanged — highest expected qualified
  gain x probability; ~4.4% residual vs Clang on `kernel`,
  near-identical static shape, separable).

- **109 (2026-09-04 17:00 JST, amu-rank rank tick; host busy, no measurement)**:
  load1 35.83 / 5m 35.75 / 15m 36.93 (up 11 days, 8:47, 6 users, 10 CPUs) —
  ~4.8x above the 7.5 quiet limit; no bench, perfgate, or falsify
  measurement attempted. New evidence reviewed: lang-cosientist iteration 4
  (commit c7d99a0e) — parse-long hand-patch probe qualified an
  existing-op loop on wasm32 (PASS), pure desugar path ruled out; that is
  a lang-surface result with no codegen-effect number, so no H-C2/H-D/H-B/
  H-Y1 re-rank follows from it. No new ADR since 0334. H-C2 evidence cell
  trimmed: ~50 consecutive host-busy ticks (2026-09-03 10:16 – 09-04
  16:41 JST) condensed to one summary line; full ledger in git history.
  No status transitions: no new measured numbers on any open hypothesis.
  Population unchanged: H-C2, H-D, H-B, H-Y1 open. NEXT: H-C2 (unchanged
  — highest expected qualified gain x probability; ~4.4% residual vs
  Clang on `kernel`, near-identical static shape, separable).

## Standing honesty constraints

Every number above is one host on one day; the falsification numbers are
diagnostic (levi's ambient load ~1.8, below the 7.5 sanity limit but not a
claim-grade quiet window). Cross-run absolutes on gad are not comparable
(observed 2x), and iteration 49 showed within-run vs-gcc RATIOS drift
day over day as well (1.2325 vs 1.365 for byte-similar binaries) -- a
lever's verdict requires a same-run candidate-vs-candidate A/B. No entry
in this file is a claim; claims are
sealed artifacts that only the gated pipeline emits. If an iteration's
measured verdict contradicts this table, the table is what gets edited.
