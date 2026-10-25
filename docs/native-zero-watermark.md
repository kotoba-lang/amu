# Native item zero highwater (JUN-27 / JUN-332)

The native vector allocator cleared every requested item, including untouched
words of a fresh anonymous mapping. Every compiler process allocates the large
compiler memory vector, making this work visible even for tiny inputs. The
first PR1582 qualification took50m24s; its ARM bootstrap boundary corpus alone
used282.9s across206 process observations. That workflow has different runners
from earlier runs and is not a matched speedup experiment.

## Invariant and bounded change

The ARM/x86 templates reserve native private global byte offset760 as an
absolute item highwater. It starts at zero. `kxrt-vnew(off,n)` raises it to
`max(previous,off+n)` after successful descriptor construction. The five
arena checkpoints restore their original counters and never restore this
highwater. Allocation clears `[u,min(u+n,highwater))` and skips only the rest
of the requested range. Linux initializes fresh anonymous mapping contents
to zero ([Linux mmap manual](https://man7.org/linux/man-pages/man2/mmap.2.html)).

Audit each item writer: bulk copies/bytes/conj writes finish through `vnew`;
in-place writes remain inside an already described view. Region reservation
can leave untouched capacity, while a later append raises the highwater to
its actual described end. Any future item writer must preserve this invariant.
Restoration into a fresh mapping must account for restored item contents;
the optimization never permits treating reused nonzero words as fresh zeros.

The two native private contexts are separate from Wasm's context, which already
uses its own offset760. No Wasm source or public context layout changes. Keep
all item/vector/region limits, rollback counters, fuel, traps and refusals.
No new syscall, capability or hosted runtime is introduced.

For the prefix that still needs clearing, compute the item base and exclusive
byte end once. Advance an aligned cursor by8 until it reaches that end. The
same checked range is written, including its final word; count0 writes nothing.
This removes repeated base/address helper calls without caching a proof.

## Co-Scientist experiments

[Native run40213965826](https://github.com/kotoba-lang/amu/actions/runs/40213965826)
passed on actual x86/ARM. Each host used the same CPU and unchanged tiny source,
with eight fresh processes per batch in baseline/candidate/candidate/baseline
order. The baseline and candidate kernels were both built by native Amu. The
candidate reached a native self-rebuild fixed point. All32 emitted workload
containers on each ISA matched the baseline bytes.

| Host | Baseline median per compile | Candidate median per compile | Candidate/baseline batch ratio |
|---|---:|---:|---:|
| Native x86 |393.4ms|48.8ms|0.12492|
| Native ARM |955.9ms|10.4ms|0.01271|

These are tiny-process build results, not cold full-compiler or whole-CI speedup
claims. Scope reuse, partial old/fresh ranges, nesting and retained outer data
passed. Two independently built runtime-template mutants (missing highwater
and relative rather than absolute highwater) compiled successfully and exited1
under the actual native oracle. A compilation error cannot count as detection.

The earlier40213565810 attempt stopped before native execution because its
preflight checked offset760 across native and Wasm ABIs together. The corrected
guard audits only the two selected native templates. That failed preflight is
not included in performance/correctness samples. Portable successful native
observations are in `docs/evidence/native-zero-watermark-20261026/`.

[Run40218914293](https://github.com/kotoba-lang/amu/actions/runs/40218914293)
compared the reused-prefix loop separately on both native ISAs, holding the
highwater logic fixed. The source allocates1,048,576 items in32 scopes, checks
and dirties first/middle/final words, then repeats. Baseline/candidate resource
reports are byte-identical. On x86, median process time was0.6518->0.1500s
(ratio0.23016); ARM ratio was0.28514. Both scope oracles passed and a separately
built last-word mutant actually exited1. This is a bounded runtime workload,
not a whole-compiler or workflow result. An earlier local draft used a private
seed CLI helper as a guest builtin and failed compilation; that harness error
is excluded from measurements. The successful workload uses vector operations
only.

## Frozen compiler workload comparison

[Run40220687668](https://github.com/kotoba-lang/amu/actions/runs/40220687668)
measures the combined runtime change on exactly the same core18 source,
producer, CPU and limits, in baseline/candidate/candidate/baseline
order on each actual native host. All four outputs per ISA equal the normal
core container digest6ad407c2. Results differ from the tiny-process workload:

| Host | Baseline median | Candidate median | Ratio |
|---|---:|---:|---:|
| Native ARM |25.2516s|24.3024s|0.96241|
| Native x86 |152.5571s|154.8740s|1.01519|

ARM improved about3.8%; x86 improvement is not confirmed. Do not extrapolate
the tiny-process or clearing-loop percentages to whole compiler performance.
These two-pair measurements did not pass `--source-lock`; they do not measure
the locked controller route. They are a bounded experiment, not an official score.
The remaining compiler/CI goal needs additional mechanisms and measurements.

## Integration qualification remains separate

The production candidate rebuilds the Amu role and binds its new digest in
the native controller/factory. Normal core18/container bytes remain unchanged.
Native ARM FULL47 F2=F3 and core-generation agreement only qualify derivation;
all original runtime/resource/lock/controller/public/shared/browser gates must
still execute on the new pinned root/public images. The mandatory two-slot
plan adds the zero oracle and all three built/executed mutants on each native ISA.
No original gate is removed, and the uncached main/full chain remains.

The source/image bytes are now qualified by the fresh complete evidence
below; each final PR head must still pass mandatory CI. DefCID checked producers, SCC/object persistence and an actual PR
workflow at most20min remain open. A cache or experiment result is never an
admission, controller verdict, operation approval or deployment.

The combined candidate also passed local native ARM uncached full tier with
126 fresh calls, root reproduction, all core generations and the cold
C0->core/C0->Kw->Pw->F paths; read/store reuse was disabled. Full19/MIR/GMIR,
resource/lock validation passed146 fresh calls and18 named refusals. All27
guest containers equal the H21-only intermediate corpus byte for byte; the
native runner intentionally changes with its runtime. The seven released
arena fields are zero and the large MIR release count remains155,688,217.
These local results are not a substitute for fresh native x86/controller,
public aliases/source-lock90, shared UI or Chrome qualification in the PR.


## Native complete24 pin correction

The initial PR run40220599783 passed ARM, native x86 fixed point, runtime
controls and both complete label suites, but the native Kotoba gate refused
`gate-positive` with E4002. Its canonical24 image expectations still described
the earlier runtime. The complete compiler correctly emitted different ELF
bytes for the changed native runtime. No controller/public qualification is
claimed from this failed run.

Update only the24 image expectation hashes, preserving every source digest,
result, exit, fuel and native comparison. Cross-target native ARM builds must
match all24 images emitted on actual native x86. Rebuild and bind the Kotoba
gate, combined gate source, controller, factory, root and public compiler in
dependency order. Fresh native execution must still verify all24 numerical,
exit and fuel results, all refusals and parent-death cleanup.

The preflight now compiles the24 cases with the pinned public native compiler
and runs that same native Kotoba gate before expensive derivation. Wrong-image
and wrong-fuel ledgers must be refused with E4002. Python transports source and
records the native exits; it does not decide numeric correctness. Every later
full/controller/public/shared/Chrome check remains mandatory.


## Exact source/image qualification

[Run40223651906](https://github.com/kotoba-lang/amu/actions/runs/40223651906)
passed all five mandatory jobs for source990eccb59/head3bb81695c. All three
actual native x86 compiler generations match the public image. Both ISAs ran
the original24 label calls/nine mutants/unannotated control and the11 zero
calls/three executable mutants. The native controller passed24 cases,
18 refusals and parent-death cleanup; public entry exercised3 aliases and
90 source-lock boundaries; shared UI and Chrome also passed. Local uncached
full-v3 and full corpus-v3 passed on the same root. All27 guest containers
and the native runner equal the preceding runtime candidate bytes.

Controller wall time was338.245s; its Amu rebuild phase was331.551s. Complete
PR workflow duration was28m13s, so20min remains unqualified. Runner differences
prevent treating the earlier50m24s and this28m13s as a matched causal speedup.
Raw native receipt identities and source/image hashes are recorded in
`qualified-native.json`; that observer summary does not replace native verdicts.
Final metadata heads require fresh mandatory CI. No deployment is claimed.


## Locked-route regression screen and final metadata head

[Run40228776657](https://github.com/kotoba-lang/amu/actions/runs/40228776657)
compared the old8cd12aed and newdd289a23 public images on the same native
x86 EPYC9V74 host, CPU0, frozen core44faa79a, KSL1 lock and controller
environment (8MiB stack, no extra fuel/command override). Both emitted6ad407c2.
Old/new wall times were256.157/255.229s (ratio0.99638). The initial pair did not
meet the predeclared5% trigger for an ABBA extension; no broad speedup or
statistical equivalence is claimed from this two-call regression screen.
The external controller sandbox was not applied in this diagnostic.

[Final source/image metadata run40226249485](https://github.com/kotoba-lang/amu/actions/runs/40226249485)
passed all five mandatory jobs atd38bfaf07. Controller wall time was469.232s,
with462.185s in Amu rebuild. The complete PR workflow took34m11s; the earlier
source/image qualification took28m13s on different runners. Both observations
leave the20min whole-CI goal open. Codec40226249494 passed on both native ISAs.
The subsequent documentation correction changes no source/image/policy bytes.
