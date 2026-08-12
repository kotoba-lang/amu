# Performance baseline

Performance claims for Kotoba must name the source fixture, compiler commit,
target, host, and whether startup and host-boundary costs are included. A raw
machine-code instruction timing is not a language benchmark.

## Reproducible cold-compile measurement

Run the same `.kotoba` fixture through the portable Wasm and host-native
backends in fresh compiler processes:

```text
npm run benchmark-compiler -- --runs 5 --output performance.json
```

The JSON report uses the versioned `kotoba.performance-baseline/v1` schema. It
contains every sample plus median and p95 values for:

- end-to-end process-cold wall time;
- time after the compiler namespaces have loaded;
- time from loading the shared CLI support through command completion;
- their difference, which exposes launcher and namespace-load cost;
- artifact and provenance sizes;
- the host platform, architecture, Node version, and compiler commit.

The harness performs one unmeasured compile first. That populates the sealed
dependency-classpath cache, so dependency downloads and a stale-lock JVM
fallback cannot be mistaken for compiler work. Every measured sample still
starts a fresh `bin/kotoba` process and a fresh nbb compiler process.

The same report also starts one target-locked persistent worker per backend,
performs an unmeasured warmup, and records warm request round-trip and loaded
compiler durations. It then changes only the policy and records the
artifact-cache miss that reuses HIR and KIR, and adds a whitespace-only source
edit that reruns the frontend but reuses semantically identical KIR. Cold,
artifact-hit, policy-change, and semantic-edit results stay separate; startup
is never silently removed from the cold number.

For an opt-in CI regression gate, set millisecond ceilings. No default ceiling
is embedded because hosted-runner variance makes a single global number
misleading:

```text
KOTOBA_BENCH_MAX_WASM_MS=1500 \
KOTOBA_BENCH_MAX_NATIVE_MS=2000 \
npm run benchmark-compiler -- --runs 7
```

## Phase timing

Set `KOTOBA_COMPILER_TIMING=1` on an ordinary `compile` or `check` command.
The nbb fast path emits one stderr line prefixed by `KOTOBA_TIMING`, followed by
JSON in the `kotoba.compiler-timing/v1` format. Normal stdout and artifacts are
unchanged when timing is disabled.

The `command` phase is the loaded-compiler duration used by the benchmark.
`totalMilliseconds` begins when the backend-free shared support namespace has
loaded and therefore also exposes most target-specific namespace loading.
Measured phases include source admission/read, frontend analysis, policy read,
capability admission, KIR lowering, backend emission, artifact sealing,
independent native verification, provenance, and writes. The outer `command`
phase includes the complete compiler command after namespaces load.

## Target-specific namespace closures

`bin/kotoba` selects a lean entrypoint before starting the compiler process:

- `check` and `wasm32*` load the Wasm entrypoint without either native emitter;
- `aarch64*` loads only the AArch64 emitter;
- `x86_64*` loads only the x86-64 emitter;
- policy decoding, diagnostics, timing, and exit-code behavior remain in one
  backend-free shared support namespace.

On the Apple arm64 development host, three process-cold samples of
`examples/i64-semantics.kotoba` reduced the AArch64 median from 5.49 seconds to
3.54 seconds while preserving the 4,768-byte KEXE and 953-byte provenance.
Wasm moved from 4.73 seconds to 4.58 seconds in the same small sample; treat
those numbers as implementation evidence, not portable performance ceilings.

## Persistent compiler worker

Start a worker whose backend cannot change during its lifetime:

```text
bin/kotoba -M worker --target wasm32
bin/kotoba -M worker --target aarch64
bin/kotoba -M worker --target x86_64
```

The stdin/stdout protocol is newline-delimited JSON. After namespace loading,
the worker emits a `ready` message. Requests carry the ordinary CLI arguments:

```json
{"id":1,"args":["compile","examples/i64-semantics.kotoba","--target","wasm32","--output","/tmp/i64.wasm"]}
```

Each `result` contains `status`, `stdout`, `stderr`, and optional phase timing.
The ordinary CLI's EDN success/error contract is preserved inside the stdout
or stderr string. Shut down cleanly with:

```json
{"id":"shutdown","op":"shutdown","args":[]}
```

The worker is deliberately sequential and bounded:

