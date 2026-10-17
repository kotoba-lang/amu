# Amu selfhost cross-domain performance research

Status: active research. M104 has a bounded translated-port result. M105 has
the baseline/candidate ABBA repeat plus four CPU-gated, exact full-19 M4
campaigns for isolated selfhost compiler variants. Same-image controls show
that the apparent small gains are unresolved timing drift, not established
compiler speedups. This does not support a general or world-fastest claim. The 2026-10-17
xgboost width-two hand-patch passes exactness, but its loaded-host ABBA run does
not support a promotion. A per-lane follow-up also passes exactness, but was
slower in all five loaded-host ABBA pairs; that compiler-source change was
reverted. See
`docs/evidence/m105-abba-m4-20261016/`,
`docs/evidence/crossdomain-m105-all19-20261016/variant-timing-m4/`, and
`docs/evidence/embench-xgboost-width2-20261017/`. A new T2
constant-division-hoist candidate passes its 19-workload exactness run but
changes none of the official Embench images; its strings/collections timing
is heavily loaded and exploratory only. It remains unpromoted in
`docs/evidence/crossdomain-m105-branchy-div-hoist-20261017/`.

## Why the translated-port comparison can beat C

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

The M105 stage measurements do not explain that M104 advantage. Across the
four new M4 campaigns, both compiler variants still have a Kotoba/C geometric
mean below 1, but same-image controls move with the apparent change. After
normalizing the image-changed workloads against those controls, the reciprocal
variant is 1.01072 and the MSub variant is 1.00038 versus the M105 baseline.
That leaves the causal effect unresolved; it does not show that selfhosting
itself makes a program faster. Full raw trials and the control calculation are
in `docs/evidence/crossdomain-m105-all19-20261016/variant-timing-m4/`.

## Rank from the M105 full-suite M4 ABBA repeat

The four CPU-gated campaigns accepted all 19 workloads in both arms. The
M105-baseline Kotoba/C ratios above one were xgboost 1.520, statemate 1.287,
sglib-combined 1.142, huffbench 1.096, and picojpeg 1.028. The current candidate
ratios were 1.413, 1.456, 1.155, 1.116, and 1.113 respectively.

The xgboost candidate image is the four-wide early-stop image
`1c4aab16…c941a400d`. Its candidate/baseline Kotoba raw-time ratio was 0.9163;
the shared C raw-time ratio was 0.9862, giving a control-normalized ratio of
0.9291. This is a promising roughly 7% per-workload improvement signal, but
xgboost still ran slower than C at 1.413, and the ABBA repeat has only two
campaigns per compiler. Treat the early-stop mechanism as the highest-ranked
measured candidate, not as a finished win. The width-two follow-up was
inconclusive on the loaded M1: its median ratio to four-wide was 1.024.

Statemate's image was identical in both arms; its raw Kotoba time moved to
1.0473 while the shared C time moved to 0.9261, leaving a normalized ratio of
1.1308. That is timing drift, not evidence that a compiler change caused its
1.456 ratio. Sglib-combined is the next changed-image gap at 1.155, while the
huffbench and picojpeg changes also do not separate compiler effect from
campaign drift. See `docs/evidence/m105-abba-m4-20261016/analysis.json` and
its raw-record verifier before ranking another broad compiler patch.

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

## Meta-review: all-19 selfhost reach check (2026-10-16)

After combining reciprocal division, MSub fusion, and the four-wide xgboost
early-stop candidate, the current seed source at `6103f5cf` was rebuilt from
the adopted native bootstrap. G1, G2, and G3 all produced image
`b10e381344a1f5a8b82cac981c0011bd20ecbcc4b48dd5f5dce97364c74e8a00`, and the
compiler regenerated all 19 workload images. The pinned M104 exactness harness
passed all 19 at its recorded iteration counts, including result, fuel, and
arena values. Seven images changed: matmult-int, nsichneu, picojpeg, qrduino,
sglib-combined, slre, and xgboost. This proves cross-workload reach and
correctness only; it provides no timing result. The build, image hashes, and
exactness report are in `docs/evidence/crossdomain-m105-all19-20261016/`.

The closest C-comparison gaps in the existing M104 M4 record remain xgboost
(1.515 Kotoba/C), picojpeg (1.446), slre (1.194), qrduino (1.177), and
sglib-combined (1.087). To compare compiler generations fairly, the verified
M105 baseline and current M105 each compiled the same current port sources;
the baseline passed exactness on all 19 workloads. Four loaded-host pairs on
five domains show mixed current/baseline medians: xgboost 1.133, picojpeg
1.060, slre 0.953, qrduino 1.123, sglib-combined 0.889. Pair ranges are wide,
and raw idle stayed below the 70% qualification threshold throughout. These
figures only prioritize follow-up work; they do not establish either a speedup
or the effect of any one optimization. The earlier M104-versus-current-M105
diagnostic is also cross-generation and cannot attribute changes. Next, profile
the apparent xgboost, picojpeg, and qrduino regressions against the same-source
baseline, falsify the emitted-code hypotheses, then retime on a qualified host.

