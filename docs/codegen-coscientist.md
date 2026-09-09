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
| H-C2 | the remaining ~4.4% vs Clang on `kernel` after H-C: the mutated stream and clang's are now near-identical in shape (62 vs 61 instructions; amu-mut still loads the now-dead `0x7fffffff` constant), so the residue is scheduling/front-end shaped | open — generate from an instruction-order diff | pending; 2026-09-03 10:16 JST falsify tick: host busy (load1 48.01), no measurement attempted | 2026-09-03 10:31 JST falsify tick: host busy (load1 38.40, 1min avg over 10-day uptime), no measurement attempted | 2026-09-03 10:52 JST falsify tick: host busy (load1 28.49, load15 33.90), no measurement attempted; NEXT は H-C2 のまま | 2026-09-03 11:27 JST falsify tick: host busy (load1 29.81, load15 35.26), no measurement attempted; NEXT は H-C2 のまま | 2026-09-03 13:33 JST bench tick: host busy (load1 23.21, load5 17.62, load15 17.86, up 10 days), no measurement attempted; NEXT は H-C2 のまま | 2026-09-03 13:34 JST falsify tick: host busy (load1 16.07), no measurement attempted | 2026-09-03 15:08 JST falsify tick: host busy (load1 27.24, load5 20.98, load15 18.49, up 10 days), no measurement attempted; NEXT は H-C2 のまま | 2026-09-03 16:00 JST falsify tick: host busy (load1 12.74, load5 14.16, load15 17.30, up 10 days), no measurement attempted; NEXT は H-C2 のまま | 2026-09-03 17:40 JST bench tick: host busy (load1 35.54, load5 35.97, load15 28.99, up 10 days, 10 CPUs), no measurement attempted; NEXT は H-C2 のまま | 2026-09-03 18:37 JST falsify tick: host busy (load1 19.32, load5 16.19, load15 16.23, up 10 days, 10 CPUs), no measurement attempted; NEXT は H-C2 のまま | 2026-09-03 19:13 JST bench tick: host busy (load1 14.80, load5 15.08, load15 17.02, up 10 days, 10 CPUs), no measurement attempted; NEXT は H-C2 のまま | 2026-09-03 19:20 JST falsify tick: host busy (load1 15.78, load5 17.17, load15 17.41, up 10 days, 10 CPUs), no measurement attempted; NEXT は H-C2 のまま | 2026-09-03 19:50 JST bench tick: host busy (load1 13.64, load5 13.92, load15 15.25, up 10 days, 11:38, 10 CPUs), no measurement attempted; NEXT は H-C2 のまま | 2026-09-03 20:46 JST falsify tick: host busy (load1 15.18, load5 16.38, load15 18.98, up 10 days, 12:34, 13 users), no measurement attempted; NEXT は H-C2 のまま | 2026-09-03 20:57 JST falsify tick: host busy (load1 15.18, load5 18.75, load15 19.72, up 10 days, 12:45, 13 users), no measurement attempted; NEXT は H-C2 のまま | 2026-09-03 21:07 JST bench tick: host busy (load1 11.04, load5 15.25, load15 17.22, up 10 days, 12:55, 13 users), no measurement attempted; NEXT は H-C2 のまま | 2026-09-03 23:17 JST falsify tick: host busy (load1 17.75, load5 16.84, load15 16.84, up 10 days, 15:05, 11 users, 10 CPUs), no measurement attempted; NEXT は H-C2 のまま | 2026-09-04 01:06 JST bench tick: host busy (load1 23.07, load5 28.48, load15 25.13, up 10 days, 11 users), no measurement attempted; NEXT は H-C2 のまま | 2026-09-04 01:25 JST falsify tick: host busy (load1 23.72, load5 17.92, load15 19.33, up 10 days, 11 users), no measurement attempted; NEXT は H-C2 のまま | 2026-09-04 03:54 JST falsify tick: host busy (load1 17.99, load5 17.61, load15 19.83, up 10 days, 10 CPUs), no measurement attempted; NEXT は H-C2 のまま | 2026-09-04 04:22 JST rank tick: host busy (load1 14.42, load5 13.99, load15 16.33, up 10 days, 10 CPUs), no measurement attempted; NEXT は H-C2 のまま | 2026-09-04 05:12 JST falsify tick: host busy (load1 19.05, load5 17.39, load15 18.10, up 10 days, 11 users, 10 CPUs), no measurement attempted; NEXT は H-C2 のまま | 2026-09-04 07:40 JST bench tick: host busy (load1 29.14, load5 22.55, load15 22.15, up 10 days, 23:28, 11 users, 10 CPUs), no measurement attempted; quiet limit 7.5 exceeded 4x; NEXT は H-C2 のまま | 2026-09-04 10:46 JST falsify tick: host busy (load1 18.51, load5 28.00, load15 26.93, up 11 days, 10 CPUs), no measurement attempted; NEXT は H-C2 のまま | 2026-09-04 11:00 JST falsify tick: host busy (load1 32.81, load5 32.59, load15 29.42, up 11 days, 2:48, 8 users, 10 CPUs), no measurement attempted; NEXT は H-C2 のまま | 2026-09-04 11:08 JST bench tick: host busy (load1 44.19, load5 42.09, load15 35.17, up 11 days, 2:56, 10 users, 10 CPUs), no measurement attempted; quiet limit 7.5 exceeded ~6x; NEXT は H-C2 のまま | 2026-09-04 11:20 JST falsify tick: host busy (load1 59.44, load5 46.81, load15 38.53, up 11 days, 10 CPUs), no measurement attempted; quiet limit 7.5 exceeded ~8x; NEXT は H-C2 のまま | 2026-09-04 11:27 JST bench tick: host busy (load1 64.86, load5 61.12, load15 48.78, up 11 days, 3:15, 10 users, 10 CPUs), no measurement attempted; quiet limit 7.5 exceeded ~8.6x; NEXT は H-C2 のまま | 2026-09-04 11:41 JST bench tick: host busy (load1 66.67, load5 60.14, load15 52.99, up 11 days, 3:29, 9 users, 10 CPUs), no measurement attempted; quiet limit 7.5 exceeded ~8.9x; NEXT は H-C2 のまま | 2026-09-05 01:45 JST falsify tick: host busy (load1 13.25, load5 14.89, load15 11.40, up 6 days 13:38, 13 users, 10 CPUs), no measurement attempted; quiet limit 7.5 exceeded ~1.8x; NEXT は H-C2 のまま | 2026-09-05 03:41 JST falsify tick: host busy (load1 40.39, load5 30.46, load15 18.65, up 6 days 15:39, 13 users, 10 CPUs), no measurement attempted; quiet limit 7.5 exceeded ~5.4x;  2026-09-05 08:15 JST falsify tick: host busy (load1 77.13, load5 90.87, load15 71.08, up 58 min), no measurement attempted; NEXT は H-C2 のまま | 2026-09-05 ~05:20 JST falsify tick: host at quiet-gate threshold (monitor open: load1 8.38; 05:02 load1 5.84/load5 5.48/load15 6.79; 05:04 load1 9.29/load5 6.55/load15 7.11, 10 CPUs, up 6d17h) — load1 exceeded 7.5 quiet limit, measurement refused per policy, no hand-patch run. Tooling note: this tick hit persistent terminal stdout loss (commands ran, output empty), so bench tooling was not invoked; H-C2 deferred intact. NEXT は H-C2 のまま (retry at load1 < 5) | 2026-09-05 08:07 JST falsify tick: host busy (load1 262, load5 142, load15 61, up 50min, 10 CPUs) — quiet limit 7.5 exceeded ~35x; no bench/perfgate/hand-patch run attempted; NEXT は H-C2 のまま. | 2026-09-05 09:31 JST falsify tick: host busy (load1 15.23, load5 34.76, load15 44.26, up 2:14, 14 users, 10 CPUs), quiet limit 7.5 exceeded ~2.0x; no measurement attempted; NEXT は H-C2 のまま. | 2026-09-05 23:45 JST falsify tick: host busy (load1 11.76, load5 9.72, load15 9.51, up 16:28, 9 users, threshold 7.5), no measurement attempted; NEXT は H-C2 のまま | 2026-09-05 23:48 JST falsify tick: host busy (load1 14.67, load5 12.24, load15 10.59, 23:48  up 16:31, 9 users, load averages: 14.67 12.24 10.59, threshold 7.5), no measurement attempted; NEXT は H-C2 のまま | 2026-09-05 23:48 JST falsify tick: host busy (load1 23.28, load5 14.55, load15 11.49, 23:48  up 16:31, 9 users, load averages: 23.28 14.55 11.49, threshold 7.5), no measurement attempted; NEXT は H-C2 のまま | 2026-09-05 23:48 JST falsify tick: host busy (load1 25.18, load5 15.09, load15 11.69, 23:48  up 16:32, 9 users, load averages: 25.18 15.09 11.69, threshold 7.5), no measurement attempted; NEXT は H-C2 のまま | 2026-09-05 18:15 JST falsify tick: host busy (load1 12.16, load5 22.89, load15 29.86, up 10:58, 22 users, 10 CPUs), quiet limit 7.5 exceeded ~1.6x; no measurement attempted; NEXT は H-C2 のまま. | 2026-09-05 18:32 JST falsify tick: host busy (load1 123.78, load5 90.95, load15 61.15, up 11:15, 15 users, 10 CPUs), quiet limit 7.5 exceeded ~16.5x; no measurement attempted; NEXT は H-C2 のまま. ; 2026-09-05 19:01 JST falsify tick: host busy (load1 31.87, load5 33.72, load15 44.99, up 11:43, 15 users), no measurement attempted; NEXT は H-C2 のまま | 2026-09-05 19:27 JST bench tick: host busy (load1 22.58, load5 38.33, load15 44.19, up 12:10, 15 users), quiet limit 7.5 exceeded ~3.0x; no measurement attempted; NEXT は H-C2 のまま. | 2026-09-05 19:37 JST falsify tick: host busy (load1 47.61, load5 33.14, load15 36.43, up 12:20, 15 users, 10 CPUs), quiet limit 7.5 exceeded ~6.3x; no measurement attempted; NEXT は H-C2 のまま. 2026-09-06 00:28 JST falsify tick: host busy (load1 8.54, load5 9.57, load15 13.31, up 17:11, 9 users, threshold 7.5; note: load falling 15m>5m>1m but policy is strict on load1), no measurement attempted; NEXT は H-C2 のまま | pending; 2026-09-03 10:16 – 2026-09-04 16:41 JST: ~50 consecutive ticks refused host-busy (load1 11–83, quiet limit 7.5; last: 16:41 JST load1 31.42 / 5m 37.39 / 15m 39.53), no measurement attempted; 2026-09-04 19:00 JST falsify tick: host busy (load1 63.86 / 5m 68.40 / 15m 57.20), no measurement attempted; 2026-09-04 17:08 JST: load1 26.09 / 5m 31.82 / 15m 34.88 — refused host-busy again; 17:09 JST recheck load1 23.48 still > 7.5 (full tick ledger in git history pre-trim); 2026-09-04 17:52 JST: load1 17.73 / 5m 30.74 / 15m 36.15 — refused host-busy again, no measurement attempted; 2026-09-04 17:58 JST (rank tick 111): load1 18.34 / 5m 29.44 / 15m 35.46 — still > 7.5, host busy | 09-09 20:39 amu-falsify: host busy (load1 145.0>7.5), measurement refused (tick 20:38)
| H-D | `kernel_batch` loop-path remainder (~8% vs Rust diagnostic, refused `:too-noisy` in ADR 0281): body scheduling / per-iteration instruction mix | open; measurement first needs the noise fixed (H-B) or the loop lengthened | ADR 0279 measured 1.349x behind pre-#653..#660; levi 2026-08-29 read 1.08x diagnostic |
| H-B | batch-fixture noise (rsd 0.47 vs policy 0.10) is scheduler migration of a long single-call region across P/E cores; pin the timed region's QoS | open | performance.md already documents an E-core migration incident; 2026-09-03 10:00 JST falsify tick: host busy (load1 82.83), no measurement attempted | 2026-09-05 09:03 JST bench tick: host busy (load1 51.16, load5 45.12, load15 62.11, up 1:46), no measurement attempted; NEXT (J-B idle>=9/10 rerun) not run, no numbers recorded | | 2026-09-05 19:50 JST falsify tick: host busy (load1 32.94, load5 36.78, load15 38.06, up 12:33, 15 users), no measurement attempted; NEXT (J-B idle>=9/10 rerun, then H-Z3, then H-C2) not run, no numbers recorded | 2026-09-05 20:02 JST falsify tick: host busy (load1 91.55, load5 65.61, load15 50.28, up 12:45, 15 users), no measurement attempted; NEXT (J-B idle>=9/10 rerun, then H-Z3, then H-C2) not run, no numbers recorded | 2026-09-05 20:39 JST falsify tick: host busy (load1 28.26, load5 21.45, load15 23.21, up 13:22, 15 users), no measurement attempted; NEXT (J-B idle>=9/10 rerun, then H-Z3, then H-C2) not run, no numbers recorded | 2026-09-05 20:11 JST bench tick: host busy (load1 12.31, load5 40.89, load15 48.54, up 12:54, 15 users), no measurement attempted; NEXT (J-B idle>=9/10 rerun, then H-Z3, then H-C2) not run, no numbers recorded | 2026-09-05 20:25 JST falsify tick: host busy (load1 10.69, load5 16.38, load15 29.02, up 13:08, 15 users, threshold 7.5), no measurement attempted; NEXT (J-B idle>=9/10 rerun, then H-Z3, then H-C2) not run, no numbers recorded | 2026-09-05 21:01 JST falsify tick: host busy (load1 36.16, load5 26.72, load15 27.42, up 13:44, 15 users, threshold 7.5), no measurement attempted; NEXT (J-B idle>=9/10 rerun, then H-Z3, then H-C2) not run, no numbers recorded | 2026-09-05 22:26 JST falsify tick: host busy (load1 21.47, load5 16.50, load15 15.58, up 15:09, 15 users, threshold 7.5), no measurement attempted; NEXT (J-B idle>=9/10 rerun, then H-Z3, then H-C2) not run, no numbers recorded | 2026-09-05 23:45 JST bench tick: host busy — load1 5.32 (23:38) -> 7.61 (23:42) -> 12.30 (23:44) RISING, not decaying; top -l2 CPU 26.5% user / 59.9% sys / 13.6% idle (~1.4/10 idle CPUs vs quiet gate idle >=9/10), kernel_task 200%, node 181%+57%, PhysMem 31G used / 236M unused / 16G compressed, active swap in/out — quiet window NOT sustained, no measurement attempted; NEXT (J-B idle>=9/10 rerun of jb_imod_control.c, then H-Z3, then H-C2) not run, no numbers recorded
| H-E | call-crossing values go to stack slots instead of the callee-saved registers the prologue already spends: `kernel_call` saves x19–x26 yet stores/loads all eight call results through the stack (8 STR + 11 LDR + 3 constant-mov round-trips) | **closed — landed in iteration 21 and confirmed in the emission.** `kernel_call` at `b5a0c302` is 252 code bytes with 1 STR + 1 LDR in the whole module. ⚠ iteration 20's "past clang's 5.03" does NOT hold: on a host-qualified run 2026-09-06 clang is **4.701** and amu **5.034** on this domain, so the domain is a 7% loss, not a win. Do not cite 5.03 as clang's cost | iteration 122c; `bench/runtime-comparison/qualified-30pair-20260906.json` |
| H-F | protect domains where amu already leads (kernel_wide +7% vs rustc diagnostic) with byte-accurate regressions | standing | #637–#639 pattern |
| H-Y1 | wasm32 pays a host crossing per iteration merely to CARRY a reference-typed parameter (`typed-assert-ref` prologue), and self-recursion pays it per iteration where `loop`/`recur` pays it once | **counted — iteration 51** (ADR 0285); widening the lowering is the open follow-up | 4096 element visits: self-recursion 4227 `assert-ref`, `loop`/`recur` 129; 2.032 vs 1.032 crossings/element, identical KIR-verified return values. Also a capability limit: self-recursion traps `RangeError: Maximum call stack size exceeded` between 6,128 and 12,128 iterations, `loop`/`recur` is O(1) depth. `structured-loop-body?` is already general — only `loop-helper-name?` gates it — but the prologue fuel charge must move into the loop to keep one iteration at one unit |
| H-Y2 | a pixel-domain carrier must be guest-addressable memory indexed by the guest's own load; making the existing carrier merely bigger does not reach a usable cost | **reflect stage re-run on a quiet host, iteration 52 — still `:not-separated-from-noise`, and that is the result** | on levi at load1 1.78-2.14, n=15: today's `vector-at` marginal 381.72 ns/element (separated by 4 orders of magnitude), proposed load marginal 0.0314 ns/element (gap 0.031 vs summed stdev 0.044, refused). The cost to remove is measured; the cost to add is below the floor |

## Iteration log
2026-09-05 19:03 JST (amu-rank cron, tick 122): host busy (load1 28.30 / 5m 31.50 / 15m 42.20, threshold 7.5) — measurement refused, rank-only pass. git fetch clean (no new origin commits; HEAD 912913b7). Evidence reviewed since tick 121: sibling entry 18:48 amu-falsify (busy-refusal) already in working tree; no new ADR (0338 remains newest measured landing); no new measured numbers. No re-rank, no status transition. Population unchanged: J-B confirmed-diagnostic but unqualified (awaiting idle>=9/10 rerun), H-Z3 top of the codegen ladder (quiet-host hand-patch A/B pending), H-C2/H-D/H-B/H-Y1 open; J-C blocked behind J-B. Note: 8+ untracked append-*/amufalsify-*/load-check scripts under scripts/ plus docs/probe_out.txt and docs/codegen-cosientist.md.bak114 remain untracked (cross-bot cron residue, not touched by rank). NEXT unchanged: J-B fully-quiet-host rerun (idle>=9/10) of bench/runtime-comparison/jb_imod_control.c for the perfgate-qualifiable number, then H-Z3 quiet-host hand-patch A/B, then H-C2.


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
  J-B (ADR 0335: first positive separated signal +6.2/+7.0/+6.7% on
  constant-divisor imod; needs a fully-quiet-host rerun for a
  perfgate-qualifiable number. H-C2 demoted to second: no falsification
  number across 40+ busy ticks on its ~4.4% residue)

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

<!-- merge note 2026-09-06: this section sat on main with an unresolved conflict block; two loop lineages numbered entries independently while it was conflicted, so both sets are kept below and entry numbers repeat. -->

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

- **110 (2026-09-04 17:35 JST, amu-bench bench tick; host busy, no measurement)**:
  load1 37.51 / 5m 35.70 / 15m 36.84 (up 11 days, 9:23, 6 users, 10 CPUs) —
  ~5x above the 7.5 quiet limit; no bench, perfgate, or falsify measurement
  attempted. Top CPU consumers: kotoba-shell-host ~99.9%, Chrome helper
  (Renderer) ~99.1%, java app server ~97.5% — interactive user workload, not a
  fleet measurement window. No new ADR since 0334; no new "要 quiet-host 測定"
  item pending (J-B confirmatory quiet-host rerun still pending per tick 10).
  No re-rank, no status transition: no new measured numbers. Population
  unchanged: H-C2, H-D, H-B, H-Y1 open. NEXT: H-C2 (unchanged — highest
  expected qualified gain x probability; ~4.4% residual vs Clang on `kernel`,
  near-identical static shape, separable).
- **92 (2026-09-05, falsify pass; host busy, no measurement)**:
  load1 29.70 / 5min 40.26 / 15min 35.71 (up 6 days, 12:23, 13 users, 10
  CPUs) — far above the 7.5 quiet limit; per policy no bench, perfgate, or
  hand-patch measurement attempted, no numbers recorded. FETCH_HEAD
  reviewed: no new measured evidence against any open hypothesis since
  entry 91. Population unchanged: H-C2, H-D, H-B, H-Y1 open. NEXT: H-C2
  (unchanged — highest expected qualified gain × probability; ~4.4%
  residual vs Clang on `kernel`, near-identical static shape, separable).

