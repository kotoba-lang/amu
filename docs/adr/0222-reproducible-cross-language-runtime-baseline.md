# 0222 — Reproducible cross-language runtime baseline

- Status: accepted
- Date: 2026-08-09
- Machine-readable companion:
  [`0222-reproducible-cross-language-runtime-baseline.edn`](0222-reproducible-cross-language-runtime-baseline.edn)

## Context

Compile timings and instruction snippets cannot establish execution speed.
Earlier scalar loops also hid three independent effects: JVM/process startup,
optimizer removal of closed-form work, and aggregate allocation through the
typed host. Native measurements are invalid if they bypass the production
supervisor, while a Wasmtime CLI without the required externref host cannot
honestly execute typed collections.

## Decision

`scripts/runtime-comparison.mjs` owns
`kotoba.runtime-comparison/v7`. It executes five checksum-bound workloads:
scalar multiplication, balanced branch, loop-carried xorshift32, and an
xorshift-indexed eight-item vector construction/read in both proven
non-escaping and forced-materialization forms. The seven lanes are
Kotoba Wasm/V8, Wasmtime CLI, supervised Kotoba native, primitive and boxed
Clojure, advanced ClojureScript, and release Rust.

Cold process wall time, in-process steady time, supervised native batch wall
time, RSS, and payload size remain separate. Native steady state is timed
inside the production W^X, fork-supervised sandbox. Its opt-in repeat protocol
admits only pure empty-allowlist execution, resets fuel and every bounded arena
per invocation, and rejects nondeterministic results. The V8 Wasm lane uses the bounded
production-compatible browser typed host when an artifact imports it. A
materialized vector/Wasmtime cell is explicitly unsupported because the
standalone CLI supplies no `kotoba:typed` externref host; a fully
scalar-replaced artifact has no such import and is measured.

Scalar workloads use the requested iteration count, capped at 5,000 for the
recursive pinned backend and 10,000,000 for a classpath-verified candidate.
Vector allocation uses 256 pinned iterations and 100,000 candidate iterations:
the former respects the recursive helper and bounded native arena; the latter
provides a stable optimizer-resistant interval without turning the benchmark
into a long endurance test.

The materialized vector row crosses a source vector-returning function
boundary every 512th iteration. This is a real escape that remains stable when
non-escaping `vector-count` is scalar-replaced, while keeping total calls below
the fixed fuel ceiling. The Wasm candidate imports a fixed two-page scratch memory,
reserves aligned slices through a private module LIFO bump pointer, evaluates
items once from left to right, and invokes one synchronous checked host copy.
Nested or re-entrant construction therefore cannot overwrite an outer
in-progress value. Wraparound, capacity exhaustion, unaligned ranges, and
oversized counts trap or are host-rejected; the memory and bump pointer are not
exported. The host admits the function and memory imports only as a pair and
allocates no scratch memory for typed modules that do not use bulk vectors.
Published compiler pins still report this row as unsupported. A local-root
candidate admits `:vector-i64`/`:vector-f64` parameters and results on
non-exported `defn-` functions. Native code already carries those context-owned
handles as one word. A subsequent copy-v1 slice admits only a zero-argument,
non-entry export returning one of those vector types. The POSIX parent
supervisor validates the invocation-owned handle and bounded slice, then
atomically publishes canonical little-endian wire data; the guest receives no
host path or output pointer. Vector parameters and entry results remain
rejected, and tender-native/Windows integration remains open.

Candidate native measurement is atomic across `kotoba-kir`,
`kotoba-verifier`, and `kotoba-native`: the harness requires all three root
options together, verifies every exact `src` path in the resolved classpath,
uses the same candidate verifier for compile and extract, and re-checks every
commit/dirty state before writing the report. Partial override sets fail before
compilation; mid-run checkout changes discard the evidence.

Candidate performance and publication are separate states.
`scripts/qualify-wasm-backend.mjs` emits
`kotoba.wasm-backend-qualification/v2`, compiling scalar, scalar-replaced
vector, and materialized-vector fixtures through JVM and nbb, requiring byte
identity, `wasm-tools` validation, and their deep checksums. Promotion
additionally requires a clean checkout,
an advertised remote ref, and exact agreement between the candidate commit,
`deps.edn`, and `deps-lock.edn`.

## Evidence

On the Apple arm64 host, five pinned samples measured these steady medians
(ns/iteration):

| Workload | Kotoba Wasm | Clojure | Boxed Clojure | CLJS | Rust | Wasm/Rust |
|---|---:|---:|---:|---:|---:|---:|
| scalar | 12.54 | 14.73 | 228.96 | 12.13 | 2.43 | 5.17× |
| branch | 15.86 | 16.23 | 179.77 | 11.48 | 4.33 | 3.66× |
| integer mix | 24.40 | 43.32 | 121.37 | 42.36 | 2.88 | 8.46× |
| vector allocate/scan | 7,777.99 | 2,868.65 | 3,079.75 | 462.73 | 2.77 | 2,812.38× |

The structured-loop candidate used ten million scalar iterations and 100,000
vector iterations:

| Workload | Candidate Wasm | Clojure | Boxed Clojure | CLJS | Rust | Wasm/Rust |
|---|---:|---:|---:|---:|---:|---:|
| scalar | 0.68 | 0.68 | 8.39 | 0.92 | 2.25 | 0.30× |
| branch | 1.06 | 1.01 | 2.82 | 1.20 | 5.35 | 0.20× |
| integer mix | 3.05 | 5.13 | 6.44 | 3.91 | 3.90 | 0.78× |
| vector allocate/scan | 5,998.10 | 269.38 | 296.08 | 29.98 | 4.03 | 1,489.75× |

