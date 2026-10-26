# Native proof-scan refactor (JUN-332 / JUN-27)

The refactor targets the original full core18 cold compile, with a
600-second goal on the same actual native x86 host. It does not substitute a
cached verdict for any compiler, controller, main/full-tier, resource or refusal
gate. FULL-MANIFEST47 and both core18 manifests retain every module.

## Hypothesis and controls

The previous unmodified controller spends 99.8% of its wall time in one compiler
child. Native marker diagnostics now distinguish helper execution from the name
of the source function being emitted. ARM's 240-second, right-censored probe
observed 1,560 outer `gn-small-label` calls, with 123.97 seconds in those scans.
Actual x86 run40182962542 likewise observed 1,309 calls /111.007 seconds in
a 240-second censored probe. A follow-up ARM CCF-only probe observed 2,035
`ccf-label-source` calls /133.657 seconds, versus 141.5 seconds in CCF.
The cold frontend and uninstrumented portions are outside those totals. This is
exploratory cost attribution, not an x86 speed result or a qualification verdict.

`glx-prepare` builds a private unique-label table after clw/trg/alen/cpp preparation.
The old scan is retained verbatim under a private name. Only `(start=1, found=0)`
queries against the indexed immutable large module use the table. Zero denotes
missing; -1 denotes duplicates, which still return zero. Arbitrary suffixes and
accumulators execute the original scan. Invalid label bounds refuse as before.

The table is restricted to SIR counts above `t2-max-sir` and at most SIR capacity.
T2's `t2-fn-mark` and `t2-end` both exclude those large modules, so its private
SIR rewrites cannot stale this index. clw/trg rewriting finishes before index
construction. G storage, table extent and SIR extent are checked before lookup.
The table temporarily uses 131,072 existing heap words (1 MiB). The existing
alen-state cell is reused only in the disjoint large-SIR domain; the original
G allocation size is retained. If the table does not fit, scans remain unchanged.
After emission its words are zeroed and its bump allocation is released. No heap,
fuel, stack or other arena capacity is raised. This internal memory cost must
remain visible in admission and whole-closure qualification. The native oracle
also checks optional no-room fallback, zeroed release and restored heap top.

The native test entry retains the full production core prefix and the independent
old scan oracle. It exercises duplicates, absent and endpoint labels, invalid
bounds, suffixes, positive/negative accumulators, stale extents and the small-T2
fallback. CCF reuses that identity but rechecks its own excluded source window and B/C
operands. Mutants removing duplicate detection, suffix binding, accumulator
binding, CCF suffix binding, extent freshness, the CCF window, its reserved
operands, the top-of-heap release guard and optional heap fallback must compile successfully and then fail semantic
execution. A deliberate wrong-mode control must also fail.

`scripts/seed/compare-proof-scans.py` stages the baseline revision from Git,
builds both C0 images through the admitted public compiler, and compiles the
same original normal core18 source and lock in ABBA order. One CPU affinity,
producer, environment, target, limits and output digest are fixed. It records
host CPU model, kernel, cgroup limits, wall/CPU times and load. Outputs must be
byte-identical to the existing admitted core container. This comparison is
separate from rebuilding and qualifying the changed compiler's own source.

## Content identity and incremental builds

[Unison's immutable definition identity](https://www.unison-lang.org/docs/the-big-idea/)
supports reuse of unchanged definitions and their dependencies. Kotoba's
[definition identity contracts](adr/0300-definition-cids-are-computed-by-the-compiler-and-key-the-cache.md)
specify canonical DefCID/SCC identities; their older hosted Wasm implementation
is historical context, not an available native fallback. Amu's current process
artifact reuse binds exact process inputs. Neither establishes that the current
native emitter computes, persists or reuses per-definition native objects.

This candidate first removes redundant work inside a fresh cold compile. A later
native incremental path must bind checked IR plus dependency/SCC identities,
compiler image, target, ABI/layout, optimization profile and resource/proof
contract; relocate function/literal/fixup identities; revalidate artifacts and
fresh admission; and retain the uncached qualification tier. Whole-program,
current-frame and code-prefix facts cannot be keyed on a callee body alone.
Effectful operations and controller decisions are not memoized by code identity.
Warm reuse and cold algorithm timings must remain separate.

## Same-host cold compile result

[Native x86 ABBA run40185477832](https://github.com/kotoba-lang/amu/actions/runs/40185477832)
completed on one AMD EPYC 9V45 host, fixed CPU0, with the same admitted producer,
original normal core18 input, lock, target and limits. Baseline times were
1,024.688 /1,000.756 seconds; candidate times were182.958 /183.731 seconds.
The candidate median is18.10% of baseline (81.90% less time,5.52x). Both cold
candidate samples are below600 seconds; every output matches the original
admitted container. The native Amu controller-role image built for adoption is
byte-identical to the timed candidate. These are this workload's whole-process
times, not a universal project or workflow build time. See
[portable process observations](evidence/native-proof-scan-20261025/same-host-x86.json).

## Native qualification and remaining iteration cost

[Corrected native CI40191488005](https://github.com/kotoba-lang/amu/actions/runs/40191488005)
passed all five jobs. Current-source x86 controller observations record534.273
seconds in the compiler rebuild and541.429 seconds for the complete controller,
including its24-case gate, below ten minutes. This is an absolute observation
on that CI host, separate from the paired same-host algorithm comparison above.
The public image equals native F1=F2=F3; three entrypoints and90 source-lock cases,
18 native refusals, parent-death cleanup, Chrome and shared text/DOM/text-edit
passed. Both ISAs passed all nine successfully built guard-removal mutants.

The exact selected ARM root also passed the uncached full tier: G1/G2/G3,
packed core and C0-to-Kw-to-Pw-to-full provenance, with no read/store/reuse cache.
C0's current core rebuild took395.4 seconds; static core took431.8 seconds.
Fresh execution on that final root passed all19 workloads, locked MIR/GMIR,
resource and refusal probes (146 calls/18 refusals). The large MIR probe released
155,688,217 scopes and retained zero in each checked resource category. All22
benchmark/linked containers and runner match the intermediate root's outputs.
The memory-map generator preserves its output and both native routes' six
refusals. No capacity or limit was increased.

See [native qualification observations](evidence/native-proof-scan-20261025/qualified-native.json),
[raw controller profile](evidence/native-proof-scan-20261025/controller-profile.json),
[uncached ARM full observations](evidence/native-proof-scan-20261025/native-arm-full.json),
[final-root corpus](evidence/native-proof-scan-20261025/final-root-corpus.json) and
[native derivation chain](evidence/native-proof-scan-20261025/native-derivation-chain.json).
The selected adoption receipt and qualification annotations reference the
verified images and source graph; broader public compatibility and deployed
behavior remain separate.

The x86 label-proof controls now dominate21-minute independent gate scheduling:
1,113.177 seconds rebuilding test images and81.130 seconds executing semantic
controls. All21 calls still run. Independent groups are ordered by their
observed work, retaining every argv and the same two slots. A fixed-runtime
simulation predicts ARM849.118 to734.961 seconds and x861265.142 to1232.136
seconds. These are scheduling estimates, not measured speedups; GitHub hosts
vary. See [ordering observations](evidence/native-proof-scan-20261025/gate-ordering.json).
The whole PR CI took about73 minutes; the separate20-minute iteration goal
remains open. Persistent native per-definition object reuse remains future work.
