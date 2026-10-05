# Current native loop composition census

The next optimization target is now grounded in fresh current-product code:
the original matmult dot loop emits 47 words, with 30 instructions on a valid
warm descriptor path and 39 on a valid cold path. The unchanged timed C image
contains a fully expanded 20-term multiply-accumulate region. These counts
identify a structural opportunity; they are not runtime time shares or a speedup.
The qualified product remains the [18.494929% shorter same-local-read version](coscientist-same-local-read-20261006.md).
C-or-better across all 19 original workloads remains unachieved.

[Decision](evidence/coscientist-loop-composition-census-20261006/decision.json),
[registration](evidence/coscientist-loop-composition-census-20261006/hypothesis.json),
[guard model](evidence/coscientist-loop-composition-census-20261006/guard-model.json),
[checksums](evidence/coscientist-loop-composition-census-20261006/checksums.sha256).

## Observation qualification

Source commit is `b0d78e9f2f68d6d0d9d2e53cc096bbd3e346fd93`; the native
bootstrap seed is SHA-256
`1171613dde77c12aee7b07273bc337b950d1f3764307a1dde0239b0cd57085dc`.
A new temporary Kotoba observation schema records all original SIR instructions,
function/frame metadata and the contiguous emitted-word interval of each consumed
instruction group. It performs no generator-state writes, including the live
descriptor witness in state13 and scalar-tree flag in state14. This is new
one-off diagnostic code without an existing AST refactor rule; it is not added
to the product compiler.

The native compiler builds the observation compiler. That compiler builds all
19 canonical, hash-pinned original sources. Every guest byte and export offset
equals the current quiet product. Independently checked emission intervals cover
every original instruction, including coalesced/skipped groups, and partition
the code words exactly within each function. Backward branches and their labels
remain inside the owning function. Raw source, native images, complete event logs,
partitions and analysis scripts are archived.

For the original matmult guest, FN5 is 73 words with a 192-byte frame and five
callee-register locals. Its loop is original SIR3274–3315, emitted words2181–2227.
The 47-word static region includes untaken return, descriptor-miss and trap paths.
Exact instruction-word checks establish conditional paths of 30/39 executed
instructions: `k != 20`, valid handle/indices and sufficient fuel; the warm path
also requires the cached positive handle to equal the source. These are conditional
instruction counts, not measured execution traces or a full-workload profile.

An initial expected warm count of29 was rejected by the audit. The descriptor-miss
interval already contains the handle trap word, so subtracting that trap again
double-counted an omission. Union of exact omitted positions yields30; the correction
is retained in the evidence. No product or timing decision used the incorrect count.

## Unchanged C comparator

The exact C dylib retained in the latest timing has SHA-256
`12de24e5051dac499c603300fa86d2d164b66e7410d923e8aa6ec119a29f8a09`.
Its original bridge source and containing archive hashes agree with the recorded
comparison receipt. No C comparator was rebuilt for this observation.

The region at byte0x5cc–0x668 contains 40 instructions: 20 scalar loads, one
multiply and 19 multiply-adds. Row preloads, loop control, result writes and the
rest of the original workload lie outside this region. This supports investigating
expansion and value reuse; it does not establish a comparable total instruction
count, a time ratio or SIMD as the cause of the existing performance difference.
Raw native words are wrapped in a temporary assembler object solely for decoding;
that object never executes or replaces any guest.

## Prospective guarded expansion

Implement a native exact typed-SIR recognizer for the whole closed, read-only,
five-parameter affine dot loop. Capture trip bound, positive strides and offsets
from the source structure; do not match workload names or replace source bodies.
Preserve the original prologue, parameter/local/frame allocation and entry charge.
Keep the original loop as the fallback, with no corrupted cache key, descriptors,
context or input locals on guard failure.

A bounded first candidate admits an initial `k == 0`, trip bound1–64, strides1–64,
nonnegative offsets at most4095, row/column inside the trip bound, both complete
read ranges inside the validated vector, and sufficient remaining fuel for every
original backedge charge. Other inputs use the original path. In particular,
zero-trip and insufficient-fuel inputs must reach the original path before
speculative handle validation or charging. The checked path may expand sequential
loads and i64 multiply-adds, then publish exactly the original fuel/local outcome.
Unknown calls, effects, writes, allocations, aliases without proof, open replacement
dependencies and nonmatching control flow refuse admission.

A bootstrap mathematical model checked 192,000 boundary/input configurations,
including MIN/MAX, zero-trip, endpoint bounds and insufficient fuel. It admitted
756 safe configurations and checked wrapped sequential scalar arithmetic against
multiply-add arithmetic. Maximum expanded load offset fits the original unsigned
LDR encoding. This model is **not native execution proof**: it does not validate
actual handle representations, unsigned fuel ABI, fallback machine state or traps.

Next work is the actual native matcher/emitter and independent machine/state
qualification: extremes, zero-trip, invalid first/last accesses, partial fuel,
resources, aliases, effects and open imports, preserving the current470-fixture/
11,187-run prefix and all19 original bodies. Only then run a fresh quiet rotating
comparison under the existing thresholds, followed by gates and committed-source
three-generation integrated parity before adoption. No new performance measurement
or product implementation is claimed by this census.
