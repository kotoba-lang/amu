# Direct scalar tail calls: first measured compiler improvement

The aligned 19-workload zebulun baseline identified Statemate as the largest
gap (Kotoba/C time ratio 78.41). Hypothesis: its generated controller chain
spends substantial time entering and returning from short functions. The
experiment changes the compiler, preserving the canonical benchmark source.

`seed/41-a64gen.kotoba` now recognizes a direct CALL immediately followed by
RET of the same result, with at most seven arguments. It places the arguments
and context in their ABI registers, restores the current frame and branches
to the callee. The existing function-target imm26 relocation preserves the B
opcode. Stack-argument calls, indirect calls and two-result returns retain
their previous routes. Callee execution, vector bounds checks and fuel
instructions remain intact. This is new compiler algorithm authoring with
no applicable mechanical Amu refactor rule.

The candidate compiler was produced by pinned native selfhost Amu, then
rebuilt itself. Generations 2, 3 and 4 are byte-identical: 782,944 bytes,
SHA-256 `6a7e2df066f82ee330e34175e8cc65b272788b25ccccb797952a377f8f3625bc`.
It recompiled all 19 canonical workloads from unchanged sources; tested
results and exact fuel consumption match the baseline, and fuel exhaustion
still traps. Statemate's stage and repeated-state differential covers 2,873
cells, plus bounds probes. C's repeat observer rejects zero repetitions with
INT64_MIN, so that case is compared with the unchanged native reference;
the initial inappropriate C-zero comparison and its correction are recorded.

The AArch64 fixture generator adds hand-computed argument-permutation,
high-temp and cross-call fuel cases. All 792 cases pass, with the real layout
producing identical bytes to the test layout. The reviewed golden change
preserves existing function offsets, appends three fixtures and moves literal
relocations with the pool. New tail fixtures emit B rather than BL. The
real-layout test helper previously hardcoded stage-0 and omitted memory/IO
modules; it now honors the native seed through seed_modbuild and includes
the complete source closure. No stage-0 fallback produced this candidate.

ERR and G1-G5 pass. G2 reports the existing 65/66 reference equivalence,
one named frontend refusal and zero differences. G3 preserves all 300 prior
accept/refusal outcomes. The first G1 attempt could not read its external
port root; the rerun includes that existing root in wire 35's read scope.
These are the six requested gates, not a claim that all release gates pass.
The PRODUCT bootstrap inventory is unchanged.

On zebulun, the prospective rotating three-arm experiment retained every
attempt and gathered 30 accepted triples under the fixed load/background
idle rules. The same canonical source and pinned runner are used throughout.

| Arm | Mean ns per body | Relative SD |
|---|---:|---:|
| Existing r6m generated code | 2,472.93 | 0.98% |
| Tail-call candidate code | 1,202.80 | 2.21% |
| C, Apple Clang 17 -O2 | 30.09 | 1.11% |

The candidate is 2.056 times faster than the concurrently measured baseline
(51.36% less time), clearing the 5% and combined-standard-deviation criteria.
It remains 39.97 times slower than C. This supports the overhead hypothesis
and retains the remaining gap; it does not prove the entire gap is calls.
The initial 78.41 ratio is from a separate run; the 2.056 speedup comes from
the simultaneous three-arm comparison, not a comparison across runs.

These are provisional whole-call measurements, not official Embench scores.
The CPU envelope includes setup and warmup and background idle is estimated.
The candidate is a native selfhost seed; it has not been integrated into the
packaged Amu product image, and full own-source 100% qualification remains
unmet. The 19-workload baseline geometric mean stays 11.1274 until an entire
candidate suite is measured; no partial result is substituted into it.

[Evidence](evidence/coscientist-tailcall-20261005/summary.json) includes all
compiler generations, state and fuel comparisons, requested gate logs and
raw accepted/rejected timing triples. Further work is product-image
integration and whole-suite measurement, followed by a measured hypothesis
for the remaining controller/vector-access overhead.
