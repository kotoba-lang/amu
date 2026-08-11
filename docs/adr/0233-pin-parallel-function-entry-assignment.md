# ADR 0233: Pin parallel function-entry assignment

## Status

Accepted. Its five-argument fallback evidence is superseded by ADR 0236; the
four-argument zero-frame evidence remains current.

## Context

ADR 0232 minimized values preserved across straight-line calls. Function entry
still needed its own ABI proof: x86-64 allocator destinations overlap later ABI
inputs, so sequential reassignment can clobber an argument before use.

## Decision

Pin native merge `7f2120deade9425d7920689b88119790f4bdcea9` and
verifier merge `f1d8e07c49d90e8670bf1f375cb1bb2155c1a52c`, including
their MIR and codegen closure pins.

Require a four-argument scalar call to compile with zero callee and caller
frame slots and no spill operations on x86-64 and AArch64. Execute `.kotoba`
programs for both the four-argument register path and five-argument fallback in
every available real native loader process. They must return 15 and 31 without
`KEXE_TRAP`.

## Consequences

The representative four-argument module is 66 bytes on x86-64 and 40 bytes on
AArch64. The safe five-argument fallback remains 287 and 176 bytes with frame
slots `[9 6]`. This is a bounded scalar ABI and size result, not a claim of
general register allocation, aggregate calls, or Rust-wide performance parity.