## Next checks

1. Add a separate source-level KIR oracle run for the corrected collections
   fuel vector, so the historical manifest drift is independently reproduced.
2. Exercise reciprocal arithmetic boundary dividends and register-alias cases
   through a compiler fixture, in addition to the exact formula's integer
   oracle.
3. Rerun prior/candidate timing with an adequately sized arena on a quiet host,
   then compare the relevant domains against identical C twins; qualify each
   domain independently.
4. The T2 access-free counted-loop candidate now places reciprocals in
   branchy strings and collections fast copies; retain it as an incubating
   optimization until a quiet-host paired run establishes its effect. It
   changed 0/19 official Embench images, so keep ranking other compiler gaps
   against those workloads.
5. Promote incubating domains only when every required comparator arm and both
   target ISAs have measured evidence. Until then, “world fastest” remains an
   objective, not a result.
6. For xgboost `tw`, the static profile and width-four candidate remain
   exploratory. A 2026-10-17 width-two hand-patch reorders the 16 emitted walk
   bodies into pairs while preserving the final four-lane validation and
   commit. It passes exactness at n=8192, but five loaded-host ABBA pairs have
   median width-two/width-four ratio 1.024 and do not support a speedup. Keep
   compiler source unchanged; revisit with a quiet-host comparison or a
   different layout. See
   `docs/evidence/embench-xgboost-depth-20261016/profile.json` and
   `docs/evidence/embench-xgboost-width2-20261017/`.
## Evolve: M105 xgboost width-two hand-patch (2026-10-17)

The current M105 fixed-point compiler was rebuilt from the adopted native
bootstrap. G1, G2, and G3 all produced SHA-256
`b10e381344a1f5a8b82cac981c0011bd20ecbcc4b48dd5f5dce97364c74e8a00`, with no
JVM, Node, or Graal fallback. Recompiling the pinned xgboost port reproduced
the width-four payload byte-for-byte (`1c4aab16…`).

A hand-patch rearranged its 16 emitted walk bodies into two-lane pairs in the
same 960-byte code region. It adds pair exit checks after the root and steps 2
through 4, while retaining the existing four-lane final bounds/leaf
validation, fallback, and commit. The patch is in
`docs/evidence/embench-xgboost-width2-20261017/`; no compiler source was
changed.

The official xgboost exactness harness passed at `n=8192`, and all 20 ABBA
invocations matched result, benchmark fuel, and arena. Timing under load1
49.4–64.1 and raw idle 0.02–14.6% was inconclusive: paired width-two/width-four
ratios were 1.024, 1.014, 1.057, 1.089, and 0.649, with a median of 1.024.
The host did not pass the 70% idle gate. This neither qualifies a speedup nor a
regression, so the compiler remains unchanged. A later quiet-host paired run
or a different layout is needed before promotion.

## Evolve: T2 fast-copy remainder register reuse (2026-10-17)

This candidate changed the T2 `msub` emitter to reuse `x17` in fast copies
only when the preceding instruction word was the exact matching `sdiv` and
the quotient/remainder pair was eligible. It was a dead hypothesis on the
existing workload set: after a native G1=G2=G3 rebuild, baseline and candidate
generated byte-identical code for all 17 runtime-comparison fixtures and all
19 Embench Kotoba ports. The strings and collections fixtures also compiled
identically, and the candidate matched every known result and fuel value. No
timing was run; the patch was reverted. Full hashes and the attempted patch
are retained in `docs/evidence/crossdomain-m105-t2-rem-reuse-20261017/`.

This result keeps the next search focused on generated hot loops where repeated
work is visible, especially constant division in branchy loops that do not
qualify for the existing versioned-loop hoist. Any next candidate must first
change generated code on at least one relevant workload, then pass exactness
before timing.

## Evolve: T2 branchy/access-free reciprocal hoist (2026-10-17)

### Generate and debate

The prior remainder-register-reuse candidate changed no generated workload
image. The next hypothesis was narrower: a counted loop with no vector/table
accesses is skipped by T2 loop versioning even when it repeatedly divides by
the same positive non-power-of-two constant. Admitting that loop could replace
the hot `sdiv` with an exact reciprocal multiply. The counter-hypothesis was
that versioning, unrolling and extra control flow would cost more than the
saved divide, especially on short loops; a string slow-path callback could also
clobber reciprocal registers unless the callback stub preserved them.

### Reflect and evolve

