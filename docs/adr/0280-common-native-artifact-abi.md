# ADR 0280: Common native artifact ABI for bounded comparison

## Decision

The six-domain bounded Amu-versus-Rust suite measures both native arms through
one external C runner and one eight-`i64` runtime-resolved indirect-call ABI.
Rust fixtures are kernel-only dynamic libraries; they contain no measurement
loop. Amu remains raw extracted W^X code. Loading and symbol resolution occur
before timing.

This slice pins `kotoba-native`
`cdf7b45c80db1839a568c22e17d7577a782a1d1c`, including its AArch64
quotient/remainder `MSUB` fusion.

The claim contract pins the ABI name, argument map, runner compiler flags,
Darwin AArch64 target, Rust `cdylib` flags, and a per-domain semantic vector
corpus with exact results and Amu fuel consumption. Preparation seals the
runner source/binary, Rust source/library, Amu KEXE/code/provenance, every child
bundle and the root index. Measurement records context fuel before, after and
consumed on both arms. Rust must leave it unchanged; Amu must match the exact
fixture rule.

`kernel_loop_call.rs` uses an empty AArch64 assembly value barrier in its
identity helper. It emits no instruction in the helper but prevents LLVM from
proving the loop is `return n`; the competitive test requires the optimized
kernel to retain the helper call. The call, branch-call and loop-call Rust
fixtures contain no `black_box` operation.

## Scope

This removes a known comparator-only inline and constant-hoisting advantage.
It does not show that Amu wins any domain. A bounded claim still requires all
six fresh, clean, host-qualified perfgate wins. The competitor universe remains
Rust only, and the broad or world-fastest flag remains false.

The compiler/runtime remains independent of Rust. Rust and the system C
compiler are optional benchmark preparation tools only.
