# Closed affine-index vector reader composition

The qualified product change `271a8bdc1` reduces freshly measured original WikiSort
body time **8.29%**, ratio1.090449. The other18 current product guest binaries are
unchanged. Candidate time remains11.72x C. These are aligned native body comparisons,
**not official Embench scores**; C-level-or-better over all19 original workloads
remains unachieved. The experiment began October5 and finished October6.

Evidence: [qualification summary](evidence/coscientist-affine-reader-20261006/summary.json),
[timing audit](evidence/coscientist-affine-reader-20261006/timing-audit.json),
[archive checksums](evidence/coscientist-affine-reader-20261006/checksums.sha256).
Archives retain native proof programs, diagnostic code, repair notes, fresh raw
measurements, source/artifact pins, integrated executable and corpus receipts.
The baseline is the [qualified scalar-mask product](coscientist-native-census-mask-20261005.md).

## Hypothesis and implementation

The census observed59084 `value` entries and93139 ordinary vector-at lowerings
per WikiSort body. Counts identify a candidate cost, not time shares or complete
operation coverage. Actual frontend metadata/SIR now confirms a frameless leaf:
vector-i64/i64 -> i64, entry fuel/label, parameter loads, multiply by2, vector-at,
return. Hypothesis registered before building/timing: compose this exact closed
reader body, preserving wrapping arithmetic and every check/fuel/trap boundary.

The generic recognizer requires the exact typed body, two slots, depth<=3,
matching FN/END, scalar return and no open replaceable import. Other operations,
extra work, wrong types, larger slots and multiple results refuse. The multiplier
is any i64 constant; proven positive powers use shifts, other values use low64
multiply. The product algorithm contains no workload/function names.

The original caller frame/prescan and argument evaluation remain. x8 reproduces
the callee's private fuel transaction: success publishes decremented fuel, invalid
handle/index traps retain pre-call published fuel, exhaustion publishes zero.
Original handle/index checks execute in their original order before the load.
There is no descriptor/check hoisting or computation-result memoization.

Actual admission is9 WikiSort call sites, with19388 ->20120B machine code (+732B).
All19 result/exact-fuel/exhaustion comparisons pass; the other18 machines are
baseline-identical. Diagnostic and quiet target bytes are identical for all19.

An initial emitter mistake was caught before hand-proof/timing: `gn-pow2` returns0
for a non-power, not-1. The conditional was repaired to shift only for positive
returned widths and multiply otherwise. Original artifacts/notes are retained.
Canonical admitted multipliers are2, and corrected canonical bytes/offsets are
independently verified unchanged. Only the corrected variant is timed/promoted.

## Fresh quiet timing

Apple M4 zebulun, original pinned C/runner/source; all three arms freshly executed
in rotating order.30 accepted triples take30 attempts. Original admission remains
load<=4, background idle>=90%, adequate duration and relative SD<=10%. Promotion
requires ratio>=1.05 and mean gap greater than summed SDs.

| Workload | Previous product ns/body | Candidate ns/body | C ns/body | Shorter time | Candidate/C |
|---|---:|---:|---:|---:|---:|
| WikiSort |193443.84|177398.31|15133.39|8.29%|11.72x|

Gap16045.53ns exceeds summed SD13035.10ns. Product SD7010.69ns, candidate6024.41ns,
C53.56ns; relative SDs3.62%,3.40%,0.35%. Independent audits recompute row admission,
rotating order/statistics and actual source/machine/offset/compiler/C/runner/spec/
proof pins. No aggregate score or fresh measurement of unchanged18 is claimed.

## Native proof and permanent regression

- Four native seed generations byte-match:810856B, SHA256
  `c02730f5e481d794c84450dbc41835a2f55ed9bb446847311a2efce5afa8fde9`.
