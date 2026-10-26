# Closed native measurement host candidate (KOTOBA-145)

This is a candidate implementation, not a qualified performance campaign.
The owner approved a separate privileged, hash-pinned native host on
2026-10-26. Ordinary guest access to the private runtime remains forbidden;
the two CDCI roles are unchanged. No C loader/compiler, JVM, Node or other
hosted fallback is permitted.

## Factory boundary

The same complete Amu compiler builds the host and original workload
libraries. `seed/79-native-cdci.kotoba` contains a separate `bench-build`
dispatch; it does not add a role to `cdci-build`.

```
amu bench-build aarch64-linux HOST_SOURCE REGISTRY_SOURCE NEW_OUTPUT \
  --runtime-profile large-vectors-v1
```

The factory checks both source hashes before emission. It supplies its own
harmless guest entry and the existing native runtime core, and appends only
the pinned privileged source after the private-runtime boundary. It does not
enable the platform-linked format or arbitrary privileged guest calls.
Unknown/missing/duplicate flags, different source bytes, existing outputs
and unsupported targets refuse. The initial payload registry is ARM-only;
x86 measurement-host admission remains open, not silently emulated.

`registry-arm.kotoba` records newly generated payload hashes, lengths and
original export offsets for all19 unchanged libraries. Twelve payloads
match M104 byte-for-byte; seven do not. Old offsets/hashes must not be used
for those seven. xgboost's verifier keeps its original `(state,n)` signature;
the other18 verifiers take state alone. The original functions are not
wrapped, removed, simplified or rewritten for the host.

## Execution and accounting

The candidate host command is:

```
HOST WORKLOAD_ID PAYLOAD ITERATIONS PROFILE
```

IDs are the fixed original19 order. Profile0 requires the original registered
iteration count. Profile1 requires exactly one iteration and marks the
record diagnostic. It is not a reduced-count performance campaign.

Before any payload entry, the host reads one bounded regular non-symlink
file into anonymous memory, verifies its exact size and SHA-256, then makes
that same snapshot read/execute. No mutable path is used after admission.
It imports no effect grants from `KEXE_ALLOW` or service/resource variables.
The existing context v11, arenas, limits, signal handlers and syscall filter
remain in force. Positive metered fuel is required.

The sequence is: reset; original benchmark(1,0); optional original warm-seed;
reset; original benchmark(n,seed) inside the clock interval; snapshot;
original verifier in the same context outside the clock interval; snapshot;
receipt. All argument preparation precedes the benchmark-only interval.
The host uses native `CLOCK_MONOTONIC_RAW`; Python observes, never supplies
elapsed time or a successful native verdict.

The host owns an ordered native guard: warmup/reset require the pre-clock
phase; clock begin/end advance the phase; the original verifier requires the
closed clock interval and advances the final phase. A native fixed oracle
then checks the original warm seed, separately measured benchmark/verify fuel,
and both17-field snapshots against the frozen original accounting reference
`6368bd343086a6c88e0645e31dde82bcdf64742c7b4727cdd56103ef72e9b4cc`.
All19 original verifiers are allocation-free, so both current-use snapshots
equal that fixed reference. Diagnostic profile1 does not claim full-count
accounting qualification. Source golden tests supplement, but never replace,
actually executing this native guard.

Reset accepts only the closed pure state: no active scopes, budget/value
failure, public graph data, keyword intern rows, output, held lock or effect
grants. It clears used validation/region metadata, scope marks, allocation
and event counters, and restores initial fuel. It preserves mappings,
the initialized keyword pointer and private offsets752/760. In particular,
reset never lowers absolute item highwater760: reused old item storage must
still be zeroed by the existing vector allocator. It does not pretend that
warm mappings are cold memory.

The two17-field arena arrays have the existing `KEXE_ARENA_USE` order:
pairs, string-pool-bytes, vectors, vector-items, heap-bytes, conj, conj-tail,
conj-region, conj-copy, copied-words, reserved-words, regions, scope-releases,
string-regions, string-region-appends, string-copied-bytes,
string-reserved-bytes. These are current-use/event fields, not an invented
peak-memory metric. The snapshots are immediately after benchmark and after
verification. Benchmark and verification fuel are separate differences of
the same native context's fuel counter. Raw candidate receipts explicitly
set `performanceQualified:false`.

## Required qualification

`check-native-benchmark-host.py` is an observation/staging tool. Native host
success, valid raw records and factory/source refusals are only partial
evidence. A successful observer exit is not full qualification. Retain failed
builds, refused executions and their exact sources alongside later attempts.

Before adoption, finish both ISA compiler fixed points, same-compiler
original19 provenance and full-count correctness/accounting; actual built
timing/accounting/reset/highwater mutants and negative controls; ordinary
guest/private-runtime boundary tests; all previous native gates and exact-head
CI. The current public host remains native Linux x86_64; an ARM diagnostic
producer does not extend public support. Bind final public-compiler-generated
workload and host artifacts to that qualified compiler before a campaign.

`check-native-benchmark-mutations.py` builds13 isolated test compilers. Each
admits one exact semantic-mutant host hash instead of the production hash;
it adds no production whitelist or privileged guest mode. The actual hosts
then execute original full counts and must give the named native refusal
for warm count/seed, reset, clock/verifier order, skipped verification, fuel,
snapshot or highwater errors. A build failure, timeout or generic trap is
not a successful mutation control. The source golden controls also verify
that these mutants leave the fixed accounting oracle unchanged.

The native x86 qualification executes the complete public compiler's own
three-generation fixed point and all existing native gates. It then compiles
all19 unchanged libraries and the closed ARM host, checking exact equality
to artifacts actually executed by the ARM qualification. This proves the
public x86 producer's ARM factory route; it does not advertise a native x86
measurement host or run ARM code under emulation. `bench-build x86_64-linux`
continues to refuse, as specified by this factory's target boundary.

Owner confirmed this scoped merge on2026-10-26. Native x86 measurement-host
implementation/execution is tracked separately in KOTOBA-152; it is not
inferred from a public x86 compiler emitting ARM code.

Then follow the frozen KOTOBA-140 protocol: declared same-host C comparator,
host admission, full paired/interleaved repetitions, complete failures,
uncertainty and external reproduction/independent reruns. Native rebuilds,
old payload equality, export admission and candidate nanoseconds are not
proof of speedup, an official Embench score or permission to publish a broad
performance claim.
