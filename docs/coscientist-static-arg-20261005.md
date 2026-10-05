# Closed scalar arguments: native specialization, rejected timing

No product promotion. All five changed original workloads fail both prospective
performance criteria: baseline/candidate >=1.05 and mean gap greater than summed
standard deviations. Qualified product backend remains at `33303be5a`; the
experiment starts from source HEAD `4f92e52f2`. C-level-or-better is unachieved.

## Identity and the tested hypothesis

The current definition identity is content addressing of normalized checked KIR,
types/interfaces, effects, dependencies and semantic profiles. A computation
recipe would additionally seal immutable arguments and explicit handler/state
snapshots. Native compiled specialization also requires compiler identity, target,
context/fuel ABI and packaging/relocation contracts. These are different reuse
keys; a content hash alone does not remove executed work.

The native seed lowers to SIR and writes nil KIR/definition metadata. This
prototype does not introduce linked DefCIDs or computation-result caching.
It tests a way to reduce freshly executed work: private variants for one proven
static scalar bit argument, including propagation through unchanged loop
reassignments. Original benchmark sources stay unchanged. Recognition uses no
benchmark or function names. This is one-off authoring of a new Kotoba compiler
algorithm, not a mechanical refactor; product source is not edited.

Caller arguments must be exact CONST0/1 or a caller variant's invariant parameter.
The nearest origin scan rejects intervening lower/equal temporary writes. A
whole-function branch scan rejects incoming edges bypassing the origin, including
backedges. Each write to the callee parameter must be an unchanged copy from that
same parameter, with no intervening writes and complete dominance. Unknown writes,
two-result operations and open replaceable callees refuse specialization.

Private cloned SIR retains original instructions, prescan and argument transport;
only function identities and globally unique labels are relocated. Emission of
the proven invariant LGET becomes CONST, enabling existing constant branch folding.
All original calls, frames, charges and effects remain. A deterministic table
keys variants by original callee/slot/bit within this exact module. Bounds are
16 variants,4096 copied instructions total,512 instructions per body,256 origin
steps,4096 function/edge scan steps,64 slots and16 temporaries. This table is not
a cross-module content-addressed artifact cache.

## Native evidence and unresolved qualification

After repairing regeneration, native generations2/3/4 are identical:822464B,
SHA256 `6191e5b3a4417a983f84c47b99ed0abdff2cbaafca58ffb636005697550edd82`.
Generation1 is820752B and differs; do not claim all four identical.

Native admission finds11 variants across five original programs: MD5(2),SHA-256(2),
Picojpeg(4),sglib(2),xgboost(1). The other14 guest binaries are product-identical.
All19 programs preserve representative results, exact fuel and exhaustion exits.
All8192 Picojpeg workspace cells match after one/two bodies. Diagnostic admission
and frame compilers produce exactly the quiet candidate's guest bytes on all19.
Every variant's parameters, slots, depth, frame bytes, callee-saved count, leaf
classification and outgoing area match its original callee's prescan.

301 fixtures pass4233 native hand-derived executions, including both modes,
dynamic nonzero modes, signed/wrapping extremes, unchanged/changed loop assignments,
bypassing incoming paths and all selected fuel boundaries. Real/test code,
literals and function offsets match; the test-only layout has2 trailing zero
padding bytes, so complete blob equality is not claimed.

Code review found that the first prototype left rewritten CALLs/private clones
in the same M across regeneration, potentially bypassing a newly open import.
Private owned-G metadata now restores original CALLs and FN/SIR/LABEL fills
before installing new import boundaries. Closed-then-open generation equals
fresh-open machine bytes. Actual signature-compatible substitutions allocate,
charge fuel and return77 while the diagnostic allocator clobbers x7:180 native
full-report/arena/trap comparisons pass; closed high-fuel controls differ.
The initial prototype and diagnostic parenthesis failure are preserved.

Private header101 ownership follows the normal project reset, which clears
headers0..255 and the used heap. Arbitrary appending to M after generation is
not qualified. Clone/capacity fallback probes and a complete expanded-fixture
supervisor/partial-state proof were not completed. Measurement-only preflight
forbids promotion. Because timing rejects the hypothesis, no committed-source
ERR/G1-G5, integrated rebuilding or corpus qualification is claimed.

## Fresh original-workload measurements

Zebulun Apple M4; pinned native runner and unchanged original C comparators.
Every changed guest gets30 accepted rotating product/candidate/C triples.
MD5/Picojpeg/xgboost need30 attempts;SHA-256/sglib need31. Rejected complete
triples remain in the raw data. Target300ms, minimum50ms, load<=4, background idle>=90%, RSD<=10%.
All arms execute freshly. An independent audit recomputes raw row admission,
rotation, statistics and artifact pins. These are custom aligned whole-body
comparisons, not official Embench scores or a newly measured full-suite mean.

| Workload | Product us/body | Candidate us/body | C us/body | Product/candidate | Candidate/C |
| --- | ---: | ---: | ---: | ---: | ---: |
| md5sum | 13.743 | 13.598 | 2.493 | 1.010694 | 5.454 |
| nettle-sha256 | 2.863 | 2.869 | 0.215 | 0.997833 | 13.331 |
| picojpeg | 211.676 | 207.717 | 11.042 | 1.019060 | 18.811 |
| sglib-combined | 40.925 | 40.586 | 5.806 | 1.008343 | 6.990 |
| xgboost | 1340.095 | 1349.074 | 184.150 | 0.993345 | 7.326 |

Picojpeg is1.87% shorter, while its3.959us mean gap is below10.414us summed SD.
Every changed workload fails both criteria. Code increases:MD5/SHA each316B,
Picojpeg4140B,sglib1492B,xgboost592B. Do not repeat identical-byte timing to seek
a pass. Static admission and branch folding do not establish a useful dynamic
cost reduction. All source/proof/raw timing evidence is retained.

## Next registered hypothesis

Obtain a native dynamic cost census of mode tests, direct helper calls, checked
vector operations and repeated runtime dispatch across the original workloads.
Select the measured hottest removable cost before further specialization.
Separately measure cold/warm content-addressed compilation and dependency changes;
warm result reuse must not count as fresh Embench execution. This next hypothesis
is registered only, not implemented or measured.

Evidence: [summary](evidence/coscientist-static-arg-20261005/summary.json),
[native prototype and proof](evidence/coscientist-static-arg-20261005/native-proof.tgz),
[all raw timing](evidence/coscientist-static-arg-20261005/timing.tgz),
[independent audit](evidence/coscientist-static-arg-20261005/timing-audit.json),
[next hypothesis](evidence/coscientist-static-arg-20261005/next-hypothesis.json).