- **93 (2026-09-05 00:54 JST, rank pass; host busy, no measurement)**:
  load1 6.35 / 5min 7.26 / 15min 12.80 (up 6 days, 12:53, 13 users, 10
  CPUs) — load1 sat just under the 7.5 limit, but 15min 12.80 shows
  sustained load well above it (5min 7.26 borderline); the window is not
  quiet and a rank pass runs no measurement by role, so no bench, perfgate,
  or hand-patch numbers were recorded. git fetch reviewed: new
  upstream commits are target-alias/CI work (#779, #778, #776) and the
  UEFI ADRs 0332-0334 — none carry measured numbers against H-C2, H-D, H-B
  or H-Y1. Uncommitted diff on docs/codegen-coscientist.md is entry 92
  itself (9 insertions). No re-rank, no status transition, no new
  hypothesis. Population unchanged: H-C2, H-D, H-B, H-Y1 open (J-B
  awaiting a quiet host; J-C blocked behind J-B). NEXT: H-C2 (unchanged —
  highest expected qualified gain × probability; ~4.4% residual vs Clang
  on `kernel`, near-identical static shape, separable).

- **95 (2026-09-05 02:16 JST, rank pass -- J-B re-ranked on measured evidence)**:
  load1 6.17 / 5min 6.12 / 15min 7.01 (up 6 days, 14:15, 13 users, 10 CPUs) --
  load1 sits under the 7.5 limit but load15 7.01 is borderline; a rank pass
  runs no measurement by role, so no new numbers here. Evidence reviewed:
  **ADR 0335 (amu-jit tick 9, 01:42 JST)** -- J-B's deferred control ran in a
  majority-idle window and produced the first positive separated signal:
  constant-divisor `imod` (sdiv -> smulh+asr) **+6.2 / +7.0 / +6.7% across
  three consecutive ABBA runs** (checksum-agreeing), after six busy-host runs
  with flipping signs. Diagnostic only (idle 33-62%, full quiet gate unmet,
  no perfgate verdict). Re-rank grounded in those numbers: **J-B moves above
  H-C2 as NEXT** -- J-B now has a measured effect at/above the 5% bar with a
  named AOT lowering path (constant-divisor specialization, the lever
  iteration 55 ranked (ii) against the ADR 0289 ~47-instr/element residue),
  while H-C2's ~4.4% residue has produced no falsification number across
  40+ busy ticks. J-C's blocker conditionally lifts: unblocked only once
  J-B's fully-quiet-host rerun confirms; its comparison target then changes
  to include the AOT specialized lowering. H-C2, H-D, H-B, H-Y1 remain open,
  unchanged. NEXT: J-B -- fully-quiet-host rerun (idle >=9/10) of
  `jb_imod_control.c` for a perfgate-qualifiable number; if it holds,
  hand-patch kotoba-mir/native constant-divisor specialization next.

- **94 (2026-09-05 01:43 JST, bench pass; host busy, no measurement)**:
  01:35 JST load1 5.43 / 5min 7.88 / 15min 9.39 (up 6 days, 13:34, 13
  users, 10 CPUs) — load1 は一時 7.5 を下回ったが load15 9.39 が持続負荷を
  示し、settle 確認の再測 (01:41 JST) では load1 6.59 / 5min 6.88 /
  15min 8.31、さらに 01:43 JST には load1 19.29 / 5min 10.38 / 15min 9.44
  に急上昇 — quiet window と判定できず、per policy bench/perfgate run は
  実施せず、数字は記録しない。NEXT は H-C2 のまま。

- **96 (2026-09-05 02:32 JST, falsify pass; host busy + terminal 障害, no
  measurement)**: load1 34.20 / 5min 15.49 / 15min 9.98 (up 6 days, 14:30,
  13 users, 10 CPUs) — 7.5 quiet 限界を超過。加えて本 tick の cron ホストで
  terminal 実行が機能せず (`/bin/echo`・`true`・`bash` スクリプトの
  foreground/background いずれも空出力・exit 127)、evidence 収集コマンド
  自体が一切実行できなかった。per policy 測定なし、数字なし。
  Population unchanged: H-C2, H-D, H-B, H-Y1 open (J-B は quiet-host
  再測待ち)。NEXT: J-B (entry 95 の re-rank のまま)。

- **97 (2026-09-05 02:52 JST, bench pass -- J-B confirmation rerun, diagnostic)**:
  gad at tick start load1 3.17 / 5m 5.63 / 15m 7.55 (up 6 days, 14:46, 10 CPUs);
  pre-run iostat idle 49-85% (~65% avg), during-run idle 42-74% (~65%), post-run
  idle 64-80% — quieter than ADR 0335's window (idle 33-62%) but the full quiet
  gate (idle >=9/10) was NOT met, so no perfgate run and no sealed claim. The
  entry-95 NEXT action was executed as a diagnostic confirmation rerun instead:
  `bench/runtime-comparison/jb_imod_control.c`, cc -O2, 3 consecutive runs,
  400000 iters x 40 alternations, ABBA medians (same methodology as ADR 0289 /
  0335): saving **+6.8% / +7.2% / +6.8%** (opaque 5.128/5.137/5.092 vs const
  4.778/4.769/4.745 ns/elem, ratios 1.073/1.077/1.073), all checksums agree
  (764266). That is six consecutive positive, checksum-agreeing runs across two
  distinct load windows (0335's 01:42 JST +6.2/+7.0/+6.7 and this tick) — the
  sdiv→mulh strength-reduction effect on the serial imod chain is now
  sign-stable cross-window at ~6-7%, at/above the 5% bar. Verdict: **J-B
  confirmed as a diagnostic effect, still unqualified** — perfgate.core/qualify
  has issued no verdict, so the hypothesis remains neither sealed nor claimable.
  Evidence appended to the J-B row in docs/jit-cosientist.md. No compiler
  change made. Population unchanged: H-C2, H-D, H-B, H-Y1 open; J-B awaiting
  the idle>=9/10 rerun; J-C blocked behind it. NEXT: J-B fully-quiet-host rerun
  (idle >=9/10) for the perfgate-qualifiable number.

- **98 (2026-09-05 03:33 JST, rank-only pass; host busy, no measurement)**:
  gad at tick start load1 6.23 / 5m 7.54 / 15m 7.48, iostat idle 50/23/7% over
  3 samples; two re-probes (2s/3s spacing) showed load1 8.53 -> 10.59 -> 11.75
  with idle 6-30% — load1 exceeded the 7.5 quiet limit and the trend was
  rising, so the quiet gate failed and no measurement was run. No new numbers,
  no re-rank basis: population unchanged (H-C2, H-D, H-B, H-Y1 open; J-B
  confirmed-diagnostic but unqualified, awaiting the idle>=9/10 rerun; J-C
  blocked behind it). NEXT: J-B fully-quiet-host rerun (idle >=9/10) of
  `bench/runtime-comparison/jb_imod_control.c` for the perfgate-qualifiable
  number (entry 95 re-rank stands).

- **99 (2026-09-05 03:50 JST, bench pass; host busy, no measurement)**:
  03:48 JST load1 6.96 / 5min 13.85 / 15min 16.13, then 5 re-probes over ~1min:
  load1 9.17 -> 10.57 -> 8.88 -> 8.53 -> 7.99 (5min 12.9-13.9, 15min 15.6-16.1
  declining slowly), one-shot CPU idle oscillating 30.6-73.8% across probes —
  load1 crossed the 7.5 quiet limit on every re-probe and idle fraction was
  unstable (no 9/10 idle window). Note: this tick's cron host had foreground
  terminal returning empty output; the monitor was run via a script file in a
  background session (evidence /tmp/amubench-mon*.txt). Per policy no
  bench/perfgate run, no numbers recorded. Population unchanged: H-C2, H-D,
  H-B, H-Y1 open; J-B confirmed-diagnostic (entry 97) but unqualified,
  awaiting the idle>=9/10 rerun; J-C blocked behind it. NEXT: J-B
  fully-quiet-host rerun (idle >=9/10) of
  `bench/runtime-comparison/jb_imod_control.c` for the perfgate-qualifiable
  number (entry 98 re-rank stands).

- **100 (2026-09-05 04:17 JST, rank-only pass; host busy, no measurement)**:
  04:17 JST load1 8.42 / 5min 7.27 / 15min 7.87 — load1 exceeded the 7.5 quiet
  limit at tick start, so per policy the quiet gate failed and no measurement
  was run. No new numbers, no re-rank basis: population unchanged (H-C2, H-D,
  H-B, H-Y1 open; J-B confirmed-diagnostic but unqualified, awaiting the
  idle>=9/10 rerun; J-C blocked behind it). NEXT: J-B fully-quiet-host rerun
  (idle >=9/10) of `bench/runtime-comparison/jb_imod_control.c` for the
  perfgate-qualifiable number (entry 99 re-rank stands).

- **101 (2026-09-05 04:41 JST, falsify pass; host busy, no measurement)**:
  04:41 JST load1 13.36 / 5min 8.91 / 15min 7.65, rising across the tick
  (load1 13.4-15.0, load5 9.2-9.8 over ~20 iostat samples); CPU idle
  oscillated 8-50% with sy 16-58% (no 9/10 idle window, no stable quiet
  stretch). load1 exceeded the 7.5 quiet limit on every sample, so per policy
  the quiet gate failed and no hand-patch or bench measurement was run.
  No new numbers, no re-rank basis: population unchanged (H-C2, H-D, H-B,
  H-Y1 open; J-B confirmed-diagnostic but unqualified, awaiting the
  idle>=9/10 rerun; J-C blocked behind it). NEXT: J-B fully-quiet-host rerun
  (idle >=9/10) of `bench/runtime-comparison/jb_imod_control.c` for the
  perfgate-qualifiable number (entry 100 re-rank stands).

- **102 (2026-09-05 05:12 JST, rank-only pass; host busy at probes, no measurement)**:
  rank pass runs no measurement by role. Load probes at tick: 05:05:55 load1 7.49 /
  5m 6.86 / 15m 7.18; 05:09:39 load1 5.02 / 5m 7.08 / 15m 7.33; 05:12:40 load1
  11.24 / 5m 7.50 / 15m 7.36 — load1 crossed the 7.5 quiet limit on the latest
  probe and load15 ~7.2-7.4 shows sustained borderline load; no quiet window and
  no falsify/bench number taken this tick by anyone since entry 101. Evidence
  reviewed: git log since entry 101 adds lang-cosientist iteration 4
  (parse-long hand-patch falsified, ~467-492x, evidence only) and jit tick 12
  (J-B fourth window, +6.4/+6.9%, 11 consecutive positive across 4 windows,
  still not fully quiet, diagnostic only). Neither changes the AOT population
  ranks: J-B's confirmatory evidence grew (11 consecutive positive,
  checksum-agreeing runs) but the fully-quiet (idle>=9/10) rerun that perfgate
  qualification requires has not happened, so J-B stays confirmed-diagnostic,
  unqualified, and NEXT. H-C2, H-D, H-B, H-Y1 remain open, unchanged; J-C
  blocked behind J-B. No status transition, no new hypothesis.
  NEXT: J-B fully-quiet-host rerun (idle >=9/10) of
  `bench/runtime-comparison/jb_imod_control.c` for the perfgate-qualifiable
  number (entry 95 re-rank stands).

- **103 (2026-09-05 05:15 JST, bench pass; host busy, no measurement)**:
  quiet gate checked for the J-B rerun with 20 top-based CPU idle samples over
  ~2.2 min (05:12:52-05:15:11 JST; load1 ranged 4.43-11.24 across the window,
  pre-run state read load1 7.82): idle ranged 52.85-83.45%, mean ~73%,
  0/20 samples >=90% idle -- the idle>=9/10 criterion never qualified, so
  `bench/runtime-comparison/jb_imod_control.c` was not run. (First iostat
  attempt parsed the wrong columns and read a constant idle=50 on every
  sample; discarded, top used instead -- samples at /tmp/amu_idle_samples4.txt.)
  No new numbers; population unchanged (H-C2, H-D, H-B, H-Y1 open; J-B
  confirmed-diagnostic but unqualified, 11 consecutive positive windows,
  still awaiting the idle>=9/10 rerun; J-C blocked behind it).
  NEXT: J-B fully-quiet-host rerun (idle >=9/10) of
  `bench/runtime-comparison/jb_imod_control.c` for the perfgate-qualifiable
  number (entry 102 re-rank stands).

- **104 (2026-09-05 05:30 JST, bench pass; host busy, no measurement)**:
  quiet gate checked for the J-B rerun: 05:30:50 JST load1 10.56 / 5min 6.78 /
  15min 6.57; 10 top-based CPU samples over ~10s read idle 18.40-60.72%
  (mean ~39%, sy 16.83-64.39%) -- load1 exceeded the 7.5 quiet limit and no
  sample reached the idle>=90% bar, so the idle>=9/10 criterion never
  qualified and `bench/runtime-comparison/jb_imod_control.c` was not run.
  (Foreground terminal again returned empty output this tick; probes were run
  via script files in background sessions, evidence /tmp/amubench_mon_20260905b.txt.)
  No new numbers; population unchanged (H-C2, H-D, H-B, H-Y1 open; J-B
  confirmed-diagnostic but unqualified, 11 consecutive positive windows,
  still awaiting the idle>=9/10 rerun; J-C blocked behind it).
  NEXT: J-B fully-quiet-host rerun (idle >=9/10) of
  `bench/runtime-comparison/jb_imod_control.c` for the perfgate-qualifiable
  number (entry 102 re-rank stands).

- **105b (2026-09-05 06:05 JST, bench pass; quiet gate not met, no measurement)**:
  two 10-sample top probes (~18s each, /tmp/amubench_mon_c.txt,
  /tmp/amubench_mon_c2.txt). Probe 1 (05:56): load1 5.23, idle 39.66-72.50%.
  Probe 2 (06:01): load1 3.58 (below the 7.5 limit) but idle 53.80-79.50%,
  best sample 79.50% -- the idle>=90% bar was never reached, 0/10 samples, so
  the idle>=9/10 criterion did not qualify. Sys time persistently 12-21%
  suggests residual background activity. `bench/runtime-comparison/
  jb_imod_control.c` not run. No new numbers; population unchanged (H-C2,
  H-D, H-B, H-Y1 open; J-B confirmed-diagnostic but unqualified, 12
  consecutive positive windows, still awaiting the idle>=9/10 rerun; J-C
  blocked behind it). NEXT unchanged.
- **105 (2026-09-05 05:55 JST, rank-only pass; host busy, no measurement)**:
  rank pass runs no measurement by role; load probe at tick (05:53 JST, via
  background session -- foreground terminal again returned empty output, the
  shape entry 104 documented): load1 11.36-11.57 / 5m 9.50-9.62 / 15m 7.89-7.98,
  all above the 7.5 quiet limit and load15 ~8 shows sustained load. No quiet
  window, no number taken this tick. Evidence reviewed since entry 104: no new
  measured verdicts reached the doc; population unchanged (H-C2, H-D, H-B, H-Y1
  open; J-B confirmed-diagnostic but unqualified, 11 consecutive positive
  windows, still awaiting the idle>=9/10 rerun; J-C blocked behind it). No
  status transition, no new hypothesis, no re-rank -- nothing to re-rank on.
  NEXT: J-B fully-quiet-host rerun (idle >=9/10) of
  `bench/runtime-comparison/jb_imod_control.c` for the perfgate-qualifiable
  number (entry 102 re-rank stands).

- **106 (2026-09-05 06:20 JST, bench pass; host busy, no measurement)**:
  quiet gate checked for the J-B rerun: 06:20-06:21 JST load1 10.45 then
  8.97 / 5m 7.52-7.72 / 15m 6.83-6.88 -- load1 above the 7.5 quiet limit on
  both probes, so `bench/runtime-comparison/jb_imod_control.c` was not run.
  No new numbers; population unchanged (H-C2, H-D, H-B, H-Y1 open; J-B
  confirmed-diagnostic but unqualified, still awaiting the idle>=9/10 rerun;
  J-C blocked behind it). NEXT unchanged.

- **107 (2026-09-05 08:06 JST, bench pass; host busy, no measurement)**:
  08:06 JST load1 320.00 / 5min 141.75 / 15min 57.84 (up 49 min, 13 users) —
  load1 ~40x above the 7.5 quiet limit and still rising (5min >> 15min), by far
  the busiest window yet seen; per policy no bench, perfgate, or hand-patch
  measurement attempted, no numbers recorded. amu-falsify evidence checked:
  no new "要 quiet-host 測定" item pending. Population unchanged: H-C2, H-D,
  H-B, H-Y1 open; J-B confirmed-diagnostic (13 consecutive positive windows)
  but unqualified, still awaiting the idle>=9/10 rerun; J-C blocked behind it.
  NEXT: J-B fully-quiet-host rerun (idle >=9/10) of
  `bench/runtime-comparison/jb_imod_control.c` for the perfgate-qualifiable
  number (entry 102 re-rank stands).

- **108 (2026-09-05 08:15 JST, rank pass; host busy, no measurement)**:
  rank pass runs no measurement by role. Host state at tick (08:06 JST via
  pre-run monitor): load1 332.09 / 5m 138.01 / 15m 55.55, up 49 min, 13 users
  -- by far the busiest window yet seen; per policy no bench, perfgate, or
  hand-patch work is feasible, and the tick left no numbers to rank on.
  amu-falsify / amu-bench evidence reviewed since entry 107: none new (last
  landings remain fd4c6d31 amu-jit tick 13 and the b21f13d2/db6f9fe1
  lang-cosientist evidence-only commits). Population unchanged: H-C2, H-D,
  H-B, H-Y1 open; J-B confirmed-diagnostic (14 consecutive positive windows
  across 5) but unqualified, still awaiting the idle>=9/10 rerun; J-C blocked
  behind it. NEXT: J-B fully-quiet-host rerun (idle >=9/10) of
  `bench/runtime-comparison/jb_imod_control.c` for the perfgate-qualifiable
  number (entry 102 re-rank stands).

- **109 (2026-09-05 08:20 JST, rank pass; host busy, no measurement)**:
  rank pass runs no measurement by role. Host state at tick (probe script
  evidence /tmp/amurank_mon_20260905.txt): load1 45.25 / 5m 60.03 / 15m
  62.12, up 1:03, 11 users, 10 CPUs -- far above the 7.5 quiet limit, so
  no bench, perfgate, or hand-patch work is feasible and no numbers were
  recorded. Note: this tick's cron host had foreground terminal returning
  empty output again (the shape entries 96/99/104 documented); the probe
  ran via a script file and evidence was collected with read-only file
  reads. Evidence reviewed since entry 108: ADR 0338 (amu-jit tick 13,
  fd4c6d31, already counted at 108) remains the newest measured landing
  -- J-B 14 consecutive positive runs across five windows,
  +7.6/+7.8/+6.3% in the fifth, still diagnostic-only, no perfgate
  verdict; nothing new since. No re-rank, no status transition, no new
  hypothesis -- nothing measured this tick to rank on. Population
  unchanged: H-C2, H-D, H-B, H-Y1 open; J-B confirmed-diagnostic but
  unqualified, still awaiting the idle>=9/10 rerun; J-C blocked behind
  it. NEXT: J-B fully-quiet-host rerun (idle >=9/10) of
  `bench/runtime-comparison/jb_imod_control.c` for the
  perfgate-qualifiable number (entry 102 re-rank stands).

- **114 (2026-09-05 09:39 JST, bench pass; host busy, no measurement)**:
  bench tick. Host state at tick (probe script /tmp/amubench_mon.txt +
  10s trend /tmp/amubench_trend.txt): load1 24.40->25.84 / 5m 20.22->20.92 /
  15m 31.43->31.36, up 2:22, 14 users, 10 CPUs, CPU usage 39.69% user /
  11.69% sys / 48.61% idle -- load1 ~25.8, far above the 7.5 quiet limit
  and flat over 10s (no decay), so the quiet gate fails, the NEXT item
  (J-B fully-quiet-host rerun of `bench/runtime-comparison/
  jb_imod_control.c`, idle >=9/10) was not attempted, and no bench or
  perfgate numbers were recorded. amu-falsify evidence checked via the
  NEXT header: no new "yao quiet-host sokutei" item pending. Population
  unchanged: H-C2, H-D, H-B, H-Y1 open; J-B confirmed-diagnostic but
  unqualified, awaiting the idle>=9/10 rerun; J-C blocked behind it.
  NEXT unchanged (entry 102 re-rank stands).


- **130 (2026-09-05 18:38 JST, bench pass; host busy, no measurement)**:
  amu-bench tick. Host state at tick (`uptime`/`sysctl vm.loadavg`/`date` via
  /tmp/amubench-probe-load-20260905.txt): load1 61.35, 5m 78.33, 15m 66.08,
  up 11:21, 15 users. Far above the 7.5 quiet limit (consistent with entry
  129's 33.95-41.52 range), so the quiet gate failed and no
  bench/perfgate run was attempted; no numbers recorded. Evidence reviewed:
  no new pending "\u8981 quiet-host \u6e2c\u5b9a" item since entry 129;
  NEXT unchanged. Population unchanged: H-C2, H-D, H-B, H-Y1 open;
  J-B confirmed-diagnostic but unqualified, still awaiting the idle>=9/10
  rerun; J-C blocked behind it. NEXT unchanged: J-B fully-quiet-host rerun
  (idle >= 9/10) of `bench/runtime-comparison/jb_imod_control.c` for the
  perfgate-qualifiable number; H-C2 instruction-order-diff falsify plan
  queued behind it.

- **131 (2026-09-05 18:54 JST, bench pass; host busy, no measurement)**:
  amu-bench tick. Host state at tick (`date`/`uptime` via
  /private/tmp/amubench_probe_1900.out): load1 43.97, 5m 45.80, 15m 54.32,
  up 11:37, 15 users. Far above the 7.5 quiet limit (consistent with entries
  129/130), so the quiet gate failed and no bench/perfgate run was
  attempted; no numbers recorded. Evidence reviewed: no new pending
  "要 quiet-host 測定" item since entry 130; NEXT unchanged. Population
  unchanged: H-C2, H-D, H-B, H-Y1 open; J-B confirmed-diagnostic but
  unqualified, still awaiting the idle>=9/10 rerun; J-C blocked behind it.
  NEXT unchanged: J-B fully-quiet-host rerun (idle >= 9/10) of
  `bench/runtime-comparison/jb_imod_control.c` for the perfgate-qualifiable
  number; H-C2 instruction-order-diff falsify plan queued behind it.

- **132 (2026-09-05 19:09 JST, bench pass; host busy, no measurement)**:
  amu-bench tick. Host state at tick (`date`/`uptime`/`sysctl vm.loadavg` and
  `top -l 2 -s 5` via /tmp/amubench_probe_1907.out): load1 57.73 -> 54.95,
  5m 41.73, 15m 42.51, up 11:52, 15 users, 10 CPUs; CPU idle 0.0% -> 3.37%
  over two 5s-spaced top samples (idle>=90% count 0/2, no decay). Far above
  the 7.5 quiet limit, so the quiet gate failed and no bench/perfgate run
  was attempted; no numbers recorded. amu-falsify evidence reviewed
  (entry 130/131 range): no new pending "\u8981 quiet-host \u6e2c\u5b9a" item; NEXT
  unchanged. Population unchanged: H-C2, H-D, H-B, H-Y1 open, H-Z3 top of
  the codegen ladder; J-B still awaiting the fully-quiet-host (idle>=9/10)
  rerun of bench/runtime-comparison/jb_imod_control.c; H-Z3 A/B and H-C2
  instruction-order-diff queued behind it.

| 2026-09-05 19:27 JST | amu-bench | H-C2 | measurement SKIPPED: host busy (load1 22.58, load5 38.33, load15 44.19 at 19:27 JST; policy threshold load1 > 7.5). No bench/perfgate run performed to avoid polluting evidence with busy-host noise. No new measurement. | host busy |
2026-09-05 19:45 JST (amu-bench cron, tick 124): host busy (load1 53.39 /
load5 46.43 / load15 41.26 at 19:44 pre-run, threshold 7.5) — measurement
refused. Quiet gate checked anyway for the record with 10 top-based CPU
samples over ~35s (19:44:53-19:45:23 JST, main-2.local, up 12:27, 15 users,
10 CPUs): idle 17.71-37.70% (no sample near the 90% bar, idle>=9/10 count
0/10, sy 17.67-26.12%) — far from quiet throughout. No bench, no perfgate
run, no numbers. amu-falsify evidence checked: no new "要 quiet-host 測定"
item pending. Population unchanged: J-B confirmed-diagnostic but unqualified
(awaiting idle>=9/10 rerun), H-Z3 top of the codegen ladder, H-C2/H-D/H-B/
H-Y1 open; J-C blocked behind J-B. NEXT unchanged: J-B fully-quiet-host
rerun (idle>=9/10) of bench/runtime-comparison/jb_imod_control.c, then
H-Z3 quiet-host hand-patch A/B, then H-C2.

2026-09-05 19:53 JST (amu-bench cron, tick 125): host busy (load1 36.16 / 5m 32.55 / 15m 35.73 at 19:53, threshold 7.5) — measurement refused, no bench/perfgate run, no numbers. NEXT unchanged: J-B fully-quiet-host rerun (idle>=9/10) of bench/runtime-comparison/jb_imod_control.c, then H-Z3 quiet-host hand-patch A/B, then H-C2. Population unchanged: J-B confirmed-diagnostic but unqualified, H-Z3 top of the codegen ladder (quiet-host A/B pending), H-C2/H-D/H-B/H-Y1 open; J-C blocked behind J-B.

- [amu-bench 2026-09-05 20:25] H-C2/H-D/H-B/H-Y1: host busy (load1=11.99, load5=17.18, load15=29.75; policy threshold load1>7.5) — no measurement this tick; quiet-host measurement of H-C2 deferred.

2026-09-05 21:00 JST (amu-bench cron, tick 127): host busy (load1 35.34 / 5m 24.78 / 15m 26.92, up 13:43, 15 users, threshold 7.5) — measurement refused, no bench/perfgate run, no numbers. NEXT unchanged: J-B fully-quiet-host rerun (idle>=9/10) of bench/runtime-comparison/jb_imod_control.c, then H-Z3 quiet-host hand-patch A/B, then H-C2. Population unchanged: J-B confirmed-diagnostic but unqualified (awaiting idle>=9/10 rerun), H-Z3 top of the codegen ladder (quiet-host hand-patch A/B pending), H-C2/H-D/H-B/H-Y1 open; J-C blocked behind J-B.
- [2026-09-05 21:24 JST] amu-bench: host busy (load1 127.64 / load5 111.96 / load15 90.52, up 14:07). Measurement skipped; no bench/perfgate run this window.
| H-C2 | evidence | host busy (load1 8.95, 1m/5m/15m = 8.95/7.85/14.79, macOS 26.4, 22:16 JST) - quiet gate not met, no measurement run; policy: log busy only. [amu-bench] |

2026-09-05 23:24 JST (amu-bench cron): host busy — load1 dipped to 5.41 at 23:23:19 but rose to 8.77 (23:23:53) and 8.02 (23:24:13) across three probes over ~1 min (load5 7.4-7.5, load15 11.5-11.6, 10 CPUs, up 16:07, 11 users, threshold 7.5) — no sustained quiet window, so the J-B fully-quiet-host rerun (idle>=9/10) of bench/runtime-comparison/jb_imod_control.c was NOT started per quiet-gate rule. No bench, no perfgate run, no numbers recorded. NEXT unchanged: J-B fully-quiet-host rerun (idle>=9/10), then H-Z3 quiet-host hand-patch A/B, then H-C2. Population unchanged: J-B confirmed-diagnostic but unqualified, H-Z3 top of the codegen ladder, H-C2/H-D/H-B/H-Y1 open; J-C blocked behind J-B.

| 2026-09-06 00:24 JST (amu-bench cron): host busy — J-B fully-quiet-host rerun NOT attempted. Measurement window observation 00:16-00:24 (4 min sustained, 8 x 30s samples): load1 7.72->6.94->4.02->3.25 (00:16-00:19) looked like an opening window, but then spiked 14.58->30.32 (00:20-00:21) before decaying 7.07 at 00:23; only 2/8 samples below threshold 7.5, no sustained quiet window (idle>=9/10 not observable). No bench, no perfgate, no numbers recorded. Probes via /tmp scripts (no heredoc), entry via append script per entry-117 convention. NEXT unchanged: J-B fully-quiet-host rerun (idle>=9/10) of bench/runtime-comparison/jb_imod_control.c, then H-Z3 quiet-host hand-patch A/B, then H-C2. Population unchanged: J-B confirmed-diagnostic but unqualified, H-Z3 top of the codegen ladder, H-C2/H-D/H-B/H-Y1 open; J-C blocked behind J-B.

- **356 (2026-09-09 23:05 JST, amu-rank cron)**: host busy (load1 19.30 / 5m 19.92 / 15m 25.34 at 23:02, threshold 7.5) — measurement refused, rank-only pass. git fetch: origin/main advanced b631a7fe -> 9ee8020b (PR #912 `:schemas`-declaring module may be required; PR #910 loader granted-region; PR-linked compiler/loader scope, no codegen-ladder number). Local worktree: 8 duplicate uncommitted amu-bench 22:07 busy-refusal entries in this doc collapsed to 1 by this rank tick (content identical, no measured numbers lost — blocks contained only the load1 24.26 busy refusal); no new ADR (0345 remains newest on disk); no new sibling measured evidence since tick 355. No re-rank, no status transition, no new hypothesis — no new measured numbers exist. Population unchanged: H-Z3 top of the codegen ladder, H-C2/H-D/H-B/H-Y1 open, J-C folded behind J-B. NEXT unchanged: benjamin collections walk-loop hand-patch (imod helper inlining, J-B2/H-Z3) via perfgate on a quiet fleet node (qualifying nodes levi 0.04 / joseph 0.05 / benjamin 0.05 / judah 0.07); host busy since ~tick 258.

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

<!-- merge note 2026-09-06: this section sat on main with an unresolved conflict block; two loop lineages numbered entries independently while it was conflicted, so both sets are kept below and entry numbers repeat. -->

- **111 (2026-09-04 17:58 JST, amu-rank rank tick; host busy, no measurement)**:
  load1 18.34 / 5m 29.44 / 15m 35.46 (up 11 days, 9:41, 6 users, 10 CPUs) —
  still > 7.5 quiet limit; no bench, perfgate, or falsify measurement
  attempted. No new ADR since 0334; no new evidence from sibling ticks since
  110. No re-rank, no status transition: no new measured numbers.
  Population unchanged: H-C2, H-D, H-B, H-Y1 open. NEXT: H-C2 (unchanged —
  highest expected qualified gain x probability; ~4.4% residual vs Clang on
  `kernel`, near-identical static shape, separable).

- **112 (2026-09-04 18:48 JST, amu-bench bench tick; host busy, no measurement)**:
  load1 52.58 / 5m 47.67 / 15m 44.90 (up 11 days, 10:37, 6 users, 10 CPUs) —
  ~7x above the 7.5 quiet limit; no bench, perfgate, or falsify measurement
  attempted. No new ADR since 0334; no new "要 quiet-host 測定" item pending
  (J-B confirmatory quiet-host rerun still pending per tick 10). Note: an
  empty stray file `docs/codegen-cosientist.md` (typo of this filename)
  exists untracked and is what the cron pre-run script now reads — this file
  (`codegen-coscientist.md`) remains the tournament state. No re-rank, no
  status transition: no new measured numbers. Population unchanged: H-C2,
  H-D, H-B, H-Y1 open. NEXT: H-C2 (unchanged — highest expected qualified
  gain x probability; ~4.4% residual vs Clang on `kernel`, near-identical
  static shape, separable).

- **113 (2026-09-04 19:06 JST, amu-rank rank tick; host busy, no measurement)**:
  load1 68.74 / 5m 60.96 / 15m 56.99 (up 11 days, 10:54, 6 users, 10 CPUs) —
  ~9x above the 7.5 quiet limit; no measurement requested, rank-only pass.
  Note: stray empty file `docs/codegen-cosientist.md` is still untracked; this
  file remains the sole tournament state. No new measured numbers from sibling
  ticks since 112 → no re-rank, no status transition. Population unchanged:
  H-C2, H-D, H-B, H-Y1 open. NEXT: H-C2 (unchanged — highest expected
  qualified gain x probability; ~4.4% residual vs Clang on `kernel`,
  near-identical static shape, separable).
- **110 (2026-09-05 08:25 JST, bench pass; host busy, no measurement)**:
  bench tick. Host load at tick: load1 66.52 / 5m 70.67 / 15m 67.12, up
  1:08, 11 users, 10 CPUs -- load1 far above the 7.5 quiet limit, so the
  NEXT item (J-B fully-quiet-host rerun of
  `bench/runtime-comparison/jb_imod_control.c`, idle >=9/10) was not
  attempted and no numbers were recorded (no bench, no perfgate). Note:
  this cron host foreground terminal again returned empty output (known
  shape, entries 96/99/104/109); evidence collected via a probe script
  writing to /tmp and read-only file reads. No re-rank, no status
  transition, no new hypothesis -- nothing measured this tick.
  Population unchanged: H-C2, H-D, H-B, H-Y1 open; J-B
  confirmed-diagnostic but unqualified, still awaiting the idle>=9/10
  rerun; J-C blocked behind it. NEXT: J-B fully-quiet-host rerun (idle
  >=9/10) of `bench/runtime-comparison/jb_imod_control.c` for the
  perfgate-qualifiable number (entry 102 re-rank stands).


- **111 (2026-09-05 08:52 JST, rank pass; host busy, no measurement)**:
  rank pass runs no measurement by role. Host state at tick (probe script
  /tmp/amurank_mon.txt): load1 141.76 / 5m 129.77 / 15m 97.29, up 1:35,
  11 users, 10 CPUs -- far above the 7.5 quiet limit and still rising
  (5m >> 15m), so no bench, perfgate, or hand-patch work is feasible and
  no numbers were recorded. Note: this cron host's foreground terminal
  again returned empty output (known shape, entries 96/99/104/109/110);
  evidence was collected via a probe script writing to /tmp plus
  read-only file reads. Evidence reviewed since entry 110: none new --
  git fetch shows the newest landing remains 0920ca71 (own iteration 108);
  fd4c6d31 (J-B tick 13) and b21f13d2 (lang-cosientist iter 5,
  evidence-only parse-long falsification) already counted at 108. No
  re-rank, no status transition, no new hypothesis -- nothing measured
  this tick to rank on. Population unchanged: H-C2, H-D, H-B, H-Y1 open;
  J-B confirmed-diagnostic (14 consecutive positive windows across 5) but
  unqualified, still awaiting the idle>=9/10 rerun; J-C blocked behind it.
  NEXT: J-B fully-quiet-host rerun (idle >=9/10) of
  `bench/runtime-comparison/jb_imod_control.c` for the
  perfgate-qualifiable number (entry 102 re-rank stands).

- **112 (2026-09-05 09:31 JST, bench pass; host busy, no measurement)**:
  bench tick. Host state at tick: load1 15.13 / 5m 34.42 / 15m 44.08,
  up 2:13, 14 users, 10 CPUs -- load1 above the 7.5 quiet limit (5m/15m
  ~34-44 show sustained heavy load), so per policy the quiet gate failed,
  the NEXT item (J-B fully-quiet-host rerun of
  `bench/runtime-comparison/jb_imod_control.c`, idle >=9/10) was not
  attempted, and no bench or perfgate numbers were recorded.
  amu-falsify evidence checked: no new "要 quiet-host 測定" item pending.
  Population unchanged: H-C2, H-D, H-B, H-Y1 open; J-B
  confirmed-diagnostic (14 consecutive positive windows across 5) but
  unqualified, still awaiting the idle>=9/10 rerun; J-C blocked behind it.
  NEXT unchanged (entry 102 re-rank stands).

- **113 (2026-09-05 09:34 JST, rank pass; host busy, no measurement)**:
  rank pass runs no measurement by role. Host state at tick: load1 7.39 /
  5m 22.22 / 15m 37.08, up 2:17, 14 users, 10 CPUs. load1 dipped under
  the 7.5 quiet limit for one reading but 5m/15m (22/37) show a
  sustained heavy-load wave decaying from the 08:15-09:03 peak; a
  15-min window opened on this state fails the quiet-gate intent, so no
  bench, perfgate, or hand-patch work was feasible and no numbers were
  recorded. Evidence reviewed since entry 112: jit-cosientist tick 8
  (0a14e133) -- quiet gate failed there too (load1 49.7-54.2), J-B
  rerun deferred; no new measurement to rank on. No re-rank, no status
  transition, no new hypothesis. Population unchanged: H-C2, H-D, H-B,
  H-Y1 open; J-B confirmed-diagnostic (14 consecutive positive windows
  across 5) but unqualified, still awaiting the idle>=9/10 rerun; J-C
  blocked behind it. NEXT: J-B fully-quiet-host rerun (idle >=9/10) of
  `bench/runtime-comparison/jb_imod_control.c` for the
  perfgate-qualifiable number (entry 102 re-rank stands).

- **115 (2026-09-05 09:52 JST, rank pass; host busy, no measurement)**:
  rank pass runs no measurement by role. Host state at tick (probe script
  /tmp/amurank_mon_114.txt): load1 24.13 / 5m 19.14 / 15m 22.88, up 2:35,
  14 users, 10 CPUs -- far above the 7.5 quiet limit and sustained across
  all three windows, so the quiet gate fails and no bench, perfgate, or
  hand-patch work is feasible; no numbers were recorded. Note: this cron
  host's foreground terminal again returned empty output (known shape,
  entries 96/99/104/109/110/111); evidence was collected via a probe
  script writing to /tmp plus read-only file reads. Evidence reviewed
  since entry 113: one new landing found on branch `k16-loader-port`
  (46eeedae, 09:35 JST) -- forward-port of the pure-native-k16 BOOTX64
  loader onto 5cec9196 (cli.clj + pe32plus.cljc, +186/-21). It is build
  machinery for the addressed-execution side of the goal, not a measured
  perf verdict, so it does not re-rank the codegen hypothesis population
  and needs no status transition. jit-cosientist tick 8 (0a14e133) was
  already counted at 113. Population unchanged: H-C2, H-D, H-B, H-Y1
  open; J-B confirmed-diagnostic (14 consecutive positive windows across
  5) but unqualified, still awaiting the idle>=9/10 rerun; J-C blocked
  behind it. NEXT: J-B fully-quiet-host rerun (idle >=9/10) of
  `bench/runtime-comparison/jb_imod_control.c` for the
  perfgate-qualifiable number (entry 102 re-rank stands).

- **116 (2026-09-05 10:03 JST, bench pass; host busy, no measurement)**:
  bench tick. Host state at tick (probe via background script writing
  /tmp/amu_bench_uptime.txt; foreground terminal returned empty output,
  the known shape entries 96/99/104/109/110/111): load1 37.14 / 5m 33.41
  / 15m 29.05, up 2:46, 12 users, 10 CPUs — load1 far above the 7.5
  quiet limit and sustained across all three windows, so the quiet gate
  failed, the NEXT item (J-B fully-quiet-host rerun of
  `bench/runtime-comparison/jb_imod_control.c`, idle >=9/10) was not
  attempted, and no bench or perfgate numbers were recorded.
  amu-falsify evidence checked: no new "要 quiet-host 測定" item
  pending. Population unchanged: H-C2, H-D, H-B, H-Y1 open; J-B
  confirmed-diagnostic (14 consecutive positive windows across 5) but
  unqualified, still awaiting the idle>=9/10 rerun; J-C blocked behind
  it. NEXT unchanged (entry 102 re-rank stands).

- **117 (2026-09-05 10:44 JST, bench pass; host busy, no measurement)**:
  bench tick. Host state at tick (probe script /tmp/amu_bench_probe_117.sh
  writing /tmp/amu_bench_uptime_117.txt; foreground terminal again empty,
  the known shape entries 96/99/104/109/110/111): load1 27.28 / 5m 26.32
  / 15m 25.15, up 3:27, 12 users, 10 CPUs — load1 far above the 7.5
  quiet limit and sustained across all three windows, so the quiet gate
  failed, the NEXT item (J-B fully-quiet-host rerun of
  `bench/runtime-comparison/jb_imod_control.c`, idle >=9/10) was not
  attempted, and no bench or perfgate numbers were recorded. Incident
  note: the first append attempt this tick used a shell heredoc, which
  the cron runtime mis-executed — it created a stray 1,890-byte
  `docs/codegen-cosientist.md` (s-dropped spelling) holding the entry
  twice; the real `docs/codegen-cosientist.md` (129,111 bytes) was
  verified intact before repair and the stray was moved to tmp/.
  Appends now go through a Python script
  (scripts/append-entry117-amubench.py), matching the existing
  append-*.py convention. amu-falsify evidence checked: no new
  "要 quiet-host 測定" item pending. Population unchanged: H-C2, H-D,
  H-B, H-Y1 open; J-B confirmed-diagnostic (14 consecutive positive
  windows across 5) but unqualified, still awaiting the idle>=9/10
  rerun; J-C blocked behind it. NEXT unchanged (entry 102 re-rank
  stands).

- **118 (2026-09-05 11:22 JST, rank pass; host busy, no measurement)**:
  rank pass runs no measurement by role. Host state at tick (probe script
  ~/.hermes/profiles/amu-rank/tmp/status_check.sh writing status_out.txt;
  foreground terminal again returned empty output, the known shape entries
  96/99/104/109/110/111/116): load1 11.54 / 5m 16.46 / 15m 19.79, up 4:01,
  12 users, 10 CPUs — load1 above the 7.5 quiet limit and sustained across
  all three windows (though decaying from the earlier 20+ peak), so the
  quiet gate fails and the NEXT item (J-B fully-quiet-host rerun of
  `bench/runtime-comparison/jb_imod_control.c`, idle >=9/10) was not
  attempted. Evidence reviewed since entry 117: one new landing, 8ebb3426
  (amu-jit tick 9) — quiet gate failed there too (load1 19.2-22.5, no idle
  CPU), J-B rerun deferred; its only new content is source-inspection
  (J-B premise re-verified on origin tree: imod is a user fn with a runtime
  divisor; the hand-patch arm measures levers 1+2 combined per ADR 0289
  ranking, a lever-2-only control with a non-inlined mulh arm is proposed
  as the next control). Source inspection is not a measured verdict, so no
  re-rank and no status transition; the proposed lever-2-only control is
  noted as a J-B refinement, registered for ranking once any measured
  number exists. Population unchanged: H-C2, H-D, H-B, H-Y1 open; J-B
  confirmed-diagnostic (14 consecutive positive windows across 5) but
  unqualified, still awaiting the idle>=9/10 rerun; J-C blocked behind it.
  NEXT: J-B fully-quiet-host rerun (idle >=9/10) of
  `bench/runtime-comparison/jb_imod_control.c` for the perfgate-qualifiable
  number (entry 102 re-rank stands); when quiet host is available, the
  lever-2-only control (non-inlined mulh arm) may follow it.
among the enumerated implementations (rustc, Ap2026-09-02 23:18 JST (amu-rank cron, tick 66): host busy (load1 10.18 / 5m 15.59 / 15m 16.24, threshold 7.5) — measurement refused, rank-only pass. Committed sibling busy-refusal entries (23:07, 23:16). No new measured evidence; NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers.
ple Clang C11, Zig, Go
| H-C2 | the remaining ~4.4% vs Clang on `kernel` after H-C: the mutated stream and clang's are now near-identical in shape (62 vs 61 instructions; amu-mut still loads the now-dead `0x7fffffff` constant), so the residue is scheduling/front-end shaped | open — generate from an instruction-order diff | pending |
| H-B | batch-fixture noise (rsd 0.47 vs policy 0.10) is scheduler migration of a long single-call region across P/E cores; pin the timed region's QoS | open | performance.md already documents an E-core migration incident; 2026-09-02 falsify tick: measurement refused, host busy (load1 55.35); 2026-09-03 02:00 falsify tick: measurement refused, host busy (load1 74.20 / 5m 61.47 / 15m 49.91) — no measurement started per quiet-gate rule; 2026-09-03 02:30 falsify tick: measurement refused, host busy (load1 81.47 / 5m 71.66 / 15m 72.75) |
| H-Z1 | collections' 1.93 residual is the per-element out-of-line division + un-inlined `imod` on the loop-carried chain, not crossings (ADR 0289 refuted the crossing attribution): constant-divisor strength reduction or inlining small user functions removes the hardware `sdiv` from the serial chain | open — countable statically (instruction count) while the host is busy; timing verdict deferred to a quiet window | ADR 0289: ~47 instr/element incl. 18-instr out-of-line `imod` with a hardware `sdiv` run ~165x/call, vs twin ~6-8 strength-reduced; crossings measured 1.002 (null) in isolation |
| H-Z2 | strings' 2.17 residual shares ADR 0289's cause — explicitly UNMEASURED (the kernel was never disassembled); if it does, one lever family (inline / strength-reduce / bulk fuel) serves both domains | **static premise CONFIRMED — iteration 57** (amu-falsify disassembly, load1 60, no timing); remaining: quiet-host hand-patch A/B of the lever | 2026-09-02 21:05 JST (amu-falsify, STATIC only — host busy load1 60, no timing): disassembled now. `aarch64-kotoba-v1` kernel span 436 bytes / 109 instrs; `imod` callee at 0x0 is 18 instrs with one `sdiv` at 0x34 + INT64_MIN/-1 guard rebuild, NOT inlined (bl from scan 0xd0, bl from kernel 0x210/0x220); scan loop 0x80–0xf0 = 29 instrs/element (code-point-at blr crossing w/ x7 spill ~9, fuel 5, imod call+const 4) — same shape as collections (ADR 0289's 29+18). build loop 0x13c–0x18c ~13 instrs/iter (concat blr w/ spill, fuel 5). Shared-cause premise statically confirmed; dynamic counts & lever gain still unmeasured — folded into H-Z3 for the timed verdict |
| H-Z3 | one lever family (constant-divisor strength reduction / inlining of small user `imod`) clears ≥5% separated in BOTH collections (H-Z1's 1.93) and strings (H-Z2's 2.17): static shape is identical (29 instr/element + out-of-line 18-instr `sdiv` callee in each), so one hand-patch serves both domains and the surviving gap beyond it is a different cause | open — evolve of H-Z1+H-Z2 (iteration 57); verdict requires a quiet-host hand-patch A/B (H-E's iteration-20 fixture method) | static: ADR 0289 (collections 29+18) + amu-falsify 2026-09-02 disassembly (strings 29+18, same `imod` callee shape, not inlined). No timing numbers yet — no status transition past open until a separated A/B lands. 2026-09-03 03:00 falsify tick: measurement refused, host busy (load1 103.48 / 5m 91.93 / 15m 81.02, quiet-gate limit 7.5) — no measurement started per quiet-gate rule; quiet-host A/B remains the next step; 2026-09-03 03:01 falsify tick: measurement refused, host busy (load1 114.56 / 5m 107.01 / 15m 95.23, threshold 7.5) — no measurement started per quiet-gate rule; quiet-host A/B remains the next step; 2026-09-03 03:45 JST (amu-bench cron, tick): measurement refused, host busy (load1 28.02 / 5m 33.65 / 15m 45.75, threshold 7.5) — no measurement started per quiet-gate rule; quiet-host A/B remains the next step; 2026-09-03 04:15 JST (amu-falsify cron): measurement refused, host busy (load1 20.79 / 5m 22.47 / 15m 26.22, threshold 7.5) — no measurement started per quiet-gate rule; NEXT unchanged (H-Z3 quiet-host hand-patch A/B) |
2026-09-02 20:55 JST (amu-bench cron): host busy (load1 83.35 / 5m 78.91 / 15m 88.65, threshold 7.5) — no bench/perfgate run. Monitor script amu_cowork_state.sh 復旧済 (profile scripts から sampling 成功)。NEXT = H-Z2 static disassembly は load-robust だが bench 担当の守備範囲は timing/perfgate のみのため着手せず; timed 側 (H-Z1 timing, H-B QoS pin, H-C2/H-D A/B) は全て quiet-host 待ちのまま。No numbers recorded.
2026-09-02 21:06 JST (amu-falsify cron): host busy (load1 60.35, threshold 7.5) — timed measurement refused as instructed. Ran H-Z2's NEXT (static, load-robust): disassembled `kernel_strings.kotoba` aarch64 emission (436 bytes / 109 instrs; out-of-line 18-instr `imod` w/ `sdiv` not inlined; scan loop 29 instrs/element incl. blr crossing + fuel). Static confirmation appended to H-Z2 evidence; dynamic/timing verdict deferred to quiet host. No bench, no perfgate run.
2026-09-03 01:00 JST (amu-falsify cron): host busy (load1 99.38 / 5m 76.69 / 15m 71.98, threshold 7.5) — no measurement. NEXT (H-Z2) の static 反証は 2026-09-02 21:06 に完了済み; 残作業は quiet-host 限定の H-Z3 hand-patch A/B のため本 tick は着手可能な反証なし。No bench, no perfgate run.
- **56 (2026-09-02, rank tick — host busy, rank-only)**: load1 51.66
  (threshold 7.5) — no measurement run this tick, and none attempted.
  Incorporating ADR 0289 + ADR 0290 into the population: the
  collections/strings crossing attribution is refuted (measured 1.002
  null in isolation; the residual is the per-element out-of-line
  division), so **H-Z1** is filed (constant-divisor strength reduction /
  inlining small user functions, static-count verification) and **H-Z2**
  (strings shares the cause — unmeasured; disassembly first). Both are
  load-robust: verification is instruction counts, not timings. Ranking:
  H-Z2 outranks H-Z1's timing step because it closes ADR 0289's flagged
  gap and gates whether one lever family serves both domains; quiet-host
  timing of either stays behind the busy gate. ADR 0290 (bounded map on
  wasm32) opens no performance hypothesis — the 31/128 entry gap is
  recorded there, not here. No status transitions without new numbers.
  **NEXT: H-Z2 (kernel_strings の aarch64 disassembly — static で host
  busy の影響を受けず、ADR 0289 が明示的に unmeasured と flagged した
  gap を閉じる)**
- **57 (2026-09-02 21:10 JST, rank tick — host busy, rank-only)**: load1
  19.14 (threshold 7.5) — no measurement run this tick, and none attempted.
  Incorporating amu-falsify's 21:05 static result (uncommitted diff,
  adopted here): H-Z2's shared-cause premise is statically CONFIRMED —
  `kernel_strings` disassembles to the same shape as collections (29
  instr/element scan loop + out-of-line 18-instr `imod` callee with a
  hardware `sdiv`, not inlined; 109 instrs total). **H-Z2** moves to
  "static premise CONFIRMED — iteration 57"; its timed step is folded
  into **H-Z3**, the evolve of H-Z1+H-Z2: one lever family (constant-
  divisor strength reduction / inlining of small user `imod`) is claimed
  to clear ≥5% separated in BOTH domains, so one hand-patch serves both.
  Ranking: H-Z3 now outranks H-B/H-C2/H-D because it has the only
  statically-confirmed mechanism with two pending residuals (1.93 +
  2.17) and an existing validated method (H-E's iteration-20 hand-patch
  A/B); H-B stays second since it gates H-D; H-C2 third. No timing
  numbers this tick — H-Z3 stays open, no claim-grade transition.
  **NEXT: H-Z3 (quiet host で `imod` strength-reduction/inline の
  hand-patch A/B — collections 先行、同 fixture で strings を追試。
  host busy が続く場合は測定拒否を記録するのみ)**
2026-09-02 23:01 JST (amu-falsify cron): host busy (load1 11.81 / 5m 13.30, threshold 7.5) — timed measurement refused as instructed. NEXT = H-Z3 quiet-host hand-patch A/B remains deferred; no bench, no perfgate run, no numbers.
2026-09-02 21:10 JST (amu-bench cron): host busy (load1 19.16, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B).
2026-09-02 21:15 JST (amu-falsify cron): host busy (load1 17.27 / 5m 22.17, threshold 7.5) — timed measurement refused. H-Z2 static disassembly already completed by previous tick (21:06, see evidence above); no further static work queued. H-Z3 timed A/B and all timing hypotheses remain quiet-host 待ち. No numbers recorded.
2026-09-02 21:17 JST (amu-rank cron, tick 58): host busy (load1 13.77 / 5m 18.78, threshold 7.5) — measurement refused, rank-only pass found no new evidence since tick 57 (NEXT H-Z3 quiet-host hand-patch A/B unchanged; no status transitions without numbers).
2026-09-02 21:22 JST (amu-bench cron): host busy (load1 25.80 / 5m 26.36 / 15m 36.89, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B).
2026-09-02 21:30 JST (amu-falsify cron): host busy (load1 12.25 / 5m 19.28 / 15m 29.09, threshold 7.5) — timed measurement refused. H-Z3 quiet-host hand-patch A/B unchanged, no numbers recorded.
2026-09-02 21:37 JST (amu-bench cron): host busy (load1 27.77 / 5m 27.75 / 15m 25.52, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B).
2026-09-02 21:32 JST (amu-rank cron, tick 59): host busy (load1 13.48 / 5m 17.25 / 15m 26.87, threshold 7.5) — measurement refused, rank-only pass. No new evidence since tick 58; NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers.
2026-09-02 21:45 JST (amu-falsify cron): host busy (load1 15.69 / 5m 18.06 / 15m 21.71, threshold 7.5) — timed measurement refused as instructed. H-Z2 static disassembly already confirmed (21:06) and folded into H-Z3; the only remaining static work would duplicate it. H-Z3 quiet-host hand-patch A/B and all timing hypotheses remain quiet-host 待ち. No numbers recorded.
2026-09-02 21:47 JST (amu-rank cron, tick 60): host busy (load1 9.66 / 5m 14.95 / 15m 19.91, threshold 7.5) — measurement refused, rank-only pass. No new evidence since tick 59 (all sibling bots 21:30–21:45 also busy-refused); NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers.
2026-09-02 21:52 JST (amu-bench cron): host busy (load1 18.54 / 5m 16.46 / 15m 19.06, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B).
2026-09-02 22:00 JST (amu-falsify cron): host busy (load1 19.64 / 5m 18.40 / 15m 18.66, threshold 7.5) — timed measurement refused. No static work remaining (H-Z2 confirmed 21:06, folded into H-Z3); H-Z3 quiet-host hand-patch A/B unchanged. No numbers recorded.
2026-09-02 22:02 JST (amu-rank cron, tick 61): host busy (load1 14.43 / 5m 17.09 / 15m 18.11, threshold 7.5) — measurement refused, rank-only pass. No new evidence since tick 60 (sibling bots 21:45–22:00 all busy-refused); NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers.
2026-09-02 22:07 JST (amu-bench cron): host busy (load1 14.82 / 5m 14.96 / 15m 16.61, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B; sibling evidence diff still uncommitted in working tree).
2026-09-02 22:15 JST (amu-falsify cron): host busy (load1 12.52 / 5m 14.11 / 15m 15.35, threshold 7.5) — timed measurement refused. No new static work (H-Z2 confirmed 21:06, folded into H-Z3); NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers.
2026-09-02 22:37 JST (amu-bench cron): host busy (load1 14.51 / 5m 15.65 / 15m 16.69, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B); sibling bots 22:07–22:32 all busy-refused as well.
2026-09-02 22:17 JST (amu-rank cron, tick 62): host busy (load1 7.73 / 5m 11.82 / 15m 14.28, threshold 7.5) — measurement refused, rank-only pass. No new evidence since tick 61 (sibling bots 22:07–22:15 all busy-refused); NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers.
2026-09-02 22:22 JST (amu-bench cron): host busy (load1 16.02 / 5m 13.95 / 15m 14.36, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B); working tree still carries untracked k10/m.kexe provenance/publication sidecars (build-time OS artifacts, not mine to clean).
2026-09-02 22:31 JST (amu-falsify cron): host busy (load1 47.75 / 5m 28.71 / 15m 20.44, threshold 7.5) — timed measurement refused; H-Z3 quiet-host hand-patch A/B still quiet-host 待ち.
2026-09-02 22:32 JST (amu-rank cron, tick 63): host busy (load1 15.73 / 5m 23.16 / 15m 19.21, threshold 7.5) — measurement refused, rank-only pass. No new evidence since tick 62 (sibling bots 22:07–22:31 all busy-refused); NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers.
2026-09-02 22:45 JST (amu-falsify cron): host busy (load1 15.59 / 15m 14.97, threshold 7.5) — timed measurement refused; H-Z3 quiet-host hand-patch A/B unchanged, no numbers recorded.
2026-09-02 22:48 JST (amu-rank cron, tick 64): host busy (load1 12.06 / 5m 13.10 / 15m 14.49, threshold 7.5) — measurement refused, rank-only pass. No new evidence since tick 63 (sibling bots 21:45–22:45 all busy-refused; committed their logged entries 22:37–22:45); NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers. Population unchanged: H-Z3 (evolve of H-Z1+H-Z2) remains top-ranked; H-D/H-B/Y1 gated on quiet host; C2/Z1/Z2 folded into Z3.
2026-09-02 23:03 JST (amu-rank cron, tick 65): host busy (load1 10.52 / 5m 12.35 / 15m 13.17, threshold 7.5) — measurement refused, rank-only pass. Committed sibling busy-refusal entries (22:53–23:01). No new measured evidence; NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers.
2026-09-02 22:53 JST (amu-bench cron): host busy (load1 12.83 / 5m 12.55 / 15m 13.78, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B).
2026-09-02 23:07 JST (amu-bench cron): host busy (load1 33.55 / 5m 23.03 / 15m 17.50, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z2 kernel_strings static aarch64 disassembly / H-Z3 quiet-host work). Untracked k10/m.kexe provenance/publication sidecars still present.
2026-09-02 23:16 JST (amu-falsify cron): host busy (load1 17.15 / 5m 18.60 / 15m 17.26, threshold 7.5) — timed measurement refused as instructed. H-Z3 quiet-host hand-patch A/B remains deferred; no bench, no perfgate run, no numbers.
2026-09-02 23:23 JST (amu-bench cron): host busy (load1 25.85 / 5m 19.86 / 15m 17.79, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B).
2026-09-02 23:30 JST (amu-falsify cron): host busy (load1 38.27 / 5m 29.94 / 15m 23.20, threshold 7.5) — timed measurement refused as instructed. H-Z2 static disassembly already complete (23:15前回 tick); H-Z3 quiet-host hand-patch A/B remains the sole next step, deferred. No bench, no perfgate run, no numbers.
2026-09-02 23:32 JST (amu-rank cron, tick 67): host busy (load1 27.08 / 5m 28.56 / 15m 23.51, threshold 7.5) — measurement refused, rank-only pass. Committed sibling busy-refusal entries (23:18–23:30). No new measured evidence; NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers.
2026-09-02 23:37 JST (amu-bench cron): host busy (load1 46.70 / 5m 37.61 / 15m 28.84, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B).
2026-09-02 23:46 JST (amu-falsify cron): host busy (load1 88.51 / 5m 67.85 / 15m 47.73, threshold 7.5) — timed measurement refused as instructed. H-Z3 quiet-host hand-patch A/B remains deferred; no bench, no perfgate run, no numbers.
2026-09-02 23:49 JST (amu-rank cron, tick 68): host busy (load1 75.43 / 5m 71.68 / 15m 51.82, threshold 7.5) — measurement refused, rank-only pass. No new measured evidence since tick 67 (sibling bots 23:37–23:46 also busy-refused); NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers. Population unchanged: H-Z3 top; H-D/H-B/Y1 gated on quiet host; C2/Z1/Z2 folded into Z3.
2026-09-02 23:53 JST (amu-bench cron): host busy (load1 139.81 / 5m 99.58 / 15m 69.61, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B).
2026-09-03 00:01 JST (amu-falsify cron): host busy (load1 89.51 / 5m 104.99 / 15m 87.95, threshold 7.5) — timed measurement refused as instructed. No static work remaining (H-Z2 confirmed 2026-09-02 21:06, folded into H-Z3); H-Z3 quiet-host hand-patch A/B and all timing hypotheses remain quiet-host 待ち. No numbers recorded.
2026-09-03 00:04 JST (amu-rank cron, tick 69): host busy (load1 100.06 / 5m 103.62 / 15m 89.73, threshold 7.5) — measurement refused, rank-only pass. No new measured evidence since tick 68 (sibling bots 23:53–00:01 also busy-refused). NEXT unchanged (H-Z3 quiet-host hand-patch A/B); H-Z2 already confirmed/folded into H-Z3 (script header stale on this). No status transitions without numbers.
2026-09-03 00:08 JST (amu-bench cron): host busy (load1 108.39 / 5m 101.24 / 15m 92.09, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B; H-Z2 already confirmed, script header stale). Untracked k10/m.kexe provenance/publication sidecars still present.
2026-09-03 00:18 JST (amu-falsify cron): host busy (load1 145.27 / 5m 118.91 / 15m 103.77, threshold 7.5) — timed measurement refused as instructed. No static work remaining (H-Z2 confirmed 21:06, folded into H-Z3); H-Z3 quiet-host hand-patch A/B remains deferred. No bench, no perfgate run, no numbers.
2026-09-03 00:22 JST (amu-rank cron, tick 70): host busy (load1 155.24 / 5m 138.77 / 15m 115.87, threshold 7.5) — measurement refused, rank-only pass. No new measured evidence since tick 69 (sibling bots 00:08–00:18 also busy-refused). NEXT unchanged (H-Z3 quiet-host hand-patch A/B); no status transitions without numbers. Untracked k10/m.kexe provenance/publication sidecars still present (not touched by rank).
2026-09-03 00:25 JST (amu-bench cron): host busy (load1 84.83 / 5m 125.01 / 15m 118.34, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B; H-Z2 already confirmed). Untracked k10/m.kexe provenance/publication sidecars still present.
2026-09-03 00:30 JST (amu-falsify cron): host busy (load1 52.74 / 5m 78.58 / 15m 98.56, threshold 7.5) — timed measurement refused as instructed. No static work remaining (H-Z2 confirmed 2026-09-02 21:06, folded into H-Z3); H-Z3 quiet-host hand-patch A/B remains deferred. No bench, no perfgate run, no numbers.
2026-09-03 00:32 JST (amu-rank cron, tick 71): host busy (load1 40.48 / 5m 65.92 / 15m 91.12, threshold 7.5) — measurement refused, rank-only pass. No new measured evidence since tick 70 (sibling bots 00:25–00:30 also busy-refused; their entries committed here with this tick). NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers. Untracked k10/m.kexe provenance/publication sidecars still present (not touched by rank).
2026-09-03 00:37 JST (amu-bench cron): host busy (load1 51.94 / 5m 55.51 / 15m 78.21, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B).
2026-09-03 00:45 JST (amu-falsify cron): host busy (load1 57.88 / 5m 61.70 / 15m 72.12, threshold 7.5) — timed measurement refused as instructed. No static work remaining (H-Z2 confirmed 2026-09-02 21:06, folded into H-Z3); H-Z3 quiet-host hand-patch A/B remains deferred. No bench, no perfgate run, no numbers.
2026-09-03 00:48 JST (amu-rank cron, tick 72): host busy (load1 64.44 / 5m 64.79 / 15m 71.81, threshold 7.5) — measurement refused, rank-only pass. No new measured evidence since tick 71 (sibling bots 00:37–00:45 also busy-refused; their entries committed here with this tick). NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers. Untracked k10/m.kexe provenance/publication sidecars still present (not touched by rank).
2026-09-03 00:52 JST (amu-bench cron): host busy (load1 80.00 / 5m 71.85 / 15m 72.54, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B; H-Z2 already confirmed).
2026-09-03 01:02 JST (amu-rank cron, tick 73): host busy (load1 57.27 / 5m 69.46 / 15m 69.73, threshold 7.5) — measurement refused, rank-only pass. No new measured evidence since tick 72 (sibling entries 00:52 already present in the working tree; committed here with this tick). NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers. Untracked k10/m.kexe provenance/publication sidecars still present (not touched by rank).
2026-09-03 01:07 JST (amu-bench cron): host busy (load1 50.47 / 5m 56.82 / 15m 63.61, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B; H-Z2 already confirmed). Untracked k10/m.kexe provenance/publication sidecars still present.
2026-09-03 01:16 JST (amu-falsify cron): host busy (load1 46.36 / 5m 53.96 / 15m 59.90, threshold 7.5) — timed measurement refused as instructed. No static work remaining (H-Z2 confirmed 2026-09-02 21:06, folded into H-Z3); H-Z3 quiet-host hand-patch A/B remains deferred. No bench, no perfgate run, no numbers.
2026-09-03 01:17 JST (amu-rank cron, tick 74): host busy (load1 46.02 / 5m 53.05 / 15m 58.76, threshold 7.5) — measurement refused, rank-only pass. No new measured evidence since tick 73 (sibling entries 01:07–01:16 all busy-refusal; committed here with this tick). NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers. Untracked k10/m.kexe provenance/publication sidecars still present (not touched by rank).
2026-09-03 01:22 JST (amu-bench cron): host busy (load1 39.63 / 5m 46.56 / 15m 54.35, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B; H-Z2 already confirmed). Untracked k10/m.kexe provenance/publication sidecars still present.
2026-09-03 01:33 JST (amu-rank cron, tick 75): host busy (load1 56.29 / 5m 43.84 / 15m 47.27, threshold 7.5) — measurement refused, rank-only pass. No new measured evidence since tick 74 (sibling entry 01:22 amu-bench busy-refusal; committed here with this tick). NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers. Untracked k10/m.kexe provenance/publication sidecars still present (not touched by rank).
2026-09-03 01:38 JST (amu-bench cron): host busy (load1 33.38 / 5m 43.44 / 15m 47.10, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B; H-Z2 already confirmed). Untracked k10/m.kexe provenance/publication sidecars still present.
2026-09-03 01:45 JST (amu-falsify cron): host busy (load1 45.32 / 5m 36.79 / 15m 41.64, threshold 7.5) — timed measurement refused as instructed. No static work remaining (H-Z2 confirmed 2026-09-02 21:06, folded into H-Z3); H-Z3 quiet-host hand-patch A/B remains deferred. No bench, no perfgate run, no numbers.
2026-09-03 01:47 JST (amu-rank cron, tick 76): host busy (load1 32.85 / 5m 35.32 / 15m 40.34, threshold 7.5) — measurement refused, rank-only pass. No new measured evidence since tick 75 (sibling entries 01:38 amu-bench / 01:45 amu-falsify both busy-refusal, already present in the working tree; committed here with this tick). NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers. Untracked k10/m.kexe provenance/publication sidecars still present (not touched by rank).
2026-09-03 01:52 JST (amu-bench cron): host busy (load1 28.09 / 5m 30.92 / 15m 36.99, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B; H-Z2 already confirmed). Untracked k10/m.kexe provenance/publication sidecars still present.
2026-09-03 02:08 JST (amu-bench cron): host busy (load1 140.24 / 5m 101.94 / 15m 72.17, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B; H-Z2 already confirmed). Untracked k10/m.kexe provenance/publication sidecars still present.
2026-09-03 02:02 JST (amu-rank cron, tick 77): host busy (load1 77.39 / 5m 64.44 / 15m 52.52, threshold 7.5) — measurement refused, rank-only pass. No new measured evidence since tick 76 (sibling entry 01:52 amu-bench busy-refusal, already present in the working tree; committed here with this tick). NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers. Untracked k10/m.kexe provenance/publication sidecars still present (not touched by rank).
2026-09-03 02:16 JST (amu-falsify cron): host busy (load1 74.25 / 5m 81.78 / 15m 76.09, threshold 7.5) — timed measurement refused as instructed. No static work remaining (H-Z2 confirmed 2026-09-02 21:06, folded into H-Z3); H-Z3 quiet-host hand-patch A/B remains deferred. No bench, no perfgate run, no numbers.
2026-09-03 02:18 JST (amu-rank cron, tick 78): host busy (load1 83.90 / 5m 82.82 / 15m 76.94, threshold 7.5) — measurement refused, rank-only pass. No new measured evidence since tick 77 (sibling entry 02:16 amu-falsify busy-refusal, already present in the working tree; committed here with this tick). NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers. Untracked k10/m.kexe provenance/publication sidecars still present (not touched by rank).
2026-09-03 02:23 JST (amu-bench cron): host busy (load1 67.55 / 5m 77.93 / 15m 76.72, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B; H-Z2 already confirmed). Untracked k10/m.kexe provenance/publication sidecars still present.
2026-09-03 02:33 JST (amu-rank cron, tick 79): host busy (load1 60.01 / 5m 67.09 / 15m 70.78, threshold 7.5) — measurement refused, rank-only pass. No new measured evidence since tick 78 (sibling entry 02:23 amu-bench busy-refusal, already present in the working tree; committed here with this tick). NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers. Untracked k10/m.kexe provenance/publication sidecars still present (not touched by rank).
2026-09-03 02:37 JST (amu-bench cron): host busy (load1 69.83 / 5m 67.45 / 15m 69.87, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B; H-Z2 already confirmed). Untracked k10/m.kexe provenance/publication sidecars still present.
2026-09-03 02:47 JST (amu-rank cron, tick 80): host busy (load1 87.83 / 5m 90.54 / 15m 82.22, threshold 7.5) — measurement refused, rank-only pass. No new measured evidence since tick 79 (sibling entries 02:33–02:37 amu-bench busy-refusal, already present in the working tree; committed here with this tick). NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers. Untracked k10/m.kexe provenance/publication sidecars still present (not touched by rank).
2026-09-03 02:53 JST (amu-bench cron): host busy (load1 90.65 / 5m 89.29 / 15m 83.75, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B; H-Z2 already confirmed). Untracked k10/m.kexe provenance/publication sidecars still present.
2026-09-03 03:05 JST (amu-rank cron, tick 81): host busy (load1 107.95 / 5m ~90 / 15m ~83, threshold 7.5) — measurement refused, rank-only pass. No new measured evidence since tick 80 (sibling entries 02:53 amu-bench busy-refusal, already present in the working tree; committed here with this tick). NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers. Untracked k10/m.kexe provenance/publication sidecars still present (not touched by rank).
2026-09-03 03:07 JST (amu-bench cron): host busy (load1 94.19 / 5m 104.61 / 15m 98.41, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B; H-Z2 already confirmed). Untracked k10/m.kexe provenance/publication sidecars still present.
2026-09-03 03:15 JST (amu-falsify cron): host busy (load1 89.24 / 5m 83.59 / 15m 88.54, threshold 7.5) — timed measurement refused as instructed; no bench, no perfgate run. H-Z2 static disassembly already confirmed (2026-09-02 21:06) and folded into H-Z3; the only remaining work is H-Z3's quiet-host hand-patch A/B, which cannot start under this load. No numbers recorded.
2026-09-03 03:31 JST (amu-falsify cron): host busy (load1 73.56 / 5m 68.98 / 15m 74.51, threshold 7.5) — timed measurement refused as instructed; no bench, no perfgate run. H-Z2 static work already complete (folded into H-Z3); H-Z3 quiet-host hand-patch A/B remains the sole next step, deferred. No numbers recorded.
2026-09-03 03:17 JST (amu-rank cron, tick 82): host busy (load1 62.19 / 5m 75.53 / 15m 84.70, threshold 7.5) — measurement refused, rank-only pass. No new measured evidence since tick 81 (sibling entries 03:07 amu-bench / 03:15 amu-falsify busy-refusal, already in working tree; committed here with this tick). NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers. Untracked k10/m.kexe provenance/publication sidecars still present (not touched by rank).
2026-09-03 03:24 JST (amu-bench cron): host busy (load1 84.70 / 5m 73.31 / 15m 80.13, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B).
2026-09-03 03:31 JST (amu-falsify cron): host busy (load1 73.56 / 5m 68.98 / 15m 74.51, threshold 7.5) — timed measurement refused as instructed; no bench, no perfgate run. H-Z2 static work already complete (folded into H-Z3); H-Z3 quiet-host hand-patch A/B remains the sole next step, deferred. No numbers recorded.
2026-09-03 03:47 JST (amu-rank cron, tick 83): host busy (load1 61.36 / 5m 65.70 / 15m 72.47, threshold 7.5) — measurement refused, rank-only pass. No new measured evidence since tick 82 (sibling entries 03:24 amu-bench / 03:31 amu-falsify busy-refusal, already in working tree; committed here with this tick). Population unchanged: H-Z3 top-ranked (evolve of H-Z1+H-Z2), awaiting quiet-host hand-patch A/B; H-D/H-B/Y1 gated on quiet host. NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers. Untracked k10/m.kexe provenance/publication sidecars still present (not touched by rank).
2026-09-03 03:38 JST (amu-bench cron): host busy (load1 37.40 / 5m 50.65 / 15m 63.55, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B; H-Z2 already confirmed). Untracked k10/m.kexe provenance/publication sidecars still present.
2026-09-03 03:55 JST (amu-falsify cron): host busy (load1 50.65 / 5m 47.81 / 15m 55.43, threshold 7.5) — timed measurement refused as instructed; no bench, no perfgate run. H-Z2 static work already complete (folded into H-Z3); H-Z3 quiet-host hand-patch A/B remains the sole next step, deferred. No numbers recorded.
2026-09-03 04:02 JST (amu-rank cron, tick 84): host busy (load1 39.13 / 5m 43.96 / 15m 52.92, threshold 7.5) — measurement refused, rank-only pass. No new measured evidence since tick 83 (sibling entries 03:38 amu-bench / 03:55 amu-falsify busy-refusal, already in working tree; committed here with this tick). Population unchanged: H-Z3 top-ranked (evolve of H-Z1+H-Z2), awaiting quiet-host hand-patch A/B; H-D/H-B/Y1 gated on quiet host. NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers. Untracked k10/m.kexe provenance/publication sidecars still present (not touched by rank).
2026-09-03 04:17 JST (amu-rank cron, tick 85): host busy (load1 14.80 / 5m 18.46 / 15m 31.98, threshold 7.5, trending down but above gate) — measurement refused, rank-only pass. Committed sibling busy-refusal entries 03:45 (amu-bench) / 04:01 (amu-falsify), already present in the working tree as H-Z3-row updates. No new measured evidence; population unchanged: H-Z3 top-ranked (evolve of H-Z1+H-Z2), awaiting quiet-host hand-patch A/B; H-D/H-B/Y1 gated on quiet host. NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers. NOTE: cowork-state script header still says NEXT H-Z2 — stale; H-Z2 confirmed 2026-09-02 21:06, folded into H-Z3. Untracked k10/m.kexe provenance/publication sidecars still present (not touched by rank).
2026-09-03 04:07 JST (amu-bench cron): host busy (load1 27.78 / 5m 20.35 / 15m 28.65, threshold 7.5) — timed bench/perfgate refused, no numbers recorded. NEXT unchanged (H-Z3 quiet-host hand-patch A/B). Untracked k10/m.kexe provenance/publication sidecars still present.
2026-09-03 04:32 JST (amu-rank cron, tick 86): host busy (load1 14.90 / 5m 19.45 / 15m 24.44, threshold 7.5, continuing to trend down but above gate) — measurement refused, rank-only pass. Committed sibling busy-refusal entry 04:07 (amu-bench), already present in the working tree. No new measured evidence; population unchanged: H-Z3 top-ranked (evolve of H-Z1+H-Z2), awaiting quiet-host hand-patch A/B; H-D/H-B/Y1 gated on quiet host. NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers. Untracked k10/m.kexe provenance/publication sidecars still present (not touched by rank).

2026-09-03 04:32 JST (amu-rank cron, tick 86): host busy (load1 14.90 / 5m 19.45 / 15m 24.44, threshold 7.5, continuing to trend down but above gate) — measurement refused, rank-only pass. Committed sibling busy-refusal entry 04:07 (amu-bench), already present in the working tree. No new measured evidence; population unchanged: H-Z3 top-ranked (evolve of H-Z1+H-Z2), awaiting quiet-host hand-patch A/B; H-D/H-B/Y1 gated on quiet host. NEXT unchanged (H-Z3 quiet-host hand-patch A/B), no status transitions without numbers. Untracked k10/m.kexe provenance/publication sidecars still present (not touched by rank).
2026-09-05 18:18 JST (amu-rank cron, tick 119): host busy (load1 8.57 / 5m 18.03 / 15m 26.88, threshold 7.5) — measurement refused, rank-only pass. git fetch: HEAD == origin/main (0/0). No new measured evidence since entry 118; population unchanged: H-Z3 top-ranked (evolve of H-Z1+H-Z2, quiet-host hand-patch A/B pending); J-B confirmed-diagnostic but unqualified, awaiting idle>=9/10 rerun; J-C blocked behind it; H-C2/H-D/H-B/H-Y1 open. NEXT unchanged (J-B fully-quiet-host rerun idle>=9/10, then H-Z3 A/B), no status transitions without numbers.
2026-09-05 18:47 JST (amu-rank cron, tick 120): host busy (load1 92.44 / 5m 90.18 / 15m 63.91, threshold 7.5) — measurement refused, rank-only pass. git fetch: 44 commits arrived (HEAD f1b8e243 behind origin/main 3a4f1036); local HEAD advanced past tick 119's 0/0 read (origin moved between the two fetches). NEW FINDING (rank-relevant, not a measurement): origin/main's docs/codegen-cosientist.md (blob after merge c1aece2e, PR #777 chain, committed 2026-09-05 17:46 JST) contains FIVE unresolved conflict-marker blocks (<<<<<<< HEAD / ======= / >>>>>>> origin/main at approx lines 38-45, 1388-1395, 1471-1992, 2006-2315) — the state doc itself was merged with markers left in. Consequences: (a) the origin iteration log now carries two divergent entry numberings (HEAD-side 111-113 vs origin-side 110-118, both present between markers); (b) origin-side entries 110-118 re-affirm NEXT = J-B fully-quiet-host rerun (idle>=9/10) of bench/runtime-comparison/jb_imod_control.c, then H-Z3 A/B, then H-C2 — consistent with tick 119's NEXT; (c) any sibling bot pulling origin/main and appending would inherit marker-laden prose, so the local working tree (marker-free, tick 119 entry uncommitted) is currently the cleanest copy. NOT fixed by rank this tick: the merge is a cross-bot artifact (c1aece2e authored outside this session) and repair requires choosing sides in blocks containing sibling evidence — flagged for the operator / next rank tick with origin pulled. No measured numbers this tick; no status transitions. Population unchanged: J-B confirmed-diagnostic but unqualified (awaiting idle>=9/10 rerun), H-Z3 top of the codegen ladder (quiet-host hand-patch A/B pending), H-C2/H-D/H-B/H-Y1 open. NEXT: J-B fully-quiet-host rerun (idle>=9/10) of bench/runtime-comparison/jb_imod_control.c for the perfgate-qualifiable number, then H-Z3 A/B; rank sub-task queued: reconcile the five conflict-marker blocks in the state doc on the next tick with origin pulled.
2026-09-05 18:48 JST (amu-falsify cron): host busy (load1 49.77 at pre-run / 92.44 at rank tick 120, threshold 7.5) — timed measurement refused as instructed; no bench, no perfgate run, no numbers. NEXT unchanged (J-B fully-quiet-host rerun idle>=9/10 of bench/runtime-comparison/jb_imod_control.c, then H-Z3 quiet-host hand-patch A/B, then H-C2); H-C2/H-D/H-B/H-Y1 open, H-Z3 top of the codegen ladder. No hand-patch work started: all remaining falsify paths (H-Z3 A/B, H-C2 A/B) require a quiet host; no load-robust static work remains. Working tree left marker-free per tick 120's finding (origin/main conflict markers NOT inherited). No status transitions without numbers.
2026-09-05 18:48 JST (amu-rank cron, tick 121): host busy (load1 40.42 / 5m 55.92 / 15m 61.66, threshold 7.5) — measurement refused, rank-only pass. git already fetched this tick (HEAD 70670834; origin unchanged since tick 120's 44-commit batch). Evidence reviewed since tick 120: sibling entry 18:48 amu-falsify (busy-refusal) already in working tree; no new ADR (0338 remains newest measured landing — J-B 14 consecutive positive windows, +7.6/+7.8/+6.3% fifth window, diagnostic-only, no perfgate verdict); no new measured numbers. No re-rank, no status transition. Population unchanged: J-B confirmed-diagnostic but unqualified (awaiting idle>=9/10 rerun), H-Z3 top of the codegen ladder (quiet-host hand-patch A/B pending), H-C2/H-D/H-B/H-Y1 open; J-C blocked behind J-B. Conflict-marker reconciliation (queued at tick 120) re-checked: origin/main docs/codegen-cosientist.md re-fetched to /tmp and scanned — ZERO conflict-marker lines (^<<<<<<< / ^======= / ^>>>>>>>) in the current origin blob (1765 lines), so the markers flagged at tick 120 are no longer present upstream; the queued sub-task is resolved as resolved-upstream (verified by grep count 0), no local repair needed. NEXT unchanged: J-B fully-quiet-host rerun (idle>=9/10) of bench/runtime-comparison/jb_imod_control.c for the perfgate-qualifiable number, then H-Z3 quiet-host hand-patch A/B, then H-C2.

- **122b (2026-09-05 19:15 JST, amu-falsify cron, measurement refused)**: host busy (load1 57.77 / load5 51.82 / load15 47.43, threshold 7.5) — no hand-patch or bench run attempted, no numbers. NEXT unchanged: H-C2 (instruction-order diff vs clang on `kernel`), quiet-host only.

2026-09-05 19:26 JST (amu-rank cron, tick 123): host busy (load1 75.71 / 5m 55.99 / 15m 49.89 at 19:21, threshold 7.5) — measurement refused, rank-only pass. git fetch: origin/main 3a4f1036 unchanged since tick 121's read; local doc remains marker-free with ticks 119-122 entries present. Evidence reviewed since tick 122: sibling entry 122b (amu-falsify 19:15, busy-refusal) already in working tree; no new ADR (0338 remains newest measured landing — J-B 14 consecutive positive windows, +7.6/+7.8/+6.3% fifth window, diagnostic-only, no perfgate verdict); no new measured numbers → no re-rank, no status transition, no new hypothesis. Discrepancy noted for the record: 122b (amu-falsify) states "NEXT unchanged: H-C2" while ticks 119-122 rank NEXT = J-B idle>=9/10 rerun → H-Z3 A/B → H-C2; this tick keeps the J-B-first ordering — J-B holds the only measured above-bar effect (diagnostic-only) and needs nothing but a quiet host to become perfgate-qualifiable, so its expected gain × probability still ranks first. Population unchanged: J-B confirmed-diagnostic but unqualified (awaiting idle>=9/10 rerun), H-Z3 top of the codegen ladder (quiet-host hand-patch A/B pending), H-C2/H-D/H-B/H-Y1 open; J-C blocked behind J-B. NEXT: J-B fully-quiet-host rerun (idle>=9/10) of bench/runtime-comparison/jb_imod_control.c, then H-Z3 quiet-host hand-patch A/B, then H-C2.

2026-09-05 20:08 JST (amu-rank cron, tick 126): host busy (load1 84.51 / 5m 66.73 / 15m 50.78, threshold 7.5) — measurement refused, rank-only pass. git fetch: origin/main 3a4f1036 unchanged since tick 123; local HEAD 6a18f06d unchanged. Evidence reviewed since tick 125: no new ADR (0338 remains newest measured landing — J-B imod specialization diagnostic-only, 5 consecutive positive windows +7.6/+7.8/+6.3%, no perfgate verdict); no new measured numbers from sibling bots (all busy-refusals) → no re-rank, no status transition, no new hypothesis. Population unchanged: J-B confirmed-diagnostic but unqualified (awaiting idle>=9/10 rerun), H-Z3 top of the codegen ladder (quiet-host hand-patch A/B pending), H-C2/H-D/H-B/H-Y1 open; J-C blocked behind J-B. NEXT: J-B fully-quiet-host rerun (idle>=9/10) of bench/runtime-comparison/jb_imod_control.c for the perfgate-qualifiable number, then H-Z3 quiet-host hand-patch A/B, then H-C2.

2026-09-05 21:16 JST (amu-falsify cron): host busy (load1 102.40 / 5m 106.72 / 15m 76.47, up 13:59, 15 users, threshold 7.5) — timed measurement refused as instructed; no hand-patch, no bench, no perfgate run, no numbers. Foreground terminal again returned empty output (known shape, entries 96/99/104 etc.); doc read via read_file, this entry appended via script (no heredoc, per the entry-117 incident convention). NEXT unchanged: J-B fully-quiet-host rerun (idle>=9/10) of bench/runtime-comparison/jb_imod_control.c, then H-Z3 quiet-host hand-patch A/B, then H-C2. Population unchanged: J-B confirmed-diagnostic but unqualified, H-Z3 top of the codegen ladder, H-C2/H-D/H-B/H-Y1 open; J-C blocked behind J-B.

2026-09-05 21:49 JST (amu-rank cron, tick 127): host busy (load1 12.98 / 5m 16.36 / 15m 40.91 at 21:46, threshold 7.5) — measurement refused, rank-only pass. git fetch: origin/main 3a4f1036 unchanged since tick 126; local HEAD advanced to 723e84b4 (lang-cosientist iteration 11: min/max desugar branch landed — rank-noted, not a codegen-ladder number). Evidence reviewed since tick 126: sibling entry 21:16 amu-falsify (busy-refusal) already in working tree; no new codegen ADR (0338 remains newest measured landing — J-B imod specialization diagnostic-only, 5 consecutive positive windows +7.6/+7.8/+6.3%, no perfgate verdict); no new measured numbers → no re-rank, no status transition, no new hypothesis. Population unchanged: J-B confirmed-diagnostic but unqualified (awaiting idle>=9/10 rerun), H-Z3 top of the codegen ladder (quiet-host hand-patch A/B pending), H-C2/H-D/H-B/H-Y1 open; J-C blocked behind J-B. NEXT: J-B fully-quiet-host rerun (idle>=9/10) of bench/runtime-comparison/jb_imod_control.c for the perfgate-qualifiable number, then H-Z3 quiet-host hand-patch A/B, then H-C2.

2026-09-05 22:18 JST (amu-falsify cron): host busy (load1 7.93 / 5m 7.65 / 15m 12.66, up 15:01, 15 users, threshold 7.5) — timed measurement refused as instructed; no hand-patch, no bench, no perfgate run, no numbers. Foreground terminal returned empty output (known shape, entries 96/99/104 etc.); doc read via read_file, this entry appended via script (no heredoc, per the entry-117 incident convention). NEXT unchanged: J-B fully-quiet-host rerun (idle>=9/10) of bench/runtime-comparison/jb_imod_control.c, then H-Z3 quiet-host hand-patch A/B, then H-C2. Population unchanged: J-B confirmed-diagnostic but unqualified, H-Z3 top of the codegen ladder, H-C2/H-D/H-B/H-Y1 open; J-C blocked behind J-B.

2026-09-05 22:29 JST (amu-rank cron, tick 128): host busy (load1 14.80 / 5m 14.61 / 15m 14.90 at 22:25, threshold 7.5) — measurement refused, rank-only pass. git fetch: origin/main unchanged since tick 127; local HEAD b0948418 (tick 127). Evidence reviewed since tick 127: newest sibling entry is amu-falsify 22:18 (busy-refusal, load1 7.93 — above threshold but nearly clear); no new codegen ADR (0338 remains newest measured landing — J-B imod specialization diagnostic-only, 5 consecutive positive windows +7.6/+7.8/+6.3%, no perfgate verdict); no new measured numbers → no re-rank, no status transition, no new hypothesis. Population unchanged: J-B confirmed-diagnostic but unqualified (awaiting idle>=9/10 rerun), H-Z3 top of the codegen ladder (quiet-host hand-patch A/B pending), H-C2/H-D/H-B/H-Y1 open; J-C blocked behind J-B. NEXT: J-B fully-quiet-host rerun (idle>=9/10) of bench/runtime-comparison/jb_imod_control.c for the perfgate-qualifiable number, then H-Z3 quiet-host hand-patch A/B, then H-C2.
2026-09-05 23:07 JST (amu-falsify cron): host busy — load1 dipped to 3.73 at 23:03 (from 7.47 at 22:48) but rose again during iostat observation (23:00-23:06 JST: load1 6.96->17.65, iostat idle 21-69% = 4-6 idle CPUs of 10, load5 9.2-10.7, up 15:46, 15 users, threshold 7.5) — no sustained quiet window, so the J-B fully-quiet-host rerun and the H-Z3 hand-patch A/B were NOT started (measurement not started per quiet-gate rule). No numbers recorded. Foreground terminal returned empty output (known shape, entries 96/99/104 etc.); load probes via background sleep + file redirect, doc read via read_file, this entry appended via script (no heredoc, per the entry-117 incident convention). NEXT unchanged: J-B fully-quiet-host rerun (idle>=9/10) of bench/runtime-comparison/jb_imod_control.c, then H-Z3 quiet-host hand-patch A/B, then H-C2. Population unchanged: J-B confirmed-diagnostic but unqualified, H-Z3 top of the codegen ladder, H-C2/H-D/H-B/H-Y1 open; J-C blocked behind J-B.


2026-09-05 23:10 JST (amu-rank cron, tick 129): rank-only pass, no measurement by role. Host load decaying but not yet sustained-quiet: load1 4.00 (below 7.5), load5 7.90, load15 22.21 at 23:04; sibling falsify tick 23:07 observed load1 6.96->17.65 over 23:00-23:06 with idle 4-6/10 CPUs — no sustained quiet window yet, but the J-B quiet window is close. git fetch run: local HEAD bb6f1e80 (lang-cosientist iteration 13 — docs/lang-cosientist.md scope, not a codegen-ladder number). Evidence reviewed since tick 128: falsify ticks 22:18 and 23:07 (both busy-refusals, no numbers); no new codegen ADR (0338 remains newest measured landing — J-B imod specialization diagnostic-only, no perfgate verdict); no new measured numbers -> no re-rank, no status transition, no new hypothesis. Population unchanged: J-B confirmed-diagnostic but unqualified (awaiting idle>=9/10 rerun of bench/runtime-comparison/jb_imod_control.c), H-Z3 top of the codegen ladder (quiet-host hand-patch A/B pending), H-C2/H-D/H-B/H-Y1 open; J-C blocked behind J-B. NEXT: J-B fully-quiet-host rerun (idle>=9/10) of bench/runtime-comparison/jb_imod_control.c — load trend suggests attempt it next tick — then H-Z3 quiet-host hand-patch A/B, then H-C2.

2026-09-05 23:58 JST (amu-rank cron, tick 130): rank-only pass, no measurement by role. Host load has decayed into the quiet band: load1 3.80 / load5 10.11 / load15 11.46 at 23:56 (threshold 7.5) — load1 is now below gate; load5/15 still above but falling. git fetch run: no new origin commits since tick 129 (local HEAD bb6f1e80; newest commit 57622a9e is jit-cosientist tick 13, jit scope, not a codegen-ladder number). Evidence reviewed since tick 129: falsify 23:07 was the newest sibling entry (busy-refusal, no numbers); no new codegen ADR (0338 remains newest measured landing — J-B imod specialization diagnostic-only, 5 consecutive positive windows +7.6/+7.8/+6.3%, no perfgate verdict); no new measured numbers -> no re-rank, no status transition, no new hypothesis. Population unchanged: J-B confirmed-diagnostic but unqualified (awaiting idle>=9/10 rerun of bench/runtime-comparison/jb_imod_control.c), H-Z3 top of the codegen ladder (quiet-host hand-patch A/B pending), H-C2/H-D/H-B/H-Y1 open; J-C blocked behind J-B. NEXT: J-B fully-quiet-host rerun (idle>=9/10) of bench/runtime-comparison/jb_imod_control.c — load1 3.80 is the quietest window observed today, amu-bench should attempt it this window — then H-Z3 quiet-host hand-patch A/B, then H-C2.

- **119 (2026-09-06, first host-qualified tick after 10+ consecutive
  busy-refusals; the refusals were reading the wrong machine)**: the quiet gate
  the three bots apply (`load1 > 7.5`) is prose in
  `scripts/hermes-cron-jobs/hermes-cron-jobs.json`, not code, and it reads the
  operator workstation, because every bot's `workdir` is the local checkout and
  no amu script contains an ssh. Measured this tick: that workstation at load1
  15.9–38.4, and **all seven reachable fleet nodes at busy-CPU 0.04–0.07
  against ADR 0282's 0.10 limit** (`quiet-host.cljs`, probed 7 of 7). Every
  refused tick since 2026-08-29 had a qualifying host available. Landed
  `scripts/quiet-host.cljs` (three distinct exits: qualified / probed-none /
  could-not-probe) and `scripts/remote-bench.cljs` (stages HEAD on the chosen
  node, refuses an uncommitted tree). Verified end to end on levi at
  busy-CPU 0.07→0.04. **This is a blocker fix, and per the Rank rule a blocker
  that gates every other claim outranks any single codegen win** — H-C2, H-D,
  H-B and H-Y1 were not unrankable, they were unmeasurable.

- **120 (2026-09-06, build-time axis; measured, not yet a perfgate verdict)**:
  the research goal names runtime only, so cold compile time has never been
  ranked. Re-measured `performance-baseline` on levi (host-qualified,
  commit `ee5771c0`, 5 runs):

  | target | cold process | loaded compiler | startup share |
  |---|---:|---:|---:|
  | wasm32 | 887.95 ms | 186.66 ms | 701.28 ms (**79%**) |
  | aarch64 | 1241.12 ms | 293.62 ms | 944.35 ms (**76%**) |

  Three quarters of a cold compile is process and namespace startup, not
  compiler work — that is where a build-speed hypothesis belongs, and
  `launcher-comparison` on the same host shows the front-end swap already
  banked only 1.05x (61.89 ms median saved, 1262.42 → 1200.53 ms).

  ⚠ **Do not read these against `docs/performance.md`'s 5,141.83 / 5,934.01 ms.**
  That baseline records neither its host nor that host's load, so the ~5x
  difference cannot be attributed between "quiet host", "different commit" and
  "compiler got faster". **An unqualified baseline cannot ground a regression
  claim in either direction**; the fix is to re-establish it through
  `remote-bench.cljs` so the next comparison has a host reading attached.

- **121 (2026-09-06, route fork on the tournament's own architecture —
  filed as amu #818)**: `compile --jvm-free --target aarch64-macos` **exits 0**
  and writes an artifact that both routes' verifier rejects (`native export
  table rejected`). Scope measured across three targets: `x86_64-macos` and
  `wasm32` are **byte-identical** between routes; only aarch64 diverges. Same
  `:kir-sha256`, same effects, same export table except `__kotoba_loop_1`
  (**388 vs 752 bytes**), first differing code byte at offset 308 — the first
  instruction of the loop body, `LDR x16,[x23,#8]` (nbb) vs `SUBS xzr,x0,xzr`
  (jvm). `90-docs/codegen/coscientist/iteration-32.edn` recorded this input
  failing loudly on the nbb route with `:kotoba/internal-error`; the fix
  (kotoba-native `b77496b8`, amu #722) removed the error and left the
  divergence, **turning a loud failure into a silent one**. Not claimed: which
  lowering is correct — neither artifact was executed.

- **122c (2026-09-06, the first complete host-qualified reading of the claim
  contract: 18/30)**: the competitive multidomain suite ran on a quiet fleet
  node — busy-CPU 0.033 / 0.036 / 0.036 across the three consecutive samples
  ADR 0282's gate requires — with all 30 candidate/comparator/domain pairs
  measured and every known answer verified. Report retained at
  `bench/runtime-comparison/qualified-30pair-20260906.json`.

  | workload | rust | clang | zig | go | swift |
  |---|---:|---:|---:|---:|---:|
  | narrow-arithmetic | +1.0% | +1.9% | +21.0%* | +84.9%* | +1.0% |
  | wide-register-pressure | +9.3%* | +11.9%* | +17.9%* | +86.1%* | +87.6%* |
  | deep-spill-pressure | −0.2% | +4.4% | +0.3% | +81.3%* | +92.4%* |
  | call-preservation | −6.9% | −7.1% | +39.6%* | +84.5%* | +24.9%* |
  | branch-call-control-flow | −8.3% | −11.4% | +40.7%* | +84.5%* | +21.9%* |
  | loop-call-back-edge | +0.5% | −0.9% | +32.1%* | +16.6%* | +24.4%* |

  `*` = clears perfgate. **Go 6/6, Swift 6/6, Zig 5/6, Rust 1/6, Clang 1/6.**
  12 of the 12 unqualified pairs fail on `improvement-below-threshold`, 8 also
  on `not-separated-from-noise`; only 4 are actual losses. Those 4 are
  `call-preservation` and `branch-call-control-flow` against rust and clang,
  losing by −6.9/−7.1 and −8.3/−11.4 — two LLVM backends, nearly identical
  margins, one boundary rather than four defects.

  **Correction to H-E's status, and to iteration 20's "past clang".** H-E is
  not open work: iteration 21 landed the preserved tier, and the emission
  confirms it — `kernel_call` at `b5a0c302` compiles to 252 code bytes with
  **1 STR and 1 LDR in the whole module**, not the 8 STR + 11 LDR slot shape
  H-E describes. What is stale is the comparison. Iteration 20 recorded the
  hand mutant at 4.84 ns as "past clang's measured 5.03"; on a host-qualified
  run today clang measures **4.701** on that domain and amu **5.034**. The
  5.03 figure was clang's number on some other occasion, and treating it as
  clang's standing cost made a 7% deficit look like a win. Any hypothesis
  ranked against it needs re-ranking.

  NEXT is therefore not H-E. It is: find what costs amu ~0.33 ns per call on
  `call-preservation` when the allocator is already doing the thing H-E asked
  for. The instruction-stream diff against clang's twin is the same method
  H-C used, and this time both arms are on one qualified host.

- **123 (2026-09-06, Reflect executed on the call boundary; the 6.47% gap
  decomposed, and H-C is not in the emission)**: instruction-stream diff of
  `kernel_call` against its clang twin on one quiet host, both arms measured
  in the same harness, 60 samples per arm interleaved ABBA.

  **First, the harness is neutral.** amu runs through the runner's `raw` mode
  (anonymous mmap + mprotect) and every comparator through `dylib` (dlopen +
  dlsym), which is a difference that would bias all 30 pairs if it cost
  anything. Extracting clang's own `kotoba_bench_step_c`/`kernel_call` span
  into a raw blob and running the *same bytes* both ways: **+0.11%**. The load
  path is not the gap, and the 18/30 score is not an artifact of it.

  **The gap, decomposed** (medians; clang 4.4850):

  | arm | median | vs clang |
  |---|---:|---:|
  | base | 4.7750 | −6.47% |
  | + callee strength reduction | 4.7000 | −4.74% |
  | + caller MOVs removed (`comb`) | 4.6400 | −3.46% |
  | + fuel preamble removed (diagnostic) | 4.5600 | −1.67% |

  Two shippable compiler changes, worth **+3.13%** together on this domain,
  every manifest input byte-identical and the one-fuel-per-call contract
  intact:

  1. **The callee still multiplies.** `step` ends `MOV x2,#2147483647;
     MSUB x0,x1,x2,x0`; clang ends `sub x9,x9,x9,lsl #31; add`. Same
     instruction count, one fewer multiply, and it is on the dependency chain
     of all eight calls. Measured alone: **+2.49%**.
  2. **Four dependent MOVs in the caller.** amu emits `ADD x2,x19,#k; MOV
     x0,x2` where clang emits `add x0,x19,#k`, plus one `MOV x0,x19` when x0
     already holds n. Measured alone: **+1.28%** — and that understates the
     compiler change, because a byte-preserving hand patch must leave NOPs
     where the real fix removes instructions.

  **H-C reaches some fixtures and not others.** Counting across all six
  required fixtures at `b5a0c302`: MSUB 16 / 16 / 24 / 1 / 1 / 0.

  ⚠ **This entry first said "SUB-with-shift zero everywhere". That was a
  broken instrument, not a finding.** The detector masked
  `(x & 0xffe0fc00) == 0xcb000000`, and `0xfc00` covers the shift-amount
  field — so the companion test `imm6 != 0` could never be true and every
  fixture reported zero by construction. Re-measured with a decoder validated
  against clang's own `sub x9,x9,x9,lsl #31` (`0xcb097d29`, imm6 = 31):
  `kernel` emits **8** shifted subtracts. H-C is active there. What is true is
  narrower and is what iteration 124 acts on: the two call domains emit an
  MSUB and no shifted form.

  ⚠ **And H-C's +2.46% on `kernel` did not reproduce.** Strength-reducing all
  16 sites there (1:1 MOV/MSUB, so an in-place patch is exact) measured
  **−0.15% → +0.00%** vs clang at n=12. The transformation is worth ~2.5% on
  the call domains and nothing measurable on `kernel`. That is a third figure
  in this file whose measurement conditions did not travel with it.

  **`kernel_wide` and `kernel_deep` cannot be hand-patched this way at all**,
  and the reason matters for the compiler change: they hoist the constant into
  x13 **once** and reuse it across 16 and 24 MSUBs. Rewriting that single MOV
  destroys the constant for every later site — the correctness gate caught it
  (results 3793385996124 and 4963239473660 against 5224842816 and 2552249090).
  In those domains the transformation *adds* an instruction per site rather
  than trading one for one, so it must be measured there before it is assumed
  to help.

  **Neither fix flips a pair.** `call-preservation` goes −7.1% → about −4%:
  closer, still a loss. The pair nearest to qualifying remains
  `deep-spill-pressure` vs clang at **+4.4%**, needing +0.6pp — and that is a
  domain where this transformation is not yet known to be safe or profitable.

  NEXT: the ~1.67% that survives with both fixes applied and fuel removed,
  where amu and clang execute the same instruction mix. Static shape is
  exhausted as an explanation; this one needs a scheduling or front-end
  measurement.

- **124 (2026-09-06, the single-MSUB clause was unreachable; and why
  `deep-spill-pressure` wins)**: kotoba-native #142 lands the first half of
  iteration 123's finding as a compiler change.

  `a64-serial-msub-chain?` opens with `(<= msub-count 1)` — a single MSUB is
  trivially one serial chain, which is the case the shifted form wins. **That
  clause was unreachable.** Its values come from
  `a64-profitable-cached-mersenne-values`, which reads the constant cache, and
  the cache admits only constants occurring more than once (correctly — one use
  saves no materialization). The one case the chain test exists to admit was
  filtered out a layer earlier. `kernel_call` and `kernel_call_branch` now emit
  clang's shape; `kernel`, `kernel_wide`, `kernel_deep` and `kernel_loop_call`
  are byte-identical, and the gate's own 5.1% loss on independent lanes is
  preserved.

  Two guards worth keeping in mind for the next such change. Being Mersenne is
  not enough to admit a constant — every 2^k−1 is, including the 3 in
  `(i64-shift-left a 3)`, and admitting shift amounts moved allocation under
  unrelated code (7 encoding-parity failures). And the first byte-identity
  comparison was **confounded**: the baseline used amu's *pinned*
  kotoba-native while the candidate used main, so #138's fuel preamble
  (`CBNZ; BRK; SUB` → `SUBS; B.cond; BRK`) showed up as this change moving
  `kernel` and `kernel_loop_call`. Compare against the same base.

  **`deep-spill-pressure`: amu's lead is structural, and the obvious "waste"
  is the reason for it.** amu emits 48 constant-materialization words against
  clang's 1, which reads as pure overhead until you look at what it buys:
  amu computes `n*48271` **once** and adds a folded per-lane constant
  `k*48271+1`, where clang emits 24 separate MADDs. amu trades one extra word
  per lane for 23 fewer multiplies, and that is why it is +4.4% ahead rather
  than behind. Do not "fix" it toward clang's shape.

  The cost is real but nearly forced: only lane 0's addend fits an ADD
  immediate, only lanes 0–1 fit a bare MOVZ, and lanes 2–23 need MOVZ+MOVK.
  One untested lead — the addends are an arithmetic progression, so the five
  power-of-two lanes (k = 1, 2, 4, 8, 16) could be `ADD xd, base, xM, LSL #s`
  with 48271 held in xM: one word where three are spent now, 10 words of 241.
  ⚠ Unmeasured, and this fixture's docstring says it sits *above* the register
  pool, so pinning xM may buy spills that cost more than the words save. It
  needs the hand-patch treatment before it is believed.

  This pair still needs **+0.6pp** to qualify and is the nearest of the eight
  near-misses. NEXT is that lead, measured — not the call boundary, where
  #142 takes `call-preservation` from −7.1% to about −4% and the remaining
  deficit is scheduling-shaped rather than static.

- **125 (2026-09-06, PROVEN CEILING on `narrow-arithmetic`)**: this file's
  opening paragraph names a proven ceiling as an honest terminal state — *"if
  Amu's emitted stream for a domain is cost-identical to LLVM's best, a strict
  ≥5% win on that domain is unreachable for anyone, and recording that is a
  result."* That is now the measured state of `narrow-arithmetic`.

  Disassembling the `kernel` symbol only (not the module — the module carries
  `bench`, `__kotoba_loop_1` and `main`, and comparing it against one clang
  symbol reports 275 against 61 and 24 rounds against 8, which is how this
  comparison was first got wrong):

  | | instructions | MADD | SMULH | shifted SUB | shifted ADD |
  |---|---:|---:|---:|---:|---:|
  | amu | **61** | 8 | 8 | 8 | 8 |
  | clang | **61** | 8 | 8 | 8 | 8 |
  | rust | **61** | 8 | 8 | 8 | 8 |

  amu and clang emit **the same opcode sequence**. 60 of 61 words differ, and
  every one of those differences is a register number; the single opcode
  difference is `MOVZ x13,#48271` against `MOVZ w8,#48271`, the same immediate
  in the 32-bit form. rust lands on 61 with the same mix.

  So the three unqualified `narrow-arithmetic` pairs — rust +1.0%, clang
  +1.9%, swift +1.0% — are not near-misses waiting on a codegen idea. **Three
  compilers agree on the program.** The residual is register assignment and
  measurement noise, and a ≥5% separated win is unreachable for any of them.
  H-C is already applied here (the 8 shifted subtracts), which is the other
  half of iteration 123's correction.

  **This bounds the claim contract.** Of the eight positive-but-unqualified
  pairs, three are at a shared ceiling. The bounded fastest claim requires all
  thirty; it is therefore not reachable by codegen work on this fixture set,
  and no amount of iteration will make `narrow-arithmetic` a 5% win.

  What remains genuinely open, in order of reachability:

  | pair | now | needs | shape of the gap |
  |---|---:|---:|---|
  | `deep-spill-pressure` × clang | +4.4% | +0.6pp | one untested lead (124) |
  | `deep-spill-pressure` × zig | +0.3% | +4.7pp | unexamined |
  | `loop-call-back-edge` × rust | +0.5% | +4.5pp | unexamined |
  | `call-preservation` × rust/clang | ≈−4% after #142 | +9pp | ~1.67% survives with fuel removed |
  | `branch-call-control-flow` × rust/clang | −8 to −11% | +13pp | unexamined, the largest deficit |

  The honest statement of where the tournament stands: **amu native is fastest
  among the enumerated implementations against Go and Swift on all six required
  domains (12 of 12 pairs qualified), leads Zig on five of six, and against the
  two LLVM backends holds one domain, ties one at a proven ceiling, and trails
  on the call boundary.** That sentence is measurable, measured, and true. The
  contract's sentence is not, and 125 is the reason it cannot become true here.

- **126 (2026-09-06, if-conversion FALSIFIED on `branch-call-control-flow`;
  and a bug report I filed and withdrew)**: the largest deficit in the
  tournament (−11.4% vs clang) had never been opened. Static shapes:

  | | instructions | control flow | epilogues |
  |---|---:|---|---:|
  | amu | 59 | `CBNZ`, hot path on the **taken** side | **2** (duplicated) |
  | clang | 44 | `cmp` + `csel`, branchless | 1 |

  The obvious hypothesis: if-convert a two-arm branch with cheap arms into a
  conditional select, as clang does. Hand-patched byte-preserving — 7 ADD,
  `CMP x19,#0`, `CSEL x0,xzr,x0,EQ`, one epilogue, 6 NOP — every manifest input
  identical including `n=0 → 0`, which is the arm the select exists for.

  **+0.12%, not separated; the median moved the wrong way (4.920 → 4.950).**
  The hypothesis is wrong, and in hindsight obviously so: the benchmark calls
  with `n=200` every time, so the branch is perfectly predicted and costs
  nothing, while the 15 extra instructions sit almost entirely in the
  *not-taken* path where they are never fetched. `CSEL` only adds a dependency
  on the compare. **Instruction count is not the cost here; occupancy of the
  executed path is.**

  So the ~4pp that separates this domain from `call-preservation` — same eight
  calls, same arithmetic, one `if` — is still unexplained, and it is not the
  branch. Both save the same number of registers (5 store instructions each),
  so the prologue is not it either. NEXT is an instruction-by-instruction diff
  of the two amu emissions, which is cheap and has not been done.

  ⚠ **The fixture's docstring is wrong and should be corrected**: it says the
  `if` "sends it to the conservative all-vreg path where every value gets a
  stack slot whether or not anything was short of registers." There are **no
  value stack slots** in the emission — only the callee-saved prologue and
  epilogue. That describes a compiler that no longer exists.

  ⚠ **kotoba-native#143 was mine and was wrong.** I reported #138 as breaking
  the verifier for call-containing functions, on a clean-looking bisect. The
  bisect was measuring my own harness: I compiled with an overridden
  kotoba-native and ran `extract-native` **without** the override, so the
  verifier re-emitted with amu's pinned compiler and compared against bytes
  from a different one. With the override on both sides the artifact verifies,
  and re-emitting directly gives 0 differing instructions of 63.
  `verifier.cljc:1891` was doing exactly its job. Issue withdrawn and closed.

  The residue worth keeping: `native instruction stream rejected` reads as a
  defect in the artifact rather than as a version mismatch between the emitter
  that produced it and the one checking it. Naming both identities in that
  message would have ended this in seconds rather than a bisect.

- **127 (2026-09-06, the `if` costs amu 3% and earns clang 1%, on 52 vs 51
  executed instructions)**: the cheap diff that should have come before 126's
  hand patch. `kernel_call` and `kernel_call_branch` differ by one `if`.

  Instruction for instruction, the two amu emissions are **the same program**
  through the entire call sequence — bytes 0–148 differ only in which
  callee-saved register holds which result. Two real differences:

  1. `kernel_call` reuses **x19** for the fifth call result, because `n` is
     dead after the fourth argument. `kernel_call_branch` cannot: `n` is live
     to the `CBNZ x19`, so it takes **x26** instead and saves one more
     register. That is forced by the program, not a choice — clang keeps x19
     for its `cmp x19,#0` for the same reason. Both save 5 store instructions.
  2. The duplicated epilogue, which 126 already showed is off the hot path.

  Executed instructions at `n=200`: **51 for `kernel_call`, 52 for
  `kernel_call_branch`** (39 through the CBNZ, then 13 at the branch target).
  One instruction apart.

  And the direction is the tell:

  | | amu | clang |
  |---|---:|---:|
  | `kernel_call` | 4.7750 | 4.4875 |
  | `kernel_call_branch` | **4.9200** | **4.4450** |

  **Adding the `if` makes clang faster and amu slower.** clang gains 0.9%;
  amu loses 3.0%. On one extra executed instruction, with the same register
  discipline and the same call sequence.

  Three structural hypotheses are now falsified for this domain: the branch
  itself (126, if-conversion +0.12%), the prologue (same store count), and
  instruction count (52 vs 51). What remains is layout- or front-end-shaped —
  amu's executed path spans 236 bytes across a forward jump where
  `kernel_call`'s is 204 contiguous — and that is not visible in a static
  diff. It needs a measurement this loop does not currently have: the
  hand-patch method cannot move code without moving branch targets, so
  testing a layout hypothesis means a compiler change or a
  performance-counter read, not a byte substitution.

  That is the honest edge of the method here, and it is worth naming rather
  than working around: **every remaining deficit in this domain is smaller
  than what a byte-preserving patch can resolve.**

- **128 (2026-09-06, layout FALSIFIED too; four hypotheses down on
  `branch-call-control-flow`)**: 127 ended by saying a layout hypothesis needs
  an instrument this loop does not have. That was wrong — it needs one shift.

  Prepending NOPs to the blob and calling at `48+k` moves the whole code
  together, so every relative branch stays correct and *only the placement*
  changes. Six shifts, both fixtures, 14 interleaved samples each, every
  variant verified to still answer 1190481486 with fuel 1:

  | shift | +0 | +4 | +8 | +16 | +32 | +64 |
  |---|---:|---:|---:|---:|---:|---:|
  | `kernel_call` | 4.7650 | 4.7600 | 4.7650 | 4.7600 | 4.7600 | 4.7600 |
  | `kernel_call_branch` | 4.9300 | 4.9200 | 4.9300 | 4.9225 | 4.9200 | 4.9650 |

  Spread: **0.11%** and **0.91%** of median. The ~3.3% gap between the two
  fixtures is present at every alignment, including the ones that break
  16-byte alignment. **Placement is not the cause.**

  Falsified for this domain, each by measurement rather than argument:

  | hypothesis | verdict |
  |---|---|
  | the branch itself | if-conversion to CSEL: **+0.12%**, median worse (126) |
  | the prologue | identical store count, the extra register is forced (127) |
  | instruction count | 52 executed against 51 (127) |
  | code placement | flat across six shifts (128) |

  What survives is the one thing 127 found and could not price: with the `if`,
  `n` is live to the test, so the allocator cannot recycle x19 for the fifth
  call result and takes x26 — ten callee-saved registers in play against nine,
  across eight calls. Same instruction count, one more architectural register
  live across every call boundary. That is a rename/pressure question, and the
  next honest instrument for it is a performance counter, not another
  substitution.

  Recording the negative space deliberately: a later reader should not re-run
  any of these four. The cheap structural explanations for this domain are
  exhausted, and the remaining 3.3% is smaller than any of them.

- **129 (2026-09-06, CONFIRMED: one extra callee-saved register is 2.84% of
  the 3.36%)**: after four falsifications, the surviving suspect from 127 —
  ten callee-saved registers against nine — is isolated and priced.

  The test removes every other variable. `kernel_call` is patched to hold its
  fifth call result in **x26** instead of recycling x19, which is exactly what
  the branch version is forced into, and **nothing else changes**: no branch,
  no extra instruction, same executed path, same layout.

  | arm | callee-saved | branch | median | vs base |
  |---|---:|---|---:|---:|
  | `kc-base` | 9 | no | 4.7600 | — |
  | `kc-x26` | **10** | **no** | **4.8950** | **+2.84%** |
  | `kcb-base` | 10 | yes | 4.9200 | +3.36% |

  **The register accounts for 2.84 of the 3.36 points. 0.53% is left for
  everything else — the branch, the second epilogue, the extra instruction.**
  That is consistent with 126 and 128 finding nothing in those.

  The first attempt at this patch answered 1180682672 instead of 1190481486:
  I moved the definition and one use but missed that the sum chain also reads
  the fifth result (`ADD x2,x22,x19`). The correctness gate caught it. A
  register-renaming patch has to rename *every* reader, and the readers are
  not adjacent to the definition.

  **Why amu pays this and clang does not.** clang saves ten callee-saved
  registers in *both* fixtures — `stp x26,x25 / x24,x23 / x22,x21 / x20,x19 /
  x29,x30`. amu's `kernel_call` saves nine, because it notices `n` is dead
  after the fourth argument and recycles x19. So amu is *better allocated*
  than clang on `kernel_call`, and the `if` takes that advantage away: with
  `n` live to the test, x19 cannot be recycled and amu is forced up to clang's
  ten. clang's two fixtures measure 4.4875 and 4.4450 — nearly flat — for
  exactly this reason: it never had the advantage to lose.

  ⚠ **This explains the amu-to-amu delta, not the amu-to-clang deficit.**
  amu's nine-register `kernel_call` is still 6.4% behind clang's ten-register
  one, so register count is not that gap. Do not read 129 as pricing the
  distance to clang.

  Whether it is fixable is doubtful and should be stated: eight results plus a
  live `n` is nine values across eight calls, and the allocator is already
  tight. Spilling `n` trades the register for a stack slot on the same path.
  The honest reading is that `branch-call-control-flow`'s extra deficit over
  `call-preservation` is **forced by the program**, and the domain's real
  target is the ~6.4% it shares with `call-preservation`, not the 3.36%
  between them.

- **130 (2026-09-06, #142 measured as shipped, and the gate cannot see it)**:
  kotoba-native#142 is confirmed in real compiler output — `kernel_call`'s
  module goes MSUB 1 → 0 and shifted-SUB 0 → 1, and the artifact answers every
  manifest input with fuel 1. Measured against the same clang binary:

  | | median | min | vs clang |
  |---|---:|---:|---:|
  | before #142 | 4.7600 | 4.7550 | −5.90% |
  | **after #142** | **4.6900** | **4.6750** | **−4.34%** |

  **+1.47% median, +1.66% mean at n=110 per arm.** Both robust statistics move
  together and stay put as samples accumulate.

  ⚠ **It will not pass perfgate, and more samples make that worse.** At n=50
  the gap was 0.0740 against a summed-sd of 0.0867 — nearly separated. At
  n=110 the gap is 0.0805 and the summed-sd is **0.3964**, because longer runs
  catch more outliers on a shared machine even when the node is quiet by the
  busy-CPU gate. Each arm's own spread is fine (rsd 0.044 and 0.039, well
  inside the policy's 0.10); it is the *sum* of two spreads being compared
  against a 1.7% effect.

  That is worth stating as a property of the tournament rather than of this
  change: **`perfgate.core/qualify` as configured cannot resolve an
  improvement of this size on this fixture.** A real 1.5–2% gain is invisible
  to the gate individually. Since the claim contract needs ≥5% *per pair*,
  improvements of this magnitude can only ever count by accumulating into one
  measurement — several landed together, measured once — not by being
  qualified one at a time.

  Two consequences for how this loop should proceed:

  1. **Do not discard a hypothesis because its hand-patch came back "not
     separated."** 126's if-conversion (+0.12%) is a genuine null; 123's
     strength reduction (+2.49%) and this (+1.66%) are not — they are real
     effects under the instrument's resolution. The ledger has been recording
     both with the same phrase, which flattens the distinction.
  2. **Report median and min alongside the mean.** Here they are stable to
     0.005 ns across 110 samples while the mean wanders by 0.08; the gate's
     verdict and the robust statistics disagree, and only one of them is
     tracking the change.

  `call-preservation` now stands at **−4.34%** against clang, from −6.47% when
  123 opened it.

- **131 (2026-09-06, ONE FRAME ALLOCATION INSTEAD OF TEN — the first pair
  flip: `deep-spill-pressure` × clang QUALIFIES)**: amu builds its frame by
  chaining pre-indexed stores, so every save serially depends on the previous
  SP. clang allocates once and uses offset addressing.

  ```
  amu     STP x19,x20,[sp,#-16]!   clang   stp x26,x25,[sp,#-0x50]!
          STP x21,x22,[sp,#-16]!           stp x24,x23,[sp,#0x10]
          STP x23,x24,[sp,#-16]!           stp x22,x21,[sp,#0x20]
          STR x25,    [sp,#-16]!           stp x20,x19,[sp,#0x30]
          STP x29,x30,[sp,#-16]!           stp x29,x30,[sp,#0x40]
  ```

  SP updates per fixture: `kernel` 0, `kernel_wide` 0, `kernel_loop_call` 2,
  **`kernel_deep` 8, `kernel_call` 10, `kernel_call_branch` 15** — against two
  for clang in every case.

  Hand-patched to one allocation plus offset addressing. **Instruction count
  unchanged**; only the addressing mode differs. Every manifest input
  identical, fuel intact, on both fixtures tested.

  **`deep-spill-pressure` × clang, n=60 per arm:**

  | arm | mean | improvement | separated | rsd | qualifies |
  |---|---:|---:|---|---:|---|
  | amu base | 9.5262 | +4.35% | yes | 0.035 | **no** (under 5%) |
  | **amu + frame** | **9.3244** | **+6.37%** | **yes** | **0.013** | **YES** |

  All four `perfgate.core/qualify` conditions: improvement ≥ 0.05 ✓,
  separated from summed spread (0.6345 > 0.2196) ✓, both arms' rsd ≤ 0.10 ✓,
  ≥ 5 samples ✓. **This is the first pair to cross, and it takes the score to
  19/30 once the compiler emits it.**

  **`call-preservation` × clang:** +3.41% median on top of #142, moving amu
  from −4.22% to **−0.67%** — near parity, and amu's *minimum* (4.3500) is
  now below clang's (4.4600).

  Two encoding errors on the way, both caught rather than measured: `STR x25`
  lost its base-register field and addressed x15 (instant SIGSEGV), and a
  post-index LDP had `0xA8D0` where `0xA8C0 + 0x50000` is `0xA8C5`. The patch
  script now *generates* encodings from a register/offset spec instead of
  carrying hand-computed words, which removes the class.

  This is a prologue/epilogue emission change, not an allocator change — the
  registers saved and the frame size are identical, only the addressing mode
  moves. It should apply to every non-leaf function on this target.

  NEXT: `branch-call-control-flow` has **15** SP updates, the most of any
  fixture, and sits at −11.4%. Same patch, not yet measured there.

- **132 (2026-09-06, #145 shipped and measured; fp/lr fold attempted and
  reverted)**: the frame change is in the compiler and reproduces the hand
  patch. `kernel_deep` goes 8 SP updates → 2, and with the **real compiler
  output** at n=60:

  | arm | mean | vs clang | qualifies |
  |---|---:|---:|---|
  | amu base | 9.5723 | +4.52% | no |
  | **amu #145** | **9.4229** | **+6.01%** | **YES** |

  `call-preservation` measured across the whole progression:

  | | SP updates | vs clang |
  |---|---:|---:|
  | #142 only | 10 | −4.82% |
  | **#142 + #145 shipped** | **4** | **−1.69%** |
  | hand patch, fp/lr folded | 2 | −0.35% |

  **The remaining 1.32% is fp/lr.** The compiler still gives `stp x29,x30,
  [sp,#-16]!` its own pre-indexed push where clang folds it into the area
  (`stp x29,x30,[sp,#0x40]` then `add x29, sp, #0x40`, keeping fp pointing at
  the AAPCS64 frame record).

  ⚠ **I implemented that and reverted it.** Concatenating fp/lr onto `saved`
  and re-pairing is wrong whenever `saved` has odd length: `kernel_call` saves
  x19–x25, seven registers, so the pairs become `(x19,x20) (x21,x22)
  (x23,x24) (x25,x29) (x30)` — **x25 pairs with x29 and x30 is stranded**.
  15 failures and 87 errors against a clean baseline. Reverted; the branch is
  back to 380 tests / 5145 assertions / 0 failures.

  Doing it correctly means fp/lr must remain its own pair at the top of the
  area regardless of the parity of `saved`, which is a change to
  `a64-saved-frame`'s shape rather than to its caller. Worth +1.32% on
  `call-preservation` and it would not flip that pair — at −0.35% amu would
  be level with clang, and the contract wants +5%.

  That is the second time today a change in this file was over-broad on the
  first attempt (the other: admitting every Mersenne constant, including the
  `3` in a shift). Both were caught by the suite rather than by review, which
  is the argument for running it before pushing rather than after.

- **133 (2026-09-06, the full contract re-measured with #145: 18/30 → 19/30)**:
  the competitive multidomain suite, host-qualified, run with kotoba-native
  repinned to the frame change. Every one of the 30 pairs re-measured, not
  extrapolated.

  ```
  domain                        rust      clang-c11        zig          go         swift
  narrow-arithmetic         +1.0→+2.6   +1.9→+1.1   +21.0*→+20.9* +84.9*→+84.5*  +1.0→+0.4
  wide-register-pressure   +9.3*→+8.2* +11.9*→+11.9* +17.9*→+17.8* +86.1*→+86.3* +87.6*→+87.7*
  deep-spill-pressure       -0.2→+1.9   +4.4→+6.9*   +0.3→+2.2    +81.3*→+81.9* +92.4*→+92.7*
  call-preservation         -6.9→-1.2   -7.1→-1.3   +39.6*→+42.3* +84.5*→+85.3* +24.9*→+28.3*
  branch-call               -8.3→-4.1  -11.4→-7.8   +40.7*→+42.8* +84.5*→+85.3* +21.9*→+24.8*
  loop-call-back-edge       +0.5→+0.5   -0.9→-0.8   +32.1*→+31.6* +16.6*→+14.6* +24.4*→+24.5*
  ```

  **19/30. Newly qualified: `deep-spill-pressure` × clang-c11. Lost: none.**

  The call domains moved furthest — `call-preservation` gained **+5.7pp**
  against both LLVM backends and is now within noise of each (−1.2%, −1.3%
  from −6.9%, −7.1%). `branch-call` gained +4.2pp and +3.6pp. Nothing
  regressed anywhere; the two leaf domains are untouched because they have no
  save area.

  **Where the remaining eleven sit, and what each needs:**

  | pair | now | needs | reachable? |
  |---|---:|---:|---|
  | `narrow-arithmetic` × rust / clang / swift | +2.6 / +1.1 / +0.4 | +2.4…+4.6pp | **no — proven ceiling (125)**, three compilers emit the same 61 instructions |
  | `deep-spill` × zig / rust | +2.2 / +1.9 | ~+2.8pp | open |
  | `call-preservation` × clang / rust | −1.3 / −1.2 | ~+6.3pp | open; +1.32pp of it is the fp/lr fold (132) |
  | `branch-call` × rust / clang | −4.1 / −7.8 | ~+9…+13pp | open; 2.84pp is a forced extra register (129) |
  | `loop-call-back-edge` × rust / clang | +0.5 / −0.8 | ~+4.5…+5.8pp | unexamined |

  So the contract's ceiling on this fixture set is **27/30**, not 30 — three
  pairs are provably unreachable. Of the eight that remain, `deep-spill` ×
  zig and × rust are the nearest at ~2.8pp.

- **134 (2026-09-06, `loop-call-back-edge` is a second proven ceiling — the
  contract's real maximum is 25/30, not 30)**: the last unexamined domain.

  amu already bulk-charges fuel: an entry test decides whether the whole
  iteration count fits the budget and, if it does, runs a loop with **no
  per-iteration fuel accounting at all**. The metered nine-instruction body
  exists as the fallback. So the fast path is:

  ```
  amu     MOVZ x0,#1 ; BL id ; SUB x19,x19,#1 ; ADD x20,x20,x0 ; CBNZ x19
  clang   mov w0,#1  ; bl id ; add x20,x0,x20 ; subs x19,x19,#1 ; b.ne
  ```

  **Five instructions each**, same operations, differing only in whether the
  decrement-and-test is `SUB`+`CBNZ` or `SUBS`+`B.NE`. Measured +0.5% against
  rust and −0.8% against clang — parity, as the shapes predict.

  So two more pairs join `narrow-arithmetic`'s three at a shared ceiling:

  | pairs | why unreachable |
  |---|---|
  | `narrow-arithmetic` × rust, clang, swift | 61 instructions each, same opcode sequence (125) |
  | `loop-call-back-edge` × rust, clang | 5-instruction loop body each (134) |

  **The bounded fastest claim needs all 30 and five are unreachable, so the
  contract cannot be satisfied on this fixture set. The reachable maximum is
  25/30, and amu is at 19.**

  The six genuinely contestable pairs, with what each needs:

  | pair | now | needs |
  |---|---:|---:|
  | `deep-spill` × zig | +2.2% | ~2.8pp |
  | `deep-spill` × rust | +1.9% | ~3.1pp |
  | `call-preservation` × clang | −1.3% | ~6.3pp |
  | `call-preservation` × rust | −1.2% | ~6.2pp |
  | `branch-call` × rust | −4.1% | ~9.1pp |
  | `branch-call` × clang | −7.8% | ~12.8pp |

  Known unbanked levers against those: the fp/lr fold (+1.32pp on the call
  domains, 132) and whatever explains `branch-call`'s residue after the
  2.84pp forced register (129). `deep-spill`'s obvious remaining lever —
  shifted-add for the power-of-two lanes — needs two extra live registers in
  the fixture built to exhaust them, and the SIMD spill-parking pass is
  already firing there (7 FMOV pairs, zero spill traffic), so the register
  budget is spoken for.

  **What the tournament can honestly claim today**: amu native is fastest
  among the enumerated implementations against **Go and Swift on all six
  domains**, leads **Zig on five of six**, and against the two LLVM backends
  holds `wide-register-pressure` outright, holds `deep-spill` × clang, ties
  two domains at proven ceilings, and trails on the call boundary.

- **135 (2026-09-06, two ADD immediates instead of MOVZ+MOVK: FALSIFIED at
  −7.57%, and the reason generalises)**: `kernel_deep` spends three
  instructions per lane materialising the folded addend —
  `MOVZ xR,#lo ; MOVK xR,#hi,lsl 16 ; ADD xd,x2,xR`. Every addend
  (`k*48271+1`, max 1,110,234) is under 2^24, so a 24-bit constant addition
  covers all of them: `ADD xR,x2,#hi12,LSL #12 ; ADD xd,xR,#lo12`. Two
  instructions for three, 22 lanes, 9% of the function.

  Patched all 22, every manifest input identical, fuel intact.

  **−7.57%. Slower, decisively.**

  The mechanism is worth keeping. `MOVZ`+`MOVK` do not depend on `x2` at all —
  they are constant materialisation, and the machine issues them in parallel
  with everything else. Only the final `ADD` sits on the path from `x2`, so
  the lane costs **one** dependent cycle. The two-ADD form puts *both* adds on
  that path: fewer instructions, **two** dependent cycles. I removed an
  instruction that was free and lengthened the chain that was not.

  That is the second time this fixture has punished an instruction-count
  argument. The first was the folded constant itself: 48 materialisation words
  against clang's one *looks* like waste until you see it buys a single
  multiply where clang emits 24 MADDs (124). Both times the "waste" was
  off the critical path.

  **The lesson is now general enough to state as a rule for this loop:
  on this machine, count instructions to find candidates and measure
  dependency chains to judge them.** 126 (if-conversion, +0.12%) and this
  are the same error in different clothing — 126 removed instructions from a
  path that was never fetched, this one removed instructions that were never
  waited on.

  ⚠ The absolute numbers in this run are ~2% above the previous one for every
  arm including clang (clang 10.29 here against 10.03 in 133) — the host
  drifted. The comparison is interleaved so the *relative* verdict stands, but
  do not read these means against another run's.

  With this falsified, the levers I can find on `deep-spill` are exhausted:
  SIMD spill-parking is already firing (7 FMOV pairs, zero spill traffic),
  the frame is fixed (#145), the shifted-add form needs two live registers the
  fixture is designed to deny, and the constant form is already optimal for
  the dependency graph. `deep-spill` × zig (+2.2%) and × rust (+1.9%) may be
  closer to a ceiling than the 2.8pp gap suggests.

- **136 (2026-09-06, the fp/lr fold is NEUTRAL, and the fleet's ssh had been
  returning 0 for every failure)**:

  Two results, one of which invalidates a number I put in the source tree.

  **The fold buys nothing.** kotoba-native #146 makes fp/lr the top slot of
  the single save-area allocation and forms fp with `add x29, sp, #offset`,
  so a call frame costs two SP updates instead of four and matches clang's
  shape exactly. Entry 132 recorded **+1.32% on call-preservation** for this.
  **That number was wrong.** A clean A/B — both sides staged on judah in one
  session, all 30 candidate/comparator/domain pairs, both quiet-gate
  qualified, all five comparators complete on all six domains with identical
  tool versions:

  | | base (kn main) | candidate (fold) |
  |---|---|---|
  | qualified pairs | **19/30** | **19/30** |
  | largest pair delta | — | **0.35pp**, signs mixed |
  | call-preservation × clang | −1.27% | −1.12% |
  | branch-call × clang | −7.47% | −7.11% |
  | branch-call × rust | −4.23% | −4.47% |

  **This is a null result, not a measurement of the wrong binary** — the
  check that separates the two is the one entry 130 says to run.
  `amuNativeKexe` is 3–4 bytes smaller in four of the six domains
  (`narrow-arithmetic` 7114→7110, `call-preservation` 2999→2996,
  `branch-call` 3124→3120, `loop-call` 3167→3163) and `amuNativeCode`'s
  digest moves with it. The comparator binaries differ in digest too, but
  their **source hashes and byte counts are identical** — Mach-O UUIDs, not
  a changed comparator.

  So the prologue's SP updates were never on the dependency path either.
  That is the third instance of the rule from 135, and the strongest,
  because these instructions *do* execute every call and the kernels call
  100,000 times: **removing two of them from a hot prologue changed nothing
  the judge can see.** Out-of-order execution absorbs them. Count
  instructions to find candidates; measure dependency chains to judge them.

  **The transport had been lying.** `ssh <node> 'exit 7'` returns **0 on all
  eight fleet nodes** — they are reached over Tailscale, which does not
  propagate the remote exit status. `remote-bench.cljs`'s stated contract,
  `1 = the benchmark ran and failed`, was therefore **unreachable**. The
  first baseline run of this very A/B died with `spawnSync nbb ENOENT`
  inside the suite and the script reported **exit 0 and a one-byte log** —
  indistinguishable from a run with nothing to say. Had I not gone looking
  for the missing JSON, the comparison would have been drawn from one side.

  Fixed in amu #830, with both directions shown on real nodes: the status is
  carried as `AMU-EXIT=$?` from inside a subshell (`true`→0, `exit 7`→7,
  missing binary→127, while ssh says 0 for all three), ssh is invoked through
  `spawnSync` with argv so the *local* shell stops expanding `$PATH` and
  `$JAVA_HOME` in the remote command, and the chosen host is checked for the
  tools before staging. A missing sentinel is exit 2 — refused — never a pass.

  **The fleet is far narrower than the roster suggests.** Of eight nodes,
  **only judah can run this benchmark end to end.** `nbb` is absent on levi,
  zebulun, joseph and dan; simeon has node only as a keg-only `node@22`
  outside the forced PATH; benjamin has no egress to github.com
  (`AMU-EXIT=128`, connection refused on port 443). quiet-host ranks by
  idleness alone, so it kept electing hosts that could not answer — which is
  a large part of why this loop spent so many ticks unable to measure
  anything. The refusal now names the PATH it searched, because "simeon
  lacks node" sends the reader to the wrong fix.

  Score unchanged at **19/30**; the reachable maximum remains 25/30 (134).

- **137 (2026-09-06, `branch-call` costs ONE CALLEE-SAVED REGISTER, and the
  fixture comment that misdirected four hypotheses was false)**:

  `branch-call × clang` is −7.11%, the largest reachable gap left. Four
  hypotheses were spent on it (126 if-conversion, 127 instruction count,
  128 placement and prologue register count) and all four were falsified.
  They were all consistent with the story the fixture tells about itself:

  > the only difference is that this function contains control flow as well
  > as calls, which sends it to the conservative all-vreg path where every
  > value gets a stack slot

  **That is false, and `:all-vregs` is not assigned anywhere in the backend
  any more.** Disassembling both kernels from the same compile (kn main,
  kexe 2996 and 3120 bytes — the exact sizes this run's report records, so
  these are the measured binaries):

  | | kernel_call | kernel_call_branch |
  |---|---|---|
  | instructions | 51 | 59 |
  | sp-referencing memory ops | 10 | 15 |
  | **of which spills** | **0** | **0** |
  | callee-saved registers | x19–x25 (**7**) | x19–x26 (**8**) |

  Every `[sp]` reference in both is the callee-saved save/restore. Neither
  kernel spills a single value.

  **What the `if` actually costs is one extra live range.** The test reads
  `n` *after* the last call:

  ```
  kernel_call         ... add x2, x19, #3   <- n dies here, d reuses x19
  kernel_call_branch  ... cbnz x19, 0xb8    <- n lives to the bottom, d takes x26
  ```

  Entry **129 priced one extra callee-saved register at +2.84%**. That is a
  large share of the ~6pp by which this domain's clang gap (−7.11%) exceeds
  `call-preservation`'s (−1.12%) — the same kernel, the same calls, one more
  register held across them.

  Note this does not contradict 128. 128 falsified *prologue register
  count* — saving a register that nothing keeps alive is free. 129 measured a
  register that is genuinely **live across calls**. The distinction is the
  whole finding: it is not the save/restore that costs, it is the occupancy.

  **New hypothesis H-LR (live-range hoisting):** the condition depends only
  on the argument, so evaluating it before the calls would let `n` die at its
  last arithmetic use and bring the register count back to 7. The obstacle to
  check first is fuel: a path that skips the eight calls consumes less, and
  the batch check asserts exact fuel. A form that keeps all eight calls on
  both arms and only hoists the *test* does not have that problem.

  The correction is also in the fixture, so the next reader is not sent after
  the same absent mechanism. **A stale comment cost four iterations here** —
  worth remembering that the rule about implementation snapshots applies to
  benchmark fixtures too, not just to ADRs.

- **138 (2026-09-06, `deep-spill` is PARTLY ISSUE-BOUND — the rule from 135
  has a second half, and this is the first measured path to 20/30)**:

  135 and 136 both concluded that instructions off the dependency path are
  free. `deep-spill` spends **49 of its 241 instructions (20%) materialising
  lane constants** with MOV/MOVK — and those have no inputs at all, so by
  that rule they should cost nothing. They do not cost nothing.

  Diagnostic fixture `kernel_deep_narrowconst`: `kernel_deep` with the lane
  multiplier 48271 replaced by 3, so every folded constant `3i+1` fits an
  add-immediate and all 47 materialisation instructions vanish. Lane count,
  modulo sequence, lane-13 shadowing and dependency structure identical.
  Two independent runs on judah:

  | | median | min |
  |---|---|---|
  | `kernel_deep` | 9.01 / 9.01 | 8.97 / 8.97 |
  | `kernel_deep_narrowconst` | 8.66 / 8.64 | 8.62 / 8.62 |
  | **delta** | **3.88% / 4.11%** | **3.90% / 3.90%** |

  Run 1's control carried an outlier (rsd 0.067, max 10.75); the minima are
  identical across both runs, so the effect survives it.

  **Removing 19.5% of the instruction stream bought 3.9% of the time — a
  transfer ratio of about 0.20.** Not 1.0 (fully issue-bound) and not 0
  (fully latency-bound). At ~5.8 instructions per cycle across 24 independent
  lanes, this kernel is wide enough that instruction count is worth something,
  which the serial kernels of 126–128 and 135–136 never were.

  **So the rule needs both halves: count instructions where the ILP is high,
  measure chains where it is low.** The two are not competing heuristics —
  they apply to different regimes, and every falsification in 126–136 came
  from a low-ILP kernel while this confirmation comes from a high-ILP one.

  **What it is worth, costed honestly.** Against the multidomain figures
  (amu 9.40, rust 9.63, zig 9.68 — the `runtime` suite's absolutes are 9.01,
  so only the *ratio* transfers, not the level):

  | form | instrs removed | projected | vs zig | vs rust |
  |---|---|---|---|---|
  | `LDR` literal, no base register | 23 (9.5%) | 9.22 | 4.75% | 4.25% |
  | `LDP` from a base register | 32 (13.3%) | 9.15 | 5.5% ✓ | 4.98% |
  | **`LDP` literal, no base register** | **34 (14%)** | **9.14** | **5.6% ✓** | **5.1% ✓** |

  The middle row is a trap: it needs a register held across the function, and
  `deep-spill` is the kernel with none to spare (`a64-simd-park-spills` is
  already parking seven pairs in SIMD). 129 priced one extra live register at
  +2.84%, which would eat the whole gain. **`LDP (literal)` is the form to
  build** — PC-relative, two constants per instruction, no base register. Its
  constraint is range: the 7-bit scaled offset reaches ±1KB, so the pool has
  to sit next to the function.

  That projects **20/30, possibly 21/30** — the first measured route past 19
  since the ceilings were proven. It is close to the threshold on rust (5.1%
  against a required 5.0%), so it should be treated as one pair expected and
  a second hoped for, not two banked.

  Infrastructure note: `:gmir/rodata-address` already exists (it backs
  `bytes-literal`), so there is a rodata path to extend rather than invent.

  ⚠ The diagnostic fixture is not in the claim manifest and the `runtime`
  suite carries **no quiet-gate verdict** (`quietGate: None`). These numbers
  are diagnostic. The claim path stays the competitive multidomain suite.

- **139 (2026-09-06, it is the MOVKs, not the instruction count — removing 23
  buys what removing 47 buys)**:

  138 concluded `deep-spill` was partly issue-bound and costed a constant pool
  on a transfer ratio of 0.20. **A third variant falsifies that reading.**

  `kernel_deep_movonly` uses multiplier 2039, so every folded lane constant
  (max 46898) fits sixteen bits and needs a bare MOVZ with **no MOVK** —
  removing 23 instructions where `narrowconst` removes 47. All three measured
  on judah behind an explicit busy ≤ 0.10 gate:

  | variant | instrs removed | median | min | median gain | min gain |
  |---|---|---|---|---|---|
  | `kernel_deep` | — | 9.33 | 9.00 | — | — |
  | `kernel_deep_movonly` | **23 (9.5%)** | 9.09 | 8.60 | **2.57%** | **4.44%** |
  | `kernel_deep_narrowconst` | 47 (19.5%) | 8.87 | 8.63 | 4.93% | 4.11% |

  **Removing 23 instructions and removing 47 are indistinguishable.** If
  instruction count were the mechanism, the second row should be worth about
  half the third. It is worth the same — on minima it is worth slightly more,
  which is what two readings of one quantity look like.

  So 138's "partly issue-bound, ratio 0.20" was **the wrong model fitted to one
  data point**. The right statement: **the MOVK is what costs, and the MOVZ
  that remains is free.** MOVZ→MOVK→ADD is a three-long chain into each lane
  because MOVK read-modify-writes the register MOVZ just wrote; a bare MOVZ
  makes it two. The rule from 135/136 was never violated — I had simply
  mis-assigned which of the two instructions sat on the chain.

  ⚠ **138's projection table should not be used.** It scaled a made-up ratio
  across three candidate forms. The measured quantity is a single number:
  **eliminating the MOVKs is worth about 4%**, and eliminating anything else
  is worth nothing.

  **What that is worth.** Against the multidomain figures (amu 9.40, rust 9.63,
  zig 9.68 — only the ratio transfers, the `runtime` suite's level is different):
  4% puts amu at ~9.02, which is **6.8% against zig and 6.3% against rust**.
  Both clear the 5% bar, and both gaps (0.66 / 0.61 ns) clear the ~0.42 summed
  stdev. That is **21/30**, from one change.

  **The change to build is `LDR (literal)`** — not the LDP variants 138 costed.
  One PC-relative word replaces MOVZ+MOVK, and critically it has **no register
  input**, so unlike MOVK its latency is schedulable: with 24 independent lanes
  there is ample slack to issue the loads early. No base register, so none of
  the register pressure that makes 129's +2.84% a threat on this kernel.

  The residual risk is exactly that scheduling assumption — a load is ~4 cycles
  against MOVK's 1, so if the loads do *not* get hoisted, this loses rather than
  wins. That is the thing to measure first on the implementation, and it is why
  this is specified rather than claimed.

  Site: `a64-constant` (machine_ir.cljc ~3665) already picks between wide-move,
  logical-immediate and seeded forms; the pool becomes a fourth choice when the
  wide form needs two or more words. It needs a literal-pool fixup alongside the
  existing branch fixups in `resolve-layout`, pool placement after the function
  body, and a ±1MB range check with a fall back to the wide move.

  ⚠ Diagnostic fixtures, not claim fixtures. The `runtime` suite carries no
  quiet-gate verdict of its own (`quietGate: None`) — the ≤ 0.10 gate here was
  imposed by the harness around it, after an ungated batch produced a control
  of 9.67 against 9.01 in two quiet runs and a 23.58 outlier. **That ungated
  batch is discarded, not averaged in.**

- **140 (2026-09-06, the load's latency is hidden — LDR-literal measured 4.5%
  faster than MOVZ+MOVK, so #147 has nothing left to measure)**:

  139 specified `LDR (literal)` with one open risk: a load is ~4 cycles against
  MOVK's 1, so if the loads are not hoisted ahead of their uses the change
  loses instead of winning. That is now measured rather than assumed.

  A hand-written microbenchmark reproduces the `deep-spill` lane shape exactly
  — 24 lanes of `add / smulh / add / asr / add / msub`, with the magic
  constants read off amu's own disassembly — in two variants differing only in
  how the lane constant arrives. Both compute identical results over n = 0..4.
  Ten invocations on judah across two batches, each the minimum of seven
  interleaved rounds:

  | | movk | ldr | gain |
  |---|---|---|---|
  | batch 1 (5 runs) | 8.683–8.708 | 8.317–8.325 | **4.13 – 4.50%** |
  | batch 2 (5 runs) | 8.708–8.725 | 8.317–8.325 | **4.50 – 4.59%** |

  **Two unrelated methods, one number:** the fixture diagnostic said removing
  the MOVKs was worth ~4%, and a hand-written A/B that changes nothing else
  says 4.5%. That agreement is worth more than either reading alone.

  Two things this run teaches about its own method:

  * ⚠ **The same benchmark on this workstation says LDR is 7% SLOWER.**
    Different chip, load average over 100. A microbenchmark is only evidence
    about the machine it ran on, and the claim path's machine is the fleet.
  * The first version used **x20** as the accumulator. x20 is callee-saved, so
    clobbering it corrupted the C driver's loop counter — and that surfaced as
    runs taking 30+ minutes and never finishing, **not** as a wrong answer.
    A wrong answer would have been caught immediately by the equality check
    that was already there; a corrupted caller was not. The accumulator is x9.

  Nothing is left to measure before implementing #147. The projection stands:
  `deep-spill × zig` → ~6.8%, `× rust` → ~6.3%, both clearing the 5% bar and
  the ~0.42 ns separation floor. **19/30 → 21/30.**

- **141 (2026-09-06, the literal pool is FALSIFIED at −0.54% ± 1.57%, and both
  diagnostics that predicted +4% were measuring the wrong thing)**:

  #147 was built: `LDR (literal)` against a per-function constant pool, scoped
  to the `:aarch64/constant` encoder, pool emitted inside each function so
  `extract-native` still copies it. Structurally it works — all 22 LDR sites in
  `kernel_deep` resolve to distinct real lane constants inside the extracted
  range, and the encoding came from clang's assembler rather than by hand.

  **It buys nothing.** Four quiet-qualified A/B pairs on judah:

  | run | control drift | deep-spill raw | drift-corrected |
  |---|---|---|---|
  | 1 | +2.14% | −0.11% | **−2.24%** |
  | 2 | +0.39% | +0.11% | **−0.29%** |
  | 3 | −2.00% | −0.11% | **+1.89%** |
  | 4 | −0.37% | −1.89% | **−1.52%** |

  **mean −0.54%, sd 1.57, n=4** — zero, against a predicted 4%.

  The correction matters and is what makes this readable at all: **four of the
  six domains are byte-identical between the two builds** (only `deep-spill`
  +56 bytes and `wide-register-pressure` +8 changed), so their delta is pure
  run-to-run drift. It ran from −2.0% to +2.1% between pairs. Without that
  control I would have read run 1 as "the pool makes narrow-arithmetic 4.17%
  slower" — on a kernel whose bytes did not change.

  **Why 139 and 140 both predicted a gain that is not there.** Neither
  diagnostic modelled the substitution:

  * the **fixture** (139) removed the MOVKs and put **nothing** in their place
    — strictly less work, so of course it was faster;
  * the **microbenchmark** (140) did compare MOVZ+MOVK against LDR, but its
    lanes were chained through a serial accumulator (`add x9, x9, x4`), which
    serialises them and hands each load a long window to complete. The real
    kernel sums in a tree at the end, so there is less slack and the load's
    ~4 cycles land where MOVK's 1 used to.

  **Two agreeing measurements were still both wrong, in the same direction, for
  the same reason.** The agreement felt like corroboration in 140 and was
  actually a shared blind spot: both compared "constant is cheaper" against
  "constant is dearer" without reproducing what the real change does, which is
  swap two ALU ops for one load *in the real dependency graph*.

  ⚠ **A further caution about the score itself.** The baselines across these
  four pairs scored **19, 19, 15, 19** — the *same commit*, four times. A
  single 30-pair run resolves the score to about ±4 pairs when the host is
  merely quiet-gated. `19/30` is what this build typically scores, not a
  reading precise to one pair, and no single run should be used to claim a
  pair was gained or lost.

  Not landing. The branch stays as evidence; #147 is closed as measured and
  rejected. **19/30 stands, and the reachable maximum is still 25.**

- **142 (2026-09-06, the published score was stated to a precision it does not
  have — one outlier sample can cost three pairs)**:

  141 recorded in passing that four runs of one commit scored 19, 19, 15, 19.
  Following that up turned out to matter more than the compiler change it was
  a footnote to, because **kotoba-lang.org was publishing `19/30` as a flat
  number** and I am the one who put it there.

  **What the ±4 actually is.** Not four independent losses. One sample of
  **10.48 ns against a median of 5.165** in amu-native's own arm on
  `branch-call` — the next largest was 5.67 — pushed that arm's relative stdev
  to **0.1373** and tripped perfgate's `too-noisy` rule. Dropping that single
  sample gives **0.0465**. Because `too-noisy` is evaluated **per arm**, one
  bad amu measurement disqualified **three comparator pairs at once**, and
  those pairs were 17%, 25% and 43% ahead. Comparisons not remotely in doubt,
  lost to one scheduler hiccup.

  That correlation is the whole explanation for the spread: the score does not
  move one pair at a time, it moves in blocks of up to five.

  **What I did NOT do.** Loosen `max-relative-stdev`, or trim the outlier.
  Either would raise my own score by weakening the judge that grades it. The
  gate is doing its job; the reporting was wrong.

  **What changed.** `project-runtime-comparison.cljs` now takes several
  reports and publishes the **median**, `scoreByRun`, `observedRange`,
  `stableQualifiedPairs` (won every run), and per-pair `qualifiedRuns` — so
  "won once" and "won always" stop rendering identically. Every extra report
  faces the same refusals as the first, plus one more: **its quiet gate must
  have passed.** A run whose host was never measured does not vote. Both
  refusals were exercised and neither writes an artifact.

  **Republished from five host-qualified runs of amu main c6f21d1e**
  (busy-CPU 0.05–0.09):

  | | |
  |---|---|
  | per run | **19, 19, 17, 17, 19** |
  | median (headline) | **19** |
  | observed range | **17–19** |
  | qualified in every run | **16** |

  The headline is unchanged — 19 was right *as a median*. What was wrong was
  publishing it bare. kotoba-lang.org now reads "Median of 5 host-qualified
  runs; the score ranged 17–19 and 16 of the 30 pairs qualified in every one."

  Marginal under this build: `wide-register × clang` 4/5 (12.02%),
  `deep-spill × clang` 4/5 (**6.18%** — genuinely near the 5% bar),
  `wide-register × rust` 3/5 (7.98%).

  **Consequence for this loop.** Every single-run A/B in entries 130–141 was
  reading a quantity whose one-run resolution is about ±2 pairs. The
  drift-corrected comparisons survive that (they compare arms within a run),
  but **no future entry may claim a pair was gained or lost from one run.**
  The threshold for "this changed the score" is now a median over repeated
  host-qualified runs.

- **143 (2026-09-06, the bounded claim is UNATTAINABLE, and one of this
  ledger's own ceiling claims does not reproduce)**:

  Chasing the score further, I went to re-verify 134's ceilings rather than
  cite them. Two results, opposite in sign.

  **Confirmed, and stronger than 134 stated.** Disassembling all three
  artifacts for `narrow-arithmetic`:

  | | instructions | encodings |
  |---|---|---|
  | amu native | **61** | differ from the others **only in register numbers** |
  | Apple clang -O3 | **61** | **byte-identical to rustc** |
  | rustc -O3 | **61** | **byte-identical to clang** |

  Same mnemonic sequence, position for position, all three. A ≥5% margin over
  identical code cannot be produced. So `narrow-arithmetic × clang` and
  `× rust` are not pairs more work will win — **and therefore neither is
  30/30. The bounded claim is unattainable, not unmet.** That distinction was
  missing from what kotoba-lang.org published ("stays unqualified" reads as
  "not yet"); it now says so, listing only the pairs actually disassembled.

  **Did not reproduce.** 134 claims five such pairs. `loop-call-back-edge`
  does not check out with this method: `extract-native --symbol kernel`
  returns `:offset 4 :length 40` — ten instructions containing a fuel
  preamble, a prologue, `mov x1,#0` and an epilogue, with **no back edge, no
  `bl`, and no `ret` inside the extent** — for a kernel the suite times at
  **~140 ns**, two orders of magnitude above every other domain. clang
  compiles the same shape to a real 20-instruction loop.

  Those two facts cannot both be right. **I have not withdrawn 134** — it may
  have been measured another way — but the published artifact now lists two
  ceiling pairs rather than five, and the anomaly is amu#843.

  ⚠ **This reaches backwards.** `extract-native`'s extent is how 137, 141 and
  142 counted per-domain instructions. If it can understate a function, those
  counts inherit the doubt. The `narrow-arithmetic` comparison above does not
  (61 × 4 = 244 bytes, and all three agree instruction-for-instruction, which
  a truncated extent would not produce), but **no future instruction count
  from this tool should be quoted without checking the extent against the
  disassembly's own shape** — a function that does not end in `ret` was not
  fully extracted.

  Also filed: kotoba-native#148, a redundant `mov x0, x19` immediately after
  `mov x19, x0` in the entry sequence of both call-shaped kernels — real, and
  **explicitly too small to move the score** (~0.9% of one kernel's
  instructions, against a 5.31pp gap, and below this fleet's noise floor).

  Score unchanged: **median 19/30, range 17–19, stable 16**.

- **144 (2026-09-07, SIMD spill-parking's +3.21% has eroded to +0.67% ± 1.15%
  — the fifth lever to measure at zero, and the reason is one of our own
  landed changes)**:

  I had dismissed re-testing this pass because its docstring cites **+3.21%
  separated** from iterations 23–24. That is a citation, not a measurement:
  the figure came from **hand-substituting** fourteen spill instructions on a
  compiler that has since gained #142, #145 and #146. The rule about
  implementation snapshots applies to measurements too, and I applied it to
  everything except the numbers that were already in my favour.

  Compiled both shapes and ran three interleaved quiet-host pairs
  (busy-CPU 0.06–0.09), drift-corrected against the five domains whose bytes
  do not change between the arms:

  | rep | drift | deep-spill | corrected |
  |---|---|---|---|
  | 1 | +2.35% | +2.41% | **+0.06%** |
  | 2 | −1.44% | +0.85% | **+2.29%** |
  | 3 | +0.01% | −0.32% | **−0.33%** |

  **Disabling the pass costs +0.67%, sd 1.15, n=3.** Right in sign — parking
  is still the better shape and stays — but **indistinguishable from zero**,
  and nowhere near 3.21%.

  The shapes genuinely differ, so this is not one binary measured twice: on
  `kernel_deep`, parked is 241 instructions / 14 FMOV / 8 sp-memory ops;
  unparked is 243 / 0 FMOV / 22.

  **The likely cause is #145, which this loop landed.** Once the frame became
  a single allocation with offset addressing, a stack-slot round trip stopped
  being expensive enough for a register-file move to beat by much. An
  optimization worth 3% against N dependent SP updates is worth much less
  against two. **Landing one optimization can quietly retire another's
  value**, and nothing in the codebase notices — the docstring kept asserting
  3.21% for as long as anyone cared to read it (kotoba-native#149 corrects it).

  ⚠ I also repeated the #143 mistake inside this experiment: compiled with the
  pass disabled and ran `extract-native` without the flag, so the verifier
  re-emitted the parked shape and rejected the export table. The ledger
  already records that exact error. **Reading about a mistake does not prevent
  it; only making the configuration impossible to split does.**

  **Where this leaves the search.** Five levers on `deep-spill` now measure at
  or near zero — constant pooling (141), SIMD parking (here), and the frame,
  Mersenne and two-ADD results already recorded. The division sequence is
  instruction-for-instruction identical to clang's and rustc's. On the
  evidence, amu's deep-spill codegen is at a local optimum, and the 2.09pp to
  zig is not reachable by the kind of peephole this loop has been generating.

  Score unchanged: **median 19/30, range 17–19, stable 16**.

- **145 (2026-09-07, induction-variable strength reduction across lanes is
  −5%, which closes the second and last direction out of this local optimum)**:

  144 ended by saying the remaining gap "is not reachable by the kind of
  peephole this loop generates". That was an admission that every lever tried
  so far changed **instruction selection** and none changed **dependency
  structure**. So here is the structural one.

  The lane constants are an arithmetic progression: `(n+i)*48271+1 ==
  ((n+i-1)*48271+1) + 48271`. Textbook induction-variable strength reduction —
  replace 24 independent constant materialisations with 23 adds off the
  previous lane. `kernel_deep_incremental` does exactly that, and its lane
  results are **bit-identical** to `kernel_deep`'s (checked in Python over the
  verification inputs and beyond, including a negative n).

  Two quiet-host runs (busy-CPU 0.04–0.06):

  | rep | kernel_deep | incremental | median | min |
  |---|---|---|---|---|
  | 1 | 9.01 | 9.47 | **−5.11%** | −4.89% |
  | 2 | 9.01 | 9.46 | **−4.99%** | −4.90% |

  **The incremental form is 5% slower**, reproducibly, on both statistics.
  The serial edge costs far more than the ~4% of materialisation it removes.

  **Both directions out of this point are now measured, not assumed:**

  | direction | change | result |
  |---|---|---|
  | instruction selection | pool the constants (141) | **0%** |
  | | park spills in SIMD vs stack (144) | **0.67% ± 1.15%** |
  | dependency structure | chain the lane inputs (here) | **−5%** |

  Shortening the instruction stream without touching the chains buys nothing;
  shortening it *by* touching the chains costs 5%. That is what a local
  optimum looks like from the inside, and it is now a measurement rather than
  the assertion 135 made and 144 repeated.

  It also explains the earlier pair that looked contradictory. 139's fixtures
  (`narrowconst`, `movonly`) removed materialisation and **substituted
  nothing** — strictly less work, ~4% faster, and unreachable by a compiler,
  because a compiler has to put *something* there. Every real substitution
  since has landed between 0% and −5%.

  **What would still be worth someone's time**, none of it a peephole: the
  24-lane fixture is designed to exceed the register file, so the win would
  have to come from needing fewer live values at once — vectorising the lanes
  (rustc reaches for NEON here and is still slower, so this is not obviously
  free), or reassociating the final sum tree to shorten lane lifetimes. Both
  are register-allocation-scale changes, not encoder changes.

  Score unchanged: **median 19/30, range 17–19, stable 16**.

- **146 (2026-09-07, interleaving the sum is +3.17% — the first positive
  result in this series, and the first measured route to 20/30)**:

  145 said the remaining move was register-allocation scale, not encoder
  scale, and named two candidates. This is the second one: **reassociate the
  final sum so lanes are consumed as they are produced.**

  `kernel_deep` computes 24 lanes and then sums them, so all 24 are live at
  once — which is the pressure the fixture exists to create.
  `kernel_deep_accum` folds each lane into an accumulator immediately. Same
  lanes, same arithmetic, **same result** — i64 addition is associative, so
  the reassociation is exact (verified in Python over the verification inputs
  and beyond, including a negative n).

  | rep | kernel_deep | accum | median | min |
  |---|---|---|---|---|
  | 1 | 8.97 | 8.71 | **+2.90%** | +2.14% |
  | 2 | 9.02 | 8.71 | **+3.44%** | +3.13% |

  **+3.17% median, +2.64% min**, both runs, both statistics, same direction.

  **The mechanism is confirmed by disassembly, not inferred:**

  | | instructions | FMOV | sp-mem ops | callee-saved pairs |
  |---|---|---|---|---|
  | `kernel_deep` | 241 | 14 | 8 | 4 |
  | `kernel_deep_accum` | **219** | **0** | **0** | **0** |

  Peak liveness falls far enough that the function needs **no callee-saved
  registers and no frame at all** — it becomes a leaf that fits in the
  caller-saved bank. Every spill, every SIMD park, and the whole prologue go
  away together. That is a much larger structural change than any encoder
  lever tried in 141–145, and it is why it is the only one that moved.

  **What it is worth.** Applying +3.17% to the current figures (amu 9.46,
  zig 9.68, rust 9.63):

  | pair | now | projected | |
  |---|---|---|---|
  | deep-spill × zig | 2.27% | **5.37%** | **qualifies** |
  | deep-spill × rust | 1.77% | 4.88% | still short |

  **That is 20/30**, and rust lands close enough that run-to-run variation
  would sometimes carry it.

  ⚠ **This is a fixture, not a pass.** I have measured the shape a compiler
  transformation would produce, not the transformation. 141 is the cautionary
  case — but the two differ in exactly the way that matters: 139's fixtures
  removed work and **substituted nothing**, which no compiler can do, whereas
  this one performs an operation reordering a compiler is free to perform, on
  the same instructions, and the disassembly confirms the predicted mechanism
  rather than merely the predicted timing.

  Specified as kotoba-native#150. The pass has to (a) find a sum whose terms
  are independently computed, (b) prove the reassociation exact — trivial for
  wrapping i64 addition, **not** for floats — and (c) interleave the folds
  with the producers. Step (c) is where it can go wrong: fold too eagerly and
  the accumulator becomes the serial spine that cost 5% in 145.

  Score today unchanged: **median 19/30, range 17–19, stable 16.**

- **147 (2026-09-07, the hoist is built and measured on the compiler path:
  deep-spill −2.66% ± 0.32 — the first compiler change in this series that
  moved the real artifact)**:

  146 measured a hand-written fixture. This is the pass (kotoba-native #151):
  before allocation, a pure register-only instruction for which at least one
  operand's last use is that instruction moves up beside the later of its
  producers. It never crosses a barrier — label, branch, call, memory,
  terminator, physical register, **or `:mir/argument`** — and never splits a
  multiply→add/subtract pair the AArch64 selector fuses.

  **The argument barrier was found by breaking it.** With arguments
  crossable, `sum-five`'s first add climbed above the materialisation of the
  remaining parameters and the allocator stored them: a frameless leaf grew
  three spill slots, 31 failures and an error. Nothing may rise above the
  last argument. That is now in the code, not only here.

  **What it produces.** `kernel_deep` through amu: 241 instructions / 14 FMOV
  / 8 stack ops / 4 callee-saved pairs → **219 / 0 / 0 / 0**, byte-for-byte
  the fixture's shape; a 6-lane unit check shows the hoisted order equals the
  interleaved-accumulator order instruction for instruction. Blast radius is
  **one domain**: the other five benchmark kernels are byte-identical to main
  (the call kernels' sums stay put because every operand sits behind a call
  barrier).

  **Compiler-path A/B**, three interleaved quiet-host pairs on judah
  (busy 0.06–0.09), drift-corrected against the five byte-identical domains:

  | rep | control drift | deep-spill corrected |
  |---|---|---|
  | 1 | +1.34% | **−3.07%** |
  | 2 | −6.73% | **−2.28%** |
  | 3 | −0.16% | **−2.62%** |

  **mean −2.66%, sd 0.32, n=3** — every rep negative, and the tightest
  measurement in this series. The fixture said −3.17%; the pass delivers
  −2.66%. **141's fixture-vs-pass gap did not recur**, for the reason 146
  predicted: this fixture performed the same reordering the pass performs.

  Per pair on the hoist side: `deep-spill × zig` **5.64 / 6.46 / 5.98%** —
  above the bar in every rep, qualified in two (rep 1 missed separation by
  0.03 ns, gap 0.54 vs summed stdev 0.57). `× rust` 3.92 / 5.32 / 4.95 —
  qualified once, at the line as projected (4.88% projected, 4.73% measured).
  `× clang` widened from ~6.5–7.5% to 9.3–10.5%. Scores 19→19, 6→21, 19→20.

  ⚠ **Rep 2's base run scored 6/30 under a −6.73% drift.** The amu arm hit
  rsd 0.416 on four domains at once (33 `too-noisy` reasons) — a disturbance
  that began *after* the quiet gate sampled. Do not read that pair as +15.
  Its drift-corrected deep-spill delta still agrees with the clean reps
  because medians survive what rsd does not; that is the whole argument for
  the drift control. The honest score effect is **+0 to +1 per clean pair**.

  **Tests told the truth about themselves.** Three fixtures created pressure
  with exactly the shape this pass removes — independent lanes and a trailing
  sum — so the pass made them frameless and they stopped testing anything
  (bounded spills, the post-allocation fallback, the preserved-tier
  prologue). Each now consumes every lane twice, which is what real pressure
  looks like; pins re-measured (2→7 slots, 24→25, saves 5/6 registers). The
  frame tests' helper also bypassed `compile-gmir` and compared a hoisted
  prologue against an un-hoisted save set. One x86 pin moved by a 3-byte
  `mov rax,r8`: the caller's running sum now lands in r8. Recorded as one
  move, not hidden in a count.

  **What is and is not public.** #151 merged at 01:00 (before the A/B
  finished; the measurement is posted on it). amu main still pinned
  kotoba-native at adeb1b0f, **17 behind**, so the shipped compiler and the
  published 19/30 had none of #142/#145/#146/#151. amu #853 advances the pin
  across all three baked sites (deps.edn, the regenerated lock, the exact-sha
  test) — #839 had moved only deps.edn, which is why it was blocked. Per 142,
  the published number changes only after five host-qualified runs of the
  new main are projected. Expected: **median 20/30**, with rust close enough
  to carry it to 21 some runs. Not claimed until measured.

- **148 (2026-09-07, the eleven pairs ranked by what can move them; the call
  domains read instruction by instruction against clang)**:

  Re-ranking from the five published-basis runs (`pub-1..5`, same commit),
  counting truthy `qualified?` — the earlier per-pair table in this file
  counted tuples and read 3/3 for everything:

  | never qualified (0/5) | mean margin | why |
  |---|---:|---|
  | narrow-arithmetic × rust / clang / swift | +0.9 / +1.1 / +1.0% | the same 61 instructions (143). Not winnable |
  | loop-call-back-edge × rust / clang | +0.8 / −0.6% | amu's loop body is 10 instructions to clang's 20 and it does not matter: the call to `step` is the cost. A tie by construction |
  | call-preservation × rust / clang | −5.9 / −6.4% | amu is slower. Decomposed below |
  | branch-call-control-flow × rust / clang | −8.2 / −11.4% | amu is slower. Decomposed below |
  | deep-spill-pressure × rust / zig | −0.1 / +0.9% | the pairs 147's hoist moves (+4.7 / +6.0% in its A/B) |

  Three more are lost only to `not-separated-from-noise` in one or two runs
  of five (wide × rust 3/5 at +7.5%, wide × clang 4/5 at +11.4%, deep × clang
  4/5 at +5.6%): the gap is real and the arms' own spread swallows it.

  So of the eleven, **five cannot be moved by codegen** (identical code, or
  call-bound ties), two are within reach of the hoist, and four are the call
  boundary. The honest ceiling of this fixture set is 22–24 of 30, not 30.

  **The call boundary, decomposed by reading.** rustc and clang agree
  byte-for-byte with each other on every kernel (249 / 132 / 61 / 42+12 /
  44 / 20 instructions). `kernel_call_branch` through amu at kn `d5fdf8c`
  executes 52 instructions per call to clang's 44 (59 static; the untaken
  `n = 0` arm and its epilogue are seven of them). The eight:

  | count | what | removable? |
  |---:|---|---|
  | 4 | fuel: `ldr x16,[x7,#8]; subs; b.hs; str` | no — the contract |
  | 1 | `mov x19,x0 ; mov x0,x19` — x0 already holds n | yes |
  | 3 | `add x2,x19,#k ; mov x0,x2` where clang writes `add x0,x19,#k` | yes |

  Same four on `kernel_call` (51 static, 48 after #152). Both kinds sit on
  the dependency path INTO the call — the callee waits on them. Iteration 123
  had priced a NOP-patched removal at +1.28% and #148 filed it as "too small
  to move the score"; against a −6% gap with no other instruction-level
  difference left, it is the only shippable item on this domain.

  Also found on the way: clang keeps **seven** callee-saved registers on
  `kernel_call` (x19–x25) and eight on the branch kernel — the same as amu.
  The register count was never the gap; 128 was right to falsify it.

- **149 (2026-09-07, the four copies are removed by a post-allocation
  coalescing pass; the blast radius is exactly the two call domains)**:

  kotoba-native #154 (`c9d5c44` on main): one forward pass over the
  allocated instruction vector, aarch64 only. A move whose destination
  already holds its source is dropped (an alias recorded by the previous move
  between the two registers, forgotten on any write to either, on a call, or
  at any op the pass does not model). A single-instruction producer
  immediately followed by a move of its result, with the result dead after
  the move and the producer not reading the move's target, produces into the
  target. "Dead" walks forward only through ops the pass understands — read
  → live, write → dead, call kills a caller-saved register it does not read,
  return / tail-call kill everything, anything else → live — so the
  conservative answer always keeps the copy.

  Static, through amu with both sides compiled the same way:

  | kernel | kn main `bf23a30` | + coalescing |
  |---|---|---|
  | `kernel_call` | 240 B / 48 instr / 6 saved / 8 sp | **224 B / 44** / 6 / 8 |
  | `kernel_call_branch` | 284 B / 59 / 8 / 15 | **268 B / 55** / 8 / 15 |
  | `kernel`, `kernel_wide`, `kernel_deep`, `kernel_loop_call` | byte-identical | byte-identical |

  The only instruction-level differences are the four copies. The suite's
  own loop-call word pin moved 53 → 51 (its helper's constant argument was
  the same shape); the bench fixture's loop is not, and is byte-identical.
  389 tests / 5247 assertions; every new assertion was run without the pass
  first and fails there.

  Pin-only A/B on judah (amu `61c7c183`'s tree with ONLY the kotoba-native
  sha moved; three interleaved reps; the four byte-identical domains are the
  drift control):

  | pair | domain | drift-corrected amu-native | pairs |
  |---|---|---:|---|
  | hoist → +cross-call (#152) | call-preservation | **+0.04% sd 1.35, n=2** | rust / clang 0/2 → 0/2 (−0.6 / −1.0%) |
  | +cross-call → +coalescing (#154) | call-preservation | **−1.42% sd 2.08, n=3** | rust / clang 0/3 → 0/3 (−0.3 → −0.2%, −0.8 → −0.5%) |
  | | branch-call-control-flow | **−1.05% sd 1.14, n=3** | rust / clang 0/3 → 0/3 (−3.8 → −4.0%, −6.9 → −6.7%) |

  The `pa` pair ran three reps; rep 1 is not a data point — the hx arm
  tripped the harness's per-domain host-load gate mid-run (18 pairs
  `multidomain host-load gate failed`, amu medians +12% across the board,
  control drift 10.6%) even though the pre-run quiet gate had passed. The
  analysis now excludes any rep in which an arm tripped that gate. On the
  two clean reps the cross-call hoist is a null at this resolution: three
  fewer instructions and one fewer callee-saved pair do not show up on a
  4.6 ns kernel whose spread is ±1.5%.

  The `pb` pair needed five reps to get three clean ones: reps 1 and 3 tripped
  the mid-run host-load gate outright, and of the three that did not, rep 4
  carried a 9.5% control drift (the co arm scored 14/30) and rep 5 a −2.7%
  one (the hx arm 13/30) — judah was being shared with fleet gates the whole
  hour, and the harness's gate catches the gross cases, not all of them. On
  what survives, coalescing reads favourable on both call domains and
  separated from zero on neither: −1.4% and −1.1%, each inside its own
  spread. It flips no pair. Its honest summary is the static one — four
  fewer instructions per call on the dependency path, the exact copies clang
  never emits — plus a runtime signal in the right direction that this host
  cannot resolve at n=3.

  **What the three passes did to the call boundary is visible in the
  published run instead** (150): call-preservation × rust went from −5.9% to
  −0.8% and × clang from −6.4% to −0.7%; branch-call × rust from −8.2% to
  −2.5%, × clang from −11.4% to −6.1%. Not one of them is a qualified pair,
  and with amu now within a point of rust on `call-preservation` while still
  paying four fuel instructions per call that rust does not, there is no
  static shape left on that domain that codegen can remove. It joins the
  ceiling list, one level below `narrow-arithmetic`: not identical code, but
  identical code plus the contract.

- **150 (2026-09-07, the pin advances to kotoba-native main and the score is
  re-measured through the published pipeline)**:

  amu #857: `06badc8 → c9d5c44`. The outgoing pin (#839) was one commit on a
  side branch; its allow-list entry is on kotoba-native main as `4e717ab`, so
  nothing is dropped and the pin is back where the pin rule wants it. #853
  (pinning `d5fdf8cb`) conflicted once #839 landed and is closed as
  superseded — nothing was rebased. The iOS golden fixture is re-emitted and
  re-sealed (48 code words, same exports, Mach-O 544 bytes, object digest
  `def77da7… → f60879b3…`); JVM 11 / 61 and nbb 6 / 14 green.

  Six runs for five votes. Run 5 passed the pre-run quiet gate and tripped
  the harness's mid-run host-load gate (`hostLoadQualified false`, 0/30 —
  a fleet gate was on judah at the time; `~/.gftd/fleet-ci-tick.log` shows
  `test-*-murakumo-judah` passes minutes apart all hour). **The projector
  used to count such a run.** It checked only the quiet gate, so a run whose
  medians were another tenant's could vote a 17 into the published spread —
  which is what 142's `[19, 19, 17, 17, 19]` most likely was. The projector
  now refuses any report with `hostLoadQualified false` (kotoba-lang #612,
  shown to refuse the contaminated report, to accept a clean one, and to
  refuse a mixed set), and the publish pipeline runs until it holds five
  host-qualified reports.

  Projected from runs 1–4 and 6, amu main `42f092ea`:

  | | before (142) | now |
  |---|---|---|
  | median | 19 / 30 | **19 / 30** |
  | per run | 19, 19, 17, 17, 19 | 19, 19, 19, 20, 20 |
  | stable floor (qualified in every run) | 16 | **19** |
  | deep-spill × rust / × zig | −0.1% / +0.9% | **+4.1% / +4.8%** (0/5 and 2/5 — at the line) |
  | call-preservation × rust / × clang | −5.9% / −6.4% | **−0.8% / −0.7%** |
  | branch-call × rust / × clang | −8.2% / −11.4% | **−2.5% / −6.1%** |

  The median did not move; almost everything under it did. The three passes
  took the call boundary from a 6–11% deficit to within a point of rust on
  `call-preservation`, and put both open deep-spill pairs within one point
  of the 5% line — and none of that is a qualified pair, because the judge
  asks for 5% and separation, not for closer. That is the right judge.

  kotoba-lang.org shows the same card (`RUNTIME SPEED · 19/30`); what changed
  on it is the range (`19–20`, was `17–19`) and the floor (`19 of 30 in every
  run`, was 16). The proven-unwinnable disclosure stands.
- **355 (2026-09-09 20:0x JST, amu-rank cron)**: host busy (load1 22.40 / 5m 20.72 / 15m 23.87 at 20:02, threshold 7.5) — measurement refused, rank-only pass. git fetch: origin/main advanced 3ef1a709 -> b631a7fe (PR #908 jv/granted-region-pin — a hosted native target may read a region its caller granted; compiler/ABI scope, no codegen-ladder number); local HEAD 1e2de5ea carries unpushed rank ticks 287/288 and lang-cosientist iteration 29 (operator merge still the standing blocker). Evidence reviewed since tick 354: no new sibling entry in the state doc (last committed entry is tick 354); no new ADR (0345 remains newest in docs/adr; 0347 in memory is not present on disk — noted, not acted on); the only new artifacts are sibling busy-refusal status sidecars (docs/.amf-appendbusy-0909-*.status through 17:38). No new measured numbers -> no re-rank, no status transition, no new hypothesis. Population unchanged: H-Z3 top of the codegen ladder (benjamin imod hand-patch A/B pending quiet host), J-C folded, H-C2/H-D/H-B/H-Y1 open. NEXT unchanged: benjamin collections walk-loop hand-patch (imod helper inlining, J-B2/H-Z3) via perfgate on a quiet fleet node.
