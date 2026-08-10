# ADR 0225: bounded persistent compiler and reproducible compile baseline

- Status: accepted
- Date: 2026-08-10
- Machine-readable companion:
  [`0225-bounded-persistent-compiler.edn`](0225-bounded-persistent-compiler.edn)

## Context

Fresh nbb processes repeatedly pay launcher and namespace-load costs. Prior
timings could not distinguish that cost from frontend, admission, lowering,
emission, verification, provenance, and writes. Reusing compiler state can
reduce latency, but an unbounded daemon or policy-insensitive cache would weaken
Amu's resource and authority boundaries.

## Decision

Amu provides target-specific nbb entrypoints and an opt-in, target-locked,
sequential NDJSON worker. Inputs, argument counts, argument sizes, and worker
lifetime are bounded. Recoverable caller errors do not poison later requests;
an internal compiler error fail-stops the process.

The worker has process-local, size- and count-bounded LRU caches. Artifact
identity includes target, source, and exact policy material. Native entries are
admitted, sealed, independently verified, and given provenance before
insertion. Payload hashes are checked on every hit.

HIR and KIR caches exclude policy because those transformations are
policy-independent. Nevertheless current-policy admission always runs before
KIR reuse. Stage entries are integrity checked and source spelling may reuse
KIR only when serialized semantic HIR is identical.

The `kotoba.performance-baseline/v1` harness records fresh-process and warm
worker measurements separately, including phase decomposition, artifact size,
host identity, and compiler commit. CI thresholds remain opt-in and
host-specific.

## Consequences

Repeated small-module builds can avoid process startup and unchanged work
without broadening ambient authority or weakening admission. Target-specific
entrypoints also avoid loading irrelevant emitters.

Cache contents are not durable, shared, or trusted across compiler processes.
This decision does not claim runtime parity with Rust, Clojure, or
ClojureScript, and it does not establish universal compile-time ceilings.
Changed-module function-level invalidation remains future work.
