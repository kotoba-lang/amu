# ADR 0226: cross-language runtime evidence is workload-bound

- Status: accepted
- Date: 2026-08-10
- Machine-readable companion:
  [`0226-cross-language-runtime-evidence.edn`](0226-cross-language-runtime-evidence.edn)

## Context

Claims that Kotoba or Amu is faster than Clojure, ClojureScript, or close to
Rust are meaningless unless the implementations compute the same observable
result and the report separates steady-state execution, process startup,
memory, artifacts, and compilation. Native execution also has a production
supervisor boundary whose cost must not be silently mixed into a kernel claim.

## Decision

Amu owns a versioned `kotoba.runtime-comparison/v2` harness with two explicit
suites. The default `core` suite builds and runs source-controlled kernels only
through admitted Amu Wasm32 and Amu native code. It neither requires nor probes
Rust or another comparison toolchain. The `competitive` suite adds optimized
Rust, warmed Clojure, advanced ClojureScript, Go, Mojo, Python and TypeScript as
optional adapters. Every sample must produce the same independently calculated
result. Engine order rotates by run, and the report binds the exact host,
measured toolchains, compiler commit, dirty state, build times, artifact sizes,
process wall time, maximum RSS, and steady-state call time.

An unavailable or deliberately disabled comparison adapter is recorded in
`skippedEngines`. Rust normalization is `measured`, `unavailable`, or
`not-requested`; `slowdownVsRust` is null unless Rust was actually measured.
Therefore Rust can support a competitive claim but cannot become an Amu build,
test, runtime, or release dependency.

The native direct-call runner is a separate benchmark-only C program. It
retains W^X mapping and the context ABI but deliberately bypasses production
supervision and sandboxing. Its output must state that boundary. It cannot be
selected by the production loader, whose source and path remain unchanged.

The Wasm runner admits the module through `instantiateKotoba`, rejects imports,
and calibrates a safe batch on fresh instances outside timed intervals because
fuel is sealed. It accumulates only call intervals; process wall time separately
retains instance-creation cost. Benchmark fuel is explicit, sealed into the
artifact, recorded in the report, and matched by the native benchmark context.

## Consequences

Performance discussion can cite a reproducible ratio for a named workload and
machine without turning it into a universal language ranking. The core gate
smoke-tests both Amu backends and proves the no-Rust boundary. Competitive
adapter tests are separate and do not gate Amu qualification when a toolchain
is absent. Neither suite enforces a universal speed threshold.

The first kernel does not cover allocation, collections, strings,
capabilities, I/O, concurrency, or whole applications. More workload families
may be added under new names; they must preserve equal observable results and
the same evidence boundaries. Native numbers from the direct runner are not
evidence that the production sandbox path has equivalent latency or safety.
