# ADR-0402 -- the AIUEOS user target gets a PLC variant: raw cap-call against a declared set, in the PLC ELF layout (KOTOBA-175)

- Status: **implemented** (seed/74, seed/78, `scripts/seed/check-aiueos-user-plc-native.py`).
- Date: 2026-11-01
- Tracking: KOTOBA-175; unblocks kotoba JUN-722 (the AIUEOS PLC RT smoke, `AIUEOS_PLC_RT_SMOKE=1`).
- Follows: ADR 0373 (intrinsic stubs replaced by inline code), the user-v1..v5 targets in seed/74.

## Context

kotoba's `os/aiueos/scripts/compile-plc-st.py` turns IEC 61131-3 Structured Text into a Kotoba program whose only
effects are raw `(cap-call ID ARG)` with ID 16..19 (input read, output stage, commit, watchdog). No Amu could compile
it (measured 2026-10-31 on main b19e93b):

- `amu-full-root.macho` refuses `cap-call` with `E2101 unknown or unsupported form`;
- seed/74's user target has no raw cap-call and refuses any capability (E7101, `MM-CAPS` non-zero);
- its layout is not the one the kernel's PLC path admits. user-v1 enters at 0x220000 with a zero bitmap, while kotoba's
  `os/aiueos/kotoba/plc-user-elf-valid.kotoba` (linked as `kotoba_aiueos_user_elf_valid` in the PLC build) admits
  exactly:
  - ELF64 LE x86-64 `ET_EXEC`, entry 0x1e1000, phoff 64, two 56-byte phdrs; image 8280..12288 bytes;
  - RX at file 4096 / VA 0x1e1000, 0 < filesz = memsz <= 4096, align 4096;
  - RW at file 8192 / VA 0x1e2000, filesz = memsz = 88, align 4096;
  - an 88-byte context: +0 = 0 (result), +8 = 512 (fuel), +16 = 0xf0000 (the capability bitmap of IDs 16..19,
    exactly), +48 = 0x1e1020 (the syscall trampoline), every other byte 0.

user-v1's 0x220000 layout serves Amu's own boot payload (seed/84 `package-aiueos-user-payload`, the slot-v1..v4
admission and `check-aiueos-user-*` gates), so changing it would break those users. kotoba's default
`user-elf-valid` admits the 0x1e0000 catalog layout, but no current kotoba user ELF comes from Amu's user-v1
(`user-smoke.elf` and the zero-cap fixtures predate the 0x220000 move, amu d2f9b01f).

The capability ABI, from the kernel (kotoba `os/aiueos/kernel`, the source of truth):

- `syscall.c`: `AIUEOS_SYSCALL_RUNTIME_CALL = 5`; the dispatcher admits the handle as a
  `KOTOBA_RUNTIME` capability with the `RUNTIME` right for the requesting domain, and under `AIUEOS_PLC_RT_SMOKE`
  routes `pointer` 16..19 of domain 4 to `aiueos_plc_capability_call(pointer, length)`.
- `entry.S` `aiueos_syscall_entry`: rax = number, rdi = handle, rsi = pointer, rdx = length; the dispatcher is a System V
  call, so r8..r11 are not preserved across the syscall.
- `process.c` / `loader.c`: the kernel stores the domain's runtime handle at context word 10 (+80).
- The retired route (kotoba-native `machine_ir.cljk` `x86-capability-call`, and the disassembly of the
  `user-smoke.elf` it emitted) tested the bitmap byte at context+16+ID/8, `ud2` otherwise, set esi = ID, rdi = the
  context, called the trampoline through context+48, and reloaded r9; the trampoline is
  `mov eax,5; mov rdi,[rdi+0x50]; syscall; ret` at entry+0x20.

## Decision

A new target, `x86_64-aiueos-user-plc-v1`, selected explicitly; user-v1..v5 and every other route keep their bytes.

```
compile SOURCE --target x86_64-aiueos-user-plc-v1 --capabilities ID,ID,.. --output NEW
```

