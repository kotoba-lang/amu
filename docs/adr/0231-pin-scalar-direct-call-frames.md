# ADR 0231: Pin scalar direct-call frames

## Status

Accepted.

## Context

ADR 0230 pinned aggregate contract v1 and deliberately held extracted calls.
The canonical GMIR, MIR, and MC repositories now publish version 3 function
modules. `kotoba-native` consumes them with independent function frames and
both production emitters route a bounded scalar direct-call module through
that pipeline.

A compiler pin is not sufficient execution evidence. The Amu consumer must
also run the emitted image in the real x86-64 and AArch64 loader processes and
prove that a caller value survives the call.

## Decision

Pin `kotoba-native` merge `228e389ccc449d6256a7f6ba0b623203e0a439d9`
and independently matching `kotoba-verifier` merge
`6df0626c78c60d45103d2d18ea23afc8471acf7b`.

Require aggregate ABI v2. Scalar direct calls are admitted only with
per-function frames, live-value preservation, parallel argument assignment,
and the target's single-word return register. Record and variant parameters or
results remain held. Standalone expression lowering still rejects call-shaped
KIR; only a validated function module may acquire GMIR v3 calls.

The ISA execution suite compiles a helper and a zero-arity entry whose local
value `40` remains live while the helper computes `2`. Both real loader
processes must return `42` without `KEXE_TRAP`.

## Consequences

Amu now has a production, cross-target scalar direct-call route with a pinned
producer/verifier closure and executable evidence. Indirect calls, recursion,
more than five scalar arguments, aggregate boundaries, and liveness-minimal
call spilling remain outside this slice. No Rust-wide speed, size, safety, or
compile-time parity is claimed.

ADR 0230 remains authoritative for the aggregate representation and holds; its
scalar-call hold is superseded by this decision.