The patch adds division-based eligibility for access-free counted loops and
records hidden reciprocal registers in the string callback save mask. It was
built from the adopted native bootstrap without JVM, Node or Graal fallback;
G1, G2 and G3 are byte-identical at image SHA-256
`bf6148d28cedb834830a335d3313e9d3bec4fb32a179be5ac3b789080110fdc7`.

Generated code changes in both synthetic incubating fixtures. The strings
kernel grows from 1,360 to 2,344 bytes and contains `smulh` reciprocal
instructions in the fast copies, while guarded `sdiv` fallback sites remain.
The collections kernel grows from 3,064 to 3,128 bytes and likewise gains
`smulh` fast copies with a guarded `sdiv` fallback. The non-ASCII callback
fixture traverses 32 valid UTF-8 code points and matches baseline result and
fuel. Both fixtures also match all six registered result/fuel inputs.

The candidate then recompiled all 19 pinned Embench Kotoba ports. The official
exactness harness passed 19/19 results, fuel values and arena counters. Its
native images were byte-identical to the current M105 compiler's images for
all 19 workloads. This candidate therefore has no generated-code reach in the
official Embench set; the fixture results cannot be used to predict an
Embench-wide gain.

An exploratory same-host timing run used 10,000 calls per sample and ten
paired rounds per comparison. In the stored ratios, candidate/baseline was
1.040 for strings and 0.582 for collections; C/candidate was 0.165 and 0.197,
respectively. The host load averages rose from 114.02 to 123.21, far outside
the quiet-host gate, and samples had large outliers. These values do not
establish either a speedup or a regression; they only preserve the direction
for a future qualified run. Exact reports, full disassembly and raw samples
are in `docs/evidence/crossdomain-m105-branchy-div-hoist-20261017/`.

### Verdict

Keep this as an unpromoted experiment for the two incubating runtime-comparison
fixtures. Do not attribute the Embench/C result to it: all 19 official images
are unchanged from the current M105 compiler. The immediate Embench search
should return to the same-source C gaps and generated-code evidence already
ranked above; promotion still requires qualified per-domain evidence.

## Evolve: statemate repeated-state driver probe (2026-10-17)

### Explain the C comparison

“Selfhost” identifies how the Amu compiler was built; it does not by itself
make programs compiled by Amu faster than C. The M104 translated-port GM was
Kotoba/C = 0.8213, and a separate M4 campaign reported 0.78777, but those are
geometric means over 19 different workloads. C is still faster on individual
workloads. In the current M105 M4 record, statemate is a large gap: Kotoba/C
was 1.2874 for the baseline campaign and 1.4559 for the candidate campaign.
The statemate image did not change between those compiler variants, and its
same-image control moved substantially, so the normalized 1.1308 change is
timing drift rather than an attributable compiler effect. See
`docs/evidence/m105-abba-m4-20261016/analysis.json`.

The source shapes suggest why statemate is harder for Amu. Upstream C keeps
state in global scalar variables and a 64-byte `Bitlist`; its repeated driver
clears the bitlist and calls `init`, `interface`, and `FH_DU`. The translated
Kotoba port represents state as a 169-element vector and contains 517 private
`s-N` state functions plus 355 `vector-at` reads. Every vector access and
state transition must preserve Amu's vector, bounds, memory, and fuel
semantics, while clang can optimize the C globals and calls under `-O2`.
Generated code shows a `bl` from the repeated driver into `body` and a fuel
check at that function entry. This is a source/codegen explanation supported
by static evidence, not a measured attribution of the 1.4559 ratio.

### Falsify a wrapper-call hypothesis

The candidate was to inline `body`'s four-operation composition into the
recursive `repeats` expression. This removes one repeated helper call while
keeping the same state-transition functions. The unmodified source compiled
with the same selfhost G3 reproduced the pinned statemate image exactly:
264,184 bytes, SHA-256 `6cb09af5…d5e6636`. The inline source generated
264,568 bytes, SHA-256 `28832123…03655c9`.

All six exploratory executions returned the expected result and arena
accounting. The inline version consumed exactly 27,279,360 fewer benchmark
fuel units, equal to the iteration count: deleting this call also deletes its
per-call fuel charge. It therefore does not pass the pinned result/fuel/arena
exactness rule. Timings were 18.60, 8.53, and 4.50 seconds for baseline, and
16.38, 10.78, and 20.11 seconds for inline, in
`base, inline, inline, base, base, inline` order. The baseline spread alone is
over 4x, so the loaded-host measurements cannot decide whether this call is a
material runtime cost. The full per-run record is
`docs/evidence/crossdomain-m105-statemate-call-inline-20261017/receipt.json`.

### Verdict and next experiment

