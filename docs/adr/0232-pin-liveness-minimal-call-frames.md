# ADR 0232: Pin liveness-minimal call frames

## Status

Accepted.

## Context

ADR 0231 pinned the first correct scalar direct-call frame. Its all-vreg policy
stored every definition and reloaded every use. The merged compiler closure now
publishes an explicit `:call-live` policy for straight-line callers and retains
all-vregs as the safe CFG/register-pressure fallback.

## Decision

Pin native merge `30d4a1fb6f1ccc4e52d5abd11852a7fecf8bcab8`
and verifier merge `f17698b44c4757325972c7340a205960afefe0be`.

Require the representative caller to own one frame slot and exactly one save
plus one lazy reload for its single live-across value on both native targets.
Keep the existing real-process proof: x86-64 and AArch64 must execute the
compiled helper/caller image and return `42` without `KEXE_TRAP`.

Record and variant function boundaries remain held. The complete aggregate ABI
v2 call guarantee set remains mandatory.

## Consequences

For the pinned KIR fixture, emitted code decreases from 123 to 84 bytes on
x86-64 and from 108 to 88 bytes on AArch64. Dead pre-call values need no frame
traffic. CFG liveness, slot coloring, indirect calls, recursion, aggregate
calls, and Rust-wide performance parity remain unclaimed.

ADR 0231 remains the call-admission record; this ADR supersedes only its
non-minimal spill policy.