**The capability set rule.** `--capabilities` is required: canonical decimal IDs 0..63, strictly ascending, comma
separated, at least one (anything else E7109, exit 2). The context bitmap at +16 is exactly that set. Each
`(cap-call ID ARG)` is checked at compile time:

- ID must be an integer literal on every path to the call: the last SIR write of the argument temp before the call is a
  CONST 0..63, and no branch outside that span enters it. A parameter, a computed value, a value merged from branches
  or 64 is `E7109 malformed cap-call`. A wrong arity is the checker's E2103; a source that defines `cap-call` itself is
  E2001.
- An ID outside the set is `E7101 cap-call capability N is not declared by --capabilities`.
- `typed-cap-call` stays refused (E7101), as in user-v1.

So a declared but unused ID is allowed (the bitmap is the declaration), and a used but undeclared ID never produces an
image.

Why a flag and not `--policy FILE`: the shared driver deliberately refuses every explicit policy until a structured,
qualified policy parser exists (seed/90 `drv-r5b-gate`, E-POLICY-FILE). A second, target-local EDN reader would be the
unqualified parser that gate refuses. kotoba's build script passes the list and requires its policy file to be that
list's canonical rendering.

**The call.** `cap-call` is a stub `(defn- cap-call [capability :i64 argument :i64] :i64 0)` appended to the source
(the ADR 0373 pattern; the frontend, checker and lowering are unchanged). xk-intr maps calls of that function, and only
under this target (`M[212]`), to:

```
mov rsi,[ID]          ; 48 8b b5 disp32
mov rax,[r9+16]       ; 49 8b 41 10      the context bitmap
bt  rax,rsi           ; 48 0f a3 f0
jc  +2 ; ud2          ; 72 02 0f 0b      an unset ID traps before any request
mov rdx,[ARG]         ; 48 8b 95 disp32
mov rdi,r9            ; 4c 89 cf
mov eax,0x1e1020      ; b8 20 10 1e 00   the image's own trampoline
call rax              ; ff d0
mov r9,[rbp-8]        ; 4c 8b 4d f8      the dispatcher clobbers r9
```

and the answer (rax) is the call's value. Two differences from the retired route: `bt` on the whole bitmap word
instead of a byte test (the same bit), and a direct call to the trampoline's fixed address instead of an indirect call
through context+48. The context is writable by the program, and an indirect call through it would let a data write
pick the call target. context+48 still holds 0x1e1020, which the validator requires.

**The layout.** The user-v1 entry (`lea r9,[context]; call main; mov [context],rax; pause; jmp`, then the trampoline at
+0x20) and code generation are reused unchanged. The addresses are moved to 0x1e1000 / 0x1e2000, fuel 512 is written at
+8, the bitmap at +16 and 0x1e1020 at +48. Text stays at most 4096 bytes (E7104).

## Consequences

- kotoba's `build-plc-native-program.sh` builds the PLC program, which passes `plc-user-elf-valid` and
  `make-plc-native-receipt.py`. The receipts name `x86_64-aiueos-user-plc-v1`.
- The PLC kernel loader (kotoba `loader.c`) copied the context from file offset 65536 (JUN-145's catalog
  `ELF_DATA_OFFSET`), beyond a PLC image that `plc-user-elf-valid` bounds at 12288 bytes. It now takes the data
  phdr's offset. That is the kotoba-side half of this change.
- Gate `check-aiueos-user-plc-native.py` (mac-selfhost-aiueos, `mac-root`):
  - the motor PLC program compiles to its pinned ELF, which passes a replica of `plc-user-elf-valid` and the
    receipt checks;
  - there is one call sequence per source call;
  - the bitmap is exactly the declaration;
  - the E7101 / E7109 / E2103 / E2001 refusals and the nine malformed lists write no artifact;
  - the validator replica rejects superset-bitmap, 0x220000-entry, moved-data and fuel-256 mutants;
  - user-v1's scalar ELF keeps its SHA-256.
- Not qualified here:
  - typed capability kinds;
  - arguments other than one i64;
  - a PLC program with zero capabilities;
  - the 0x1e0000 catalog profiles (fuel 256, bitmap 60);
  - execution, which kotoba's QEMU smoke covers.