Do not promote the source edit or claim a speedup. A compiler-level inline
pass would have to preserve the removed call's fuel charge and pass exact
result, fuel, and arena checks. That is a useful narrow falsifier, but the
larger portable opportunity is to lower proven constant-index accesses on a
fixed-length vector without repeated bounds work. The next statemate trial
should first compare that generated code with the pinned image, preserve exact
fuel accounting, and then use a qualified paired timing run. Keep the
representation hypothesis provisional until runtime evidence supports it.

## Evolve: T2 loop-callee speculative-inline admission (2026-10-17)

The T2 speculative-link check used to reject a parent candidate whenever a
mostly-constant call targeted a callee containing calls. That was too broad:
loop callees are separately refused by `t2-callee-pre?` and remain real calls,
so they need not block inlining their small parent wrapper. Narrowing the link
check this way produced a native selfhost fixed point: G1=G2=G3 at SHA-256
`4a8876f60603e0d864fae4323762d766303ff04249d2d2802d5783ee6b758429`.

Compared with the prior branchy reciprocal-hoist candidate, the change altered
12/19 pinned port images: edn, huffbench, matmult-int, md5sum, nettle-aes,
nettle-sha256, picojpeg, qrduino, sglib-combined, tarfind, ud, and wikisort.
The official exactness harness passed all 12 changed images at their registered
iteration counts, including result, benchmark and verify fuel, and arena
accounting. The other seven images were unchanged. The exactness receipt is
`workspaces/codex/amu-statemate-loop-call-inline-20261017/attempt-2/exactness-12-escalated/report.json`.
The 12 changed native payloads grew by a net 4,016 bytes (from 972,951 to
976,967 bytes), another reason to require timing before deciding whether the
broader inline admission helps.

No paired timing was run for this candidate, so image changes and exactness do
not establish a speedup. Keep it unpromoted until a qualified host measures
the affected workloads against identical C and Kotoba controls. This candidate
did not change statemate and does not explain the recorded M104 geometric-mean
advantage over C.

## Falsify: self-recursive nested-callee inline admission (2026-10-17)

The next T2 candidate tried to stop a direct self-recursive callee from
blocking speculative inlining of its small parent wrapper. It rebuilt from the
adopted native bootstrap and reached G1=G2=G3 at SHA-256
`ef2ceb749edfa8a3aeae3845612d377d9fcfcb498e4775f926f7ccaff8e6b541`.
All 19 pinned ports compiled successfully, but every generated native payload
was byte-identical to the preceding loop-callee-inline candidate. This
admission change therefore did not reach code generation for the official
workload set and provides no speedup evidence. The image comparison is in
`docs/evidence/crossdomain-m105-statemate-recursive-inline-20261017/README.md`;
the complete build and compile outputs are under
`workspaces/codex/amu-statemate-recursive-inliner-20261017/attempt-3/`.

Since none of the 19 images changed, there was no new exactness case to run.
The prior candidate's 12 changed images already passed the official exactness
harness, and the other seven matched the prior pinned images. Do not promote
this compiler-policy change. Return to generated-code opportunities that
actually alter one of the high-gap workloads, while retaining the distinction
between the M104 translated-port aggregate and current M105 per-workload
evidence.

## Falsify: duplicate minimum-vector-length check proof (2026-10-17)

A candidate tried to let `t2-bch-covered?` remove a constant-index bounds check
directly from the interprocedural minimum vector length. The native compiler
reached G1=G2=G3 at SHA-256
`77d48ee4c3d73fbcbd64566258287ea0a96e8b5940c0fa50de16708b13a6a9ed`, but
none of the 19 pinned workload images changed. Inspection showed the proof is
already applied earlier: `t2-chk-vals` calls `t2-hm` for each constant-index
vector access and sets the unchecked flag when the minimum length exceeds the
index. The attempted change duplicated that existing proof, so it was removed.
See `docs/evidence/crossdomain-m105-interprocedural-bounds-20261017/README.md`.

This closes off the simple bounds-check hypothesis for these images. The next
statemate search should locate costs that survive the existing minimum-length
and redundant-check analyses, starting with repeated state-transition call
entry/return work and confirming T2 admission before adding another broad
optimization rule.

## Evolve: repeated body-entry guard inspection (2026-10-17)

The pinned statemate disassembly narrows that search. `repeats` has a loop at
`0x3f434` and issues `bl 0x3dad0` for `body` on every iteration. The `body`
entry decrements fuel, then checks that the vector descriptor is valid and its
length exceeds index 168 before taking its fast path. On the fast path,
`clear-bits` is already lowered to sixteen paired NEON stores covering the
64-element bitlist. The old `body` wrapper-call experiment therefore exposed
both per-iteration call/entry work and a repeated vector-shape guard, while
showing that removing the entry without preserving one fuel unit per iteration
breaks exactness. The disassembly is
`workspaces/codex/amu-statemate-call-inline-20261017/attempt-1/base/base-image.disasm.txt`
and matches the pinned 264,184-byte image in the receipt above.

