# C-free runner vehicle (b): raw-ELF byte emitter, minimal verification
(JUN-29 / JUN-19 vehicle (b), 2026-10-19)

Measures vehicle (b) of `native-seed-c-free-runner-surface.md` §4 ("a raw-ELF
byte emitter — machine code written directly, no external toolchain, but every
instruction is hand-audited") after the vehicle (a) probes
(`native-seed-c-free-runner-expressiveness-20261019.md`) measured that the
current seed subset cannot express the runner. Measurement record; no runner
implementation is claimed.

## 1. What was emitted

A Linux x86-64 ELF64 whose machine code is written as hand-audited byte strings
by `raw_elf_runner_probe.py` (Python = measurement/orchestration only; the
artifact build uses no assembler, linker, or C). It contains exactly the
instruction constructs the seed subset refused:

| construct | instruction shape | seed route status (vehicle (a) probes) |
|---|---|---|
| capability I/O | `call [rdi+0x30]` (cap_call @48) | refused E7101 (OP-STR first, OP-CAP gate) |
| pair vtable dispatch | `call [rdi+0x38/0x40/0x48]` (slots 56/64/72) | fn-ref refused E7101 detail 22 |
| indirect dispatch | `mov rax,[rdi+0x70]; call rax` | refused E2104 (frontend) |
| tail dispatch | `mov rax,[rdi+0x38]; jmp rax` | refused E2104 (frontend) |
| string literal | `lea rsi,[rip+disp32]` -> embedded `"runner-probe"` | refused E7101 detail 16 |
| fuel@8 contract | `mov rax,[rbx+8]; sub rax,1; mov [rbx+8],rax` | expressible (both routes) |
| refusal trap | `js trap -> ud2` | expressible (both routes) |
| Linux exit path | `xor edi,edi; mov eax,60; syscall` | n/a (freestanding need) |

Artifact: `raw_elf_runner_probe`, **252 bytes**, ELF64 ET_EXEC `EM_X86_64`,
one R+X PT_LOAD, `e_entry 0x400078`, no section headers.
sha256 `22b7eb1a39d75836d43f5e83122418a8f60cb914c0897e12f46a39b3b0b4e8f4`.

## 2. Verification layers

1. **Independent parser + pattern scan** (written against the file, not the
   emitter's state): 55/55 checks pass — ELF header/phdr fields, entry inside
   the segment, every hand-audited sequence at its recorded offset, `call
   [rdi+disp8]` found exactly once at each of 0x30/0x38/0x40/0x48, fuel
   read/sub/write triple, `ud2`, `jmp rax` (`receipt.json` `checks`).
2. **Independent decode**: `llvm-objdump -d --triple=x86_64-unknown-linux`
   decodes the code region exactly as the hand-audit table
   (`objdump-code.txt`; host toolchain used as a measurement instrument only,
   not in the artifact build).
3. **Execution** (`probe_harness.c`, measurement instrument only — explicitly
   not an accepted run path): the harness loads the code region out of the
   emitted ELF into RWX memory and calls it in-process against a synthetic
   `kexe_context_v11`--shaped table whose slots hold C stubs. Host is arm64
   macOS; the code runs under Rosetta x86-64. **6/6 PASS**
   (`harness-output.txt`, `HARNESS_PASS`):

   | check | result |
   |---|---|
   | vtable sum across 6 slots | ret=454 (30+56+64+72+112+120) |
   | string literal reaches stub | cap stub `strcmp("runner-probe")` matched -> 30, not 999 |
   | fuel@8 inline contract | 100 -> 99 exactly |
   | slot call counts | each of 6 slots called exactly once |
   | tail `jmp rax` dispatch | returns 56 (pair_new stub) |
   | fuel exhaustion -> `js` -> `ud2` | SIGILL caught x1, fuel written back as 2^64-1 |

## 3. Hand-audit findings (execution caught what byte scans did not)

1. **`rdi` is caller-saved.** The first draft kept addressing the context
   through `rdi` after the first `call [rdi+0x30]`; the stub returned with `rdi`
   clobbered and the next dispatch jumped through a garbage pointer (debug
   harness: `SIGSEGV at si_addr=0x4d5554584d555458` right after `[stub30]`).
   Fix: keep the context in callee-saved `rbx` and reload `rdi` before every
   dispatch (`mov rdi, rbx`). The measured kx64-v1 guest payloads chain
   `call [rdi+disp32]` too — whether the compiler emits the reload between
   sites is a concrete follow-up question for the emitter codegen, not
   something the byte scans of the last tick could answer.
2. **SysV stack alignment must be 16 bytes at every vtable call site.** The
   entry sequence uses exactly three register pushes, which leaves `rsp`
   16-byte aligned before each `call`; a naive prologue leaves it misaligned
   and SSE-using stubs fault.

Both are exactly the class of defect "every instruction is hand-audited" is
meant to catch — and the audit here was executed, not eyeballed.

## 4. What this bounds

* **Vehicle (b) is viable in principle**: a byte emitter can express the full
  runner-construct set that vehicle (a)'s seed subset refused, and the emitted
  instructions execute correctly against the vtable layout of
  `:sysv-ctx-v11` (slots 48/56/64/72/112/120, fuel@8, `ud2`).
* **Not claimed**: this is not the runner. Remaining for the runner itself:
  Linux process semantics (seccomp base + fs-scope sets of surface doc §2,
  `openat2` `RESOLVE_BENEATH` containment, pre-sandbox arena mapping), the
  v9/v10 data/range slots, and the admission verification of surface doc §5.3.
  None of that was executed here: the harness runs the code region **in
  process**; the Linux `exit` sequence in the image is byte-scanned only.
* Scaling hand-audited bytes to a ~13k-line loader surface is the argument for
  the kernel-profile runner slice (`:aiueos-c-free-bare-metal-v1`, ADR 0271;
  JUN-30 / JUN-102) instead — vehicle (b) is the fallback/benchmark, and now
  has a working verification harness to grade either route against.

## 5. Runner-slice admission receipt binding (JUN-30 / JUN-102)

`receipt.json` (emitted by the probe) demonstrates the binding the runner-slice
admission must record (JUN-29 acceptance: "a reproducible receipt records
runner, compiler, source graph, and output hashes"):

* `artifact.sha256` (runner/output hash), `artifact.code_sha256`
* `source_graph.producer` + `emitter_sha256` (for the real slice: the pinned
  source graph / manifest unity hash and the G2 producer sha)
* `runner_slice_binding`: `layout :sysv-ctx-v11`, `wires [35,37,38,39]`
  (`:fs/app-data`/`:io/write`/`:cli/args`/`:io/write-error`), the six vtable
  slot displacements, `fuel_offset 8`, `trap ud2`
* `hand_audit_table`: offset/mnemonic/bytes for every emitted instruction
* `checks` + `checks_ok`: the independent verification results

## 6. Provenance

* emitter `raw_elf_runner_probe.py` sha256
  `460d5ae284f6717d9bae26fa9c3a5b2472565b8012adcb47099dcd0099a44975`
* harness source `probe_harness.c` sha256
  `dcb2f39795a0d7849a9d16c74091b7eb056c2df556b1060bc32ebf1f73e232b8`
* receipt `receipt.json` sha256
  `0c1d2bef99151bf319ad4320ed688600aadb5cd409a2aa9c1fe7b04dea76fdee`
* No trusted C loader, NBB/Node, JVM, or GraalVM in the artifact or its build;
  the clang-built harness and llvm-objdump appear only as measurement
  instruments and are excluded from any accepted run path.

Files under `docs/evidence/native-seed-c-free-runner-raw-elf-20261019/`.
