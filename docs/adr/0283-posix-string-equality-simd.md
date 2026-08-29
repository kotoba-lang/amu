# ADR 0283: POSIX checked string equality uses explicit 16-byte SIMD

## Decision

After the existing handle, length, allocated-slice, and canonical UTF-8 checks,
the POSIX KEXE loader compares equal-length string bytes in 16-byte chunks.
AArch64 uses NEON `vceqq` plus `vminvq`; x86-64 uses SSE2 `cmpeq` plus
`movemask`; a bounded `memcmp` handles the tail. Other architectures keep the
scalar `memcmp` path.

The context ABI and callback offsets do not change. The reviewed loader source
identity advances in `kotoba-lang/artifact`; old receipts correctly fail the
identity check against the new loader. Windows is unchanged and retains its
separate source identity until implemented and executed there.

## Verification and claim boundary

The loader must compile at `-O3 -Wall -Wextra -Werror`. On supported build
architectures, optimized assembly must contain the selected SIMD instruction
family. Existing cross-ISA string execution vectors retain semantic parity.
This proves explicit vectorized comparison is emitted; it is not by itself a
latency or broad fastest claim. Public performance claims require the same
artifact, machine, workload, repetitions, noise gate, and qualification policy.