A candidate for further investigation is to version the repeated loop: check
the vector shape once, then use a fast body path while preserving each body's
fuel charge and retaining the original fallback for vectors that do not meet
the guard. This is only a static hypothesis. The present evidence does not
prove that the vector descriptor stays unchanged across every transition, nor
that T2 can express this safely. The generic single-use inline probe below
compiled successfully but left statemate byte-identical, so there is still no
candidate image or timing result for this repeated-vector-guard transformation.

## Falsify: single-use private callee inline probe (2026-10-17)

A T2 rule then allowed a private, non-exported, non-address-taken callee with
one direct call site inside a repeated or recursive caller to bypass the
ordinary size limit. The selfhost compiler reached G1=G2=G3 at SHA-256
`1544a204b003bd3b5ec9831be008fcbd5ffa5a91c44f922a4ca13a1dca539588` and
compiled all 19 ports. Only picojpeg, sglib-combined, and xgboost changed;
their native payloads grew by 160, 1,000, and 680 bytes respectively. The
other 16 images were byte-identical to the prior recursive-inliner candidate.

The intended statemate target did not change: its image remains the pinned
264,184-byte payload. The three changed images passed the official exactness
harness, including result, fuel, and arena accounting. No paired timing was
run, so this is correctness evidence only and the rule remains unpromoted. See
`docs/evidence/crossdomain-m105-statemate-singleuse-inline-20261017/README.md`
and its `exactness-report.json` receipt.

## Falsify: deep-fixture remainder divisor reuse (2026-10-17)

A T2 emitter probe attempted to reuse the divisor register from `sdiv` for the
following remainder `msub` in `kernel_deep`. A native selfhost fixed point was
built, but baseline and candidate fixture images were byte-identical at 2,508
bytes. Two one-generation diagnostics also left the payload unchanged; neither
diagnostic was a fixed point or executed. The reason the reuse predicate did
not admit the fixture remains unproven. No timing or runtime comparison was
run. Evidence and raw workspaces are indexed in
`docs/evidence/crossdomain-m105-rem-sdiv-reuse-20261017/README.md`.

The fixture defines all 24 remainder lanes before the final sum. Inspection of
`t2-positions`, `t2-scan`, and `t2-e-vals` confirms that allocation positions
and ordinary block emission both follow ascending IR value order. The results
therefore stay live across the other lanes and spill; changing only the
allocator's spill heuristic cannot shorten those intervals. A future test
needs a semantics-safe instruction schedule or incremental sum formation, with
division trap ordering and exact fuel accounting checked. This remains a
static pressure hypothesis, not a measured compiler benefit, and it does not
explain the M104 translated-port comparison.

## Falsify: XGBoost per-lane walk skip (2026-10-17)

A static XGBoost depth profile showed that 52.6% of walks finish before the
fifth level. The candidate kept the four-way interleaving but inserted a
per-lane leaf branch before each later walk body, aiming to skip 14
instructions for a lane that had already reached a leaf. This traded fewer
feature, threshold, and child reads for twelve more branches. The prior
width-two probe did not show a gain, so lane-skip ranked as a reversible
experiment rather than a likely win.

The candidate was added to `tw-entry`, rebuilt to a G1=G2=G3 selfhost fixed
point, and used to recompile the pinned XGBoost source. The generated
66,732-byte image exactly matched the hand-patched prototype. Official
exactness passed at `n=8192`, with result `1`, benchmark fuel `2806009749`,
and matching arena accounting.

Five exploratory same-host ABBA pairs returned lane-skip/four-wide ratios
`1.0653, 1.1370, 1.1303, 1.0539, 1.0160`; all 20 invocations were exact. The
host load1 ranged from 24.37 to 34.71 and idle from 6.5% to 39.1%, so the
measurement failed the 70% quiet-host gate and is not a qualified performance
claim. Since all five pairs favored the existing four-wide layout, the
compiler source was restored to its original group checks. No C comparison was
made. Full receipts and scripts are in
`docs/evidence/embench-xgboost-lane-skip-20261017/README.md`.

## Falsify: statemate compare-zero branch fusion (2026-10-17)

The next statemate probe replaced a compare-zero plus conditional branch with
`cbz`/`cbnz` when the compared temporary was dead on both successor paths.
The candidate selfhost compiler converged at G1=G2=G3, and its statemate image
was the only image changed relative to the preceding M105 candidate. Its
disassembly contains 25 fewer `cmp` and 25 fewer `b.ne`, with 25 more `cbnz`.
The official exactness harness passed all 16 images that differ from the M104
record; the other three still match that record.

