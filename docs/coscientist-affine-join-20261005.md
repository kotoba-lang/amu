# Constants across joins: native proof succeeds, performance promotion fails

The candidate is not promoted. On fresh original-workload timing, Picojpeg is
4.37% shorter, ratio1.045654<1.05, and the mean gap is below summed standard
deviations. Qualified product source at `33303be5a` stays unchanged; source HEAD
before this experiment is `83fa3b30b`. C-level-or-better remains unachieved.
This follows the [two rejected affine-writer variants](coscientist-affine-writer-20261005.md).

## A falsified admission assumption

A first native prototype selects move/add/shifted-add when affine index arguments
are proven0/1/positive powers of two. Four compiler generations are identical
(810096B), but a diagnostic native observer on all19 canonical sources reports
9 eligible affine writers and **zero eligible index specializations**. Source
literals alone do not establish usable compiler descriptors. Every IDCT write
has a branch in its value argument; `gn-op-label` conservatively materializes
and forgets constant descriptors. The other18 programs have no affine writers.
Reject this zero-admission hypothesis before timing or full semantic proof.
The native compiler build is not a claim that its guest semantics are qualified.

## The distinct implemented hypothesis

The second isolated Kotoba backend recovers a constant only by an exact bounded
SIR proof. It finds the nearest CONST for the target temporary while every
intervening writer starts above that temporary. It then scans the entire current
function's branches and rejects **every** edge entering the candidate span from
outside, including later backedges. Thus the CONST dominates all admitted
paths and no admitted path changes the value. Unknown span operations, malformed
missing label positions, conflicting writes, function boundaries and exhausted
work bounds refuse recovery. Input SIR retains its existing checked unique-label
contract. Bounds are256 instructions for origin and4096 for function search and
edge scan; proof failure retains the original runtime operand.

Only0/1/positive powers2^1..2^62 are recovered. Their wrapping affine index uses
move, ADD or shifted-register ADD; the latter equals base+operand*2^p modulo2^64.
Actual branches, value computations, effects, fuel, checks and partial writes
still execute in their original order. Existing exact closed callee/body proof,
open-import refusal, retained nonleaf caller/frame and t<=2 admission remain.
Recognition uses no benchmark/function names. This is a one-off new compiler
algorithm authoring exception to mechanical AST refactoring; no product edits.

Native observation now finds **4/9** specialized sites in Picojpeg. Diagnostic
and quiet compilers emit byte-identical guest code for all19 programs. This
uses exact SIR content proofs, not linked KIR DefCIDs or computation-result
memoization. Every timed body executes freshly.

## Native evidence and its boundaries

Generations1/2/3/4:812152B, SHA256
`be8d169c2a0178522b1770ac83f45e40839b9ac5b63a06db71c4b8224493aa8f`.
All19 original matched programs preserve representative results, exact fuel
consumption and exhaustion exits. All8192 Picojpeg workspace cells match across
one/two bodies. Other18 guest binaries are identical to the qualified product.
Picojpeg is48672B vs47880B in the product; source is unchanged.

- 421 fixtures,14043 actual native hand-derived executions pass; real/test
  emitted layouts are identical.
- 50 positive/refusal constant-recovery cases are checked in native real/test
  generators. Cases include both value branches, changes on one arm, an incoming
  path bypassing CONST, later backedges, origin bounds and unknown RES2 writes.
- Two additional independent native probes prove that function search and edge
  scan each refuse at4096, while their nearest origin is within256. The original
  long-span control reaches the origin limit; it does not establish these other
  limits on its own.
- All44 joined operand callers are instruction-decoded: known zero/one/powers
  select exact move/add/shift fields; noneligible constants keep generic MADD.
- 22152 full supervisor/partial-arena comparisons preserve reports, fuel,
  signals and cells. They cover original admitted affine patterns and both
  branches for22 joined fixed-operand callers, all13 wrapping/index geometries,
  four signed extremes and all fuel boundaries. This is not every possible
  cross-product of all421 fixtures.
- 23 refused callers are independently instruction-identical to the previously
  staged candidate after BL relocation/fixture normalization, composing with its
 36855 full comparisons. Stack-home x0/x16/x17 loads are explicitly decoded.
- Actual signature-compatible allocating import substitutions pass15 ordinary
  and18 joined cases. Open imports retain calls; intentionally closed controls
  differ or trap. Diagnostic x7-clobber loaders do not enter timing.

Diagnostic repairs are preserved. The generated observer first referenced PM-1;
then it probed the first zero-index write rather than the second joined write;
finally it assumed a rejected descriptor's unused payload was zero. Refusal is
correctly checked by its tag; unused payload can be stale. The hand-oracle
receipt was reconstructed from the terminal14043/14043 result after the probe
failure. Identical emitted code/function tables and identical run-table hash
are required before composing that actual execution evidence with repaired
reports; no repeated14043 executions are claimed. An additional bounds probe
had one excess output-expression parenthesis, also repaired. These changes do
not alter compiler or canonical guest bytes.

## Fresh timing and independent audit

Zebulun Apple M4, unchanged original C comparator and pinned native runner,
30 rotating product/candidate/C triples in30 attempts. Target300ms, minimum50ms,
load<=4, background idle>=90%, RSD<=10%. All raw rows/calibrations remain.
Promotion requires ratio>=1.05 and mean gap>summed SD; no thresholds are relaxed.

| Picojpeg arm | Mean us/body | RSD |
| --- | ---: | ---: |
| Qualified product, freshly measured | 207.516 | 2.54% |
| Isolated constant-join candidate | 198.455 | 3.33% |
| Original C, freshly measured | 10.781 | 0.95% |

Ratio1.045654, time reduction4.366%, gap9.060us<sum SD11.882us. Reject promotion
on both criteria. Candidate/C18.407x. Independent audit recomputes statistics,
order, complete-triple/environment admission and binary pins. This is an aligned
custom whole-body comparison, not an official score or a suite geometric mean.
No same-byte resampling is used to seek a pass. Measurement starts after native
hand-oracle/dominance preflight while fuller state proof runs independently;
original measurement-only metadata prohibits promotion and is retained. Full
state proof finishes afterwards. No integrated rebuilding/release gates are
claimed for this rejected candidate.

## Next prospective hypothesis

Specialize closed callees for immutable scalar arguments, retaining original
call boundaries, frame classification, charges and export identities. Source
and native SIR show two literal false/true calls of the IDCT pass; its mode flows
through a loop to the lane transform and repeated conditionals. A useful proof
must handle the parameter's unchanged loop reassignment; treating every parameter
as immutable or guessing from names is unsound. First count actual admissible
sites on all19 originals. Bound specialization growth, deterministically key
variants by exact body/dependency proof + static arguments + compiler/ABI/profile,
and refuse open imports or unproved writes. Current SIR identities must not be
reported as linked KIR DefCIDs. This hypothesis is registered only, not implemented
or measured. Retain original workloads and prospectively fixed timing rules;
full native/gate/integrated/corpus proof is mandatory before product promotion.

Evidence: [summary](evidence/coscientist-affine-join-20261005/summary.json),
[zero-admission predecessor](evidence/coscientist-affine-join-20261005/zero-admission.tgz),
[native proof and repairs](evidence/coscientist-affine-join-20261005/native-proof.tgz),
[raw timing](evidence/coscientist-affine-join-20261005/timing.tgz),
[next hypothesis](evidence/coscientist-affine-join-20261005/next-hypothesis.json).
