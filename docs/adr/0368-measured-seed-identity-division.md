# 0368: Measured identity division in the native seed

Date: 2026-10-04
Status: implemented in the research branch; no new recorded rung or packaged product image

## Decision

Optimize signed i64 `quot x 1` in `seed/41-a64gen.kotoba` by forwarding the
operand through the existing destination/register machinery. This is total
for all i64 values, including MIN. Constant folding remains unchanged;
division by zero and MIN/-1 retain their existing traps. No fuel charge,
boundary check, capability or ABI changes.

The single compiler edit implements a new lowering decision. It is not a
mechanical refactoring of repeated source patterns, so the hand-edit
exception in AGENTS.md applies. Generated fixtures are rebuilt by their
existing generator; they are not edited by hand.

## Experiment and evidence

Follow the Generate / Reflect / Rank / Evolve / Meta-review loop from
`docs/codegen-coscientist.md`, with C as the comparator requested here.
Before changing the compiler, hand-patch the emitted divisor-one MOV/SDIV
sequence to NOP/MOV. All 30 rotated pairs on asher return the independently
computed wrapping-i64 recurrence answer. The patch is 2.7513 times faster
than the original, with means separated from their summed sample deviations.

After implementation, measure the compiler-produced artifact, r6m and
Clang C11 -O2, on the same runner with 30 rotated samples per arm,
30,000 calls and one untimed warmup per sample. The candidate improves
from 25.765 us to 9.330 us (63.79% less time). C takes 9.249 us: no
separated C win. This is a fixed synthetic recurrence, not Embench.
The saved measurement script reproduces a 2.754x r6m speedup in another
90 samples with identical artifact hashes. Its apparent 1.22% gain vs C
is below 5% and not separated from the summed deviations, so the C verdict
remains negative.

The original MOV/SDIV sequence is replaced by one MOV, or no instruction
when the destination aliases the input. The complete experiment artifact
shrinks from 112 to 104 bytes. The seed builds itself to the same bytes
in generations 1, 2 and 3. Both r6m and the candidate compile the generator
unit; the resulting generator passes all 786 execution cases, including
MIN, MAX, aliasing, deep temporaries, division-by-zero and MIN/-1 traps.

All 19 existing Embench ports regenerate to byte-identical r6m code. This
optimization therefore provides no Embench improvement. None of the ports,
upstream C sources, previously measured scores or recorded rung hashes
are changed to manufacture a result.

## Claim boundary and next candidates

The existing JVM-backed perfgate launcher explicitly refuses to run. The
research script applies the numeric 5% improvement, summed-standard-deviation
separation and 10% relative-deviation checks as a diagnostic. It does not
replace the provenance/claim validator or claim formal perfgate qualification.
No official Embench score or C superiority is established.

Keep the broader six-domain / five-comparator claim contract intact. Next,
align initialization and verification boundaries between the full Kotoba
ports and C; qualify the native judge; then investigate read-only data
representation, bounded helper inlining and loop range proofs. Preserve
integer overflow, UTF-8, bounds and fuel semantics. A ≥5% separated C win
is required before claiming superiority for an individual workload; a
complete faithful suite is required before any suite-level claim.

The power-of-two/magic-division, multiply-add and ASCII-context prototypes
do not justify adoption. Some regions were too short for a robust verdict;
the matrix multiply-add patch did not improve its measured workload.

Evidence: `docs/evidence/coscientist-identity-division-20261004/` and
`docs/coscientist-identity-division-20261004.md`.