Five exploratory ABBA pairs on the loaded M1 Max ranged from 0.380 to 1.197
candidate/base. All 20 calls passed result, fuel, and arena checks, but load1
was about 122–134 and CPU idle remained below 22%. The timing is inconclusive,
so this statemate change remains unpromoted. Full evidence and workspaces are
indexed in `docs/evidence/crossdomain-m105-statemate-zero-branch-20261017/`.

To continue the objective across different workloads, the next hypothesis
should come from another domain's hot native code, with its C gap, exactness
surface, and counter-hypothesis recorded before changing the compiler.

## Falsify: generic compare-zero branch fusion (2026-10-17)

The generic fused-branch emitter was changed to use `cbz`/`cbnz` when an
equality predicate compares a nonconstant value with zero. A same-source
no-fusion control and the candidate each reached a G1=G2=G3 selfhost fixed
point. Recompiling the pinned 19 ports changed 18 native images; depthconv
stayed byte-identical. Official exactness passed all 18 changed images.

Five loaded-host ABBA blocks per changed workload produced 360 exact runs.
Candidate/control median ratios were below one for 11 of 18 workloads and the
median across per-workload medians was 0.993. The effects were mixed: edn was
0.943, while huffbench was 1.113 and statemate was 1.047. Load1 ranged from
22.07 to 78.34 (median 33.05), with large pair-level outliers, so the run is
unqualified and does not establish a compiler speedup. Keep this candidate
unpromoted; the result supports the earlier explanation that selfhosting is
compiler provenance, while runtime speed comes from workload-specific source,
generated code, and measurement conditions. Full records are in
`docs/evidence/crossdomain-m105-cmp-zero-fusion-20261017/`.

## Falsify: XGBoost pairwise leaf-check reassociation (2026-10-17)

The XGBoost early-stop checks and final leaf validation each formed their
predicate with three dependent `and` instructions. The candidate reassociated
each into two independent ANDs and a combine. Both candidate and same-snapshot
control reached G1=G2=G3 fixed points and compiled all 19 pinned ports; only
XGBoost changed. Its 8,141-instruction image passed official exactness at
`n=8192`, including result, fuel, and arena accounting. Disassembly confirms
the five intended dependency chains were shortened without changing the
instruction count.

Ten exploratory ABBA pairs completed 40 exact runs. Candidate/control ratios
had median 0.989, with 6/10 pairs favoring the candidate; raw medians were
3.838 s for candidate and 3.708 s for control. Load1 ranged from 34.26 to
41.52, so the evidence is mixed and unqualified. Do not promote this change.
Full records are in
`docs/evidence/crossdomain-m105-xgb-pairwise-leaf-check-20261017/`.

## Falsify: T2 multiplication interval analysis (2026-10-17)

T2's range analysis was extended in an isolated compiler candidate to derive
bounded products from four endpoint products, retaining only results inside
the signed i32 range used by its interval representation. The candidate
reached a G1=G2=G3 fixed point and compiled all 19 pinned ports. Every native
image remained byte-identical to the exact-source control, so the candidate
does not reach current Embench runtime code. No exactness rerun or timing was
needed, and no runtime benefit is claimed. Full records are in
`docs/evidence/crossdomain-m105-t2-mul-range-20261017/`.

## Falsify: Sglib input-table source rewrite (2026-10-17)

The Sglib input function is called 600 times per body, so its nested 100-value
equality map looked like a possible C gap. The control disassembly shows that
the selfhost compiler already lowers it to a bounds check and one indexed
literal-table load. Rewriting the port as a vector table returned the same
result and arena report but added exactly 600 fuel per body and 100 fuel in
verification. A single `n=8192` instruction-count diagnostic was 1.3096x the
control; no timing was run. Keep the source and compiler unchanged. The next
Sglib search should focus on hot vector operations and data-structure bodies.
Full records are in
`docs/evidence/crossdomain-m105-sglib-input-table-20261017/`.

## Sglib hot-path profile and rejected list rewrite (2026-10-17)

A two-second sample profile of the unchanged M105 guest placed the largest
sampled regions in linked-list merge, tree search/insertion/rebalance, and heap
sift-down. The host was loaded, so these samples rank code regions but do not
measure their elapsed-time shares. The 1.1546 Kotoba/C Sglib gap remains a
workload-specific M105 result.

A private branchless rewrite of `list-merge` preserved result, fuel, and arena
exactly at registered `n=253952`, but increased the median dynamic instruction
count by 20.82% over three same-host diagnostic runs. It was rejected without
timing. Next, inspect backend lowering of the original compare/update shape
while keeping the source and exact fuel unchanged; tree and heap paths follow
in the profile rank. Details and hashes are in
`docs/evidence/crossdomain-m105-sglib-hot-profile-20261017/`.

The image check identified why: the source rewrite removes the existing
104-word `lp-entry` AArch64 body from the output image, while both the control
and input-table candidate retain it. That shape-matched kernel is part of the
reason the original Sglib port is efficient.

