# Native dominated same-local vector reads

Latest qualified experiment: [guarded whole-dot expansion with direct return](coscientist-dot-unroll-return-20261006.md). Fresh30 paired triples qualify67.814724% less original matmult body time (3.107011x); native tests/gates and committed-source3gen integration pass. C remains4.680001x faster; all19 C-or-better remains open. Earlier experiments below retain their historical decisions.

Adopted on the research branch: the original full matmult body is18.494929%
shorter in a fresh quiet comparison; other18 guest binaries remain identical.
The committed-source integrated image reproduces the measured machines and is
byte-identical across3 generations. The all19 C-or-better goal remains unachieved:
matmult still takes14.3349x C time. These are aligned body measurements, not an
official Embench score or a newly measured full-suite aggregate.

[Summary](evidence/coscientist-same-local-read-20261006/summary.json),
[next hypothesis](evidence/coscientist-same-local-read-20261006/next-hypothesis.json),
[checksums](evidence/coscientist-same-local-read-20261006/checksums.sha256).
The archives preserve prospective registration, source/prototype, native images,
hand oracles/state observations, permanent prefix audit, raw measurements,
gates including the initial resource-scope failure, and integrated inputs/results.

## Mechanism and identity

The previous [dynamic descriptor reuse](coscientist-identity-and-reuse-20261006.md)
was rejected: it actually hit, but a3.12% shorter mean did not exceed either
promotion threshold. This experiment starts from the qualified direct affine-read
product and adds a distinct guarded path. It is not another timing of the same
machine.

Original nonleaf functions must contain an actual high-depth vector read within
a validated same-function loop. The first read retains the positive/equal dynamic
handle guard, original handle validation on a miss, and descriptor capture in
x3/x4. A later affine read uses only an index check and current item load when its
source is proved to be the same stable local on the same straight-line path.
Compile-time witness state13 is named; dynamic mode is8; existing14 remains the
scalar-tree flag. Runtime cache key is x5; it starts empty and returning calls
invalidate it.

Only constants, local loads and integer scalar arithmetic preserve the static
witness. A local assignment to the handle invalidates it; so does a result written
directly to that local by `gn-fin` while skipping its coalesced `LSET`. Labels,
branches, comparisons (including fused branches), calls, runtime operations,
capabilities, allocations, fuel and unknown forms reset the static witness.
Unavailable source identity refuses comparison omission. Index checks and fresh
item loads remain; current contents may change. No new frame/local allocation,
ABI, capability grant or resource budget is introduced.

This is exact native SIR proof, not connected typed-KIR DefCID caching or
computation-result memoization. Current definition identity remains content
addressing of normalized implementations and dependencies. Reusable optimization
proofs may later be sealed with definition/compiler/target/effect/resource identity
once the native bridge exists. Every measured original body is freshly executed.

## Native proof before measurement

Four compiler generations are816,568 B and SHA-256
`1171613dde77c12aee7b07273bc337b950d1f3764307a1dde0239b0cd57085dc`.
The previous qualified baseline is814,312 B,
`a9cceee002d6365f3e68b740321b9e362635121bd575b613ac28d4b3da93372e`.
All original19 results, exact fuel and fuel traps match. Existing434 fixtures and
9,339 native executions pass with unchanged expectations before timing.

Additional4,085 full-state comparisons:

- 1,848 paired affine-read comparisons across33 independently authored cases:
  same/different local, alias source, current-content writes, reassignment,
  coalesced read result and arithmetic local writes,7-argument clobbering call,
  allocation, fuel, join, i64 extremes/wrap and invalid first/second index.
- 1,920 loop-key/branch/mutation/call/allocation comparisons.
- 72 actual allocating open-import replacements; closed controls differ.
- 24 ASCII/Unicode, output and indirect-call states.
- 12 resource-exhaustion/partial-write states.
- 209 full/partial-fuel original19 states.

Real and independent test-only layouts agree. Actual native observation sees only
originalmatmult FN5 affected: two reads of source local1, output x14/x15, original
192B frame and5 allocated callee locals. First frame/parameter words and fuel words
remain exact; x5 initialization is the only prologue addition. First descriptor
read has its19-word dynamic guard; the later read is exactly4 words (index cmp,
conditional branch, trap, item load). The other18 guests are exact baseline bytes.
Diagnostic and quiet compilers produce identical target bytes/offsets for all19.

