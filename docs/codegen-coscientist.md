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
| H-C2 | the remaining ~4.4% vs Clang on `kernel` after H-C: the mutated stream and clang's are now near-identical in shape (62 vs 61 instructions; amu-mut still loads the now-dead `0x7fffffff` constant), so the residue is scheduling/front-end shaped | open — generate from an instruction-order diff | pending |
| H-D | `kernel_batch` loop-path remainder (~8% vs Rust diagnostic, refused `:too-noisy` in ADR 0281): body scheduling / per-iteration instruction mix | open; measurement first needs the noise fixed (H-B) or the loop lengthened | ADR 0279 measured 1.349x behind pre-#653..#660; levi 2026-08-29 read 1.08x diagnostic |
| H-B | batch-fixture noise (rsd 0.47 vs policy 0.10) is scheduler migration of a long single-call region across P/E cores; pin the timed region's QoS | open | performance.md already documents an E-core migration incident |
| H-E | call-crossing values go to stack slots instead of the callee-saved registers the prologue already spends: `kernel_call` saves x19–x26 yet stores/loads all eight call results through the stack (8 STR + 11 LDR + 3 constant-mov round-trips) | **hand-falsified — iteration 20: +6.66% separated (5.19 → 4.84 ns), fuel contract intact, past clang's 5.03**. Compiler work: assign call-crossing values to the preserved tier in the scan | performance.md's conservative-path tables; iteration-20 fixture retained in `levi:~/amu-evidence/` |
| H-F | protect domains where amu already leads (kernel_wide +7% vs rustc diagnostic) with byte-accurate regressions | standing | #637–#639 pattern |

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
- **22 (next)**: six-domain re-score on this pin. call-preservation
  entered the loop at −5.0/−5.7% and its fixture now measures ~6% ahead of
  both; branch-call and loop-call also contain calls and may move. Then
  rank what remains from the fresh matrix (deep-spill vs rustc/zig was
  −3.8/−2.6%).

## Standing honesty constraints

Every number above is one host on one day; the falsification numbers are
diagnostic (levi's ambient load ~1.8, below the 7.5 sanity limit but not a
claim-grade quiet window). No entry in this file is a claim; claims are
sealed artifacts that only the gated pipeline emits. If an iteration's
measured verdict contradicts this table, the table is what gets edited.
