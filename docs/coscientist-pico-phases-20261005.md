# Native Picojpeg cumulative-phase diagnosis

The measured compiler is the promoted native sign-extension fixed point, SHA-256
`af790a71b85e853a910cd08e2be2f647099e33d5f688283800841f58bdb5b063`.
Canonical benchmark/product sources and the C comparator are unchanged. This
experiment selects the next execution optimization; it adds no result cache.

Two diagnostic exports are appended to a copy of the canonical Picojpeg source.
They repeat reset+header initialization, or reset+header initialization+coefficient
reconstruction, 32 times using one owned workspace, like the original full body.
The canonical full `bench` export remains intact. Diagnostics are new one-off
algorithm authoring, not mechanical product source rewrites. Python scripts live
only in bootstrap measurement tooling; the measured compiler and execution are
native, with no Node/JVM/nbb fallback.

The compiler inserts a 52-byte vector-allocation adapter after all functions.
Adding diagnostics moves it by 632 bytes. A strict prefix comparison initially
failed; a narrower proof verifies all original instructions remain identical
except exactly three BL relocations, each targeting that same byte-identical
adapter. No arbitrary instruction normalization or ignored difference is used.
Each export returns 1 at n=1,2,8,32 with recorded fuel; a fresh builder replay
reproduces the exact manifest, code hash, offsets and fuel. Two failed attempts
to parameterize the replay tool are recorded in verification.json; they were
variable-shadowing errors after native compilation, not product/compiler failures.

On zebulun (Apple M4), the pinned runner and existing noise policy collect 30
accepted rotating triples in 30 attempts: target 300 ms, minimum 50 ms, load <=4,
estimated background idle >=90%, each arm RSD <=10%, maximum 90 attempts.
All calibration and measurement rows are retained. All recorded results,
warmup counts and exact per-call fuel have also been checked after collection.

| Cumulative execution | Mean us/body | RSD |
| --- | ---: | ---: |
| Reset and header initialization | 10.849 | 4.15% |
| Reset, headers and coefficient reconstruction | 86.482 | 2.00% |
| Original complete workload including verification | 260.791 | 2.10% |

The coefficient diagnostic is about 33% of complete elapsed time; initialization
is about 4%. These are separate cumulative paths with differing wrappers,
branches and compiler layout, so their differences are not exact exclusive phase
costs. They support prioritizing transform/color execution over initialization;
they do not distinguish IDCT, color, vector checking and register spills yet.
No C measurements were taken in this diagnostic, no reduced workload is offered
as Embench, no new suite mean is inferred, and this is not an official score.
The previous aligned whole-body experiment remains the latest C comparison:
260.285 us native versus 10.798 us C, a 24.104x time ratio.

## Next registered hypothesis

Repeated checked vector operations reconstruct a handle descriptor, load its
length, load the item base and calculate offset+index. Transform routines repeat
these operations on the same vector. A generic compiler proof that a descriptor
and arena identity remain valid could reuse that address calculation and bounds
information, reducing execution cost. Test this on freshly executed canonical
workloads, without result memoization or benchmark-name special cases.

The initial admission domain should be a straight-line region: identical proven
handle value and context, no allocator/capability/unknown call, and no intervening
mutation of descriptor/arena metadata. Reuse of a bounds check also needs an
identical proven index or a separately proved range. Writes to vector elements
must invalidate cached element values, even where the descriptor remains valid.
Calls, branch joins and unknown effects invalidate the proof. Preserve fuel,
trap order, context limits and high temporary homes. If the available SIR cannot
establish these facts, retain the existing checked path. This is a design
hypothesis, not an implemented or measured optimization.

Content identity can safely key the resulting specialized IR only once the native
route has an explicit checked definition-identity bridge; current raw SIR hashes
must not be presented as typed KIR DefCIDs. Include compiler, semantic profile,
ABI, target and specialization assumptions in an artifact key. Result caching
requires a separate input/state/effect contract, as documented in
[the identity investigation](coscientist-content-address-20261005.md).

Reproduction tools: `scripts/seed/image/build-native-phases.py` takes repo,
new output directory, native fixed-point seed, command loader, canonical native
code and runner. `measure-native-phases.py` takes the diagnostic directory,
runner, existing timing spec and a new output directory, with
`darwin_cpu_idle.py` on PYTHONPATH. It refuses wrong hosts/pins and overwrite.

Evidence: [manifest](evidence/coscientist-pico-phases-20261005/manifest.json),
[instruction proof](evidence/coscientist-pico-phases-20261005/canonical-relocation-proof.json),
[all rows](evidence/coscientist-pico-phases-20261005/timing.json),
[diagnostic source/code/logs](evidence/coscientist-pico-phases-20261005/diagnostic.tgz),
[replay verification](evidence/coscientist-pico-phases-20261005/verification.json).
