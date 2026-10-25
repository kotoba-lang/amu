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

## First cycle: measured outcomes

The [native x86 annotation tournament](https://github.com/kotoba-lang/amu/actions/runs/40207570673)
used one Xeon 6973P-C host, CPU0 and the same admitted public compiler image.
Baseline/all/all/baseline build times were 36.6722 / 11.1885 / 11.2947 /
36.6657 seconds. Medians are **36.6689 -> 11.2416 seconds (69.34% less)**.
All seven screened/alternating images matched the pre-existing whole-image
digest and each ran both its semantic and wrong-mode entry afresh. Native
ARM with its own unchanged packed producer measured 20.9625 -> 6.2818 seconds.
These results concern the full-prefix label-oracle source, not a whole CI run.

Adopt H17 as a candidate source refactor: make the three implementation
parameters explicit without changing checker bodies. Retain the full original
unannotated-source build, whole-image equality and execution/refusal controls
in the mandatory native label gate. Its existing nine mutation controls stay;
the gate grows from 21 to 24 fresh calls. Regenerate root/public/controller
pins because source and controller source-lock identities change, even though
the normal core container/raw image and Amu selfhost role remain byte-identical.
Native ARM candidate F1=F2 and two core generations agree. The subsequent
uncached full/core/cold/corpus and native x86/controller/public qualification
passed for these source/image bytes; final PR heads still require mandatory CI.

The [native x86 proof localization](https://github.com/kotoba-lang/amu/actions/runs/40207573562)
supports H10: `ccf-code` and `ccf-fixes` each ran 2,484 times, consuming
35.93 and 25.00 instrumented seconds respectively. They scan mutable output.
Reject H12's proposed query/count-only prefix key: a native counterexample
keeps the query and CODE/FIX fill counts unchanged while rewriting a prior
word to ADRP, a forward branch, a negative or an oversized word. The original
validator refuses each rewrite and accepts restoration. Direct vector writes
also exist outside `gn-put`; a future write-aware revision must cover them.
This refutes that key, not every possible prefix optimization. No mutable
prefix memoization was adopted.

H13 remains open: the separately qualified DefCID codec is not a checked
frontend producer, SCC object store or persistent incremental build. H14/H15
need actual whole-workflow timings after this candidate; neither the short
unit build nor an estimated parallel schedule closes the 20-minute goal.
Portable observations, producer/source/image hashes and the rejected-key
counterexample are in `docs/evidence/native-source-refinements-20261026/`.

## Qualification and the remaining workflow goal

[Run 40209874933](https://github.com/kotoba-lang/amu/actions/runs/40209874933)
passed every native ARM/x86/shared/Chrome job for source head `8fbbaf3e27`.
The public image agrees with all three actual native x86 generations. The
native controller ran 24 cases, 18 refusals and parent-death cleanup; public
validation exercised all three aliases and 90 source-lock boundary cases.
Both ISAs executed the original nine mutants and the new unannotated-source
build/image-equality/execution controls. Local ARM full-tier provenance used
no read/store reuse, and all19/MIR/GMIR/resource/lock checks passed. All 28
emitted corpus artifacts equal the preceding qualified artifacts byte for byte.

The controller observation is 468.687 seconds, separately below the ten-minute
compiler target. The complete PR workflow was **50m24s**, so the twenty-minute
goal is **not met**. Its ARM job was 21m43s: bootstrap9m51s and independent
gates8m02s, plus runtime/live/transport work. The bootstrap's boundary corpus
alone used 282.9 seconds across 206 process observations. Different runners
prevent treating this workflow duration as a matched before/after experiment.
The exact metadata, native receipt digests and source/image pins are recorded
in `qualified-native.json`; neither that observer summary nor a cached artifact
replaces fresh native admission or any mandatory check.

## Evolving H13: native checked identities and SCC search

The next discriminator is a real native checked producer, before attempting
objects/store reuse. The pure KIR prototype runs the existing native checking
pipeline and refuses missing schema/effect bridges. It is outside FULL47 and
does not yet identify the complete Seed compiler source graph.

| Candidate | Prediction and discriminator | Native ARM screen |
| -- | -- | -- |
| Immutable member templates and empty/single dependency-sort bypass | Eliminate repeated normalization and needless sorting while preserving all canonical payloads | Combined SCC8 screen346.138s to67.836s; all group/member CIDs match an independent native oracle |
| Compare at the first differing member | Avoid constructing the remainder of each permutation's payload; exhaustive search and tie order stay identical | Same SCC8 1.355s; native full-payload differential and executed mutation controls pass |
| Persist native symbolic objects | Reuse unchanged DefCID/SCC emission with all context sealed and fresh admission | Not implemented; no cache or whole-CI qualification from the identity prototype |

The first timings are local unpaired screens, not cold-compiler or workflow
gains. A separate same-input/producer/CPU ABBA experiment compares template
full-payload versus member-prefix comparison. Both variants still examine
all40320 permutations. The full normalizer is retained as a native oracle,
and a manually authored SCC8 forces the canonical winner to permutation40319.
Native x86 qualification and the remaining end-to-end goal remain required.
See `docs/native-incremental-build.md` and the checked-DefCID evidence folder.

The local native ARM ABBA result isolates the prefix comparator call-site
change with both variants using the same immutable templates and all40320
permutations. CPU0, compiler, input and environment are identical: baseline
68.186/67.826s, candidate1.338/1.338s; medians68.006 to1.338s (ratio0.019677).
Every complete group/member output is byte-identical. This is a bounded SCC8
identity workload on the local native ARM VM, not a quiet-host publication,
cold compiler measurement or whole-workflow gain. Different ISA/compiler
results must be recorded separately rather than inferred from this ratio.