This pre-scalar-replacement candidate reaches workload-local integer parity
while remaining far from Rust, Clojure, and CLJS on materialized aggregate
construction. That row remains the controlling evidence for escaping vectors.

A subsequent bounded non-escape analysis scalar-replaces let-bound vector
literals used only by `vector-at`/`vector-count`. It preserves left-to-right element
evaluation, evaluates the index once, retains bounds traps, folds count only
after item evaluation, and caps the
representation at 32 locals. Escape and wider literals fall back to externref.
In a new five-sample row, V8 fell from 5,998.10 to 15.36 ns/iteration while
Rust measured 2.59, a 5.94× ratio. The 652-byte artifact has no typed-host
imports and returns checksum `2847627` under both V8 and standalone Wasmtime.
This proves a fast non-escaping representation, not general persistent-vector
allocation parity.

The v7 matrix forces materialization with a source vector-returning function
boundary every 512th iteration; `vector-count` is now scalar-replaceable and
no longer serves as an artificial cliff. Five 100,000-iteration samples
measured 967.69 ns for the scratch-backed Kotoba Wasm path, 244.19 for
primitive Clojure, 237.68 for boxed Clojure, 22.83 for advanced
ClojureScript, and 2.62 for Rust. The 369.00× Wasm/Rust gap remains material,
but the single-copy path is 6.20× faster than the pre-bulk 5,998.10 ns
candidate and 8.04× faster than the pinned 7,777.99 ns materialized row. The
2,282-byte artifact (`9fe581a8…`) intentionally retains typed-host imports, so
standalone Wasmtime is explicitly unsupported. Supervised native is also
unsupported under the published compiler pins.

The private-boundary candidate then completed the same five-workload matrix.
The three clean candidate components were `kotoba-kir` `5cff10e`,
`kotoba-verifier` `e6d275e`, and `kotoba-native` `ef2df69`. For native, five
samples produced these medians:

| Workload | Cold process | Supervised steady | Rust ratio | Startup-inclusive upper bound | RSS | KEXE |
|---|---:|---:|---:|---:|---:|---:|
| scalar | 14.29 ms | 13.40 ns/iteration | 5.54× | 69.37 µs/iteration | 4,308,992 B | 9,480 B |
| branch | 12.87 ms | 15.55 ns/iteration | 7.23× | 61.36 µs/iteration | 4,276,224 B | 9,480 B |
| integer mix | 14.81 ms | 22.93 ns/iteration | 8.96× | 56.61 µs/iteration | 4,276,224 B | 9,480 B |
| vector allocate/scan | 33.96 ms | 74.10 ns/iteration | 28.59× | 56.66 µs/iteration | 4,341,760 B | 7,884 B |
| vector materialize/scan | 12.17 ms | 63.01 ns/iteration | 24.23× | 43.72 µs/iteration | 4,325,376 B | 8,903 B |

Every checksum passed, including the materialized function-boundary row. Each
steady sample uses 10 warmup and 100 measured invocations of 256 workload
iterations; the safety reset is part of the measured interval between calls.
This closes the native steady measurement gap without an unsafe direct-call
harness, but does not establish general Rust parity. A 5,000-iteration single
invocation still traps at the unchanged fuel boundary.

The changed loader hashes to `94fd2a6c…`. The coordinated local `artifact`
candidate pins that identity and passes the complete attested conformance and
931-test/7,342-assertion compiler suite through an explicit local-root override. The published
artifact pin still names the previous loader, so the default suite deliberately
fails the identity gate until artifact publication, compiler pin advancement,
lock regeneration, and another full verification. No identity check is relaxed.

The v2 qualification gate reproduced byte-identical scalar, scalar-replaced
vector, and materialized-vector Wasm from JVM and nbb, validated all three, and
returned checksums `2318261108` at one million integer iterations and `7560`
at 256 iterations for each vector form. It reports `candidateQualified: true`
but `promotionReady: false`: the backend tree is dirty, the compiler pins still
name its published base commit, and this development qualification did not run
the opt-in publication check.

`npm run test-runtime-comparison` validates all five workload contracts, every
supported lane, the explicit unsupported state, timing/RSS metadata, Rust
ratios, and native safety. `npm run test-wasm-backend-qualification` verifies
pin parsing and fail-closed promotion state transitions.

## Consequences

General Rust parity is not established. Structured loops, i32-local xorshift,
bounded aggregate scalar replacement, and scratch-backed bulk construction
solve the measured scalar/non-escaping bottlenecks and remove per-item host
calls from literal materialization. Materialized vectors still create and copy
a host object each iteration and remain the highest-priority runtime target.
Work should extend escape analysis and add a bounded region/arena
representation across wider lifetimes, while retaining immutable semantics and
host-side type validation. Private native vector boundaries are executable.
The first exported result boundary now uses invocation-copy rather than
exposing a handle; exported inputs, entry results, tender-native consumption,
and Windows parity remain intentionally denied.

The next comparison gaps are an embedded typed Wasmtime host, vector
map/reduce, immutable tree/list,
string scan, capability calls, Chicory, and packaged Clojure AOT. The backend
candidate also remains unpublished until its commit, remote ref, compiler pin,
lock, and full conformance evidence agree.