- maximum encoded request line: 64 KiB, enforced while bytes arrive;
- maximum arguments: 64, each at most 4,096 characters;
- default lifetime ceiling: 1,000 input lines, including malformed requests;
- `KOTOBA_WORKER_MAX_REQUESTS` may set a ceiling from 1 through 100,000;
- malformed/usage/admission requests fail independently;
- an internal compiler failure returns status 70 and then fail-stops the worker;
- a Wasm worker cannot compile native targets, and an ISA worker cannot switch
  ISA.

On the same Apple arm64 host, five post-warmup requests measured:

| Worker, before content cache | Median | p95 |
|---|---:|---:|
| Wasm32 | 13.3 ms | 21.3 ms |
| AArch64 | 25.6 ms | 33.4 ms |

These figures include NDJSON round-trip and artifact writes. They meet the
initial sub-100-ms small-module target without weakening admission, native
verification, provenance, or target confinement.

### Content-addressed verified-artifact cache

Each worker owns an in-memory LRU cache. Its SHA-256 key binds the cache schema,
exact target profile, source text, whether an explicit policy was supplied,
and the exact policy text. An omitted policy and an explicit `{}` policy are
therefore distinct even though both admit the same pure fixture.

Only successful results are inserted:

- Wasm entries contain a defensive copy of the emitted bytes;
- native entries are inserted only after admission, machine-code emission,
  artifact sealing, independent verification, and provenance generation;
- every hit re-hashes the cached artifact and native provenance before writing;
- an integrity mismatch removes the entry and fail-stops the worker as an
  internal compiler error;
- cache state never crosses a worker-process or compiler-version boundary.

The default limits are 128 entries and 64 MiB of payload. They can be lowered or
raised within hard ceilings using `KOTOBA_WORKER_CACHE_ENTRIES` (1–4,096) and
`KOTOBA_WORKER_CACHE_BYTES` (1 byte–1 GiB). Entry count bounds key/map overhead;
the byte setting bounds artifact and provenance payload. Least-recently-used
entries are evicted until both ceilings hold, and a single oversized entry is
not retained.

Five cache-hit requests on the same host measured:

| Worker cache hit | Median | p95 |
|---|---:|---:|
| Wasm32 | 0.881 ms | 1.475 ms |
| AArch64 | 0.778 ms | 1.453 ms |

The benchmark checks the cache status and byte-compares every hit against its
miss/warmup artifact. For native it separately compares both KEXE and
provenance. These are unchanged-source incremental results, not claims about
compiling changed modules.

### Policy-independent HIR/KIR stage cache

Artifact identity must include policy text, but frontend analysis and KIR
lowering do not depend on policy. Each worker therefore owns a second bounded
LRU for those immutable stages. A key binds the stage-cache schema, exact
source text, and stage name for HIR. KIR instead binds the stage-cache schema,
stage name, and serialized admitted HIR. HIR and KIR entries cannot alias each
other, while source spelling changes that produce identical HIR can reuse KIR.

On an artifact miss the worker resolves HIR, decodes the current policy, and
always runs capability admission. Only after admission succeeds does it
resolve KIR. Consequently a cached HIR/KIR cannot turn a denied policy into an
accepted build. The worker integration test first admits a capability-using
module, then recompiles the identical source with a denying policy and requires
the normal status-65 admission failure.

Each stage entry stores a SHA-256 digest of its serialized immutable value and
is re-hashed on lookup. A mismatch evicts the entry and fail-stops the worker.
The cache is process-local and has separate default limits of 128 entries and
64 MiB. Configure it with `KOTOBA_WORKER_STAGE_CACHE_ENTRIES` (1–4,096) and
`KOTOBA_WORKER_STAGE_CACHE_BYTES` (1 byte–1 GiB).

Five cache-hit measurements on the same Apple arm64 host were followed by one
sample for each incremental case:

| Worker and incremental change | Round trip | Loaded compiler |
|---|---:|---:|
| Wasm32, policy changed; HIR/KIR hit | 14.12 ms | 9.21 ms |
| AArch64, policy changed; HIR/KIR hit | 22.56 ms | 21.58 ms |
| Wasm32, whitespace edit; HIR miss/KIR hit | 19.89 ms | 19.30 ms |
| AArch64, whitespace edit; HIR miss/KIR hit | 40.58 ms | 39.80 ms |

The benchmark requires `:cache :miss` in both cases and independently checks
the expected stage statuses. It also byte-compares the semantic-edit artifact
with the original. This safely handles frontend-equivalent edits; function-
level invalidation for semantically changed modules remains a separate
optimization that requires frontend dependency-graph support.

