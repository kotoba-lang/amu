# Paired timing preparation for the 19 native selfhost profiles

The shared harness prepares the current 19 matched active profiles, compiling
canonical Kotoba sources with the pinned native selfhost Amu compiler and
original C adapters with Clang -O2. Native machine bytes must equal the prior
qualified artifacts. C adapters are selected explicitly from retained evidence
archives; archive/member hashes, source hashes, compiler/runner hashes and
upstream commit/files are checked before building. Picojpeg's header adapter
and QR/SGLIB support files are included explicitly.

Local correctness preparation passes all 19 pairs with two calls and one
untimed warmup in each arm. It records result/call counts and executable
identity, discarding diagnostic elapsed values. This extends the independent
prior full-profile differentials; a successful verifier alone does not prove
all intermediate states. PRODUCT inventory stays at 97. Wrong-host measurement
and changed-source preparation refuse under Python -O before output creation.

Run preparation from a checkout and the previously pinned environment:

```sh
python3 scripts/seed/image/measure-embench-matrix.py REPO ENV NEW_OUTPUT
```

Add --measure only on asher. Measurement rotates C/Kotoba order across 30
pairs, calibrates each arm toward 300 ms, uses one untimed warmup and requires
at least 50 ms per interval. Each ABI call contains 32 complete original bodies
(depthconv uses its qualified 2,000-body batch); per-body time divides by the
actual calls and batch size. Source-defined per-call initialization/allocation,
representation costs, bounds/ownership/ABI and final verification remain
inside both intervals. This differs from official trigger-boundary scoring.

Rows retain every interval and load before/after. Load above 4 refuses the
run while preserving partial evidence. Per-workload summaries report mean,
standard deviation, relative deviation and Kotoba-time/C-time ratio. A candidate
needs relative SD <=10%, at least 5% speedup and separation greater than the
sum of standard deviations; negative/nonseparated findings remain in results.
The geometric mean across all 19 is a custom time ratio, not an Embench score.

The tool now records Darwin HOST_CPU_LOAD_INFO tick differences around each
runner invocation, including setup/warmup and enclosing the timed interval.
Intervals below 90% idle are preserved and refused; missing/nonadvancing
counters refuse as well. This is an enclosing CPU envelope, not counters at
the exact internal timed boundaries. formalPerfgateQualified and
officialEmbenchScore remain false, even if the numerical criterion passes.
Exact-boundary qualification, official driver integration and a measured
C-or-better result still require evidence. asher is offline and direct SSH times out at this
snapshot. No timing was performed locally and no performance win is claimed.

New measurement/configuration authoring has no applicable mechanical Amu
refactor rule. No compiler/product source is rewritten, no host fallback is
added and no refactor verify pass is claimed. Python and Clang are bootstrap
measurement tools; the measured Kotoba machine code is produced by native
selfhost Amu. Complete own-source/no-host-process 100% qualification remains
unmet.

Evidence: [summary](evidence/coscientist-suite-timing-20261005/summary.json),
[preparation artifacts](evidence/coscientist-suite-timing-20261005/preparation.tgz).

### 2026-10-05: CPU activity envelope

Darwin CPU tick deltas now accompany each measurement row. Missing/invalid
counters or idle below 90% refuse the run; the rejected row is retained.
Boundary/32-bit wrap/zero-tick/invalid-field checks and a live local counter
probe pass; wrong-host timing refuses under Python -O and PRODUCT stays 97.
Counters enclose runner setup, warmup and timing, so exact-boundary and
official-driver qualification remain unmet. No benchmark timing was taken.
API layout was verified against the installed SDK and
[Apple XNU host_info.h](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/mach/host_info.h).
