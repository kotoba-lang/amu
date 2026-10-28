# Native dynamic fuel attribution on complete Picojpeg

Local scalar hypotheses repeatedly failed the prospective timing acceptance
rule. To select a larger target, count the successful emitted fuel checks by
function on the complete, unchanged canonical Picojpeg workload. This diagnostic
collects dynamic execution counts, not exclusive CPU time or an Embench score.

The promoted native fixed-point seed compiles a diagnostic compiler from Kotoba
source. That native compiler builds the canonical benchmark. A diagnostic C
loader appends 8,192 counters after the original ABI v11 fields (offset 400,
measured by offsetof); none of the existing context field offsets change.
The backend stores the current function id in previously unused private scratch
field 13. After each original successful fuel check it increments that function's
counter using reserved x16. A failed charge never reaches the counter. Original
call, branch, return and fuel-check order remain; no result is memoized, and no
charge, bound or workload operation is removed. These one-off diagnostic algorithms
are not mechanical refactoring or product-path changes. The measured native
compiler route has no Node/JVM/nbb frontend fallback.

The compiler emitting instrumentation is native-built by the promoted fixed point;
it is a diagnostic compiler, not a promoted independently qualified three-generation
product. Instrumented execution uses the extended diagnostic loader, not the
performance runner. Its elapsed time must not be reported as comparable performance.

The first native SIR dumper refused `rem` with E2101 because it omitted the source
helper library appended by the real driver. Preserve that failure. The repaired
dumper appends the same `ck-r6b-lib` source, then runs the real frontend/lowerer.
Its function ids and names label the diagnostic counters, including appended
helpers; the timed canonical source remains unchanged.

At n=0/1/2/17/32, results match the promoted canonical baseline. Exact consumed
fuel is respectively 1 / 222,003 / 443,939 / 3,772,979 / 7,102,019. Every run's
sum of counters equals its exact consumed fuel. Counts include lowered self-tail
iterations and attribute inline helper charges to the function emitting them;
they are not necessarily function-entry/call counts. A one-body invocation
includes its original setup, so do not infer per-body counts for every function
simply by dividing the complete report by n.

| Function emitting charges | Successful checks at n=1 |
| --- | ---: |
| put8 | 60,492 |
| set-lane | 43,008 |
| zero-coefficients | 21,021 |
| fill-lane | 19,440 |
| pixel-clamp | 18,592 |
| lane-dc | 17,836 |
| multiply-idct, recent rejected compound target | 2,640 |

The top six account for 81.26% of checks in the one-body invocation. This changes
the next target selection: the small multiply helper has far fewer dynamic
charges than vector-writing/loop paths. Counts alone do not prove fuel or any
listed function dominates exclusive time. Previous rejected masked-store and
vector-descriptor candidates remain rejected; do not remeasure identical code.

Next hypothesis: prove and fuse a generic wrapper that computes a multiply/add
index, narrows a scalar value, and calls a proved in-place vector-write wrapper.
`set-lane` supplies an instance but its name must not enter admission. Retain the
existing checked handle/index/write path and all original optional fuel checks.
Unknown dependencies, effects and SIR shapes keep the old route. This could remove
substantially more dynamic call/frame overhead than the 2,640-charge multiply
helper; it is unimplemented and requires native proof and fresh paired timing.

Evidence: [counts and exact parity](evidence/coscientist-native-fuel-profile-20261005/profile.json),
[diagnostic backend](evidence/coscientist-native-fuel-profile-20261005/backend.diff),
[diagnostic loader extension](evidence/coscientist-native-fuel-profile-20261005/loader.diff),
[source, native binaries, raw output and preserved failure](evidence/coscientist-native-fuel-profile-20261005/native-diagnostic.tgz).