-587 fixtures include240 actual positive call sites and refused controls.
  38064 actual baseline/candidate hand-result/trap/full-state comparisons cover
  244 callers,156 cases each:6111 successes,31953 traps. Signed extremes,
  negative/zero/odd/large multipliers, wrapping indices, live register/home values,
  allocation before calls and low fuel are covered. A separate audit hand-derives
  remaining fuel, all memory counts and every allocated vector item.
-96 actual import comparisons replace the same-signature function with a charging,
  allocating implementation returning77; the diagnostic allocator clobbersx7.
  Open baseline/candidate agree and closed controls differ. Allocation/items/fuel
  are independently checked.72 more cases cover extreme invalid handles.
- Fresh native real/test generators produce the same new587-fixture code/offsets
  modulo explicit padding. The old319-fixture blob/offsets equal the previous
  qualified golden; its3940 earlier executions compose by complete artifact
  identity and are not repeated in that receipt.
- Permanent regression adds23 fixtures after the complete original319 definitions
  and runs.342 fixtures freshly pass4196/4196 native executions with real/test
  layout checking. Final caller metadata stays scalar; reader leaves get vector
  metadata. That correction (`c5526f060`) passes without changing the machine
  golden. Earlier authoring runs are retained and not added to final counts.

This is one-off new compiler algorithm/test authoring, not a mechanical rewrite
covered by an existing AST refactor rule. Generated artifacts remain authoritative
outputs of `scripts/seed/a64gen-fixtures.py`. Frozen replay inputs reproduce exact
executed587-fixture IDs and244 caller cases independently of later test edits.

ERR/G1–G5 pass against exact current MANIFEST/native fixedpoint. G1's legacy
ports pass19/19 under both seeds; G2 preserves65/66 with1 existing refusal;
G3 preserves recorded r6m outcomes; G4 has84 identical containers; G5 detects no
started program. Legacy G1 ports are distinct from the19 original timed workloads.
Bootstrap inventory is unchanged. All release gates/100% selfhost are not claimed.

## Integrated source and command

The committed-source unified image has162 objects/generation and117 frontend
objects. All objects, `amu`, `amu.bin`, `amu.kseed` byte-match across three generations.
Executable6076152B, SHA256
`fc0ee0ae098d32c7f654fa87cf90df474abc2616a9c67b3d296a692538fcabb3`.
Its command checks/compiles/extracts all19 originals to exactly the qualified
fresh measured machine bytes and offsets. External inputs are content pinned;
the complete external source snapshot remains local, as recorded in the receipt.

Every391-row check,391-row compile and891-row export outcome matches the previous
qualified scalar-mask product, including debt: check358 same accepts/33 same
refusals; compile300 behavior-same,27 Amu-only accepts,12 Amu-only refusals,
3 differing accepted behaviors,49 shared refusals; exports875 same,15 existing
closure-handle differences,0 timeouts,1 missing. This preserves prior outcomes;
it does not resolve those stage-0 discrepancies.

`bin/amu` remains the Node bootstrap. No launcher switch, rung-record update or
wire20 grant occurs. Host build wrappers remain bootstrap tooling; the native
self-rebuild proof does not establish100% of the product selfhost goal.

## Next registered hypothesis

[Next hypothesis](evidence/coscientist-affine-reader-20261006/next-hypothesis.json):
reuse a validated vector descriptor only with dominance and unchanged handle/state
proof, retaining original index/fuel/trap boundaries. Unknown calls, capabilities,
mutation and open imports invalidate admission. The actual runtime's in-place
vector append can change descriptor length: content identity does not make heap
state immutable. This is registered, not implemented/measured. The objective
remains C-level-or-better across the full original19-workload scope.

## October6 runtime correction

The registered next-hypothesis statement above about in-place append changing
an existing descriptor length was incorrect. `intern_vector` creates a new table
entry, and `checked_vector_conj` returns its new handle. Old/new descriptors retain
different lengths. The historical archived hypothesis is unchanged. See the
[validity-reuse experiment and correction](coscientist-vector-validity-20261006.md):
semantic proofs pass, fresh1.23% timing fails promotion, product stays unchanged.
