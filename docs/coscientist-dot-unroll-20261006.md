# Guarded whole-dot expansion: native proof and rejected timing

Latest qualified experiment: [guarded whole-dot expansion with direct return](coscientist-dot-unroll-return-20261006.md). Fresh30 paired triples qualify67.814724% less original matmult body time (3.107011x); native tests/gates and committed-source3gen integration pass. C remains4.680001x faster; all19 C-or-better remains open. Earlier experiments below retain their historical decisions.

The original full matmult body runs much faster in this temporary native
prototype, but the experiment **fails the unchanged stability rule**. Do not
promote it or retime the identical machine. The product remains the
[qualified same-local-read implementation](coscientist-same-local-read-20261006.md).
The all19 C-or-better objective remains unachieved.

[Summary](evidence/coscientist-dot-unroll-20261006/summary.json),
[independent timing audit](evidence/coscientist-dot-unroll-20261006/timing-artifact-audit.json),
[pre-timing proof pins](evidence/coscientist-dot-unroll-20261006/preflight-audit.json),
[checksums](evidence/coscientist-dot-unroll-20261006/checksums.sha256).
Full native and timing archives retain prototypes, prospective registration,
all observations, failed authoring/check attempts, calibration and every raw row.

## New native algorithm

An exact closed typed47-instruction SIR recognizer captures a five-parameter
read-only affine dot loop. It captures constants and labels from the structure,
without workload names. It requires the exact vector/i64 signature, five locals,
depth10, original nonleaf frame, resident callee-register parameters and validated
same-function label ownership. Unknown calls, effects, allocations, writes,
control flow or open-replacement dependencies refuse admission.

Trip/strides are bounded1–64 and offsets0–4095. The runtime fast path requires
initial `k == 0`, unsigned row/column below the trip bound, a valid positive
vector handle, both complete read endpoints within the current vector, and enough
remaining fuel for every original backedge charge. Other inputs take the original
loop. Unused invalid handles at zero-trip are not validated. Proved arithmetic
ranges avoid i64 index overflow; sequential multiply-add preserves low64 sum wrap.

The original prologue, parameters, frame and entry charge stay exact. Valid reads
are expanded, fuel is published with the exact original total, and the original
locals/exit path produce the result. Guard failure preserves input locals, context
and fuel, clears the temporary cache key, and reaches the original loop. Descriptor
and index checks are proved before expansion, with fresh item reads throughout.
No result cache, DefCID bridge, host runtime, capability grant or resource-budget
change is introduced. This is newly authored Kotoba code and independent hand
fixtures without an existing mechanical AST rule, kept outside the product source.

## Native qualification before timing

The final temporary seed is824,728 B, SHA-256
`7b410343e2df5e8afea620814fbb4fa4f3151cfb76434349eb9f792480351867`.
All four native generations are identical. The final prototype source hash is
`4f1e7e674a5a2b18b390a95894d66a03508c93890f06f65b704e15793ac76b9b`.

The original470 fixtures /11,187 native executions pass without changing any
expectation. After adding conservative label-ownership guards, the final compiler
reproduces exactly the same fixture bytes and function offsets already executed;
real and independent test layouts agree. The preflight pins this derivation and
the final source, rather than attributing old execution to a different machine.

Additional2,786 full supervisor-state comparisons:

- 1,955 independent native frontend hand-oracle comparisons across11 variants:
  trips1/2/3/20/64, distinct strides/offsets, overlaps, short vectors, refused
  stride65/negative offset/trip65, MIN/MAX wrap, invalid indices, zero-trip and
  partial fuel up to the public maximum2^53−1.
- 400 direct raw-boundary invalid-handle and unused zero-trip comparisons.
- 184 independently authored SIR wrapper observations, matching frontend baseline
  and candidate results, fuel, items and traps; real/test code and offsets agree.
- 209 original19 full and partial-fuel states.
- 38 original19 low-resource states, retaining partial allocation/item contents.

Native mutation tests change and restore all188 SIR fields, check ten type/metadata
refusals, three foreign-label refusals, open replacement and invalid local-register
refusals. A separate30-case diagnostic places a trap at the first expanded madd:
positive cases actually hit it; zero-trip, insufficient fuel and unproved inputs
retain normal fallback observations. Diagnostic images are never timed.

All19 canonical source/result/exact-fuel/trap checks pass. A read-only native
observer identifies exactly originalmatmult FN5, SIR3273, and produces every
current quiet guest byte/offset. Only matmult changes, to10,648 B. Its original
18-word prefix (192-byte frame, five parameter placements and entry fuel) and
55-word loop/return tail remain exact;98 words are added before the original loop.
All20 load/load/madd groups are checked against the actual machine words.

Initial authoring failures are preserved: a typed source cannot forge a vector
from an i64 branch, so invalid handles are tested at the raw native boundary;
the loader rejects initial fuel0 and budgets above2^53−1, so zero remaining fuel
is reached through original charges within its existing allowed range. One
register test initially chose another valid register; it was corrected to an
unassigned register. Two layout comparisons initially confused real and test
padding/order; actual code/literal bytes and offsets are checked exactly, with
only the verified trailing zero padding admitted. No semantic expectation or
performance criterion was loosened.

## Fresh measurement and rejection

Authorized zebulun, Apple M4; the same pinned runner, original source and C dylib.
30 rotating product/prototype/C triples were accepted out of31 attempts. Existing
load<=4, background idle>=90%, minimum50ms interval, RSD<=10%, speedup>=1.05 and
gap greater than summed SD apply. All source/machine/spec/receipt pins and raw
statistics are independently recomputed.

| Original matmult body | Mean us | SD us | RSD |
| --- | ---: | ---: | ---: |
| Current qualified product |12.659296 |1.291649 |10.203164% |
| Guarded whole-dot prototype |4.327167 |0.240836 |5.565669% |
| Unchanged C |0.921334 |0.009699 |1.052661% |

The provisional product/prototype ratio is2.925539 and prototype/C is4.696633.
The large mean reduction and separation clear those two tests, but the product
RSD exceeds10%. Therefore aggregate stability is false and promotion fails.
The large provisional gain is evidence for the algorithm, not a qualified product
speedup. No full-suite aggregate or official Embench score is claimed.
Product gates and integrated rebuild are not run for a rejected prototype;
`seed/41-a64gen.kotoba`, default rung, `bin/amu` and grants remain unchanged.

## Next distinct machine

[Registered follow-up](evidence/coscientist-dot-unroll-20261006/next-hypothesis.json)
returns the expanded sum through the original epilogue directly, avoiding dead
parameter writes and the original zero-trip/return branches after success.
It retains the full original fallback and resets the generator's compile-time
unreachable flag before emitting that fallback. Runtime successful return restores
the original frame/callee registers. This changes actual generated code and is
not a repeat measurement of the rejected machine.

At this archive snapshot the follow-up has four byte-identical native generations,
824,656 B, SHA-256
`5acce408459f4953e9371c04775396afc962a618170a92890fd6b4ed6a21ede1`.
Its source/creation recipe are archived. Independent native execution proofs and
a new prospective measurement must finish before any promotion. The source body,
C comparator and all original19 requirements remain fixed.