## Sglib pointer-cache kernel (2026-10-17)

The private candidate keeps the source and shape matcher unchanged and carries
node addresses through the merge loop, updating only the side that was
selected. The 20-word kernel required six explicit branch-target repairs after
growing from 18 words; attempts that missed literal offsets did not terminate
even at `n=1024`. Attempt 4 reached a G1=G2=G3 selfhost fixed point, passed
registered exactness at `n=253952`, and passed the preregistered ±2%
instruction-count gate. Its median dynamic instruction count was 0.99522 of
the matched control.

Ten exploratory ABBA/BAAB blocks on the loaded M1 Max favored the candidate in
9/10 blocks, with median candidate/control ratio 0.98678. Load1 ranged from
16.33 to 29.46 and block ratios ranged from 0.932 to 1.109, so this timing is
unqualified and the change remains private. The experiment did not compare
against C. Full reports and hashes are in
`docs/evidence/crossdomain-m105-sglib-pointer-cache-20261017/`.

## Sglib heap hole candidate (2026-10-17)

The profile's `0x6600–0x6c00` heap-stage region contains the `0x6878–0x68d4`
sift-down loop. The original loop wrote the displaced value into every child
position as it descended. A private hole-style kernel kept that value in a
register, shifted one child value per level, and wrote the held value once at
the final position. Attempt 1 missed one leaf exit and trapped; attempt 2 fixed
both exits.

Attempt 2 reached a G1=G2=G3 fixed point and passed registered exactness at
`n=253952`, including result, benchmark fuel, verification fuel, and arena.
Its dynamic-instruction median was 0.99569 of control. Ten exploratory paired
blocks all remained exact, but the candidate was faster in only 3/10 and its
median elapsed ratio was 1.02634. Load1 ranged from 23.05 to 33.43, so reject
this as a performance candidate on current evidence. Details are in
`docs/evidence/crossdomain-m105-sglib-heap-hole-20261017/`.

## Sglib tree-insert path cursor candidate (2026-10-17)

The tree kernel at `0x9250` records the `tree-find` path, then replays a second
per-level validation before linking a missing value. A miss guarantees the
input differs from every visited node; `tree-insert` compares the same value
against unchanged nodes and therefore chooses the same path. The candidate
skips those repeated comparisons while preserving the 24-byte path-cursor
advance consumed by `tree-fix`. A first direct-skip attempt exposed that cursor
state as necessary and failed fuel exactness; the corrected attempt retains
it.

The corrected candidate reached a G1=G2=G3 fixed point and passed registered
exactness at `n=253952`, with result, benchmark fuel, verify fuel, and arena
matching control. Three instruction-count runs had a median 0.9354 of control.
The standard unchanged-image ±2% diagnostic reports out of range because this
candidate intentionally removes about 6.5% of dynamic instructions; the
registered exactness result is separately PASS. Ten loaded-host ABBA/BAAB
blocks were all exact, with 7/10 favoring the candidate and median elapsed
ratio 0.99029. Load1 ranged from 38.59 to 50.74, so this is still exploratory
and is not promoted. No C comparison was made. A same-predecessor full-19 build confirms that only the Sglib native image changes; the other 18 images, KSEED files, and exports remain identical. Candidate images pass registered exactness for all 19 workloads. This verifies reach and cross-workload correctness, not speed. Full evidence is in
`docs/evidence/crossdomain-m105-sglib-tree-path-skip-20261017/`.

A quiet-host paired rerun is the next gate for the tree candidate. These
Sglib-specific results do not explain the separate M104 geometric-mean
translated-port result as a general property of selfhosting, and they do not
establish an official Embench score or a general fastest-language claim.

## Sglib combined list and tree kernel candidate (2026-10-17)

The earlier list pointer-cache kernel and tree-insert path-cursor skip were
composed in one seed candidate on separate source lines. The combined source
reached a G1=G2=G3 fixed point at
`98c7af4b3ed13a290a61e0d95e6b24135aad5ce8d9a5d818cfe4418df0872a70`. A same-predecessor build compiled all 19 ports;
only `sglib-combined` changed image, KSEED, and exports. Its registered
exactness passed at `n=253952`, with benchmark fuel
`3858038786`, verify fuel 605, and matching arena.
The other 18 ports remain byte-identical to previously exact same-predecessor
images.

Three dynamic-instruction diagnostics had median `28886414971` versus the
control median `30970746764` (93.2700% of control). The
standard unchanged-image count gate reports FAIL because the intended change
exceeds its 2% diagnostic band; registered result/fuel/arena exactness passed.
Ten exploratory ABBA/BAAB blocks were exact in all 42 runs, with candidate
faster in 8/10 and median elapsed ratio
0.97083. Load1 ranged from
27.36 to 50.04; this loaded-host sample is not qualified.
No C comparison was made, so the candidate remains private and unpromoted.
Evidence is in
`docs/evidence/crossdomain-m105-sglib-combined-kernels-20261017/`.

