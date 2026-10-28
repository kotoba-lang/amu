# Native census and repeated scalar-mask composition

The qualified product change at `501e4cae2` reduces freshly measured MD5 body time
by10.57% and SHA-256 by5.25%. The other17 original aligned workloads retain the
previous product machine bytes. C-level-or-better remains unachieved. These are
aligned native body comparisons, **not official Embench scores**.

Evidence: [summary and receipts](evidence/coscientist-native-census-mask-20261005/summary.json),
[raw timing audit](evidence/coscientist-native-census-mask-20261005/timing-audit.json),
[sealed archive checksums](evidence/coscientist-native-census-mask-20261005/checksums.sha256).
The archives include diagnostic code, native proof programs, negative results,
raw timing rows, source pins, integrated image and corpus comparison receipts.

## Identity and the experiment

Current checked definition identity is content addressing. This optimization uses
exact closed SIR bodies and types, not a connected DefCID cache or a computation
result cache. Immutable implementation knowledge permits removing a proven call
boundary while preserving observable execution. The distinction is developed in
[the content-address report](coscientist-content-address-20261005.md).

After rejected scalar argument specialization, a native dynamic census counted
actual function entries and ordinary runtime-operation lowerings across all19
original programs. All19 n0/n1/n2 structured outcomes match the previous product;
20 independent controls validate the counters. MD5 enters mask32 5184 times per
body, SHA-2561776 times and AES u32 170 times. Wikisort enters value59084 times,
with93139 ordinary vector-at lowerings; Xgboost has888265 ordinary vector-at
lowerings. These are counts, not time shares or complete operation coverage:
fused operations bypass some counted sites. The diagnostic loader and counters
are absent from the timed and product artifacts.

Hypothesis: directly compose an exact closed frameless i64 low-bit-mask leaf.
Recognition requires one i64 argument/result, the exact LGET/CONST/BIN-AND/RET
body, positive contiguous low bits, matching end marker and bounded frame/depth.
Optional entry fuel and labels are handled explicitly. Open replaceable imports,
multiple results, other types/operations/frames and malformed bodies refuse.
Emission uses UBFX, retaining the original caller frame/prescan, argument
transport and the original callee fuel transaction. Allocation, effects, traps
and partial writes cannot be silently skipped.

The first matcher admitted synthetic examples but zero actual sites. Native
metadata exposed frontend entry labels; the generic recognizer was repaired
before timing. The unrestricted candidate then admitted9 MD5 sites,14 SHA sites
and1 AES site. All19 correctness comparisons passed, but AES failed the timing
rule; the unrestricted product candidate was rejected.

The revised hypothesis requires at least two direct scalar call sites under a
16384-record bound. This generic code-growth heuristic contains no workload or
function names. It was registered before the revised native build. MD5/SHA retain
exact previously successful timed source/machine bytes and entry offsets; AES
returns to previous product bytes. The successful fresh timing evidence is
composed by artifact equality, **not resampled to seek a pass**. Every changed
original workload still must meet the original threshold.

## Fresh quiet timing and the rejected arm

Apple M4 host zebulun; rotating product/candidate/C triples,30 accepted each.
MD5 and SHA each required32 attempts, AES30. Admission requires load<=4,
idle>=90%, adequate run duration and relative SD<=10%. Promotion requires
product/candidate>=1.05 and mean gap greater than the summed SDs. Raw rows,
order, statistics and artifact pins were audited independently.

| Workload | Previous product ns/body | Candidate ns/body | C ns/body | Time reduction | Candidate/C | Decision |
|---|---:|---:|---:|---:|---:|---|
| MD5 |13689.37|12241.97|2493.52|10.57%|4.91x|qualified|
| SHA-256 |2903.46|2751.17|217.95|5.25%|12.62x|qualified|
| AES, unrestricted only |25509.20|25084.17|1381.71|1.67%|18.15x|rejected; product bytes restored|

MD5 ratio1.118233: gap1447.40ns exceeds summed SD821.71ns.
SHA ratio1.055353: gap152.29ns exceeds87.03ns.
AES ratio1.016944 fails1.05; gap425.03ns also falls below743.57ns.
No aggregate improvement or official normalized score is claimed.

## Native proof and integration

- Four native seed generations are byte-identical:808824B,
  SHA256 `42b83e2bf088158ef02412d6373cb10b5e39387738ed3be2f314f34e34f249da`.
- The extended407-fixture proof previously executed11582 hand-derived native
  runs. The revised real/test generator emits the exact entire fixture blob and
  function offsets used in those executions; those runs were not repeated.
-4768 full supervisor comparisons likewise compose through exact closed fixture
  blob/offset equality. Signed extremes, live temporaries and low fuel are covered.
-112 allocating open-import comparisons were freshly executed for the revised
  variant. Whole imported-image equality is not claimed: a differently typed
  single-use control changes admission, so those observations are tested directly.
- The permanent generator adds typed mask and refusal controls. Its319 fixtures
  freshly pass3940/3940 native executions, with real/test layout comparison.
- ERR and G1–G5 pass. Initial scratch/external-checkout read-scope failures and
  corrected dependent G1/G4 reruns are retained. Bootstrap inventory is unchanged.
  This is not a claim that all release gates or100% selfhost requirements pass.

The committed source builds a unified image in three byte-identical generations:
162 objects per generation,117 frontend objects. `amu`, `amu.bin` and `amu.kseed`
match across generations. The executable is6076152B with SHA256
`e4105f4be60dbc81f24d2ccc2c4f5cf6c453a5e405cf1b5eb02632e09e8a448e`.
The integrated command compiles all19 canonical programs into exactly the
qualified native guest bytes and entry offsets. External inputs are content
pinned; their full source snapshot remains local, as recorded in the receipt.

Every391-row check outcome,391-row compile outcome and891-row export outcome
matches the previous qualified signed-clamp product, including existing gaps:
check358 accepted/33 refused; compile300 behavior-same,27 Amu-only accepts,
12 Amu-only refusals,3 differing accepted behaviors,49 shared refusals;
exports875 same,15 existing closure-handle differences,0 timeouts,1 missing.
Thus this change preserves prior parity; it does not resolve those gaps.

`bin/amu` remains the Node bootstrap. No rung update, launcher switch or wire20
capability grant accompanies this compiler change. Native guest/self-rebuild
verification does not imply that host build wrappers have no bootstrap tooling.

## Next registered hypothesis

[The next hypothesis](evidence/coscientist-native-census-mask-20261005/next-hypothesis.json)
is generic closed affine-index vector-reader composition, motivated by measured
Wikisort entries. Preserve wrapping arithmetic, original checks/trap order,
callee fuel, caller frame and open-import refusal. It is registered, not
implemented or measured. Larger descriptor/check reuse is a separate unimplemented
track requiring mutation and effect-order proofs. The C performance goal remains
active.
