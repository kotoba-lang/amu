# Native iteration experiments (JUN-332 / JUN-27)

## Goal and method

Reduce native development latency without changing any qualification
condition. Compiler refactoring is authorized, but a source change must earn
admission through the same native, fixed-point, semantic and refusal gates.

The method follows Google Research's [AI co-scientist](https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/):
generate competing explanations, challenge them with a discriminator, rank
survivors by expected effect and cost, evolve a measured candidate, and review
its evidence. The hypothesis table is an engineering adaptation, not a claim
that Google's system or models executed these experiments.

## Registered hypotheses

| ID | Explanation and discriminator | Admission / falsification | State |
| -- | -- | -- | -- |
| H1 | The controller's Amu core rebuild dominates. Observe both sealed child lifetimes and CPU accounting separately from preflight, post-build validation and receipt finalization. | Dominant if rebuild is >90% of controller wall; reject that explanation if hashing/other phases dominate. | Confirmed:99.7% in native x86 run40170244993 |
| H2 | Unbounded independent gate fan-out adds CPU and memory contention. Compare the original scheduler with two admitted gate groups and the same commands, on the same host class/source/image. | No missing/altered gate or verdict. Record wall, CPU, queue time and RSS; do not infer speed from concurrency alone. | Bounded scheduler candidate |
| H3 | The static compiler's own implementation dominates rebuild cost. After H1, compare check versus compile, workload scaling and native CPU samples where available, then refactor the observed hot path. | Same native output, original correctness/fuel/arena/refusal corpus and full compiler self-rebuild. Rank an unqualified or regressing candidate below the baseline. | Await H1 |
| H4 | Late discovery of a local fault wastes complete builds. Run identities, native locked project controls and CDCI preflight before full qualification. | Broken lock/metadata or a failing gate must stop dependent full work. Local success must never stand in for full success. | Early preflight candidate |

The baseline is a previous successful run, 40151980803: controller-positive
3279.737s and the separate 24-case gate 4.198s. These are historical whole-call
times, not a measured decomposition or a speedup of the current candidate.

## Native x86 controller decomposition

[Run40170244993](https://github.com/kotoba-lang/amu/actions/runs/40170244993)
executes the actual controller and both roles on a4-CPU x86 Linux runner,
alone after fresh complete-compiler generations. The controller and gate
receipts are byte-identical to baseline run40165507318; production source,
public compiler and role images match. All24 cases,18 refusals and parent-death
cleanup pass. The preflight-only stage separately states that it does not
qualify the rebuild.

| Phase | Observed wall seconds |
| -- | --: |
| Controller preflight | 1.259 |
| Amu core rebuild child | **1736.053** |
| Post-build verification | 0.302 |
| Kotoba native gate | 3.479 |
| Receipt finalization | 0.051 |
| Total | **1741.145** |

The rebuild uses1735.89 CPU seconds during1736.05 wall seconds: one core is
effectively saturated. Its sampled peak RSS is457039872 bytes (about436MiB).
The controller's own CPU is1.922 seconds. Thus concurrent scheduling can
reduce waiting, while the remaining29-minute floor calls for compiler work.
The concurrent same-image baseline was2342.508 seconds. These are individual
observations, not a paired or statistically qualified speedup. Full bounded
scheduling acceptance still requires its own complete native CI.

## Scheduling

`seed/native-gate-plan.json` retains all14 independent command groups from
979049caf96a, including nested fail-closed shell pipelines. The runner admits
at most two groups and awaits every result even when one fails. Each group
has its own log and exit code. The collector alone writes schedule.json.
Worker-queue wait and shared-slot wait are recorded separately, as well as
their total and the phase-relative start/end. A zero slot wait alone does
not mean a later submitted gate had no wait in the worker pool.
The long controller / one-compiler group is queued first. The existing
per-PR supersession and uncached main/full tier behavior are unchanged.

For local heavyweight commands, from a task worktree:

```sh
python3 scripts/seed/native_build_queue.py --output /absolute/task/admission.json -- podman run --rm ...
```

All cooperating wrappers must share KOTOBA_NATIVE_SLOT_DIR and its capacity.
An already-running unmanaged container is not retroactively controlled. A
wrapper killed by SIGKILL leaves its live harness holding the inherited
slot until that harness exits. Remote/container daemon workloads after their
CLI itself dies are outside flock's lifetime: this is cooperative process
admission, not a host service or daemon-wide resource policy.

## Measurement boundaries

The controller observer uses /proc polling at50ms and wait4 accounting. It
preserves native stdout/stderr and the real exit code, and records a distinct
non-authoritative profile. Phase edges have polling/scheduling uncertainty;
the controller's own CPU combines hashing, IO and supervision. It does not
pretend to separate individual SHA calls or compiler frontend/backend work.
Final child CPU residuals may include one last controller sampling interval.
An interrupted run or missing child observation is not a complete profile.

Native x86 evidence comes from an actual x86 Linux runner. A local ARM VM
observer test or an emulated x86 process cannot qualify that measurement.
Busy-host exploratory measurements are labelled as such. A performance win
requires paired interleaved runs, source/image/argv/env pins, load records
and full semantic checks; unit tests and a pending CI do not establish one.

## Retained verification

All previous production manifests, adopted core modules, exact compiler/root
bytes,24 result/exit/fuel cases,18 CDCI refusals, parent-death cleanup, public
aliases/locks, ARM/x86 runtime controls, kernel/image/ABI suites and browser
Wasm cases remain. The additional fast preflight precedes bootstrap; a full
controller call still repeats all local controls before its real rebuild.
No JVM, Node, C compiler/loader, emulation or cached verdict is introduced.
