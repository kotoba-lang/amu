# ADR 0078: Scalar option/result Wasm lowering

Status: accepted

## Context

The frontend, reference runtime, JavaScript backend, and native word ABI admit
the monomorphic `:option-i64` and `:result-i64` operations. The typed Wasm
backend admitted the same program but had lowering only for the structurally
typed `[:option :i64]` and `[:result :i64 :i64]` forms. A valid program
therefore failed late with `typed Wasm operation is not qualified`.

## Decision

Treat the monomorphic names as sealed descriptor aliases:

- `:option-i64` encodes exactly as `[:option :i64]`;
- `:result-i64` encodes exactly as `[:result :i64 :i64]`.

No new metadata tag or host representation is introduced. The descriptor table
records the source-level alias, while its binary descriptor uses the existing
option/result encoding understood by the typed host runtime.

The Wasm backend lowers constructors, tag predicates, and payload projections
through the existing bounded typed-value intrinsics. Every projection preserves
lazy fallback evaluation, validates the descriptor before observing its tag or
payload, and returns an `i64`.

## Consequences

- Programs already admitted by the language now compile and execute on Wasm.
- Typed capability contracts using the monomorphic descriptors use the same
  metadata and host validation as their structural equivalents.
- This closes one concrete instance of issue #258. It does not close the
  umbrella requirement for one data-derived backend/admission surface.
