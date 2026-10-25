# Native optimization experiment cycle (JUN-27 / JUN-332 / JUN-358)

Apply the hypothesis generation, reflection, comparison, evolution and
meta-review method described in [Google Research's AI co-scientist report](https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/).
This is an adaptation to compiler experiments, not a claim of using Google's
service. A model's ranking decides which bounded experiment to try; measured
native evidence decides whether its result is accepted.

The continuing goals are native DefCID/SCC persistent incremental build and
at most 20 minutes for the complete PR native workflow with unchanged
compiler/core inputs. Preserve every qualification condition and the uncached
main/full chain. The preceding matched x86 compiler result (PR1577) and the
bounded DefCID codec (PR1581) are different milestones.

## Generation and reflection: initial hypothesis pool

| Candidate | Falsifiable mechanism | First experiment | Main objection / rejection condition |
|---|---|---|---|
| H10 | Another repeated SIR/proof traversal dominates the remaining core build | Coarse pass markers, then bounded proof markers on current source | Reject as a priority if not a substantial measured cost; do not cache CODE/FIX facts as immutable |
| H11 | A per-function range/summary index removes repeated immutable scans | Query-count/profile, then exact old/new oracle including suffix/accumulator/malformed inputs | Reject if the query depends on changing emission state or memory/resource bounds move |
| H12 | Most repeated proof queries fail identically and can share a negative result | Record complete query inputs/invalidation domains before implementing memoization | Reject incomplete keys, changed SIR, T2 rollback or hidden prefix dependence |
| H13 | DefCID/SCC objects avoid recompiling almost all of each one-guard mutant | Native checked producer, symbolic object relocations, persistent store and one-definition edit experiment | Codec alone is insufficient; reject stale dependencies, schema/ABI/layout/profile/resource-proof or approval replay |
| H14 | Smaller build granularity and early reuse shorten the critical path | Break group times into build, execution and dependency waits; compare real workflow completion | Reject replayed native verdicts, removed checks or unchanged workloads described as differential builds |
| H15 | Placement/slot contention explains part of CI variance | Same-host serial/two-slot and CPU topology experiment with fixed source/image/limits | Do not infer a speedup from different runners, lower load or simulated ordering |
| H16 | Repeated lexical/read/name work in parameter refinement can be shared | Measure all refinement passes, then prove an exact reusable frontend snapshot | Reject stale typed nodes, composite-type indices, failed hint/probe behavior or added memory bounds |
| H17 | Three implementation parameters left unannotated force six avoidable refinement retries | Screen each explicit `:string` annotation, then original/all/all/original with the identical producer and emitted bytes | This changes source workload, not the compiler algorithm; preserve unannotated inference coverage before adoption |

Advance candidates using expected removable time, evidence strength,
implementation cost and regression exposure. These are experiment priorities,
not measured performance scores. After each real experiment, preserve the
result including refusals, rejected hypotheses and uncertainty; revise the
next candidate rather than repeatedly testing an unsupported explanation.

H16/H17 were generated from native pass measurements, rather than assumed
before profiling: the original prefix performs seven lexical/read/name/check
rounds. The x86-image build spent most observed time in that repeated frontend,
while the core-container build was dominated by machine-code emission. These
are separate bottlenecks and need separate experiments.

`scripts/seed/compare-source-refinements.py` screens the three annotations
individually and then runs a same-host B/C/C/B comparison. It pins the producing
image and CPU, checks every generated image against the original qualified
image digest, and runs each positive/refusal entry afresh. No source, algorithm,
resource or output equivalence is inferred from the timing result alone.

## Native diagnostic protocol

`scripts/seed/profile-native-passes.py` instruments a separate compiler
image with entry/exit markers. It leaves production sources/images unmodified.
The workload is frozen at PR1577's merge revision, including every module of
core18 or the complete production prefix of the label-control fixture.
Both input and output hashes must match independently qualified artifacts.
Python stages source markers, launches Amu and timestamps stderr; Amu alone
checks, lowers and emits native code. No hosted compiler or format emitter is
introduced. Local heavy commands still use the shared two-slot admission.

Start with coarse pass markers, then trace proof candidates only if that pass
dominates. Recursive traversal bodies produce one outer marker span. Fine
markers perturb runtime and are only a localization aid. Report their image
hashes and load, never mix their elapsed times into performance comparisons.
The diagnostic compiler is a newly built static image; on ARM it is not the
packed adopted root, so absolute pass times also reflect that backend change.
Use unchanged producing images for the separate source-annotation comparison.
An unfinished span or timeout is incomplete diagnostic evidence, not a pass.

## Ranking and evolution gates

1. The native correctness/refusal/resource oracle passes before timing.
2. Compare uninstrumented baseline/candidate on the same actual native x86
   host and fixed workload, locks, environment, CPU policy and resource limits.
   Use alternating ABBA/BAAB runs to expose order/temperature effects.
3. Require complete native results and output parity for proof-implementation
   refactors; preserve the original full corpus. A microbenchmark or a warm
   cache hit does not establish a cold compiler/workflow claim.
4. Only a surviving candidate advances to the full native chain, affected
   source/image pin updates, review, merge, main readback and owned cleanup.
5. Measure the complete PR workflow separately. Keep runner queue delay and
   work time visible; a simulated schedule or individual job under 20 minutes
   cannot close the workflow goal.