## Runtime comparison

Run the versioned five-workload, seven-lane benchmark matrix with:

```text
npm run benchmark-runtime -- --runs 5 --iterations 5000 --output runtime.json
```

To qualify an unpublished `kotoba-wasm` checkout without editing `deps.edn`,
pass `--wasm-local-root /absolute/path/to/kotoba-wasm`. The harness installs a
temporary tools.deps override alias, refuses to continue unless that exact
`src` directory is present in the resolved classpath, records the backend
commit and dirty state, and raises the iteration ceiling to 10,000,000. This
prevents a nominal override from silently benchmarking the pinned backend.

To measure an unpublished native boundary candidate, all three ownership
layers must be overridden together:

```text
npm run benchmark-runtime -- --runs 5 --iterations 5000 \
  --native-kir-root /absolute/path/to/kotoba-kir \
  --native-verifier-root /absolute/path/to/kotoba-verifier \
  --native-backend-root /absolute/path/to/kotoba-native \
  --output runtime-native-candidate.json
```

The harness rejects partial root sets, verifies every exact `src` directory in
the tools.deps classpath, and uses the candidate verifier for both compilation
and native extraction. It re-checks commit and dirty state before emitting the
report. This prevents a candidate artifact from being silently re-checked by
the published verifier or attributed across a checkout change.

Performance qualification alone cannot promote that checkout. Run the
fail-closed backend promotion gate with:

```text
npm run qualify-wasm-backend -- \
  --wasm-root /absolute/path/to/kotoba-wasm \
  --require-clean --require-pinned --require-published \
  --output qualification.json
```

The `kotoba.wasm-backend-qualification/v2` report compiles the scalar,
scalar-replaced vector, and forced-materialization vector fixtures via JVM
Clojure and nbb, requires byte-identical output, validates all three with
`wasm-tools`, executes their data-dependent checksums, and separately
records checkout cleanliness and both compiler pins. `candidateQualified` may
be true for a dirty development tree; `promotionReady` cannot be true until
the tree is clean and both `deps.edn` and `deps-lock.edn` name that exact
commit and a configured remote ref advertises it. Release automation must use
`--require-clean`, `--require-pinned`, and `--require-published`, not infer
readiness from benchmark numbers.

Every implementation runs five workloads with explicit checksum contracts:

- `scalar-multiply` adds `6 * 7` for `N` iterations;
- `balanced-branch` adds 41 for the first half and 43 for the second half of
  an even `N`;
- `integer-mix` applies xorshift32 repeatedly to loop-carried state seeded with
  `2463534242`, preventing a constant-sum closed form;
- `vector-allocate-scan` constructs an eight-item immutable vector each
  iteration and reads an item selected by the evolving xorshift32 state;
  a backend may scalar-replace the materialization only when the value cannot
  escape;
- `vector-materialize-scan` performs the same data-dependent read but crosses
  a source vector-returning function boundary every 512th iteration. That
  real escape prevents scalar replacement without charging enough calls to
  exceed the fixed fuel budget. The Wasm candidate builds each literal with a
  fixed two-page imported scratch memory and one synchronous typed-host copy;
  published native pins report the vector-function boundary as unsupported,
  while a qualified local-root candidate may measure a private `defn-`
  boundary without opening the exported kexe ABI.

The first two require `42 * N`; integer-mix requires
`xorshift32^N(2463534242)`. The report records concrete cold and steady
checksums and separates two measurements:

- cold process wall time includes runtime/artifact loading and executes the
  minimum checksum-stable count: one scalar iteration or two branch iterations;
- steady time is recorded inside the process after an explicitly reported
  warmup: up to 5,000 iterations for the pinned backend and 1,000,000 for a
  qualified candidate;
- peak resident memory is measured once from a fresh process with
  `/usr/bin/time` and normalized to bytes on macOS and Linux.

