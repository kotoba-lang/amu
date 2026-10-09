# Direct-callee context preservation: native proof and all19 comparison

The corrected native product passes all19 timing acceptance, native gates,
explicit import-substitution regression and three-generation integrated rebuilding.
UD is the only individually qualified improvement; no separated regression.
Initial integration failed and was not promoted; the boundary correction below
is part of the qualified source, not an optional follow-up.

## Hypothesis and bounded proof

Existing direct calls invalidate knowledge of context register x7, requiring
reloads from the caller frame before subsequent fuel/checked operations. Prove
from exact typed SIR that a direct callee and every admitted dependency preserve
input x7. Keep the actual call and caller classification/frame/ABI, only keep
context knowledge after the real call if this fact succeeds. Selection never
uses source/function/benchmark names or effect text guessed from syntax.

Proof traverses complete function records and requires matching FN signature
and END, <=7 arguments, depth<=8 and a shared512 total instruction-work budget
across all transitive bodies. Cycles that cannot finish that finite proof refuse.
Scalar arithmetic/locals/control/returns, fuel, constant-table access and function
addresses do not write x7. Only exactly admitted inline runtime vector/pair
operations pass. Allocation, capability calls, indirect calls, strings/unknown
runtime operations and other opcodes refuse. Control/label scope and types are
those of checked SIR (seed/SIR), not an admission API for arbitrary malformed
machine IR. Exhausting either proof limit uses legacy context invalidation.
No ABI, decrement, bounds check, commit point or guest observation changes.
This is one-off compiler algorithm authoring, not mechanical refactoring.

Producer is the qualified masked-writer native seed826,744 bytes, SHA-256
`ff6ac028ee32572b88c517daaccf78f823596f3986d588f98c9ae5c5a4298df1`.
Native generations2/3/4 reproduce802,888 bytes, SHA-256
`cf32f7c8bc00f418110c0dccc4419d520aeac0becc694c344925109713d8b24a`,
main offset0. First generation827,984 bytes is distinct; it is not represented
as the fixedpoint. Reduced compiler bytes alone do not prove execution or
compilation-time improvement; the transitive proof also adds compile work.

## Native state and adversarial restoration evidence

All19 canonical sources preserve results/exactfuel at0/1/2/17/32 bodies and
fuel1 exhaustion. All19 machine codes change. Pico code47,900 ->47,660 bytes;
all8,192 workspace cells after1/2 bodies match.

Existing2,363 native executions pass across304 expanded fixtures; independently
native-built test/real emitted layouts match. All3,262 full supervisor reports
and owned partial vector arenas match:2,776 existing lowfuel/partial-write/trap
cases,378 targeted preservation/refusal cases and108 adversarial x7-clobber
cases. Tests include scalar and inline vector callees, a transitive chain,
allocation/capability/indirect-call refusal, a cyclic graph and depth/work limits,
signed/index extremes, low fuel, division/bounds and real caller restoration.
Independent machine audits retain actual direct calls in all nine neighborhoods,
remove only the reload before the next caller fuel for three admitted callers,
and retain it for six refused callers.

The diagnostic loader uses the original vector allocator then sets caller-saved
x7 to0x7bad through a native assembly veneer. It never participates in timing.
A control binary NOPs exactly one retained restoration after a real allocating
callee; it fails while the unmodified candidate succeeds. This canary verifies
actual clobbering/restoration, rather than incidental C register preservation.

Supplementary fixture repairs are retained: CAP/FADDR require numeric SIR
operands; the test-only layout initially lacked ADR19 function fixups (9998).
Only that supplemental emitter is extended, and independently compared with
real42-layout. A last-function audit initially used candidate code length for
larger baseline and truncated the last call; each image now supplies its own
instruction-word end. Existing native runs/layout had passed; resuming the
same emitter outputs completes the audit/state checks. Candidate compiler and
canonical workload bytes never changed during these diagnostic repairs.

## Fresh current-product / prototype / original-C comparison

zebulun Apple M4. Current product machine code, canonical sources, original C
binaries, matrix and runner are pinned. Every changed workload is measured once
in this experiment;30 accepted rotating triples each,570 accepted from600
attempts. Target300ms, minimum50ms, load<=4, estimated background idle>=90%,
RSD<=10%, maximum90 attempts per workload. Keep all calibrations/rejections.
Independent audit recomputes quiet conditions, arm means/SDs and qualification.
At least one workload must clear >=1.05 and gain>summed SD, all arms stable,
and no changed workload may show a separated regression. Noise-only ratios
cannot support an individual improvement claim. No unchanged-code retiming.

