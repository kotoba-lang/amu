# Native proof-scan refactor (JUN-332 / JUN-27)

The pending candidate targets the original full core18 cold compile, with a
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
binding, extent freshness, the CCF window, its reserved operands and optional
heap fallback must compile successfully and then fail semantic
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
supports reuse of unchanged definitions and their dependencies. Amu already has
canonical DefCID/SCC source contracts and exact process-input artifact reuse.
Those are foundations, not proof that the native emitter already persists and
reuses per-definition native objects.

This candidate first removes redundant work inside a fresh cold compile. A later
native incremental path must bind checked IR plus dependency/SCC identities,
compiler image, target, ABI/layout, optimization profile and resource/proof
contract; relocate function/literal/fixup identities; revalidate artifacts and
fresh admission; and retain the uncached qualification tier. Whole-program,
current-frame and code-prefix facts cannot be keyed on a callee body alone.
Effectful operations and controller decisions are not memoized by code identity.
Warm reuse and cold algorithm timings must remain separate.

## Status

Candidate only. ARM semantic and nine mutation controls have passed after the heap-boundary
review repair; same-host
native x86 comparison and whole-closure qualification are in progress. No root,
public, controller or consumer pin is adopted by this document.
