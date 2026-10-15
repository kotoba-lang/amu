# Native seed cross-compilation to x86_64 Linux

The optional seed closure adds a native cross-compilation path for scalar
programs. An Amu-produced AArch64 compiler reads Kotoba, shares the adopted
reader/checker/SIR lowering, and directly emits x86-64 instructions and a Linux
ELF64 executable. Python orchestrates calls; Clang builds the existing trusted
C loader. Neither compiles Kotoba or generates guest instructions. There is no
JVM, Node or Graal fallback.

This is the first scalar profile. It does not establish that the compiler
itself runs or self-builds on x86_64, whole-component Q9 qualification, or
x86_64 Embench performance. The existing public launcher and its Kototama
default remain unchanged. The adopted seed source manifest and bootstrap
receipts also remain unchanged.

## Build and use

On macOS arm64, use new, empty workspace paths:

```sh
python3 scripts/seed/build-x86_64-linux.py --output /absolute/new-cross-build
```

This verifies the adopted source/bootstrap pins, builds the optional closure
in `seed/X86_64-LINUX-MANIFEST`, and requires native and container G1/G2 equality.
The resulting compiler runs through the trusted loader:

```sh
KEXE_COMMAND=1 KEXE_CAP_RESOURCES_35=/absolute/guest-directory KEXE_FUEL=off \
  /absolute/new-cross-build/host/kexe-loader \
  /absolute/new-cross-build/artifacts/G2.bin 0 0 aarch64 35,37,38,39 -- \
  compile /absolute/guest-directory/program.kotoba --target x86_64-linux \
  --output /absolute/guest-directory/program.elf --fuel 1000000
```

Use the resource settings in `build-x86_64-linux.py` for compiler invocations:
`KEXE_VECTORS=4194304`, `KEXE_VECTOR_ITEMS=134217728`,
`KEXE_STRING_POOL=268435456`, `KEXE_PAIRS=16777216`. Files must be inside the
explicit guest directory. The output path must not exist. The target accepts
the exact flag order above; `--fuel` is optional and defaults to 1000000.
The positive budget is bounded by 2^53-1. Unknown/additional flags, including
unimplemented policy or source-path flags, are refused, never dropped.

Example source:

```clojure
(ns example (:export [main]))
(defn- sum [n :i64 s :i64] :i64
  (if (= n 0) s (sum (dec n) (+ s n))))
(defn main [] :i64 (sum 100 0))
```

On x86_64 Linux, `chmod +x program.elf` then execute it. It writes exactly
eight little-endian bytes representing the signed i64 result to stdout and
exits zero on a complete write; a short/error write reported by the syscall
exits74. Normal process signals, including SIGPIPE, remain process signals.
The process requires
no dynamic loader, libc, companion runtime, or installed Amu compiler.

## Profile and ABI

- Exactly one exported `main()->i64`; private/direct functions accept up to
  five i64/bool parameters and return i64/bool.
- Wrapping i64 add/sub/multiply, signed quotient, bitwise operations, shifts
  with counts modulo64, signed comparisons, boolean operations, conditionals,
  loops/recur and direct calls. Existing lowering preserves parallel recur
  assignment and self-tail recursion.
- Frames are bounded to4096 bytes, call sites have16-byte stack alignment,
  parameters use rdi/rsi/rdx/rcx/r8, and r9 carries a private fuel context.
  Every source fuel site decrements a positive budget. Exhaustion executes
  UD2 (SIGILL); illegal signed division uses IDIV (SIGFPE).
- The entire SIR and every function signature are admitted before output,
  including unused functions. Handles/runtime helpers, capabilities, floats,
  indirect calls and two-register state results are refused with E7101/E7102.
  Capacity or unresolved relocation errors are E7103/E7104. Failed admission
  does not create an output; existing outputs are preserved.
- Output is ELF64 LE ET_EXEC for EM_X86_64. The header/code load segment is
  RX; the16-byte fuel context is in a separate page-aligned RW segment;
  PT_GNU_STACK requests a non-executable stack. This is an ordinary process
  executable, not a signed KEXE admission or a capability sandbox.

The encoding follows the [x86-64 System V ABI](https://gitlab.com/x86-psABIs/x86-64-ABI)
with a private hidden-context register. ELF segment layout follows the
[System V ELF program-header specification](https://refspecs.linuxfoundation.org/elf/gabi4%2B/ch5.pheader.html).

## Verification and next steps

```sh
python3 scripts/seed/check-x86_64-linux.py --selfbuild-output /absolute/new-cross-build \
  --output /absolute/new-linux-suite
python3 scripts/seed/check-x86_64-linux.py --execute-linux --output /absolute/new-linux-suite
```

The first command cross-compiles independently specified full64 boundary,
control-flow, call and trap programs, checks ELF fields/permissions/padding,
and exercises refusal and existing-output cases. The second executes the
unchanged ELF artifacts on x86_64 Linux and checks the entire eight-byte
result or the declared signal. The CI workflow transports the same artifact
suite from the native AArch64 build job to the Linux execution job.
`--execute-rosetta` separately checks the exact function code on macOS arm64
with Rosetta and the trusted x86-64 C loader. It is not Linux ELF execution.
Raw failed attempts and logs remain in the caller's workspace.

Next implementation units are the checked runtime helper ABI and literal
pool, vector/string/bytes and closure/state/float operations, x86-64 compiler
self-build, project linker/sealed artifact integration, and then a fresh
19-program comparison on x86_64 Linux. Each remains a separate qualification
gate; AArch64 benchmark results are not x86_64 results.
