# ADR 0240: native-effect evidence terminates at the aiueos C-free surface

Status: accepted — 2026-08-11

## Context

The native clock contract now reaches KIR, the independent verifier, and both
machine backends. That proves a sealed artifact can represent the request and
result; it does not prove an OS process can execute the effect. Earlier text
assigned the guest-to-host syscall to Tender and allowed a C loader process to
look like the production runtime. aiueos ADR-0013 already owns the C-free OS
boundary, so that dependency direction was wrong.

The UEFI loader also handed its memory map to the kernel as a separately
allocated pointer. Amu correctly refuses to use a pointer loaded from memory as
a new kernel-region authority. Merely weakening provenance admission would turn
firmware bytes into arbitrary kernel memory access.

## Decision

Production native effects use this only dependency/evidence chain:

```text
provider type -> Amu -> KIR/verifier -> native backend -> aiueos
                                                    execution receipt -> Amu gate
```

The receipt edge carries evidence, not implementation authority. Amu does not
own processes, scheduling, syscalls or providers; aiueos does not redefine
Kotoba types or machine IR.

The compiler-emitted PE32+ loader now places a bounded 16 KiB UEFI memory map
directly after the 64-byte boot handoff prefix in the same RW image region.
The kernel derives `boot + 64` with the existing checked `kernel-subregion`
operation. It still checks that the pointer field equals that derived address,
but never promotes the field itself into a region base. Firmware requiring a
larger map fails closed at `GetMemoryMap`; increasing this bound is a versioned
handoff change, not an unchecked pointer escape.

## Evidence rules

- hosted Tender, Linux, JVM/FFM VMM and C-reference kernel runs are oracles only;
- `:aiueos-c-free-bare-metal-v1` is the sole production native-effect surface;
- qualification requires runtime and semantic vectors plus an empty receipt for
  C sources, foreign objects, imports and dynamic dependencies;
- boot-map, allocator, paging, CPL3 and provider evidence must be accumulated in
  dependency order. A later phase cannot substitute for an earlier one.

## Consequences

The next aiueos slice can parse and allocate from the UEFI map without adding a
raw-pointer intrinsic. The 16 KiB bound is smaller than the prior 128 KiB pool,
but it is explicit, compiler-owned, QEMU-testable and fail-closed. No hosted or
C implementation becomes part of the production TCB.
