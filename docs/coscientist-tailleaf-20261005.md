# Tail-only leaf allocation: measured negative finding

After direct tail branches improved Statemate, the next hypothesis was that
functions containing only direct tail calls could avoid non-leaf register
assignment and frame preservation. The pre-scan currently marks every direct
CALL non-leaf. A prototype excludes eligible scalar tail calls from that
classification and materializes all their arguments before register moves,
preserving argument permutations when locals occupy x0..x6. Bounds checks,
callee fuel and stack/indirect-call routes remain intact.

The prototype is kept in the evidence archive; the compiler source in the
repository is unchanged. Its native seed generations 2/3/4 match at
`b7aa40b9e2650664a5570f8ba18d66a3c5f717de432377389ccabe05a843ee42`
(779,112 bytes). All 792 hand-computed fixture executions, identical real/test
layout, 2,873 previously C-validated state observations and exact batch fuel
comparisons pass. The existing code-byte golden is intentionally unchanged:
the prototype emitter is prebuilt and the independent expected-value runs
execute its output. This does not claim golden agreement or all release gates.

The first timing attempt failed the fixed 90-attempt limit with zero accepted
triples: C's initial three-call calibration overestimated its cost and selected
about 29,000 calls, yielding roughly 29ms intervals below the 50ms minimum.
All those rows remain failed. Calibration now retains up to five refinement
samples per arm, targets 75%-150% of the 300ms interval, and fails at the fixed
limit. Synthetic biased-initial and nonconvergence cases pass. The subsequent
experiment is a fresh run with the same acceptance rules and new samples;
no failed rows were reclassified. A prior archive-expansion attempt also
failed on the remote Python 3.9 API and is retained.

The baseline code for this experiment is the integrated tail-call candidate,
projected from its completed Statemate measurement with original report/hash
retained. All three arms are sampled anew; old timing values are not reused.
On zebulun, 30 accepted triples out of 33 yield:

| Arm | Mean ns per body | Relative SD |
|---|---:|---:|
| Integrated tail-call baseline | 1,207.93 | 2.00% |
| Tail-only leaf prototype | 1,198.28 | 2.06% |
| C | 30.44 | 0.91% |

The 1.008x ratio misses the 5% improvement criterion, and the 9.64ns gap is
smaller than the summed 48.76ns standard deviations. **Do not promote.**
The prototype still takes 39.36x C time. Correctness and smaller emitted code
are not performance evidence. Whole-suite candidate/C remains the completed
integrated result 10.3885; this single-workload prototype is not substituted.

Next hypothesis: inline small direct wrappers such as checked vector stores
into their caller, preserving an explicit callee-entry fuel debit, full handle
and index checks, and argument evaluation order. This would target residual
non-tail helper calls rather than the tail-only classification tested here.
It requires a prospective artifact experiment, state/fuel/bounds differentials
and a fresh concurrent comparison before implementation is promoted.

[Evidence](evidence/coscientist-tailleaf-prototype-20261005/summary.json)
includes source/binary hashes, prototype source, fixture outputs, state/fuel
checks, failed drafts and all accepted/rejected timing rows. These are custom
whole-call measurements, not official Embench scores or formal qualification.
