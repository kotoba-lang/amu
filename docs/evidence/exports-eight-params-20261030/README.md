# Exports with six to eight parameters on the aiueos object route: execution (2026-10-30)

Compiler: the Mac fixed-point full compiler (`F2-signed.macho`) that
`scripts/seed/check-aiueos-user-macos-native.py` builds from this branch's seed with the Mac root of
main `a4c16e7c`. Each source exports `f` computing `sum(a_i * (i + 1))` over its parameters:

    (ns w8 (:export [f]))
    (defn f [a0 :i64 ... a7 :i64] :i64 (+ (* a0 1) (* a1 2) ... (* a7 8)))

A bare-metal multiboot image (QEMU 10.0.3, TCG, debugcon) calls `f` the way a System V C caller does:
`rdi = 0x0102030405060708`, `rsi rdx rcx r8 r9 = 0x11 0x22 0x33 0x44 0x55`, then pushes `0x77` and
`0x66` (arguments eight and seven) and calls; it prints the return value and whether `rsp` came back to
its value before the pushes (`01`). The expected values are computed independently in Python.

| object | sha256 (first 16) | result | stack | expected |
|---|---|---|---|---|
| w6 | c2ad58cf758e2e46 | 0102030405060BAE | 01 | 0102030405060BAE |
| w7 | 5e116d9ada9cefd5 | 0102030405060E78 | 01 | 0102030405060E78 |
| w8 | ba99e09de62143b7 | 0102030405061230 | 01 | 0102030405061230 |

Negative controls (mutant compilers built the same way):

| mutant | w6 | w7 | w8 |
|---|---|---|---|
| stack-word copy reads `[rbp+24+8(j-6)]` | 0102030405060BAE (no copy at six) | 0102030405060EEF | 4C13762F40117A37 |
| `r9` stored at `[rsp+8]` | 01020304050609B0 | 0102030405060C7A | 0102030405061032 |

The harness and its linker are scratch tooling outside this repository (adapted from the JUN-556 E
smoke): `harness3.S` (the multiboot entry and long-mode set-up of the E harness, with the call above)
and `build3.py` (links the object's `.text`/`.data` and resolves its relocations). This is execution
evidence for the shim, not a kernel boot.
