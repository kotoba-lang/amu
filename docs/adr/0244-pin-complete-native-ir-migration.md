# ADR 0244: Pin the complete production native IR migration

Status: accepted

Pin `kotoba-native` at `fad9959837ec216f12e4fffccf2b5eae3c06b70e`.
Its dependency closure pins merged GMIR, MIR, and codegen contracts that cover
portable scalar/f64/control, bounded memory, runtime and capability calls,
literal data, word-field record and scalar variant boundaries, and the closed
x86-64 privileged action family, plus terminal local calls.

Both production backends invoke whole-module KIR → GMIR → MIR → allocated MC
unconditionally. Terminal calls release the current frame and use non-linking
branches on both ISAs, including mutual recursion. Multiple exports share one
final layout. Unsupported nested
or recursive aggregate representations fail before target encoding; they do
not select a legacy emitter.

Verification uses the native repository suite and Amu's real-process loader
table on both x86-64 and AArch64. Privileged x86 instructions are verified at
the exact byte-family boundary because executing them in the unprivileged test
loader is neither safe nor representative.
