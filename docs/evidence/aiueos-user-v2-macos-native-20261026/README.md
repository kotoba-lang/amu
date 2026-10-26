# Mac native user-v2 Goal compiler gate (2026-10-26)

The [v2 receipt](v2-goal.json) and [v1 fixed-point receipt](v1-fixedpoint.json)
are from one Apple Silicon run of
[`check-aiueos-user-v2-macos-native.py`](../../../scripts/seed/check-aiueos-user-v2-macos-native.py).
The signed input compiler SHA-256 was
`012bfb77a364b3b68cb5e2c406ae49535784fa2b851dfdbbe1bd10efffcb950a`;
the signed native packager SHA-256 was
`2ee308409db572c08733a4b0a28fc1908c8b15c44b045cf78e671ff798439ad0`.
The exact 47-module source unity SHA-256 was
`4d4887f14e66794e2b21708e90bdd48e3f7c18ca36c8a9e650bb81784a491300`.
F1 and F2 native compiler containers were identical, SHA-256
`8abe2443263ea671dbf20f01ccfb356ee7e0e6c1c4033bdd68d57fde20ca5d5c`.
The v1 scalar ELF remained byte-identical at SHA-256
`7f5a8c0a31b5bdf191410f007973413d16e497a20ae7fe86c734b9fea85808b1`.

F2 produced the 8,280-byte [v2 Goal ELF](v2-goal.elf), SHA-256
`548bf54f7a6776e1d943d88d4cddca4e169948de89e678c108af6249f7d58eca`.
The independent host observer checked the entry shim, two i64 arguments,
RX/RW segments, 64-byte BSS Goal region, zero-capability context and sealed
trampoline. A constant two-argument program also compiled. Wrong arity,
calculated base, substituted length, undeclared effect, wrong export name,
wrong parameter type and wrong return type all exited nonzero and produced no
ELF. Mutating either RW memory size or a zero context byte was refused by the
image observer. The [ABI document](../../aiueos-user-v2-goal-abi.md) defines
the intended OS input bytes.

To repeat on Apple Silicon with the two pinned signed native input programs,
set `COMPILER`, `PACKAGER` and a new `OUT` directory under
`github/workspaces/`, then run from this Amu checkout:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/seed/native_build_queue.py -- \
  python3 scripts/seed/check-aiueos-user-v2-macos-native.py \
    --compiler-image "$COMPILER" \
    --compiler-sha256 012bfb77a364b3b68cb5e2c406ae49535784fa2b851dfdbbe1bd10efffcb950a \
    --packager-image "$PACKAGER" \
    --packager-sha256 2ee308409db572c08733a4b0a28fc1908c8b15c44b045cf78e671ff798439ad0 \
    --output "$OUT"
```

This is a compiler and artifact gate run on macOS without a Linux, JVM, Node
or C compiler process. It does not execute the v2 ELF in an AIUEOS guest.
The current AIUEOS v1 loader still needs a separately versioned v2 rule and
Goal write path; trusted approval, model/tool execution, durable Itonami turn,
release and physical hardware qualification remain open.
