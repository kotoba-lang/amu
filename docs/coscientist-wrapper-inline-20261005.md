# Checked wrapper inlining: second measured compiler improvement

The tail-only leaf-classification experiment did not improve Statemate beyond
noise. This hypothesis instead removes short *non-tail* helper calls by
recognizing exact SIR shapes, independently of function or benchmark names.

The compiler accepts an optional entry FUEL and entry LABELs, natural-order
parameter loads, one existing inline runtime operation (or identity), RET 0
and END. The runtime slot and temporary-depth rules must already support
inlining. A CALL followed by RES2 is excluded. Other functions retain the
normal direct/tail call route. The original callee entry fuel is emitted at
the call site, including a cached leaf counter; full handle/index checks and
argument evaluation order remain intact. Prescan accounts for this fuel and
leaf eligibility. Separate modules with no local SIR definition stay calls.
This is new compiler algorithm authoring; no mechanical refactor rule covers
it. The fixture metadata adds the FF-SIR pointers present in production.

The native compiler seed is a three-generation fixed point (generations
2/3/4), 817,872 bytes, SHA-256
`2744207230f7c8705990757bfa69689b52415cba679481b1931e2fe4fd11a923`.
It is built by the previously validated native selfhost seed and then itself,
without stage-0 fallback. All 19 canonical workloads preserve tested results,
exact fuel consumption and exhaustion traps. Statemate's 2,873 previously
C-validated stage/repeated-state cells and bounds probes pass. New identity,
load/store, leaf cached-fuel, high-temp and out-of-bounds fixtures bring the
hand-computed total to 801 passing runs; real/test layouts are identical.
The byte golden changes because real function pointers enable eligible
wrappers, and seven fixtures are appended. Three new call-site instruction
audits confirm no direct BL. ERR and G1-G5 pass; G2 retains the prior 65/66
matches plus one named refusal, and G3 all 300 prior outcomes. These are six
gates, not all release gates. All 97 PRODUCT inventory entries are unchanged.

On zebulun, fresh rotating baseline/prototype/C sampling collects 30 accepted
triples under the existing fixed quiet/duration/attempt rules. Baseline code
is the integrated tail-call candidate; its original measurement report/hash
is retained, while every arm is sampled anew.

| Arm | Mean ns per body | Relative SD |
|---|---:|---:|
| Integrated tail-call baseline | 1,212.75 | 2.04% |
| Checked-wrapper candidate | 755.29 | 1.44% |
| C, Apple Clang 17 -O2 | 30.53 | 0.85% |

The candidate improves 1.606x (37.72% less time), passes the 5% improvement
criterion and separates from summed standard deviations. It still takes
24.74x C time. Statemate code grows from the prior 88,864 bytes to 111,920:
this trades code size for less dynamic call/frame overhead. No full-suite
geometric mean is inferred from a single workload, and these are custom
whole-call measurements rather than official Embench scores.

The first unified rebuild used an uncommitted codegen change while the
launcher correctly archives git HEAD. Generation 1 was compiled with the
new seed but embedded old compiler source; generations 2/3 returned to the
old tail-call image, so the three-generation comparison correctly failed.
After committing the source at `fafb295a7`, the repeated archive-based
rebuild passes three-generation equality of every object, container, native
code and command. The integrated Amu is 6,092,664 bytes, SHA-256
`40538bfb021af4662c79ab478848e9bd360d51339135062751e69cb3b3fe213d`.
All 19 sources check and compile through this image, producing the exact
measured prototype code. The failed attempt remains in evidence.

The integrated corpus preserves the prior results: check 358 same accepts
and 33 same refusals; compile 300 behavior matches, 27 Amu-only accepts,
12 Amu-only refusals, 3 differing accepted outputs and 49 shared refusals;
exports 875 same, 15 existing differences, 0 timeouts and 1 missing. Stage-0
is solely the test reference, never a compiler in the build lineage.
A full-suite rotating comparison against the prior integrated image and
unchanged C binaries now completes all 19 workloads, each with 30 accepted
triples and relative SD below 10% in every arm. Concurrent baseline/C
geometric time ratio is 10.3942 and candidate/C is 9.6251, a 1.0799x
geometric speedup (7.40% less time). Seven workloads meet the predeclared
improvement and spread criteria; none reaches C time. The whole-suite
Statemate improvement is 1.611x and its C ratio is 24.949x, distinct from
the standalone experiment above. No across-run ratio is used for speedup.

[Evidence](evidence/coscientist-wrapper-inline-20261005/summary.json) includes
all generation/source hashes, ports, state/fuel checks, fixtures, requested
gates and raw accepted/rejected timing rows. The initial fixture instruction
observer incorrectly included pool bytes after the final function; the fixed
observer and failed log remain. The first raw port compiler invocation omitted
the existing string-pool budget; the rerun uses seed_run's existing budget.
The product entry has not been switched and own-source 100% remains unproven.


| Workload | Prior / candidate speedup | Candidate / C time | Improvement criterion |
|---|---:|---:|---|
| aha-mont64 | 0.995 | 1.950 | not established |
| crc32 | 0.993 | 2.309 | not established |
| depthconv | 1.016 | 3.484 | not established |
| edn | 1.008 | 15.672 | not established |
| huffbench | 1.012 | 7.328 | not established |
| matmult-int | 1.033 | 23.883 | not established |
| md5sum | 1.153 | 5.671 | PASS |
| nettle-aes | 1.005 | 18.040 | not established |
| nettle-sha256 | 1.065 | 13.724 | PASS |
| nsichneu | 0.997 | 8.801 | not established |
| picojpeg | 1.073 | 30.118 | PASS |
| qrduino | 1.009 | 12.712 | not established |
| sglib-combined | 1.093 | 7.108 | PASS |
| slre | 0.990 | 7.424 | not established |
| statemate | 1.611 | 24.949 | PASS |
| tarfind | 1.379 | 14.539 | PASS |
| ud | 1.173 | 10.930 | PASS |
| wikisort | 1.057 | 15.768 | not established |
| xgboost | 1.026 | 7.207 | not established |

The next largest measured gap is Picojpeg (30.118x C), followed by
Statemate (24.949x) and Matmult-int (23.883x). Next work should isolate
Picojpeg decode, transform and pixel-store costs against the original C
observations, then test a general codegen hypothesis for the largest cost.
The full-suite evidence is in [suite summary](evidence/coscientist-wrapper-inline-20261005/suite-summary.json)
and `suite-timing.tgz`, including every rejected attempt and calibration row.
