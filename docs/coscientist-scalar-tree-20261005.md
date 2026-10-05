# Pure scalar threshold-tree table lowering

The bounded-fill trial failed the declared performance threshold. The next
hypothesis targets repeated coefficient-position decision trees: prove the
whole scalar decision tree and replace repeated branches with a native lookup.
This is generic new compiler algorithm authoring, not mechanical refactoring;
no existing AST refactor rule implements it. Canonical benchmark sources stay
unchanged. This is exact structural specialization, not DefCID integration or
result memoization, as explained in the [identity investigation](coscientist-content-address-20261005.md).

## Implementation and native proof

The backend accepts a complete one-argument pure SIR tree: exact local reads,
integer `<` comparisons against constants 1..63, BRZ/BR targets, and literal i64
leaves. All operands and actual prescanned label positions are checked recursively
(depth <= 7). The whole tree must end immediately in RET/END; it must exceed
128 SIR instructions. Optional entry FUEL is preserved. Unknown calls, effects,
nonliteral leaves, other comparisons, out-of-domain thresholds or smaller trees
remain on the original path. Names never determine admission.

Native lowering preserves the prologue and optional leaf fuel transaction,
then loads from a PC-relative 64-entry i64 table. Signed negative inputs return
the value at 0; inputs above 63 return the value at 63. Since every admitted
threshold lies in 1..63 these equal the original full signed-i64-domain endpoints.
There is no allocation, new external effect or helper call. Data resides after
all three return paths; the proved original body is omitted through END only.
Private scratch field 14 is reset on every function's original state clear.

Generations 2/3/4 reproduce identical 824,952-byte native compilers:
`98905d4a7c3da0d94465d99f4b32ae195c2e7972d1b995a3744a0d588595635d`.
All 19 canonical workloads preserve results, exact fuel and exhaustion exits.
Only Picojpeg and QR code changes; the other 17 binaries are byte-identical.
Picojpeg's full workspace after one/two original bodies matches (8,192 cells).
All 2,432 signed source comparisons and 770 handwritten comparisons match exact
supervisor reports, result, fuel, resources and traps. Arbitrary i64 literals,
every table interval, signed extremes and nearby unsupported trees are covered.
Four audits independently decode ADR, the scaled LDR and all 64 table entries;
there are no BL/BLR calls in admitted functions. Five near-match audits confirm
fallback admission is refused.

The fixture generator authors these regression cases, regenerates its source and
index, and the native unit harness regenerates the golden by real execution.
All 1,979 runs pass (185 fixtures); native test/real layouts match. PRODUCT
bootstrap inventory remains unchanged: 97 inventory rows and 58 distinct
PRODUCT src files before/after. ERR and G1-G5 (six gates) pass at
r6m, including 84 identical seed-generation corpus/port containers; this is not
a claim that all rung release gates pass. Preserved harness failures include an
unknown emission helper at initial prototype build, an older QR baseline refused
by hash before timing, and a temporary unit source refused by its resource root.
Each was repaired at its actual boundary, without relaxing semantic expectations.

## Quiet-host measurement

All three arms run the original body freshly, on zebulun (Apple M4) with pinned
original C, runner and source. Thirty rotating triples per changed workload meet
load <= 4, background idle >= 90%, RSD <= 10%, 300 ms target and 50 ms minimum,
with fixed 90-attempt limit. Promote a measured improvement only at speedup >=1.05
and mean separation larger than summed SDs. No identical code is resampled to
seek acceptance.

| Workload | Product us/body | Candidate us/body | C us/body | Product/candidate |
| --- | ---: | ---: | ---: | ---: |
| Picojpeg | 260.597 | 236.399 | 10.788 | 1.10236 |
| QR | 271.450 | 274.637 | 21.458 | 0.98840 |

Picojpeg improves 9.29% in elapsed time: its 24.198 us gap exceeds summed SDs
11.299 us and clears the 5% speedup threshold. QR's mean slowdown is 3.186 us,
smaller than summed SDs 14.320 us; it proves neither improvement nor regression.
Do not label QR a win. Candidate/C remains 21.9135x and 12.7987x respectively;
C-or-better remains unachieved. These are aligned whole-body measurements, not
an official Embench score, formal perfgate or a fresh suite geometric mean.

The measured algorithm was committed at `29d7163ae` before rebuilding the
integrated image. Its copied backend source is byte-identical to that commit.
The rebuilt executable is 6,092,664 bytes, SHA-256
`203e04213183a3e56ee728f4f6302a1d40f10a25e70db67c17e09a748b053a87`.
All three generations of the command, native code, container and every one of
162 objects are byte-identical; 117 frontend modules are compiled from source.
The content-pinned external input snapshot is checked and retained locally.
Every canonical source passes integrated check/compile and reproduces the exact
measured raw machine code, including both changed workloads.

Every one of 391 check classifications and 391 compile classifications/counts
matches the previous qualified sign-extension product. The complete 891-row
export table (875 same, 15 pre-existing differences, one missing; zero timeout)
is unchanged as well. Check retains 358 shared accepts and 33 shared refusals;
compile retains 300 behavioral matches, 27 Amu-only accepts, 12 Amu-only refusals,
3 differing accepted behaviors and 49 shared refusals. This proves the optimization
has not changed those outcomes; it does not close the existing language or own-source
selfhost gaps. `bin/amu` and rung pins remain unchanged.

[Integrated summary](evidence/coscientist-scalar-tree-20261005/integrated-summary.json)
and [native image, exact corpus tables, metadata and proof scripts](evidence/coscientist-scalar-tree-20261005/integrated-proof.tgz)
retain the integrated evidence. A comparison helper initially assumed every
export row has exit columns; MISSING rows have three fields. The corrected check
compares complete variable-length export rows with the baseline rather than
omitting the missing entry.

Evidence: [summary](evidence/coscientist-scalar-tree-20261005/summary.json),
[native prototype and proof](evidence/coscientist-scalar-tree-20261005/native-proof.tgz),
[all measurement rows and lineage](evidence/coscientist-scalar-tree-20261005/timing.tgz),
[six gate outcomes](evidence/coscientist-scalar-tree-20261005/gates.tsv).

The subsequent [scatter-zero experiment](coscientist-scatter-zero-20261005.md)
proves/fuses the bounded mapping/write loop, passes exact native semantic tests,
and fails the prospective performance threshold. The scalar-tree product stays
qualified; that further candidate is not installed.
