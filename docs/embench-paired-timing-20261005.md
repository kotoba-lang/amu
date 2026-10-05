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

Add --measure only on the pinned host (currently jacob). Measurement rotates C/Kotoba order across 30
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

The tool records Darwin PROCESSOR_CPU_LOAD_INFO tick differences around each
runner invocation, including setup/warmup and enclosing the timed interval.
Raw host idle and estimated background idle are both retained. Background idle
adds the waited runner child's user/system CPU share back to raw host idle,
using elapsed envelope time and logical CPU count. Estimated background idle
below 90% refuses; missing/nonadvancing counters refuse as well. This avoids
counting the benchmark's own intentionally busy core as unrelated host load.
This is an enclosing CPU envelope, not counters at
the exact internal timed boundaries. formalPerfgateQualified and
officialEmbenchScore remain false, even if the numerical criterion passes.
Exact-boundary qualification, official driver integration and a measured
C-or-better result still require evidence. The original preparation snapshot
had asher offline with SSH timeouts. Subsequent jacob attempts are documented
below. No timing was performed locally and no performance win is claimed.

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

### 2026-10-05: alternate-host preparation

The live Tailscale inventory identified jacob as an SSH-accessible Apple M4
with 10 cores. Its load at the environment probe was 2.14/2.50/2.69;
this single observation does not qualify sustained CPU idle. It runs macOS
26.3.1 (a) and Apple Clang 21, so its C baseline must be rebuilt and kept
separate from the historical asher/Clang 17 baseline. The timing spec now
pins jacob, with all numerical acceptance thresholds unchanged.

A 10,368,922-byte input archive is prepared locally. Automatic approval
review rejected its transfer because explicit authorization to send the
internal source/compiler/runner payload to jacob was missing. No transfer or
remote benchmark execution occurred. User approval is pending. The archive
hash and observed host details are recorded in
[preparation evidence](evidence/coscientist-jacob-preparation-20261005/preparation.json).
Wrong-host measurement still refuses under Python -O before creating output.
These are preparation results, with no new performance claim.

The revised configuration was then exercised locally without timing: all 19
C/Kotoba pairs passed two calls and one warmup, and the native code hashes
matched the qualified matrix. Results and generated artifacts are retained
in the same evidence directory (`local-results.json`, `local-preparation.tgz`).
The first restricted execution failed at the compiler's sandbox initialization;
the successful rerun used local execution outside that restriction and made no
network transfer. This does not prove jacob execution or performance.

### Authorized jacob execution and instrumentation corrections

The user explicitly authorized transfer and measurement, including necessary
follow-up work. The input archive was transferred to jacob. All 19 pairs then
passed native-source check, compile, qualified machine-byte comparison and
C/Kotoba repeat/warmup verification there, using native selfhost Amu and
Apple Clang 21. Three attempts exposed instrumentation issues before a
complete timing run: short correctness probes had no advancing CPU ticks;
raw host idle counted the benchmark's own core (86.77% on the first rejected
row); and consecutive intervals encountered cached host_statistics results.
Their failed results remain separate from subsequent runs.

Only actual measurement rows now capture CPU counters. Background-idle
accounting retains raw idle, child CPU nanoseconds and logical CPU count;
the 90% requirement now applies explicitly to the background estimate, not
raw host idle. This is a documented change of metric, and does not retroactively
qualify the failed rows. The estimate is not exact-boundary qualification.
The counter API now uses host_processor_info/PROCESSOR_CPU_LOAD_INFO, with
returned memory released through vm_deallocate. The installed SDK declarations
and [Apple XNU implementation](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/kern/host.c)
confirm host_statistics caching/rate limiting and the per-processor route.
Twenty consecutive local 60-ms intervals advanced. Synthetic child-share,
zero-child, negative-time, invalid-core-count and over-capacity cases passed.
The fourth remote attempt uses these revised rules; its status must be read
from retained results rather than inferred from launch success.

The fourth attempt stopped after nine retained rows, when estimated background
idle fell to 82.55% (raw idle 72.60%). It completed no 30-pair workload and
supports no aggregate performance result. All four attempts and the latest
script/spec provenance are retained in
[execution evidence](evidence/coscientist-jacob-execution-20261005/summary.json).
Configured SSH usernames also corrected the earlier mistaken classification
of eight other Macs as inaccessible. A three-second read-only CPU probe found
zebulun at 96.69% idle, but its proposed source/compiler transfer was rejected
by automatic review as a different destination from the explicit jacob
approval. User approval for zebulun is pending; no transfer occurred. The
committed timing host remains jacob. No C-or-better or official score is claimed.