| Workload | Product us/body | Prototype us/body | C us/body | Product/prototype | Prototype/C | Qualified gain |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| picojpeg | 221.078 | 221.155 | 10.796 | 0.99965x | 20.4844x | no |
| aha-mont64 | 1.106 | 1.063 | 0.544 | 1.04029x | 1.9526x | no |
| crc32 | 3.919 | 3.969 | 1.707 | 0.98725x | 2.3252x | no |
| depthconv | 0.123 | 0.123 | 0.035 | 0.99819x | 3.5219x | no |
| edn | 11.981 | 11.494 | 0.761 | 1.04237x | 15.1036x | no |
| huffbench | 55.637 | 55.494 | 7.431 | 1.00257x | 7.4681x | no |
| matmult-int | 22.666 | 22.595 | 0.954 | 1.00313x | 23.6894x | no |
| md5sum | 14.241 | 14.243 | 2.526 | 0.99987x | 5.6380x | no |
| nettle-aes | 25.614 | 25.777 | 1.419 | 0.99365x | 18.1622x | no |
| nettle-sha256 | 3.057 | 2.950 | 0.223 | 1.03654x | 13.2506x | no |
| nsichneu | 0.707 | 0.712 | 0.080 | 0.99294x | 8.9416x | no |
| qrduino | 275.289 | 281.350 | 22.338 | 0.97846x | 12.5954x | no |
| sglib-combined | 41.760 | 41.399 | 5.853 | 1.00871x | 7.0736x | no |
| slre | 7.966 | 7.908 | 1.056 | 1.00726x | 7.4890x | no |
| statemate | 0.769 | 0.765 | 0.032 | 1.00448x | 24.1366x | no |
| tarfind | 14.223 | 14.387 | 1.010 | 0.98859x | 14.2485x | no |
| ud | 0.592 | 0.543 | 0.054 | 1.09063x | 9.9624x | yes |
| wikisort | 221.442 | 204.093 | 15.243 | 1.08501x | 13.3891x | no |
| xgboost | 1359.021 | 1381.173 | 185.501 | 0.98396x | 7.4456x | no |

All19 aligned custom geometric time ratio is1.01235x
product/prototype; prototype/C is9.28044x. These are freshly
executed whole-body comparisons, not official Embench scores or formal perfgate.
C-or-better remains unachieved. No cache hit is counted as fresh execution.

Evidence: [summary](evidence/coscientist-context-call-20261005/summary.json),
[prototype](evidence/coscientist-context-call-20261005/prototype.diff),
[native proof](evidence/coscientist-context-call-20261005/native-proof.tgz),
[all19 timing](evidence/coscientist-context-call-20261005/timing.tgz),
[independent audit](evidence/coscientist-context-call-20261005/timing-audit.json).

## Link-time boundary failure and correction

Initial source commit `ae40f5d26` built generation1, but that command trapped
SIGSEGV compiling `cbor.core` into generation2. Its typed import stubs are
replaced by unconditional branches at link time (`pj-link`); an aborting
stub can look structurally context-preserving although the real implementation
allocates or calls capabilities. A local function body is insufficient evidence
when linking replaces it. Standalone timing success did not qualify that image.

Corrected source `350438194` supplies the exact generated-import FN interval
from project elaboration to `gn-run-open`. Two words appended to private generator
HEAP state hold this module-wide interval, outside the per-function reset and
without changing the shared memory/context ABI. `gn-ctx-safe` refuses any direct
or transitive dependency on those replaceable bodies. Unity `gn-run` supplies
an empty interval. It is an explicit linker boundary, not a function-name rule
or a guess based on the shape of the stub.

The linked-body regression actually replaces a scalar stub's first instruction
with a branch to an allocating implementation, using the diagnostic allocator
that clobbers x7. Six direct/transitive executions succeed with the explicit
import boundary; all six closed-body controls trap. The permanent generated unit
also checks direct/transitive refusal and independent-function admission after
all231 functions have been emitted. It retains the same machine-code golden and
passes2,400 native executions.

Corrected native generations2/3/4 reproduce803,416 bytes, SHA-256
`09b3daf75b1f1e7997e6c68d9a758d31d076d254756fa42637eae25bd0e0f0fb`.
All19 canonical guest binaries/offsets and fuel/result observations are byte/exact
identical to the timed prototype; their timing is reused because guest code,
runner and workload are identical. The changed compiler's build time is unmeasured.

The actual integrated command rebuilds itself for three generations: all162
objects (117 frontend) and container/native/command artifacts are byte identical.
Command SHA-256: `63fc7ed45dc85edb7a35c2007ca4c6ec2fb95813c7c233c0264d2f2acb4ec063`.
It checks and compiles all19 original sources into the exact measured guest bytes.
All391 check outcomes,391 compile outcomes and891 export rows match the previous
qualified masked-writer image case by case; existing differences remain.
ERR/G1/G2/G3/G4/G5 pass, including84 byte-identical generation containers and
no seed-started programs in G5. This is six selected gates, not a full release
qualification or100% selfhost claim. Build-host load33.06 is not timing evidence.
The bootstrap PRODUCT inventory is unchanged; `bin/amu` and rung pins stay as-is.

[Integrated proof archive](evidence/coscientist-context-call-20261005/integrated-proof.tgz)
retains the failed logs, correction, explicit clobber regression, native binaries,
source snapshot, all input hashes, three-generation hashes and per-case corpus
reports. External input source snapshots remain local; only hashes/logs are archived.

## Consequence for content identity

The identity system is content addressing of normalized typed implementations
and dependencies. This experiment uses exact SIR inspection, not a DefCID cache.
A future reusable proof must seal the actual dependency implementations, compiler
proof version, target and context ABI, and explicitly represent open imports.
A computation recipe identity additionally seals canonical inputs and handler/state
snapshots. Memoizing execution must preserve fuel/traps/resource observability;
a cache hit cannot be scored as freshly executed Embench work.
