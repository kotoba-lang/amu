# ADR 0252: Cache repeated constants in branchless AArch64 leaf functions

Status: accepted

Date: 2026-08-12

## Context

After logical-immediate selection, the eight-round runtime kernel still
materialized `48,271`, `1`, `2,147,483,647`, and the signed-division reciprocal
multiplier in every round. LLVM keeps those values live across the unrolled
body.

Performing unrestricted GMIR constant CSE is not yet profitable: the current
allocator has four general scratch registers, and extending three constants'
liveness can move otherwise register-only code to its conservative spill path.
A target encoder cache can use AAPCS64 caller-saved registers outside that
allocator profile, but only while its control-flow and clobber boundary is
explicit.

## Decision

For AArch64 functions whose MC is one branchless leaf and whose encodings all
belong to a closed safe set, cache up to three repeated constants in `x13`,
`x14`, and `x15`. Rank candidates by machine-code bytes eliminated, then by
first occurrence. Rewrite only source operands; physical destinations remain
owned by register allocation.

Branches, calls, host boundaries, checked-memory encoders, and every operation
outside the closed preservation set disable this cache for the whole function.
This deliberately trades some opportunities for a simple proof that no
alternate entry or private scratch convention can invalidate a cached value.

Signed reciprocal division separately retains its multiplier in `x16` across
compatible operations. The final sign correction now uses the allocated
quotient destination, leaving `x16` intact. A different reciprocal or any
operation not proven to preserve `x16` forces reload. `x17` remains local
reciprocal scratch.

Amu pins `kotoba-native`
`2fa12812356d472757f52b06193c8b7e738902ac`. GMIR, MIR, MC, verifier schemas,
and x86-64 output do not change.

## Evidence

The kernel now loads each of its four repeated constants once. Its symbol code
falls from 444 to 276 bytes: 168 bytes removed, exactly seven avoided reloads
times `(4 + 4 + 4 + 12)` bytes.

| artifact | paired median | extracted file | symbol code | KEXE |
|---|---:|---:|---:|---:|
| logical-immediate baseline | 11.028442 ns | 484 bytes | 444 bytes | 4,123 bytes |
| leaf constant cache | 10.895367 ns | 316 bytes | 276 bytes | 3,543 bytes |

These values come from 21 old/new samples alternated inside one process, with
10,000,000 calls per side after warmup. The median paired speedup is 1.0335x.
Separate-process measurements were rejected as optimization evidence because
background load and frequency changes reversed their ordering despite paired
execution restoring a stable improvement.

An additional 21-sample alternating comparison measured Amu at 1.379x Rust
LLVM O3 by median paired ratio. This improves the prior 1.487x result but does
not exceed LLVM.

Verification passed:

- `kotoba-native`: 145 tests, 2,020 assertions, including branch, checked-memory,
  reciprocal reuse, and reciprocal-clobber negative cases;
- Amu: 964 tests, 7,608 assertions;
- native/Wasm conformance and AArch64 W^X execution;
- JDK-free extraction, compiler-bundle byte parity, worker/daemon protocols,
  and seven-engine runtime smoke.

## Consequences

The common branchless arithmetic path gains LLVM-like constant reuse without
raising allocator pressure or widening the verifier contract. More complex
control flow receives no benefit until liveness-aware allocation can model
reserved registers directly.

LLVM's next visible advantage is strength reduction of multiplication by
`2^31-1` into shift/subtract arithmetic, followed by scheduling of the
round-to-round dependency chain. Those are the next backend steps; cached
registers must not be extended across calls or unreviewed encoders to pursue
them.
