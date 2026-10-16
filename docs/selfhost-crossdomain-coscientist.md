# Amu selfhost cross-domain performance research

Status: active research. No performance claim has been made.

## Why the earlier Embench-derived comparison can beat C

The corrected M104 record reports Kotoba/C = 0.8213 on one Apple M4 cycle;
a separate Apple M4 cycle with Apple clang 21 reports 0.7877703356. These are
translated-port comparisons, not official Embench scores. “Selfhost” identifies
the compiler provenance (G1=G2=G3), not the reason for the runtime speedup.

The main documented mechanism is a set of same-algorithm, shape-admitted
handwritten AArch64 kernels for hot functions. Their speedups are workload
specific and do not follow from the language or selfhosting alone. M104 disables
SHA crypto instructions on the Kotoba side and uses scalar SHA-256; its C arm
uses the pinned upstream C with the round's clang `-O2` build. The older M93
0.7999 result is not comparable: its audit found algorithm substitutions and
Kotoba-only ARMv8 SHA-256 instructions. See
`bench/embench/reproduce-20261015/README.md` and `audit/` for the records and
policy. This distinction motivates testing transferable mechanisms on new
domains instead of extrapolating the Embench result.

The 0.7877703356 follow-up is a geometric mean, not a win on every workload.
Its per-workload `Kotoba / C` ratios are below 1 for 12 of 19 workloads; C is
faster on the other seven, including xgboost (1.515) and picojpeg (1.446).
The largest Kotoba wins include depthconv (0.257), matmult-int (0.310), and
md5sum (0.502). These spreads explain why the aggregate can favor Kotoba while
the result remains workload-specific. The exact ratios are in
`bench/embench/reproduce-20261015/round-sa-m104-20261015/records/m4-macmini-attempt-20261016-r1/report.json`.

A static profile found 51,200 xgboost tree walks with a mean dynamic depth of
3.58; 52.6% finish before depth five. The measured M104 image contains the
four-walk, five-level `tw` sequence, and the model data satisfy its depth,
feature-index, and tree-size predicates for all 12,800 groups. The profile
estimates 72,718 extra steps (363,590 table/input loads) versus dynamic
traversal if every group enters that sequence. This is a concrete candidate
for the C gap, but its runtime guard outcomes and timing contribution are not
recorded; the estimate is not speed evidence. Reproduction, disassembly
instructions, and scope are in
`docs/evidence/embench-xgboost-depth-20261016/`.

The refreshed group-depth profile narrows that hypothesis: an ideal group stop
would save 39,288 of 256,000 fixed steps (15.35%), but needs 45,095
all-four-leaves decisions and 70.96% of groups still reach level five. Its
estimated 196,440 saved table/input loads omit the added checks and branch
cost, so this remains a lower-ranked experiment until generated code and paired
timing show a net gain.

The goal is to improve Amu's selfhosted native compiler across multiple
workloads. Each optimization is treated as a hypothesis: generate candidate
mechanisms, reflect against existing code and evidence, rank by reach and
falsifiability, then evolve the compiler only after exactness and host-qualified
performance checks.

## Generate

Candidate mechanisms from the existing runtime-comparison suite and compiler
backend:

1. Lower positive, non-power-of-two constant division in T2 fast loops to an
   exact reciprocal multiply. This can affect arithmetic loops in many domains.
2. Hoist reciprocal constants out of fast loops. Hoisting the divisor itself
   still leaves a variable-register `sdiv` in each iteration.
3. Reduce per-iteration fuel counter traffic. This may reach more loops, but
   needs a separate proof that traps and exact fuel accounting remain intact.
4. Improve collection access lowering. This is narrower and does not address
   the string hash loop.

## Reflect

The highest-ranked arithmetic hypothesis has direct source evidence:

- The selfhost AArch64 backend in `seed/41-a64gen.kotoba` handles positive
  powers of two specially, but its T2 fast-loop path still emits `sdiv` for a
  positive non-power-of-two constant divisor after it has been exposed.
- The older diagnostic in ADR 0289 found that `imod` stayed out-of-line, which
  hid its constant divisor. A fresh code-generation check with the adopted
  M105 native selfhost image confirms the current T2 path inlines the constant
  argument and exposes `1000003`, but still emits `sdiv` in the loop body.
  Strings loop sites are at offsets `0x154` and `0x228`; the collections
  four-way unrolled loop has `sdiv` at `0x320`, `0x340`, `0x360`, and `0x380`.
  The divisor is already hoisted in the latter loop, so the candidate should
  replace the hoisted raw divisor with its reciprocal. See
  `docs/evidence/crossdomain-m105-baseline-codegen-20261016/`.
- The existing incubating `strings-build-scan` and `collections-vector`
  workloads both hash with `imod(..., 1000003)`. Their C twins are available,
  while the other comparator arms and both-ISA promotion evidence are still
  missing. See `bench/runtime-comparison/multidomain-suite.json` and the
  diagnostic record in `docs/adr/0289-the-collections-residual-is-division-not-crossings.md`.
