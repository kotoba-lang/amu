# ADR 0234: Pin bounded lazy function-entry spills

## Status

Accepted.

## Decision

Pin native merge `eeae98511a574a1be1280b3b3fbdaa1fbdd6efed` and
verifier merge `8ced779bb88caf93792b0178da0fdcdaf38930a1`, including MIR
`534caf12` and codegen `4d960da4` in the generated dependency lock.

The aggregate ABI gate compiles a five-parameter local scalar call and requires
policies `[:allocator :call-live]`, frame slots `[1 1]`, and exactly one spill
store/load per function on both targets. The real loader gate executes the
five-argument `.kotoba` source on every available ISA and requires result `31`
without `KEXE_TRAP`.

## Evidence

The five-argument module is 115 bytes on x86-64 and 72 bytes on AArch64,
reduced from 287 and 176 bytes. The existing four-argument module remains
zero-frame and executes to `15`.

## Consequences

Amu's pinned compiler closure no longer describes or accepts whole-function
all-vreg materialization for the representative fifth entry argument. The
all-vreg path remains available for genuinely unsupported pressure and control
flow. This is not a whole-language Rust performance-parity claim.
