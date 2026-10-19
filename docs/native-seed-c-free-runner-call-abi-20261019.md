# C-free runner: kx64-v1 emitter call-site context discipline, byte-measured
(JUN-29, 2026-10-19)

Answers the follow-up question of `native-seed-c-free-runner-raw-elf-emitter-20261019.md`
§3 ("The measured kx64-v1 guest payloads chain `call [rdi+disp32]` too —
whether the compiler emits the reload between sites is a concrete follow-up
question for the emitter codegen"): does the seed x86-64 emitter reload the
context register between chained dispatches, and is SysV 16-byte stack
alignment held at every call site? Measurement record; no runner
implementation is claimed. Payloads are the same ones the slot-hit run
measured (`jun29-slots-20261019`), so this closes the open emitter-codegen
question against real compiler output.

## 1. Corpus (25 emitted payloads, all `--format kx64-v1`, `:sysv-ctx-v11`)

* **G1**: the x86-64 compiler payload, 1,231,648 code bytes, sha256
  `32fe88f0dc850728c44a4b4320b6c180292a38e98672c80759859a59469e3f34`
  (container `G1.kx64` 1,231,692 B; code region extracted from the
  `KX64V1 x86_64-linux sysv-ctx-v11 <n> 0` header). Produced by `bridge.bin`
  compiling the seed unity source (`11a3ea25…448038f`) — provenance in
  `native-seed-c-free-runner-slot-hits-20261019.md`.
* **24 pinned runtime cases** (`docs/evidence/jun29-slot-hits-20261019/`
  workloads), 117–2,928 code bytes each.

## 2. Method (two independent scans, cross-checked)

1. **Pattern scan** (`scan_calls.py`, written against the container format and
   the x86-64 encoding, not against the emitter source): every call-family
   byte site classified against the closed emitter vocabulary — host vtable
   dispatch `mov rdi,[rbp-8]` / `call [rdi+disp32]` / `mov r9,[rbp-8]`, guest
   call `mov r9,[rbp-8]` / `call rel32`, tail `mov r9` / `leave` / `jmp`,
   indirect `call rax` / `jmp rax`, epilogue `mov r9` / `leave` / `ret`,
   prologue `push rbp; mov rbp,rsp; sub rsp,imm32; mov [rbp-8],r9`.
2. **Independent linear decode** (`classify_v2.py`, `llvm-objdump -d
   --triple=x86_64-unknown-linux` over a minimal ELF64 wrapper
   (`wrap_elf.py`); host toolchain as measurement instrument only, excluded
   from any accepted run path): every decoded `call`/`jmp` classified by its
   **preceding decoded instruction**, plus a structural check — every
   cross-function transfer (`call`/tail-`jmp`) must target a function prologue
   offset, and no plain label branch may target one.

**The two methods agree exactly on every dispatch class** (G1: 1,545 host
dispatches / 6,685 guest calls / 1,709 tail dispatches / 1 `call rax`;
all 25 payloads: 1,722 / 6,692 / 1,721 / 1). 7,022 raw `e8`-byte hits in the
pattern scan are displacement/immediate/literal-pool bytes; the decode shows
none of them is an instruction boundary.

## 3. Result: the reload is emitted at every site (0 anomalies in 25 payloads)

| dispatch class | sites (25 payloads) | required context discipline | verified |
|---|---|---|---|
| host vtable `call [rdi+disp32]` | 1,722 | `mov rdi,[rbp-8]` **immediately before** | 1,722/1,722, and `rdi`-load count == dispatch count 1:1 per payload |
| guest direct `call rel32` | 6,692 | `mov r9,[rbp-8]` before (guest ctx lives in `r9`) | 6,692/6,692 |
| guest indirect `call rax` | 1 | `mov r9,[rbp-8]` before (args in `rdi..r8`) | 1/1 |
| tail dispatch `leave; jmp rel32` | 1,719 | `mov r9,[rbp-8]; leave` | 1,719/1,719 |
| tail dispatch indirect `leave; jmp rax` | 2 | `mov r9,[rbp-8]; leave` | 2/2 |
| label branch `jmp rel32` (OP-BR) | 3,384 | none — intra-function; **none targets a prologue** | 3,384/3,384 |
| entry `jmp rel32` at code offset 0 | 1 per payload | entry-by-CALL contract (below) | all 25 entry targets are prologue offsets |

All 1,722 `disp32` values are inside the 23 admitted slots (18 distinct in
use: 56 64 72 112 120 128 136 144 160 168 176 184 200 208 216 240 352 360).
All 1,722 host dispatches are followed by `mov r9,[rbp-8]` — the helper-arg
pass loads arg 4 into `r9`, so the guest context register is restored after
every host call. Every prologue (1,317 across the corpus) stores the context
home `mov [rbp-8],r9`.

**Answer: the raw-ELF probe's `rdi`-clobber defect cannot occur in emitted
kx64-v1 code.** The emitter bundles the reload with the dispatch
(`xr-call` = `mov rdi,[rbp-8]; call [rdi+slot]; mov r9,[rbp-8]`), and the
guest call paths never use `rdi` for the context (guest convention: args
`rdi..r8`, context `r9`, restored before return — every `ret` in every payload's
code region is inside a `mov r9; leave; ret` sequence (per-payload decoded
`ret` count == pattern count, 1,318 in G1). A hand-written byte emitter must reproduce
this discipline manually; the compiler cannot emit a call site without it.

## 4. Stack alignment (SysV 16 bytes at every call site)

* Prologue frames: 1,317/1,317 have `imm32 ≡ 0 (mod 16)`.
* **The code body contains no `push`/`pop` besides the one `push rbp` per
  prologue** (1,276 `pushq %rbp` below the code/pool boundary at offset
  1,183,128, each at a prologue offset; every other push/pop decode lies in
  the literal pool above the boundary — ASCII string bytes decoded as
  garbage). G1 `leave` 3,027 = 1,318 return epilogues + 1,709 tail
  dispatches. Stack arguments (n > 5) are written with `mov [rsp+disp32],…`, not pushes.
* Entry contract: code offset 0 is `jmp rel32` to a function prologue, so the
  payload must be **entered by CALL** (rsp ≡ 8 mod 16 at entry): `push rbp`
  → ≡ 0, `sub rsp,16k` → ≡ 0, hence rsp ≡ 0 mod 16 at every `call`. The C
  loader enters this way today; a C-free runner slice must match it
  (`:sysv-ctx-v11` receipt binding gains this clause).

## 5. What this bounds for the runner (connects JUN-30 / JUN-102)

* The `:sysv-ctx-v11` layout binding of `native-seed-c-free-runner-data-slots-20261019.md`
  §4 is extended by a measured **call-site contract**: host helpers receive
  `rdi = ctx` (reloaded from `[rbp-8]` per call, args in `rsi,rdx,rcx,r8,r9`),
  guest code keeps `ctx` in `r9` and restores it around every call/return,
  and the runner must enter the guest by `call` (alignment clause above).
* A runner-slice codegen that emits hand-written bytes (vehicle (b)) must
  grade against this discipline — the verification harness of the raw-ELF
  probe plus the pattern/decode scans here are the grading instruments.
* Still not claimed: Linux process semantics (seccomp, `openat2`
  `RESOLVE_BENEATH`, pre-sandbox arena mapping), v9/v10 data/range slots, and
  admission verification — unchanged from the raw-ELF record §4.

## 6. Provenance

* scanners `scan_calls.py` / `classify_v2.py` / `wrap_elf.py` (measurement
  scripts; Python = orchestration only, none in an accepted run path)
* per-payload results: `docs/evidence/jun29-call-abi-20261019/`
  (`scan-results.json`, `classify-v2.json`, `summary.json`)
* decode instrument: Xcode `llvm-objdump`; the wrapped ELFs are scratch-only
  and not committed
* measurements run on macOS arm64 2026-10-19; no trusted C loader, NBB/Node,
  JVM, or GraalVM in any payload or its build (the payloads are the same
  kx64-v1 containers measured before)