- The historical JIT experiment found that constant propagation can expose a
  reciprocal multiply after inlining. That is useful mechanism evidence, not
  proof about the current AOT/selfhost backend or its speed:
  `docs/jit-cosientist.md`.
- The older J-B control study also measured the same `sdiv` to `smulh` lever
  on a serial C `imod` chain: six diagnostic ABBA runs were positive at about
  6–7%. Those runs did not meet the quiet-host gate and were not an Amu
  workload result, so they support the mechanism hypothesis only; they do not
  predict a gain for these fixtures. See the J-B entries in
  `docs/codegen-coscientist.md`.

An independent integer oracle checked the proposed reciprocal construction
against signed division for 54 candidate positive divisors and 15,174 signed
64-bit boundary, near-multiple, and seeded-random dividends. It included
`1000003`; the generated magic is `0x8637a2a24e5ace35` with shift 19. The script
and captured output are pinned in
`docs/evidence/crossdomain-m105-reciprocal-20261016/`. This checks the
arithmetic formula, not register allocation or boundary behavior in the
Amu-generated machine code.

For positive non-power-of-two divisor `d`, let `p=floor(log2(d))` and
`M=ceil(2^(64+p)/d)`. Since `2^p < d < 2^(p+1)`, `M` is an unsigned 64-bit
value with its high bit set. The code uses signed `smulh`, adds the dividend
back to recover the unsigned-multiplier high product, shifts by `p`, then adds
one for negative dividends. The reciprocal error is below `1/d`, so it cannot
cross a quotient boundary; the final sign correction converts floor to
truncation toward zero.

## Rank

| Rank | Lever | Reach | Main risk | Falsifier |
|---|---|---|---|---|
| 1 | Hoist a positive constant reciprocal across a branchy loop with a slow path | Arithmetic loops with guards; strings `scan` is a concrete candidate | Register lifetime, fallback edges, and exact trap/fuel behavior | The loop still materializes its divisor, any edge observes a clobbered value, or paired timing shows no gain |
| 2 | Reciprocal lowering after T2 exposes a positive constant divisor in a straight-line fast loop | Repeated arithmetic in eligible T2 fast loops; collections fixture reached this path | Signed edge cases, register aliasing, compiler code size | Exact machine results differ, or generated hot loops retain `sdiv` |
| 3 | Reduce loop fuel traffic | Many counted loops | Changes trap timing or fuel semantics | Any exact result/fuel vector differs |
| 4 | Broaden collection access lowering | Vector-heavy workloads | Narrower reach and more comparator work | No separated gain in the collection domain |

## Evolve: earlier reciprocal-division intervention

The local patch limits its first intervention to T2 fast loops: it adds an
AArch64 `smulh` encoder, exact magic generation for positive non-power-of-two
constants, and loop hoisting of reciprocal values instead of raw divisors.
Positive constant division outside these fast loops remains on its existing
path. Negative divisors, zero division, `-1` overflow behavior, and
power-of-two lowering retain their existing paths.

The unmodified M105 baseline and the patched candidate are both recorded. The
patched compiler bootstraps to a byte-identical G1=G2=G3 fixed point (KSEED
SHA-256 `f60b5c…c748b476`, native image SHA-256
`40696a…5541fa55`). The adopted starting compiler is M105
`6b158aa8…45add2eb`; the patch did not use a JVM, Node, or Graal build
fallback. Full bytes and source hashes are in
`docs/evidence/crossdomain-m105-reciprocal-20261016/`, with the pre-patch
comparison in `docs/evidence/crossdomain-m105-baseline-codegen-20261016/`.

Generated code confirms the narrow mechanism. The collections four-way hot
loop now uses `smulh` reciprocal division at `0x330`, `0x360`, `0x390`, and
`0x3c0`; its scalar fast path uses `smulh` at `0x408`. The divisor reciprocal
is hoisted once. A guarded fallback still contains `sdiv` at `0x460`. The
strings fixture is byte-identical to its baseline output and keeps `sdiv` at
`0x154` and `0x228`, so this candidate does not yet improve that workload.

Exact execution checks passed for both fixtures on all six published inputs.
Strings results and fuel match the suite. Collections results match the suite,
and the patched candidate matches the unmodified M105 baseline in both result
and fuel on all six inputs. This exposed stale collections fuel expectations:
the suite was opened on 2026-08-30, before ADR 0353 made each aggregate
constructor debit the shared fuel ledger in both the reference semantics and
native targets. The adopted M105 baseline consumes
`[198, 200, 202, 212, 230, 232]`, while the old suite expected
`[148, 150, 152, 162, 172, 174]`. The manifest is refreshed to the current
executed values; this is a correctness-accounting repair, not a speed result.

