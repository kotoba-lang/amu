# Guarded whole-dot expansion with direct original-frame return

Qualified against the current same-local-read product: original full matmult body
execution is 67.814724% shorter (3.107011x speedup), while C remains 4.680001x
faster. The other 18 canonical guest binaries are unchanged. This is a same-host
aligned original-body measurement, not an official Embench score or a new full-suite
aggregate. The all19 C-or-better goal remains open.

Implementation source commit: `ad5b0804b6ddb13d6df0844d7557e95315b77d8b`.

## Identity and mechanism

[Current definition identity](coscientist-identity-and-reuse-20261006.md) content
addresses normalized typed implementation and dependencies. Computation recipes
can also be content addressed, but result reuse needs immutable argument contents,
explicit effect/handler state and observation contracts. This change uses native
SIR structural proofs; the typed-KIR DefCID bridge and result caching remain unconnected.
Every benchmark body executes freshly.

The compiler recognizes an exact closed typed 47-instruction dot loop, including
all operands, slots, label ownership and return shape. Bound and strides are 1..64,
offsets 0..4095; no benchmark name, source path or content hash is used to select it.
Only a nonleaf function with the original five resident callee locals qualifies.
After the unchanged entry fuel charge, runtime guards require k=0, unsigned row
and column within the bound, enough fuel, a valid handle and both entire index
ranges within the current vector. Guard failure changes no input local or fuel
and enters the original byte-exact loop. Open import replacement refuses expansion.

The successful path loads current items and emits bounded load/load/MADD groups,
preserving low64 integer arithmetic. After all pure valid reads it publishes the
original total backedge fuel, moves the sum to the return register and restores
the original frame/callee registers with its original epilogue. Context, vector
representation, capabilities, resource budgets and original fallback are unchanged.
All assumptions fail closed; this is not arbitrary semantic equivalence.

## Scientific trial boundaries

The [parent whole-dot candidate](coscientist-dot-unroll-20261006.md) passed semantic
proofs but failed the unchanged stability rule: baseline RSD10.203% exceeded10%.
Its apparent speedup was not adopted and the same machine was not retimed.
This distinct candidate emits a different successful path: direct original-frame
return instead of final local assignments and the old exit branches. The original
fallback is retained. Prospective registration and native proof precede timing.
Do not infer a significant speed difference between these two candidates from
separate noisy runs.

The initial remote dispatch incorrectly selected the parent's existing directory
and failed before invoking a timing runner. It was corrected to a fresh candidate
directory. Parent raw results were not remeasured; the correction and failed log
are retained in the evidence.

## Native proof

Four compiler generations are824,656 B, SHA256
`5acce408459f4953e9371c04775396afc962a618170a92890fd6b4ed6a21ede1`.
The measured originalmatmult guest is10,664 B, SHA256
`8485f727f28f1f0e31dd17d1b1a7d93544c498088b6d23120bddeef373afb49e`.
Instruction audit retains the original18-word prologue/entry-fuel prefix,192B
frame and55-word fallback/return tail. Twenty load/load/MADD groups and the
original6-word restoration/return sequence are checked explicitly.

Before measurement,2,786 full supervisor-state comparisons cover independently
authored shapes, aliases, strides, offsets, invalid handles and indices, wrapping,
zero/partial trips, fuel boundaries, resources and all19 canonical workloads.
Native admission mutation tests cover188 SIR fields,10 metadata/type cases,
foreign labels and open/local refusals. Thirty diagnostic path controls verify
actual fast-path hits and fallback; diagnostics never enter timed artifacts.
All19 diagnostic and quiet outputs have identical bytes and function offsets.

For adoption,480 permanent fixtures and11,843 native executions pass. The original
470 fixtures/11,187 expectation entries remain an exact prefix. Independent scalar
oracles add small/overlapping/wide64/refused65 cases, meaningful high-offset integer
extremes, fuel boundaries and bad handles including unused zero-trip handles.
Real and independent test-only layouts agree in code, literals and function offsets;
only checked trailing zero padding differs. Normal unit output reproduces the
independently executed blob before its reviewed golden update. ERR/G1-G5 pass;
G2 retains its existing65/66 match and one frontend refusal, and G3 retains300
programs with233 golden refusals/67 accepted. PRODUCT bootstrap counts are unchanged.
Gate seed0/1/2 mean current-source native generations2/3/4, not bootstrap stage0.

New optimization and independently authored semantic cases are a one-off hand
implementation exception: no existing AST refactor rule covers a new algorithm.
Generated test source is owned by `scripts/seed/a64gen-fixtures.py`; no new product
host-runtime path or fallback is introduced. Rung records, bin/amu selection and
wire20 grant are unchanged.

## Measurement

Authorized Tailscale host zebulun, Apple M4; same pinned C source/library and
runner as the product baseline. Thirty rotating baseline/candidate/C triples
were accepted out of32 attempts under the original load/idle/stability rules.
Independent audit recomputes all raw statistics and pins source, specification,
native artifacts, machine, C receipt and exact fuel.

| Original matmult body | Mean per body | SD | RSD |
| --- | ---: | ---: | ---: |
| Previous selfhost product | 13,395.128 ns | 733.082 ns | 5.473% |
| New selfhost candidate | 4,311.259 ns | 313.883 ns | 7.281% |
| Same-host C | 921.209 ns | 9.500 ns | 1.031% |

The9,083.869ns mean gap exceeds the1,046.964ns summed SD and registered5%
improvement threshold. All series remain below10% RSD. Native correctness alone
was not treated as a performance result. Remaining C gap is4.68x; no official
Embench or all19 C-or-better claim is made.

## Committed-source integration and evidence

Three integrated generations reproduce all162 objects (117 frontend), containers,
native code and executable commands. The executable is6,109,176 B,
SHA256 `a9984396a9bc3aaa0fc090cffce4e6c5dffc8bfd1bc8ff9ea35ed68fefa7458b`. Generation3 checks and compiles all19 original sources and
reproduces exactly their measured native bytes and function offsets.

All391 check/391 compile/891 export classifications agree with the previous qualified
same-local-read product. Every391 normalized full checker message and1780 native
export output/status files also agree. Existing gaps remain: check358 accepted/33
refused; compile300 behavior matches,27 Amu-only accepts,12 Amu-only refuses,3
differing accepted behaviors and49 shared refusals; exports875 same,15 existing
closure-handle differences,0 timeouts and1 missing. This is not100% release qualification.

[Summary](evidence/coscientist-dot-unroll-return-20261006/summary.json),
[raw timing audit](evidence/coscientist-dot-unroll-return-20261006/timing-artifact-audit.json),
[next registered hypothesis](evidence/coscientist-dot-unroll-return-20261006/next-hypothesis.json),
[checksums](evidence/coscientist-dot-unroll-return-20261006/checksums.sha256).
Full archives preserve prospective registration, prototypes, native proofs, all
permanent observations, committed source/generated expectations, normal unit,
gates, raw measurement/C receipts, dispatch correction, complete hashed external
input snapshot and three integrated generations with actual per-case results.
Research-branch adoption remains draft PR1222; main/release selection is unchanged.

Next: inspect residual original matmult write/call/fuel cost and test guarded
affine-write composition, preserving every observed write and original fallback.
It is registered, not implemented or measured.