Kotoba native's cold result uses the production W^X, fork-supervised loader.
Its opt-in steady protocol repeats deterministic pure invocations inside that
same sandboxed child, with an empty capability allowlist, fresh 512 fuel and
fresh pair/kgraph/string/vector arena cursors per invocation. Ten invocations
warm up, 100 measured invocations each execute 256 workload iterations, and a
child-side monotonic timer excludes process startup. Every result must match;
the structured report includes elapsed time, total fuel, and final arena use.
The ordinary one-shot CLI and report remain unchanged. Wasmtime CLI is reported
as a distinct cold/RSS lane without manufacturing an embedded timer. Kotoba
Wasm uses V8, Clojure reports primitive and boxed HotSpot paths,
ClojureScript uses advanced compilation on the same Node/V8, and Rust uses `-C opt-level=3
-C target-cpu=native`. Rust's scalar/branch fixtures use per-iteration
`black_box` barriers to retain those otherwise optimization-sensitive loops;
integer-mix has an intrinsic loop-carried dependency and only black-boxes the
final result. Integer-mix is the stronger scalar optimizer signal. A
materialized vector row adds production typed-host costs; a non-escaping
literal may instead be represented by checked Wasm locals. Standalone Wasmtime
is unsupported only when the emitted artifact still imports the
`kotoba:typed` externref host.

The loader source identity is now `94fd2a6c…`. A coordinated local
`kotoba-lang/artifact` candidate pins that hash and passes attested conformance,
but it is not published or pinned by this compiler yet. Consequently the
default pinned artifact identity still rejects this working-tree loader; this
is the intended drift gate. Candidate verification uses
`KOTOBA_ARTIFACT_ROOT=/absolute/path/to/artifact nbb scripts/conformance.cljs`.

Apple arm64 pinned-backend v5 results use five samples and 5,000 measured
iterations for scalar workloads. Allocation uses 256 iterations because the
recursive helper and bounded native vector arena require a shallower count.
That historical report predates the fifth forced-materialization row.

| Workload | Kotoba Wasm/V8 | Clojure primitive | Clojure boxed | CLJS advanced | Rust | Wasm/Rust |
|---|---:|---:|---:|---:|---:|---:|
| scalar multiply | 12.54 ns | 14.73 ns | 228.96 ns | 12.13 ns | 2.43 ns | 5.17× |
| balanced branch | 15.86 ns | 16.23 ns | 179.77 ns | 11.48 ns | 4.33 ns | 3.66× |
| integer mix | 24.40 ns | 43.32 ns | 121.37 ns | 42.36 ns | 2.88 ns | 8.46× |
| vector allocate/scan | 7,777.99 ns | 2,868.65 ns | 3,079.75 ns | 462.73 ns | 2.77 ns | 2,812.38× |

The vector Wasm artifact is 2,063 bytes and its supervised-native KEXE is
7,884 bytes; scalar artifacts remain 708 and 9,480 bytes. Advanced CLJS is
93,203 bytes and Rust 487,992 bytes. Native cold medians are 13–18 ms with
roughly 4.1 MiB RSS, including 16.29 ms for the vector workload. JVM classes
have no honest standalone artifact size here.

The allocation result is deliberately not hidden by the strong scalar rows.
It shows that the current externref typed host and persistent vector
construction dominate end-to-end collection throughput. The pinned recursive
loop also remains host-stack-bound, so 5,000 is the scalar ceiling without
weakening fuel or hiding an overflow.

### Structured-loop backend candidate

`kotoba-wasm` now has an upstream working-tree implementation of that target:
frontend `__kotoba_loop_N` helpers become standard Wasm `block`/`loop`/`br`
control flow, evaluating all replacement arguments before updating parameter
locals. Typed-scalar and untyped helpers both pass Wasmtime at 100,000
iterations; ordinary recursion at depth 600 still hits the unchanged fuel
boundary.

Using the classpath-verified `--wasm-local-root` path for the complete frontend
→ KIR → candidate backend, the standard matrix completed five
10,000,000-iteration scalar samples after a 1,000,000-iteration warmup, plus
100,000 aggregate iterations after an equal warmup. These rows precede the
non-escape scalar-replacement increment and retain the materialized externref
cost as its baseline:

| Workload | Candidate Wasm/V8 | Clojure primitive | Clojure boxed | CLJS advanced | Rust | Wasm/Rust |
|---|---:|---:|---:|---:|---:|---:|
| scalar multiply | 0.68 ns | 0.68 ns | 8.39 ns | 0.92 ns | 2.25 ns | 0.30× |
| balanced branch | 1.06 ns | 1.01 ns | 2.82 ns | 1.20 ns | 5.35 ns | 0.20× |
| integer mix | 3.05 ns | 5.13 ns | 6.44 ns | 3.91 ns | 3.90 ns | 0.78× |
| vector allocate/scan | 5,998.10 ns | 269.38 ns | 296.08 ns | 29.98 ns | 4.03 ns | 1,489.75× |

