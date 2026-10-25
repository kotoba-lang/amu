# Native seed cross-compilation to x86_64 Linux

> **2026-10-22: the trusted C loader was removed.** Instructions below that build
> or run it (clang, `kexe-loader`, `scripts/seed/build-*.py`, `check-*.py`) are
> historical and no longer runnable; see `scripts/seed/RETIRED.md`. The current
> route is `scripts/seed/selfhost-bootstrap.py` on arm64 Linux.


The optional seed closure adds native x86-64 code generation for standalone
scalar programs and context-v11 runtime programs. An Amu-produced compiler
reads Kotoba, shares the adopted
reader/checker/SIR lowering, and directly emits x86-64 instructions and a Linux
ELF64 executable. Python orchestrates calls; Clang builds the existing trusted
C loader. Neither compiles Kotoba or generates guest instructions. There is no
JVM, Node or Graal fallback.

The runtime profile adds strings, vectors, bytes, closures, state results and
up to16 internal arguments. The Linux selfhost closure is a source compiler:
it includes the shared frontend and x86 backend, with an explicit source-only
driver. Project linking, KIR compilation, floating-point operations,
whole-component Q9 qualification and x86_64 Embench remain separate gates.
The existing public launcher and its Kototama
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

The following describes the standalone ELF profile. The runtime profile is
described below; both share the same checked source frontend and emitter.

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

## Runtime profile and Linux self-build

Verified at source/test commit `112b8a7b23f4f8eb6094fb804f5cf9c8fd7dd49f`:
[all four native target CI jobs passed](https://github.com/kotoba-lang/amu/actions/runs/38717513906).
Actual x86_64 Linux G1/G2/G3 compiler payloads and containers match byte for
byte. The24 runtime cases match AArch64 results/traps/fuel, six refusal cases
pass, and55 standalone ELF regressions pass on Linux. The local Rosetta run
has the same whole compiler/guest bytes; a512 KiB launch-stack diagnostic also
rebuilds the compiler. Evidence and raw archives are indexed in
[`runtime-selfhost-qualification.json`](evidence/native-x86_64-linux-20261015/runtime-selfhost-qualification.json).
This qualifies the source-only compiler profile described here; public
launcher/release adoption, whole-project linking, Q9 and performance remain
separate gates.

`seed/X86_64-LINUX-SELFHOST-MANIFEST` selects the source-only compiler closure.
The build uses the adopted native AArch64 compiler to generate an AArch64
bridge from this exact closure. That bridge emits the first x86 compiler.
On Linux, the x86 compiler emits G2 from the identical source; G2 emits G3.
The harness requires whole-container and whole-payload G1=G2=G3 identity.
Python only checks pins, launches native processes and copies payload bytes.
Clang only builds the existing trusted context-v11 C loader.

```sh
# macOS arm64: generate the bridge, x86 G1 and independent AArch64 references.
python3 scripts/seed/check-x86_64-selfhost.py --prepare --output /absolute/new-selfhost
# Transfer that directory unchanged to the same repository revision on Linux.
python3 scripts/seed/check-x86_64-selfhost.py --execute-linux --output /absolute/new-selfhost
```

The CI workflow performs both stages on macOS arm64 and Ubuntu x86_64.
The Linux harness disables malloc's mmap allocations and reserves16 MiB of
ordinary heap headroom at startup, using glibc's `mmap_max=0`,
`top_pad=16777216` and `trim_threshold=16777216` tunables (plus their legacy
environment aliases). The trusted loader's filesystem provider uses malloc
for source bytes after sandbox installation; reserving the heap before its
address-space limit is lowered avoids a later allocator fallback to mmap.
The existing seccomp filter still denies guest `mmap`. These settings follow the
[glibc allocation contract](https://sourceware.org/glibc/manual/latest/html_node/Memory-Allocation-Tunables.html)
and is recorded in every Linux invocation receipt.
`tools/seed-x86_64-linux-loader.c` includes the pinned loader unchanged and
pre-touches512 KiB of the process stack before entering it. This reserves
stack pages before the same address-space ceiling takes effect, within the
existing1 MiB stack budget. It adds no guest syscall or capability grant.
The x86 emitter also lowers direct tail calls with at most5 arguments to
frame restoration plus a jump; a20,000-step mutual recursion case exercises
this path. Stack-argument calls retain the ordinary calling sequence.
`--execute-rosetta` provides a separate local diagnostic; its report never
claims Linux execution. Raw inputs, compiler generations, subprocess
arguments, before/after pins and stdout/stderr are retained. Failed attempts
retain their logs and never get a successful selfhost receipt.

The runtime compiler command has an explicit format:

```sh
compile /absolute/source.kotoba --target x86_64-linux \
  --output /absolute/new-output.kx64 --format kx64-v1
```

The tagged header is `KX64V1 x86_64-linux sysv-ctx-v11 LENGTH 0`, followed by
two newlines and exactly LENGTH payload bytes. It cannot be mistaken for the
legacy AArch64 KSEED1 format. The verified payload runs with the trusted
loader's `RAW 0 0 x86_64 ALLOW_CSV` entry. For compiler invocations add
`KEXE_COMMAND=1`, compiler resource budgets above, explicit filesystem root,
and allow wires35,37,38,39. The loader supplies runtime fuel and validates
handles, indices, UTF-8 boundaries, allocations and capability grants.

Strings use the existing pair(offset,length) representation; literal offsets
address the read-only code pool. Runtime helpers implement dynamic strings,
persistent and in-place vector operations, and bytes. Guest calls keep r9 as
context, place arguments6..16 on the stack and return state in rax/rdx.
C helper calls use ordinary SysV argument registers and reload context after
every call. Closure entries use RIP-relative addresses; pooled table reads
check unsigned indices before accessing memory. CODE packs eight bytes per
word, independently of the adopted AArch64 layout.

The helper register assignment is checked against LLVM's
[X86 calling conventions](https://github.com/llvm/llvm-project/blob/main/llvm/lib/Target/X86/X86CallingConv.td).
The exact internal convention, scratch space, relocation kinds and format
are recorded in `seed/X86_64-LINUX-ABI`. The implementation keeps all shared
frontend files and the adopted bootstrap unchanged.

Remaining target work includes project linking, sealed artifact integration,
float semantics and a fresh19-program comparison on x86_64 Linux.
AArch64 benchmark results are not x86_64 results.

## Loaderless static image (2026-10-22)

`--format static` (Linux selfhost closure, seed modules 75/76) links the
guest with a runtime written in Kotoba into one `x86_64-linux-static` ELF; no
C loader runs it. The selfhost compiler built this way rebuilds itself
byte-identically on Linux x86-64 (S1=S2=S3) and agrees with the loader-run
compiler on `kx64-v1` output; the one bootstrap step (S1) still goes through
the pinned loader. Design, limits and receipts:
[`native-seed-c-free-runner-static-image-20261022.md`](native-seed-c-free-runner-static-image-20261022.md),
`scripts/seed/check-x86_64-static.py`.
