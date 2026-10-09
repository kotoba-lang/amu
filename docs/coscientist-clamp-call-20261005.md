# Signed-clamp composition: native execution and integrated selfhost proof

Qualified native optimization: Picojpeg execution is5.48% shorter
than the previous context-preserving-call product. Source commit `33303be5a`.
C is still19.30101x faster in this aligned custom time comparison.
The goal of C-level-or-better on original workloads remains unachieved.

## Hypothesis and implementation

Exact checked SIR: one natural argument, optional entry FUEL/LABELs, an existing
width1..32 sign-extension helper, a saved scalar, nested signed comparisons
returning lower/upper/original values, exact distinct labels and RET/END.
Lower<=upper; no extra operations, allocation, capabilities or result pairs.
Both clamp body and helper must be closed against link-time replacement.
Any unproved shape uses the original path. Selection has no source/function or
benchmark-name rules. This is one-off compiler algorithm authoring rather than
mechanical refactoring; source and tests are Kotoba on the product route.

Inline the signed bitfield extension and two signed CSELs into the existing
nonleaf caller. Keep original caller classification, frame and live-temp handling.
The original callee is a leaf after the sign helper's existing exact lowering;
reproduce its optional entry/helper charges in x8. Exhaustion publishes zero,
return publishes remaining x8, and all original decrement boundaries remain.
No guest work, fuel, trap or vector validation is removed. No result memoization
or definition-CID cache is introduced. A stable body proof cannot cross an open
import, as the previous [context proof](coscientist-context-call-20261005.md) showed.

## Native semantic proof

Producer: previous qualified native seed803,416 bytes, SHA-256
`09b3daf75b1f1e7997e6c68d9a758d31d076d254756fa42637eae25bd0e0f0fb`.
Native generations1/2/3/4 reproduce806,792 bytes, SHA-256
`a3e1803d92a446862d773a18d10b5023163fd9a0a3146bc7aae1c02aa32d24c7`,
entry offset0. This is a native fixedpoint, not build-time performance evidence.

All19 original canonical sources preserve results/exactfuel at0/1/2/17/32 bodies
and exhaustion behavior. All8,192 Picojpeg workspace cells after1/2 bodies match.
Only Picojpeg guest bytes change:47,660 ->47,880 bytes. The other18 guest binaries
are byte identical to the previous qualified product and are not retimed here.

The expanded native test has287 fixtures and3,625 executions, including hand-derived
signed/clamped results, lowfuel and index traps. Independently native-built test
and real42-layout emit identical code (padding excepted). Full8,800 supervisor
comparisons cover width1/8/16/32, all four combinations of original fuel charges,
equal/negative/extreme/reversed bounds, signed input extremes, valid and invalid
vector indices, and live temps0/3/6/7/8 (including stack homes). An allocator that
clobbers caller-saved x7 forces real context restoration before the optimized code.
Full reports and owned vector arenas match, not merely final result values.

Machine audits verify35 admitted caller neighborhoods replace one real clamp call
with exactly two CSELs; five reversed-bound cases retain the real call. A separate
audit verifies exact original x8 charge counts and one return publication iff
charged. The original callee bodies still exist; this is call-site optimization.

Fifteen imported-body substitutions replace the clamp entry with a branch to a
signature-compatible allocating scalar function returning17. Open-boundary code
retains calls and matches the baseline, across register and stack temp cases.
A deliberately closed-body control inlines the old body and differs. The diagnostic
never participates in timing. Permanent generated tests also refuse an open clamp
or its open sign helper, while the same closed composition admits.
Standalone proof uses frozen pre-promotion generator/backend snapshots (tool root
rebased only) so replay cannot accidentally compare the new emitter with itself.

## Fresh quiet comparison with unchanged C

zebulun Apple M4, pinned original runner/C/workload.30 accepted rotating triples
from31 attempts; all rejected samples and calibrations retained.
Target300ms, minimum50ms, load<=4, estimated background idle>=90%, RSD<=10%,
fixed90-attempt ceiling. Acceptance registered before measurement: >=1.05x and
mean gap>sum of standard deviations, with no separated changed-workload regression.

| Arm | Mean us/body | RSD |
| --- | ---: | ---: |
| Previous native product | 220.524128 | 3.00% |
| Signed-clamp native product | 208.440353 | 2.17% |
| Original C | 10.799451 | 0.97% |

Product/candidate=1.05797234x; saved time=5.48%.
Gap12.083775us exceeds summed SD11.142774us.
Candidate/C=19.30101458x. Independent audit recomputes every quiet
condition, rotation, mean, SD and acceptance from the raw rows and pinned bytes.
These are freshly executed complete-body timings, not official Embench scores,
not formal perfgate qualification and not evidence of C-or-better performance.
Compiler build host load is not benchmark timing.

## Actual integrated product qualification

The committed source builds the integrated command, then that command compiles
its frontend/launcher source for generations2/3. All162 objects (117 frontend),
container, native code and command are byte identical across all three generations.
Command:6,076,152 bytes, SHA-256
`5b18cc4f3cdf52e6ae3b3e2dd5e13f4033f007b5d725614a987f7bef9cf3bebe`.
Every canonical source checks and compiles through this actual integrated command
into the exact measured guest binary and entry offset.

All391 check classifications/exits,391 compile outcomes and891 export rows match
the previous qualified image case by case. Existing accepted-behavior/export
mismatches/refusals remain; this is no100% selfhost claim. ERR/G1/G2/G3/G4/G5 pass,
including84 byte-identical generation containers and no seed-started program inG5.
This is six selected gates, not the full release set. The bootstrap PRODUCT
inventory stays unchanged; Node launcher/rung pins and process-spawn grants remain
unchanged. External input source snapshots remain local; their hashes are archived.

[Summary](evidence/coscientist-clamp-call-20261005/summary.json),
[native proof](evidence/coscientist-clamp-call-20261005/native-proof.tgz),
[raw timing](evidence/coscientist-clamp-call-20261005/timing.tgz),
[independent audit](evidence/coscientist-clamp-call-20261005/timing-audit.json),
[integrated proof](evidence/coscientist-clamp-call-20261005/integrated-proof.tgz).

## Next registered hypothesis

The [next hypothesis](evidence/coscientist-clamp-call-20261005/next-hypothesis.json)
is a generic five-argument affine indexed signed vector-write composition,
preserving original checked access, leaf fuel transaction and partial writes.
It is registered, not implemented or measured. Fresh SIR/charge inspection and
full all19/correctness/timing/integrated criteria are required before promotion.