Against pinned medians, structured loops speed the first three rows by about
18.4×, 15.0×, and 8.0×. They improve allocation only about 1.3× because the
typed host, not loop control flow, dominates that row. Candidate artifacts are
731-byte scalar Wasm and 2,056-byte vector Wasm.

The first two results show that structured control flow removes most loop
machinery overhead, but they are optimization-sensitive microkernels and the
scalar p95 remained noisy. The loop-carried integer-mix result is the stronger
evidence: representation-aware `u32` locals and i32 expression lowering remove
redundant i64↔i32 traffic across the xorshift chain and reach workload-local
parity with Rust. The allocation row proves why this is not evidence of
language-wide Rust parity: collection construction remains about 1,490× Rust
in this workload and materially slower than Clojure/CLJS.

### Non-escaping vector scalar replacement

The next backend increment keeps a let-bound vector literal in i64 Wasm locals
when every lexical use is a checked `vector-at` or `vector-count`. All elements
are evaluated
left-to-right at the original binding point, the index is evaluated once, and
negative, past-end, and empty-vector access still trap; count becomes a
constant only after element evaluation. Escape, shadowing, and
literals wider than 32 items retain the bounded typed-host representation; the
32-local ceiling prevents optimizer-driven code-size amplification.

The same five-sample 100,000-iteration vector row then measured:

| Workload | Candidate Wasm/V8 | Clojure primitive | Clojure boxed | CLJS advanced | Rust | Wasm/Rust |
|---|---:|---:|---:|---:|---:|---:|
| non-escaping vector construct/read | 15.36 ns | 404.27 ns | 317.57 ns | 34.16 ns | 2.59 ns | 5.94× |

This is approximately 390× faster than the immediately preceding 5,998.10 ns
materialized candidate and 506× faster than the pinned 7,777.99 ns result. The
artifact shrank from 2,056 to 652 bytes because it no longer imports the typed
host. It executes with checksum `2847627` in both the production-compatible V8
runner and standalone Wasmtime. This establishes a fast non-escape
representation, not fast general persistent-vector allocation: escaping,
wide, mutation-derived, and function-boundary vectors still use externref.

### Bounded bulk vector materialization

The v7 matrix replaces the former count-based forcing condition with a real
vector function boundary every 512th iteration. `vector-count` is now valid in
the non-escaping local representation, so it no longer creates an artificial
materialization cliff. The rare boundary makes the binding escape while
keeping the same data-dependent checksum and staying within fixed fuel.
The candidate imports a fixed two-page (128 KiB) memory, reserves a private
aligned LIFO slice before evaluating items, writes signed i64 values once, and
makes one synchronous checked host call that copies into the immutable
externref. The private bump advances before item evaluation, so nested or
host-re-entrant construction receives a disjoint slice. Unsigned wraparound,
scratch exhaustion, unaligned ranges, excessive counts, and actual-memory
bounds are rejected; neither memory nor bump state is exported. The host
requires the bulk function and memory imports as a pair and allocates zero
scratch pages for typed modules that do not use this path.

Five samples at 100,000 measured iterations after an equal warmup produced:

| v7 vector representation | Candidate Wasm/V8 | Clojure primitive | Clojure boxed | CLJS advanced | Rust | Wasm/Rust |
|---|---:|---:|---:|---:|---:|---:|
| non-escaping locals | 10.74 ns | 236.98 ns | 235.84 ns | 28.33 ns | 2.50 ns | 4.29× |
| function-boundary materialization | 967.69 ns | 244.19 ns | 237.68 ns | 22.83 ns | 2.62 ns | 369.00× |

The materialized row is about 6.20× faster than the pre-bulk 5,998.10 ns
candidate and 8.04× faster than the pinned 7,777.99 ns row, but remains 3.96×
slower than primitive Clojure and 42.40× slower than advanced ClojureScript in
this workload. The function-boundary artifact is 2,282 bytes with SHA-256
`9fe581a86a959375d3e82b95338ec1bf0b04c44bede840be8805251c262c828d`.
Standalone
Wasmtime remains explicitly unsupported for this artifact because it imports
the typed externref host; the non-escaping 652-byte artifact remains supported.
The published-pins supervised native cell is explicitly unsupported because
those KIR/verifier pins do not yet admit the private vector boundary.

### Private native vector boundary and exported copy-out candidate