No timing result is claimed for this patch. The host was busy, and static
codegen plus exact execution do not establish a performance gain.

The unchanged strings fixture narrows the follow-up. Its `scan` loop has
bounds and ASCII branches plus a slow `string-code-point-at` fallback call;
the pinned candidate disassembly still has `sdiv` at `0x228`, followed by the
multiply/subtract sequence for `imod`. The collections loop is straight-line
after its fast-loop precheck, so T2 can hoist the reciprocal; the branchy
strings loop does not take that path. This is an inference from source shape
and disassembly, not a runtime guard trace. A per-operation `smulh`
substitution would rematerialize the 64-bit reciprocal inside the loop and add
instructions, so the next compiler candidate should first investigate
loop-invariant reciprocal placement across these branches. The disassembly is
`docs/evidence/crossdomain-m105-reciprocal-20261016/fixtures/kernel_strings.disasm.txt`.

## Evolve: MSub fusion follow-up (2026-10-16)

The next AArch64 backend candidate fuses a subtraction of a product by a
positive non-power-of-two constant into `msub`. It handles both the ordinary
`x - q*k` shape and the recognized remainder shape `x - (quot(x,k)*k)`. For
the latter, the backend reuses the divisor still in `x17` only when the
quotient is single-use, there are no intervening code-emitting values, and
the operation is outside a fast loop. In fast loops, the fused product's
constant is now eligible for hoisting, so the `msub` uses the loop-invariant
divisor register rather than materializing it in each iteration. Spilled
operand paths retain their explicit safe fallback.

The M105 G1=G2=G3 fixed point passed again with this backend change. All three
KSEEDs have SHA-256 `a7aa4ac9868afc6d8d850cd5b20452a2f6f234138d0ca1eb0fab39f45d8e8a4f`,
and all three native images have SHA-256
`854fad339b1317ff85309573767a305e846e23cfee13377570973ff502258a3b`. The
bootstrap compiler built this candidate without a JVM, Node, or Graal
fallback.

Both fixtures passed exact native comparisons on all six inputs, matching the
prior M105 result, fuel, and arena report for all 12 executions. In the
strings hot loop, `sdiv` remains, but the following rematerialized-divisor,
`mul`, and `sub` sequence becomes one `msub`. In the collections fast loop,
the existing reciprocal `smulh` sequence and hoisted divisor remain; each of
the four unrolled remainder sites and the scalar tail replaces `mul` plus
`sub` with `msub`. The guarded fallback also fuses its multiply/subtract.
Pinned raw code and full disassemblies are in
`docs/evidence/crossdomain-m105-msub-20261016/`.

Exploratory runtime checks called each native kernel 20,000 and 50,000 times
per process and collected four timed samples per compiler in ABBA order. At
20,000 calls, the strings median was 97.94 ms for the candidate versus 111.92
ms for prior (14.3% shorter), while collections was 105.13 ms versus 95.67 ms
(9.0% longer). At 50,000 calls, strings was 93.78 ms versus 95.15 ms (1.5%
shorter) and collections was 122.17 ms versus 135.81 ms (11.2% shorter).
These results are not a performance claim: the first run began with load
averages 31.1/31.9/38.5, the longer runs began around 15–17/23/32.6–32.8, and
relative results changed between run lengths. Sample ranges overlap. A
100,000-iteration collections follow-up exhausted the configured vector arena
and is excluded. Results, fuel, exact benchmark inputs, binaries, and raw
timing samples are pinned in the evidence directory. Qualified quiet-host
timing and C comparisons remain outstanding.

## Next checks

1. Add a separate source-level KIR oracle run for the corrected collections
   fuel vector, so the historical manifest drift is independently reproduced.
2. Exercise reciprocal arithmetic boundary dividends and register-alias cases
   through a compiler fixture, in addition to the exact formula's integer
   oracle.
3. Rerun prior/candidate timing with an adequately sized arena on a quiet host,
   then compare the relevant domains against identical C twins; qualify each
   domain independently.
4. Prototype loop-invariant reciprocal placement for the branchy strings loop;
   do not replace its `sdiv` unless the reciprocal is kept out of the hot body.
5. Promote incubating domains only when every required comparator arm and both
   target ISAs have measured evidence. Until then, “world fastest” remains an
   objective, not a result.
6. For xgboost `tw`, compare early-stop group widths before changing codegen.
   On the pinned 128-sample / 400-tree model, width two reduces ideal
   fixed-five steps by 21.24% with 85,392 stop decisions; current width four
   saves 15.35% with 45,095 decisions. These omit comparison, branch, spill,
   and code-size costs. Hand-patch and measure width two against the existing
   width-four kernel, then require exact result/fuel behavior and qualified
   timing before keeping it. See
   `docs/evidence/embench-xgboost-depth-20261016/profile.json`.
