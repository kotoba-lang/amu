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
| H-E | functions with calls + branches take the conservative all-vreg path (+33% at 24 live values); add call-clobber handling to the scan | open — the fix is already named in performance.md; the six claim domains exercise it lightly | measured 2026-08-18 tables in performance.md |
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
- **19 (next)**: re-run the six-domain competitive suite on this pin to
  re-score the 30-pair matrix — narrow-arithmetic entered this loop at
  −6.5/−6.9/−7.7% vs rustc/clang/swift and its emission now matches
  clang-raw at parity, so the question is what perfgate certifies on the
  full harness. Then rank the next gap from the fresh matrix
  (call-preservation −5.0/−5.7% is the largest remaining claim-relevant
  deficit; its fixtures also contain quotient tails).

## Standing honesty constraints

Every number above is one host on one day; the falsification numbers are
diagnostic (levi's ambient load ~1.8, below the 7.5 sanity limit but not a
claim-grade quiet window). No entry in this file is a claim; claims are
sealed artifacts that only the gated pipeline emits. If an iteration's
measured verdict contradicts this table, the table is what gets edited.
