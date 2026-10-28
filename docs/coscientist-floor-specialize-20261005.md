# Exact wrapped-quotient specialization and signed-probe repair

A native-built SIR dumper confirms the helper's actual shape: compare x<0;
negative branch returns `-quot(wrap(-x + divisor - 1), divisor)`; nonnegative
branch returns `quot(x, divisor)`. Wrapped negation/addition matters at MIN and
near-MIN: the source helper at MIN/divisor 256 returns +36,028,797,018,963,967,
not the negative result an unconditional arithmetic shift would produce.
This prototype preserves that existing source behavior, rather than redefining
mathematical floor division. The dumped source and exact SIR are archived.

## Exact generic specialization

Match the complete 23-instruction SIR diamond, all opcodes and operands, both
branch/join labels, scalar RET/END and optional original entry FUEL. It must take
two natural parameters and contain no other operation. At the call site require
an immediately preceding CONST of its second argument, value 2^k for k=1..12.
Names never enter the proof. Unknown/absent SIR, RES2, dynamic/non-power-of-two/
larger divisors and near-matching helper bodies keep the old path.

Emit the original wrapped negative expression with signed power-of-two quotient
bias, shifts and a branch; positive x uses a shift. All full-i64 edge values are
preserved. Constant x folds the same wrapped expression. The original optional
entry FUEL is charged once; prescan distinguishes this token class from the
previous sign-extension tokens and accurately classifies fuel/leafness. Existing
caller local/high-temp protection and result coalescing remain. The division's
zero and MIN/-1 traps are impossible only in the admitted positive constant
range; other call paths retain existing division. This is one-off new compiler
algorithm authoring, not mechanical refactoring. It is an SIR proof, not a native
DefCID integration or computation-result cache.

Native generations 2/3/4 match at 825,640 bytes; exact hashes are in the summary.
All 19 canonical workloads preserve representative results, exact per-call fuel
and exhaustion traps. Picojpeg is the only changed binary; the other 18 are
byte-identical. All 8,192 workspace cells after one/two bodies match the promoted
native seed. No canonical source or fixture golden changes.

The handwritten SIR harness passes 1,206 runs across 173 fixtures, with identical
real/test layouts. Cases span divisors 2/4/128/256/4096, optional entry fuel,
caller exhaustion, MIN/near-MIN/MAX, signed values around each division boundary,
constant folding and high temporary homes. Four instruction audits confirm no
BL and no SDIV at selected admitted callers. Independent source probes execute
1,950 real guest comparisons through a signed-i64 native loader: admitted and
fallback divisors 1/2/4/128/256/4096/8192/3, dynamic divisors, a deliberately
nonmatching subtraction, constants, aliasing and high expressions. Full-fuel
outputs are hand-calculated; positive fuel budget outcomes match baseline.
The signed loader does not report an exact consumed-fuel counter, so source
probes are not claimed as per-case exact fuel measurements. Canonical runner
checks separately cover exact consumed counts.

## Input-admission flaw discovered and repaired

The timing runner accepts n only as decimal 0..2,147,483,646. Its rejection of
negative MIN caused this wave's first independent expected-value source probe
to fail. Previous probe harnesses compared exit codes without separating runner
setup rejection from guest traps. Thus the old sign-extension report's 1,872
comparisons included only 792 guest executions and 1,080 setup rejections; it
did not prove its claimed source-level signed-edge coverage. Keep that original
report/failure rather than relabeling rows. The signed SIR fixture evidence and
canonical performance timings are unaffected: their adapters/inputs are valid.

Re-execute the original sign source, previous wrapper compiler and promoted sign
compiler through the signed-i64 native loader. All 1,872 comparisons now actually
execute the guest; every one succeeds and matches. Full-fuel values are also
independently calculated for sign widths 1/2/8/16/24/31/32, high expressions,
constant wraparound, a nonmatching mask/subtraction, tails and aliasing. Failed
runs would be accepted only as guest traps if stderr contains KEXE_TRAP; setup
rejections fail the harness. No previous semantic expectation is loosened.
These repairs compare positive fuel-budget behavior, not unavailable exact
loader counters. The old constant-index and descriptor-2 rejected prototypes
likewise had 1,424 real guest comparisons and 24 setup comparisons apiece; their
old 1,448 figure must not be read as all guest executions. Their SIR/canonical
checks and rejection decisions remain separate evidence.

## Prospective performance decision

On zebulun Apple M4, pinned runner and unchanged C binary, all three arms are
sampled anew: 30 accepted rotating triples, maximum 90 attempts, target 300 ms,
minimum 50 ms, load <=4, estimated background idle >=90%, RSD <=10%. Promotion
requires >=5% speedup and mean separation above summed SD. All calibration and
measurement rows are retained with the original code-baseline lineage.

| Picojpeg arm | Mean us/body | RSD |
| --- | ---: | ---: |
| Promoted native sign-extension baseline | 262.590 | 1.82% |
| Wrapped-quotient prototype | 256.216 | 2.19% |
| Unchanged C comparator | 10.780 | 0.97% |

Speedup is 1.02488x, about 2.43% less time. The 6.374 us mean gap is below the
10.373 us summed SD and the 5% threshold, so no improvement is confirmed and
promotion is rejected. Code is 45,104 bytes versus 45,092. Candidate/C is
23.76716x: C-or-better remains unachieved. These are aligned whole-body timings,
not official Embench scores, formal perfgate qualification or a new suite mean.
Do not resample this identical prototype for acceptance. Product compiler and
integrated image remain at the previous promoted sign-extension version.

## Next hypothesis

Inspect the compound transform helper containing signed-16 narrowing, multiply
by a known scalar factor, bias +128, the admitted division by 256 and final
signed-16 narrowing. With |factor|<=4095, narrowed input times factor plus bias
has magnitude far below i64 limits; the helper's negative branch cannot overflow.
An exact compound SIR/dependency proof could therefore replace that whole chain
with narrowing, multiply, bias, arithmetic shift and narrowing, eliminating more
calls than isolated quotient specialization. This is an unimplemented hypothesis.
Validate the actual SIR and original fuel charges first; unknown shapes/ranges
must retain the baseline route. No benchmark-specific name admission is allowed.

Prototype diff uses zero context; complete sources are archived. Evidence:
[summary](evidence/coscientist-floor-specialize-20261005/summary.json),
[prototype](evidence/coscientist-floor-specialize-20261005/prototype.diff),
[native source/SIR/fixtures/probes](evidence/coscientist-floor-specialize-20261005/native-proof.tgz),
[all timing](evidence/coscientist-floor-specialize-20261005/timing.tgz),
[signed coverage audit](evidence/coscientist-floor-specialize-20261005/signed-source-audit.json),
[repaired sign source executions](evidence/coscientist-floor-specialize-20261005/repaired-sign-source-probes.tgz).