The matmult guest is10,256 B; its SHA-256 and all source/runner/C/spec pins are in
the immutable summary and timing manifests. It differs from both the qualified
baseline and the rejected dynamic-cache machine.

## Fresh timing and decision

Authorized zebulun, Apple M4; unchanged canonical source, C comparator and runner.
30 rotating product/candidate/C triples accepted out of31 attempts. The same
pre-registered load<=4, background idle>=90%, minimum50ms interval, per-arm
RSD<=10%, speedup>=1.05 and gap greater than summed SD apply. Calibration and
rejected rows are retained. Raw rows and frozen pins are independently audited.

| Original matmult body | Mean us | SD us |
| --- | ---: | ---: |
| Previous qualified product |16.211332 |0.908238 |
| Same-local proof candidate |13.213058 |0.881241 |
| Unchanged C |0.921740 |0.009656 |

Speedup1.226918;18.494929% shorter. Gap2.998274us exceeds summed SD1.789479us.
**Qualifies**, with product validation below completed before adoption. Candidate/C
is14.334906. No repeated identical-machine timing or cached result is counted.

## Product validation and lineage

Source implementation commit: `03a83ad7768ca9f6aa592f9dbffdfb038d485e42`.
The new algorithm and independent hand fixtures are one-off authoring without an
existing mechanical AST refactor rule; generated unit files use the authoritative
fixture generator.

The permanent table is470 fixtures /11,187 native executions. Original434/9,339
prefixes remain exact; new33 cases,2 helper functions and a cold sentinel append
1,848 runs. The high-level oracle agrees with independent full-state proof.
Real/test code, literals and function offsets agree. Normal unit output equals
independent test layout plus `exit=0`; only after semantic/layout validation is
the golden updated. Normal native unit passes4,039 lines.

ERR/G1-G5 pass using native generations2/3/4 mapped to gate compiler0/1/2, with
current unity hash recorded; gate seed0 is not bootstrap stage0. Initial G1 failed
E3 because its existing external port checkout was outside the supplied resource
scope. Only G1 was rerun after including the authorized workspace read scope.
G2's existing1 refusal and G3 r6m refusal expectations stay unchanged. The
bootstrap-boundary inventory is exact before/after; no new product host fallback.

From committed source and archived hash-pinned frontend/twin inputs,3 generations
of162 objects (117 frontend objects), container, native code and command reproduce
byte-identically. Integrated `g3/amu` is6,092,664 B, SHA-256
`1ec54e27322ed98a5e6fc7280f16932f502bebf0c51476983ae3f78b2b1f66ca`.
Its check/compile/extract commands yield all19 exact measured guests and offsets.

391 check classifications,391 compile classifications and891 export rows equal
the previous qualified product. All391 normalized full check messages and1,780
native output/status files agree. Existing totals remain:358 check accepts/33
refusals;300 compile behavior matches,27 Amu-only accepts,12 Amu-only refusals,
3 differing accepted behaviors,49 shared refusals;875 same exports,15 existing
closure-handle differences,0 timeouts and1 missing. Stage0 is the oracle only.
Default rung record, `bin/amu` bootstrap selection and wire20 grants are unchanged.
This is branch-qualified performance progress, not100% release readiness or main
integration.

## Next prospective experiment

The [fresh current native census](coscientist-loop-composition-census-20261006.md)
now completes the observation step below with all19 diagnostic/quiet bytes and
offsets equal. It audits the actual loop and unchanged C instructions and checks
a prospective guard model. Native loop expansion remains unimplemented/unmeasured.

Freshly observe complete current native SIR and actual emitted loop instructions,
without overwriting the now-live state13 or existing14. Verify all19 diagnostic
bytes/offsets before attributing costs; inspect the pinned C comparator separately.
Then test an exact guarded, bounded, read-only affine multiply-accumulate loop
composition to reduce per-iteration argument shuffles/checks/fuel traffic.
Insufficient fuel, invalid/unproved ranges/identity and unknown effects take the
original path. Zero-trip must preserve unused invalid-handle behavior; all i64
wrap, trap, resource and partial-state observations remain required. This follow-up
is registered only, not implemented, measured or qualified.
