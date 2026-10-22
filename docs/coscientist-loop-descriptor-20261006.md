# Dynamic-key loop descriptor reuse: all17 timing candidates rejected

All17 changed original workload guests were freshly compared with current product
and pinned C. None passes the unchanged prospective improvement rule. QR is1.63%
shorter; EDN is6.75% slower and matmult5.05% slower. Reject the complete prototype.
Product source remains qualified affine-reader HEAD `6c9daa70bb36a76851960058174c22d2107729ac`
(the report-only commit after the algorithm). C-or-better across all19 original
aligned workloads remains unachieved. These are native body comparisons,
**not official Embench scores**.

[Summary](evidence/coscientist-loop-descriptor-20261006/summary.json),
[all17 independent timing audits](evidence/coscientist-loop-descriptor-20261006/timing-summary.json),
[archive checksums](evidence/coscientist-loop-descriptor-20261006/checksums.sha256).
The census, native proof and timing archives retain exact executed inputs,
initial authoring/diagnostic failures, complete state receipts, compiled machines,
source/spec/C/runner pins and raw accepted/rejected timing rows.

## Evidence-led hypothesis

The previous [straight-line validity experiment](coscientist-vector-validity-20261006.md)
admitted only3 WikiSort sites and failed timing. A native observer now prints
all actual original19 SIR, backedges, read provenance and frame/register ownership.
Its all19 guest machines are exactly current-product bytes. Census finds loop
reads with available scratch registers in17 workloads. Those are static counts,
not time shares; broad applicability alone does not establish an improvement.

Candidate caches vector length and data base in free x3/x4 with a positive handle
key in x5. A function must have a vector read and a backward branch within a
bounded8192-record scan, and be nonleaf or a leaf with<=3 local slots. It does not
reserve registers already assigned to locals or change prescan/frame allocation.
Every read checks nonzero/same key. A miss performs the original handle validation
at the original access before caching descriptor metadata. Every access retains
its unsigned index/length trap and fresh item load; no element/result caching.

Dynamic equality covers handle changes and branch joins. Original entry dominates
key initialization. Actual returning direct/indirect guest calls and all runtime
BLR sites clear the key, including the Unicode slow path; its old DONE label
lands on the clear instruction. Proven inlined operations can retain the key.
Item writes are observed by subsequent loads. Unknown calls can change metadata,
so reuse never crosses them. Neither content identity nor an opaque handle by
itself proves immutable execution state. No ABI, x18, policy or capability grant
changes. The native DefCID/result cache remains unconnected.

Actual native observation admits272 cached read sites across17 guests. Two guests,
aha-mont64 and crc32, are byte-identical to current product. An independent machine
word audit verifies every complete cache template, fixed miss/hit/index branch
landing and disjoint operand/destination/scratch registers. Observer and quiet
target bytes are identical for all19. No workload/function names appear in the
algorithm. Canonical benchmark sources remain unchanged.

## Native proof

- Generations2/3/4 byte-match,823040B, SHA256
  `9643a3b7fc80e7c57a42a41f08bc953aa2c6b25cf1af77fa48a303359a39a1ec`.
  Generation1, emitted by the previous generator, differs and is retained.
- All19 canonical result/exact-fuel/exhaustion comparisons agree with current product.
- Fresh original342-fixture regression passes4196/4196 actual native executions,
  without touching the committed golden. Test/real code, literals and FN offsets
  agree modulo2 explicit padding bytes.
- New388-fixture generator test/real layouts match.36 callers each have two actual
  cache guard sites.2304 unique native hand-state comparisons cover two-iteration
  loops, key switching/reassignment, conditional first-read bypass, same-local
  writes, old/new append handles, live homes and signed/wrapping extremes.
-900 more hand-state cases prove3-slot leaf admission and4–7-slot refusal, including
  invalid raw handles, empty loops and private leaf-fuel publication. Actual
  leaf instructions show the cache only in the3-slot leaf.
-72 live-cache open-import comparisons execute a same-signature fuel-charging,
  allocating replacement returning77 and clobbering x7 in the diagnostic allocator.
  Open baseline/candidate agree, and closed controls differ. Allocations, every
  item, result/trap and fuel have independent hand expectations.
-24 actual side-effect cases cover ASCII fast path, Unicode slow path, stdout
  capability and7-argument indirect-call scratch clobber. Output count/result,
  vectors/items/fuel are checked and complete supervisor reports agree.
