# ADR 0230: Pin the aggregate boundary contract before extracted calls

## Status

Accepted.

## Context

Local record and variant SROA removed aggregate allocation inside one function,
but that evidence did not define what happens across a call. The established
emitters box escaping records into a pair-chain handle. The extracted GMIR path
has no call operation, allocates only caller-clobbered registers, and owns one
shared MC frame. Treating local bundles as an ABI would corrupt live values and
could let a callee release its caller's frame.

## Decision

Pin `kotoba-native` `ceca09377c53a33c4ea8bcf4a3f2e49f32cdf83d`
and `kotoba-verifier` `2b0d715febeb109710f09c279d66a7d10272de96`.

Amu requires aggregate-boundary contract v1 to retain these facts:

- escaping records use one declaration-ordered pair-chain handle;
- the host context owns its bounded 4,096-cell arena;
- both extracted allocator profiles are fully call-clobbered;
- extracted record, variant, and call boundaries remain `:held`;
- call-shaped KIR does not enter the extracted GMIR producer.

The verifier consumes the producer vocabulary while independently deriving the
types it accepts. Contract publication therefore cannot widen verification by
itself.

## Consequences

The next call implementation has an explicit admission checklist instead of an
implicit target-emitter convention. This change does not add a call operation,
remove pair allocation, define borrowing, or establish Rust performance parity.
Those claims remain held until per-function frames and call-clobber-aware
allocation execute on both native ISAs.
