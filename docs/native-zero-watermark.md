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

## Integration qualification remains separate

The production candidate rebuilds the Amu role and binds its new digest in
the native controller/factory. Normal core18/container bytes remain unchanged.
Native ARM FULL47 F2=F3 and core-generation agreement only qualify derivation;
all original runtime/resource/lock/controller/public/shared/browser gates must
still execute on the new pinned root/public images. The mandatory two-slot
plan adds the zero oracle and all three built/executed mutants on each native ISA.
No original gate is removed, and the uncached main/full chain remains.

The source/image flags remain candidate/unqualified until fresh full evidence
passes. DefCID checked producers, SCC/object persistence and an actual PR
workflow at most20min remain open. A cache or experiment result is never an
admission, controller verdict, operation approval or deployment.
