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

Amu owns a versioned `kotoba.runtime-comparison/v1` harness. It builds and runs
one source-controlled arithmetic kernel across optimized Rust, warmed Clojure,
advanced ClojureScript, admitted Amu Wasm32, and Amu native code. Every sample
must produce the same independently calculated result. Engine order rotates by
run, and the report binds the exact host, toolchain, compiler commit, dirty
state, build times, artifact sizes, process wall time, maximum RSS, and
steady-state call time.

The native direct-call runner is a separate benchmark-only C program. It
retains W^X mapping and the context ABI but deliberately bypasses production
supervision and sandboxing. Its output must state that boundary. It cannot be
selected by the production loader, whose source and path remain unchanged.

The Wasm runner admits the module through `instantiateKotoba`, rejects imports,
warms across fresh instances, and measures no more than 400 calls on one fresh
instance because fuel is sealed. No benchmark option may raise or bypass that
production fuel contract.

## Consequences

Performance discussion can cite a reproducible ratio for a named workload and
machine without turning it into a universal language ranking. CI smoke-tests
all five real engines and the report schema, but does not enforce a universal
speed threshold.

The first kernel does not cover allocation, collections, strings,
capabilities, I/O, concurrency, or whole applications. More workload families
may be added under new names; they must preserve equal observable results and
the same evidence boundaries. Native numbers from the direct runner are not
evidence that the production sandbox path has equivalent latency or safety.