## Falsify: Statemate body inline with fuel compensation (2026-10-17)

The Statemate `repeats` loop calls `body` 27,279,360 times. A candidate
inlined its transition chain and inserted a same-value vector write to preserve
the call's one fuel unit. The selfhost-generated candidate passed registered
exactness at `n=27279360`: result 1, benchmark fuel 20,159,447,042, verify
fuel 66, and matching arena use.

Ten exploratory base/candidate/candidate/base blocks were exact in all 40
runs, but the base was faster in all ten. The median paired candidate/base
ratio was 1.05573. Load1 ranged from 23.18 to 35.40, so the timing is
unqualified; it still gives no reason to adopt this rewrite. The candidate
remains rejected. No C executable or instruction-count diagnostic was
measured. Evidence and replay inputs are in
`docs/evidence/crossdomain-m105-statemate-inline-fuel-20261017/`.

This per-workload result illustrates the comparison boundary: selfhost says
which compiler produced the executable. It does not itself make the program
faster. Runtime depends on the workload source and algorithm, compiler
lowering, target, and measurement conditions. The separate M104 translated
Embench aggregate remains workload-specific evidence, not a general
selfhosting advantage or an official SPEC result.

## Loaded M1 timing screen: single-use inline candidate (2026-10-17)

The fixed-point compiler `1544a204…` changed only picojpeg, sglib-combined,
and xgboost relative to the preceding `ef2ceb74…` compiler; the other 16 of 19
images were byte-identical. The three changed images passed the registered
exactness harness. Five ABBA blocks on the M1 measured those three workloads
and used unchanged Statemate as a same-image control. All 80 timed calls passed
result, fuel, and arena checks.

The per-block ratio is the mean of the two candidate times divided by the mean
of the two base times. The median candidate/base ratios were 1.0202 for
picojpeg, 1.0155 for sglib-combined, and 0.9892 for xgboost. The same-image
Statemate control had a median ratio of 1.0371. Dividing each per-block
workload ratio by that block's Statemate control ratio gives medians of 0.9813,
0.9866, and 0.9695. These
control-adjusted readings are only a screening signal: load1 varied from
25.28 to 37.80, the block ratios moved in both directions, and the control
itself drifted. Keep the compiler change unpromoted pending a quiet-host
repeat. The run is not a C comparison or an official Embench score. Raw runs
and all 80 sanitized observations with calculations are in
[`crossdomain-m105-singleuse-inline-m1-abba-20261017`](evidence/crossdomain-m105-singleuse-inline-m1-abba-20261017/README.md).

## Statemate repeated vector-shape guard probe (2026-10-17)

Static inspection found two repeated compare/branch pairs at the entry to the
private Statemate body. An image-only diagnostic replaced the four instructions
with NOPs while retaining descriptor loads, fuel reservation, and all state
updates. The registered Statemate input passed exactness for both images and
all 20 ABBA samples: result 1, benchmark fuel 20,159,447,042, verify fuel 66,
and identical 169-item arena accounting. The five block candidate/base ratios
had a median of 0.9716, with one large outlier at 0.9250. Load1 ranged from
25.77 to 33.50.

This estimates the upside for those checks on the registered vector input.
The hand-patched image does not establish a general compiler transformation or
safe behavior for other vector shapes. The next compiler experiment must prove
the 169-element invariant through the repeated `vector-assoc!` path, hoist the
guard while retaining the fallback, and pass exactness before timing. Raw
records are in
[`crossdomain-m105-statemate-guard-nop-m1-20261017`](evidence/crossdomain-m105-statemate-guard-nop-m1-20261017/README.md).

## Falsify: T2 minimum-vector-length iteration cap (2026-10-17)

A candidate raised `t2-ml-init`'s alternating interprocedural analysis cap
from 64 to 512 passes, testing whether it could prove Statemate's 169-element
vector shape and remove the repeated body-entry length guard. The candidate
and a 64-pass control differed only in that cutoff literal. Each reached a
selfhost fixed point, and both rebuilt all 19 pinned ports.

The two compilers produced identical native images, kseeds, and export tables
for all 19 ports. Statemate's image did not change. The larger cap therefore
did not reach the registered workload code and does not explain its runtime
checks or the M104 Kotoba/C advantage. No new exactness or timing run was
needed. The compiler-source hypothesis is rejected for these inputs; preserve
the cap change out of the adopted compiler. Hashes and per-workload comparison
are in
[`crossdomain-m105-t2-minlength-cap-20261017`](evidence/crossdomain-m105-t2-minlength-cap-20261017/README.md).