Native already represents a vector as a one-word, context-owned handle. The
candidate admits `:vector-i64` and `:vector-f64` parameters/results for
non-exported functions. The next bounded slice admits a vector result only on
a zero-argument, non-entry export. Both KIR admission and `kotoba-verifier`
still reject vector parameters and vector entry results.

The native export descriptor names copy-v1, result kind, invocation-copy
ownership, and the 16,384-item ceiling. The production POSIX supervisor accepts
that mode only with a structured report, empty capability allowlist, zero
arguments, and no repeat timing. After the child exits successfully, the
parent validates the returned handle, table bounds, slice bounds, and item
ceiling, then writes a 0600 temporary and atomically renames a canonical
little-endian `KXVEC01\\0` wire file. Invalid handles return trap exit 126 and
publish no file. The child never sees the host output path or buffer. This is
not yet tender-native integration, vector input marshalling, an entry-result
ABI, or Windows parity.

A classpath-verified run generated at `2026-08-10T03:01:29.500Z` used clean
`kotoba-kir` `5cff10e`, `kotoba-verifier` `e6d275e`, and `kotoba-native`
`ef2df69`. The production W^X, fork-supervised loader passed all checksums,
including the materialized vector function boundary:

| Workload | Cold median | Supervised steady | Rust ratio | Startup-inclusive upper bound | RSS | KEXE |
|---|---:|---:|---:|---:|---:|---:|
| scalar | 14.29 ms | 13.40 ns/iteration | 5.54× | 69.37 µs/iteration | 4.11 MiB | 9,480 B |
| branch | 12.87 ms | 15.55 ns/iteration | 7.23× | 61.36 µs/iteration | 4.08 MiB | 9,480 B |
| integer mix | 14.81 ms | 22.93 ns/iteration | 8.96× | 56.61 µs/iteration | 4.08 MiB | 9,480 B |
| vector allocate/scan | 33.96 ms | 74.10 ns/iteration | 28.59× | 56.66 µs/iteration | 4.14 MiB | 7,884 B |
| vector materialize/scan | 12.17 ms | 63.01 ns/iteration | 24.23× | 43.72 µs/iteration | 4.13 MiB | 8,903 B |

The steady measurement retains the unchanged 512-call fuel contract by resetting
fuel and bounded region cursors for each supervised invocation. It is workload-
specific evidence, not general Rust parity: scalar native is 5.54–8.96× Rust
and the two vector rows are 24.23–28.59× Rust. The separate batch includes
process startup and remains only an upper bound; a 5,000-iteration invocation
still rejects with `SIGTRAP` at the fuel boundary.

The independent v2 qualification gate reproduced byte-identical scalar,
scalar-replaced vector, and forced-materialization vector artifacts from JVM
and nbb, validated all three, and checked all deep checksums. It reports
`candidateQualified: true` but `promotionReady: false` because the
implementation still lives in a dirty working tree.
The report records base commit `b0c9837f`, `dirty: true`, and
`classpathVerified: true`; these are working-tree qualification results, not a
claim that `b0c9837f` itself contains the optimization.

These candidate numbers are not yet the default compiler result: `deps.edn` remains
pinned to published `kotoba-wasm` commit `b0c9837f`. Publishing the backend
change, advancing the compiler pin, regenerating `deps-lock.edn`, and rerunning
the complete conformance suite are required before removing the pinned 5,000
iteration cap from `benchmark-runtime`.

## Remaining comparison matrix

Runtime comparisons should use equivalent semantics and publish at least these
lanes:

| Lane | Required mode |
|---|---|
| Kotoba Wasm | V8 and Wasmtime; Chicory reported separately |
| Kotoba native | verified KEXE, target-native host |
| Clojure | AOT plus warmed HotSpot; primitive and boxed variants |
| ClojureScript | advanced compilation on the same V8 version |
| Rust | `--release`, pinned `rustc`, explicit `target-cpu` |

The scalar loop, balanced branch, integer-mix, materialized vector baseline,
non-escaping vector scalar replacement, bounded literal bulk materialization,
cold-start, boxed/primitive Clojure, V8/Wasmtime split, and peak-RSS lanes now
exist. The remaining workload set is recursion, vector map/reduce, immutable
list/tree, string scan, mutation-derived vectors, exported vector input marshalling,
allocation/region teardown, and capability calls.
Chicory and an embedded typed Wasmtime host with a steady timer must still be
reported separately. Until those lanes
exist, the project may report the workload-specific figures above but not
general Rust parity or an overall Clojure/CLJS speedup.