-12 resource-limit cases preserve partial append copies, reserved zero slack and
  allocation writes when the descriptor table is full; item-budget failures retain
  the original items. Hand expectations and complete baseline/candidate states agree.

Those3312 full-state comparisons and4196 regressions were sealed before timing.
A further209 comparisons, completed while timing ran, compare all original19 final
vector items and complete supervisor state at n0/1/2 and eight partial-fuel budgets.
Full-fuel result and exact fuel also match the canonical receipts. The diagnostic
allocator clobbers x7. This is additional post-start evidence, not retroactively
part of the original timing preflight.

Authoring corrections are explicit and archived: the final-function instruction
end must exclude literal bytes; interior conj reserves a doubled growth region,
including zero slack, rather than just length+1; FADDR fixture operands require
numeric FN IDs. The small diagnostic supervisor's512-item output guard was
expanded to the actual item maximum for the additional whole-workload observation.
No compiler change, expectation weakening or measured-runner change followed
these corrections. The initial census also exhausted its observation-only vector
table; larger diagnostic allocation limits completed the same observer.

This is one-off new Kotoba algorithm/test authoring, outside existing mechanical
AST refactor rules. Product gates/integrated rebuilding are not rerun after
performance rejection. The preceding qualified product remains current; no
launcher switch, rung update, wire20 grant or100% selfhost claim occurs.

## Fresh quiet comparison

Apple M4 zebulun, pinned original source/C/runner and rotating3-arm order.
30 accepted triples per guest,510 accepted in total, 527 attempts. The unchanged
rules require load<=4, background idle>=90%, adequate interval, relative SD<=10%,
ratio>=1.05 and mean gap greater than summed SD. All17 finish with stable samples,
but none qualifies. Row admission/order/statistics and actual source/native/offset/
compiler/C/runner/spec/preflight pins are independently audited. Identical code is
not retimed to seek a pass. Unchanged2 guests are not freshly retimed; no new
all19 aggregate score is reported.

| Workload | Product ns/body | Candidate ns/body | C ns/body | Shorter time | Decision |
|---|---:|---:|---:|---:|---|
|depthconv|120.63|120.94|34.15|-0.26%|Reject|
|edn|11453.06|12225.59|751.18|-6.75%|Reject|
|huffbench|54630.59|54660.20|7348.40|-0.05%|Reject|
|matmult-int|22588.64|23729.03|948.19|-5.05%|Reject|
|md5sum|12584.13|12876.42|2507.42|-2.32%|Reject|
|nettle-aes|25706.75|26148.42|1413.25|-1.72%|Reject|
|nettle-sha256|2790.83|2811.30|220.96|-0.73%|Reject|
|nsichneu|712.80|711.65|79.21|0.16%|Reject|
|picojpeg|215947.99|215231.70|11193.82|0.33%|Reject|
|qrduino|282558.01|277955.84|22211.06|1.63%|Reject|
|sglib-combined|41249.82|42225.58|5815.04|-2.37%|Reject|
|slre|7901.62|7836.73|1046.95|0.82%|Reject|
|statemate|763.81|764.21|31.63|-0.05%|Reject|
|tarfind|13949.56|14473.40|1006.37|-3.76%|Reject|
|ud|546.13|551.27|54.13|-0.94%|Reject|
|wikisort|185553.35|186056.07|15181.83|-0.27%|Reject|
|xgboost|1367452.53|1385626.79|183909.88|-1.33%|Reject|

## Next registered hypothesis: the high-temp C boundary

The actual SIR reveals one matmult vector read at temporary6 and five SHA256
reads at temporaries>=6. `gn-inl` admits vector-at only at t<=5; other reads
execute the real C runtime helper. In matmult's inner loop, a t5 read can create
this cache, then a t6 read immediately performs a C call and invalidates it.
This is an observed generated-code mechanism, not a measured time attribution.

The [next hypothesis](evidence/coscientist-loop-descriptor-20261006/next-hypothesis.json)
is to compose those high-temp reads inside the retained original nonleaf frame:
keep the original live-home saves, load vector/index into proven-free x0/x1,
restore x7, perform original handle/index checks and load, and use original result
placement. Prescan remains unchanged. No loop cache or descriptor hoisting.
Native raw-handle/high-depth/live-home/fuel/SIGILL/import/resource proofs and the
same all19 admission/fresh-timing/gates/integration requirements precede promotion.
This next algorithm is registered, not implemented or measured.
