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

Then follow the frozen KOTOBA-140 protocol: declared same-host C comparator,
host admission, full paired/interleaved repetitions, complete failures,
uncertainty and external reproduction/independent reruns. Native rebuilds,
old payload equality, export admission and candidate nanoseconds are not
proof of speedup, an official Embench score or permission to publish a broad
performance claim.
