# Exact masked vector writer: native transaction proof and timing

Promoted after native proof, qualifying quiet timing, six gates and integrated product verification. C-or-better remains unachieved.
This registered experiment changes only Picojpeg's machine code; the18 other
canonical workloads remain byte-identical. All19 original sources are unchanged.

## Implementation

Recognize exactly three natural parameters, entry FUEL, AND255 of the third
argument, a direct call to the existing proved charged in-place vector writer,
and scalar RET/END. Reject uncharged wrappers, other masks, extra/unknown shapes,
RES2 and caller temp height>4. No source/function/benchmark names select behavior.
This is one-off compiler algorithm authoring, not mechanical source refactoring.

The new recognition stays outside prescan's gn-call-wrapper: the caller retains
its original nonleaf classification, frame and fuel publication. Inlining uses
free x0/x8 in that retained nonleaf caller and pinned argument temps/locals.
It restores the original context, loads the callee fuel transaction into x8,
retains both original unit decrements and zero-publication exhaustion traps,
masks the value, checks handle/index and writes. Only successful return publishes
x8. A bounds trap retains pre-call fuel exactly. It does not replace this with
caller gn-op-fuel, batch/precharge fuel, remove bounds checks or reuse old outputs.

Producer is the qualified scalar-tree seed824,952 bytes, SHA-256
`98905d4a7c3da0d94465d99f4b32ae195c2e7972d1b995a3744a0d588595635d`.
Native generations2/3/4 reproduce826,744 bytes, SHA-256
`ff6ac028ee32572b88c517daaccf78f823596f3986d588f98c9ae5c5a4298df1`,
with main offset0. Picojpeg code grows43,084 ->47,900 bytes (11.18%). This cost
was known before timing; smaller call overhead does not automatically imply
faster execution.

## Native proof

All19 result/exactfuel/exhaustion comparisons pass for0/1/2/17/32 bodies and
fuel1. Full Pico workspace after1/2 bodies matches across8,192 cells.
Existing1,979 native executions pass across279 expanded fixtures; independently
native-built test/real emitted layouts match. All8,264 full supervisor reports
and owned partial vector arenas match. The suite includes2,776 existing partial
state/trap cases and5,488 masked-writer cases: negative/edge i64 values, indices
-1/0/1/3/4/MIN/MAX, fuel1..7 and large budget, valid first write then possibly
invalid second write, live temps at0/1/4 and fallback at5, charged/uncharged
outer/inner wrappers, other mask, and real unknown predecessor call.
Instruction audits confirm six admitted callers, two leaf transactions each,
exact zero-exhaustion sequences, success publication and unchanged caller
prologues. Refused shapes retain calls.

Three diagnostic repairs strengthened evidence without changing compiler or
workload bytes. The last-fixture scan first included unaligned literal pool
bytes; it now uses emitted code words. The first unknown predecessor was an
already admitted identity; it now uses ADD1 so a real call remains. Context
slot0 is at framebytes-8 rather than byteoffset0; the audit resolves the actual
STR x7 slot and requires its matching LDR immediately before the first leaf
transaction fuel load. Original failed notes/first emitters and final proofs
are retained. A re-used test output directory also required exist_ok. The
first native compiler invocation inside the outer sandbox failed sandbox_init;
the same bytes execute through the authorized native loader boundary.

## Fresh timing against original C

Host zebulun Apple M4; unchanged canonical source/C/runner pins. Only changed
Picojpeg is timed, avoiding repeated identical-code trials for18 unchanged
workloads. Thirty accepted rotating product/prototype/C triples from
31 attempts, fixed90-attempt cap, target300ms/minimum50ms,
load<=4, estimated background idle>=90%, each arm RSD<=10%. All calibration,
rejection and raw rows are saved; an independent audit recomputes acceptance,
means and SDs. Prospective qualification is >=1.05 speedup and mean gain greater
than summed SDs, with no separated regression across changed workloads.

| Arm | Mean us/body | RSD |
| --- | ---: | ---: |
| Qualified product | 236.314 | 2.19% |
| Prototype | 220.984 | 2.29% |
| Original C | 10.808 | 0.88% |

Product/prototype=1.06937x; prototype/C=
20.44584x. Mean gain=15.330us versus summed SD
10.249us. Timing qualified: True.
These are aligned freshly executed whole-body measurements, not official
Embench scores, formal perfgate or a newly measured all19 geometric mean.
C-or-better remains unachieved. Product source and regression goldens are updated; rung pins and bin/amu
remain unchanged. The qualified integrated image is rebuilt below.

Evidence: [summary](evidence/coscientist-masked-writer-20261005/summary.json),
[prototype](evidence/coscientist-masked-writer-20261005/prototype.diff),
[native proof](evidence/coscientist-masked-writer-20261005/native-proof.tgz),
[fresh timing](evidence/coscientist-masked-writer-20261005/timing.tgz),
[independent audit](evidence/coscientist-masked-writer-20261005/timing-audit.json).

## Product promotion and integrated qualification

Source commit `3510b765960f8010be0a84a8863fc1e565e9b3b2` contains the new
backend and21 regression fixtures. Hand-derived expectations also read the stored
masked value, preserving signed extremes, valid/invalid indices, live temps and
low-budget traps. All2,363 native product runs pass across206 fixtures; generated
test/real layouts match, and the product golden comes from actual native execution.

ERR and G1-G5 (six gates) pass at r6m, including84 byte-identical generation
corpus/port containers and a G5 interposer canary plus60 seed commands without
program starts. These are six gates, not all rung release gates. Bootstrap
inventory before/after is identical. First unit source-scope and G1 source-scope
failures are retained: the harness initially omitted its authorized temporary or
adjacent original-port directory. Repair only the resource-root configuration;
G1/G4 were rerun after this evidence-based diagnosis, not to seek better timing.

The launcher builder snapshots Git HEAD, so the source commit precedes rebuilding.
Using the same content-pinned frontend/compat input snapshot, integrated native
command, code/container and all162 objects match across3 generations. All117
frontend modules rebuild. Image SHA-256 is
`711f9d40e7dc51092b307cd34550176061ccf865edafc292ffeebc5177812019`.
Its check/compile/extract of all19 original sources exactly reproduces each
measured candidate native binary and entry offset. The rebuilt source snapshot
contains the actual promoted backend, not the old Git source.

Every classification/exit/result matches the previous qualified scalar-tree
product on391 check rows,391 compile rows and891 export comparisons. Check:
358 accept/33 refuse; compile:300 behaviour-same,27 Amu-only accept,12 Amu-only
refuse,3 differing accepted behaviour,49 shared refusal. Exports:875 same,
15 existing differences,1 existing missing,0 timeouts. Existing gaps remain;
these counts do not claim complete language/selfhost coverage.

[Integrated qualification](evidence/coscientist-masked-writer-20261005/integrated-summary.json),
[six gate outcomes](evidence/coscientist-masked-writer-20261005/gates.tsv),
[product validation artifacts](evidence/coscientist-masked-writer-20261005/product-validation.tgz).
External input source snapshots stay local; archived hashes and generated native
artifacts preserve the evidence boundary.

The next registered experiment proves context-register preservation through
exact direct callees/dependencies and elides only redundant caller reloads.
Unknown effects, runtime calls, allocation and callbacks retain legacy invalidation.
Caller frame/classification, call ABI and fuel/trap/publication points remain.
This is [registered](evidence/coscientist-masked-writer-20261005/next-hypothesis.json),
unimplemented and unqualified here; changed workload timings and full native
proofs are required before another promotion.
