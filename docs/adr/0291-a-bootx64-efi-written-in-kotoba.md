# ADR-0291: A BOOTX64.EFI written in Kotoba

- Status: accepted
- Date: 2026-09-02

## Context

`os/aiueos/uefi/main.c` is C, and it had to be. The UEFI target could compile
Kotoba and package a PE32+ EFI application, but the application could not do
anything: UEFI calls an image entry with `(EFI_HANDLE ImageHandle,
EFI_SYSTEM_TABLE *SystemTable)` in RCX and RDX, and the entry shim discarded
both. There was no console, no boot services, no memory map, and no way to
reach any of them.

Four other things were in the way, each in a different repository, and none of
them visible from the one before it:

- the frontend admitted privileged operations but had no spelling for a
  firmware call, an unchecked pointer read, or a jump that does not return;
- the verifier admitted the kernel-facing operations for the two aiueos KERNEL
  targets and refused `:x86_64-aiueos-uefi-v1` -- so a UEFI application could
  not even write a port;
- `kotoba.mir`'s conservative expansion sliced two registers for a privileged
  action's arguments, which is fine until one takes four;
- and `package-efi` froze `.text` at RVA 0x1000, `.data` at 0x2000 and
  SizeOfImage at 0x4000, which put a **4096-byte ceiling on `.text` that
  nothing checked**. Past it, `.data` was mapped over the tail of the code and
  the image was still a byte-valid PE.

## Decision

**Entry contract v2.** A module that exports a two-arity `efi-main` is
packaged on `:microsoft-x64-two-arity-efi-status-v2`. The shim parks RCX at
context+0x50 and RDX at +0x58 -- where `kernel-boot-info` and the new
`kernel-system-table` read them -- and also passes them positionally in RDI
and RSI, the internal ABI's first two parameter registers. Both, deliberately:
the entry reads them as parameters, and anything it calls reads them out of
the context without threading them through every signature. The context grows
from 80 to 96 bytes, for both contracts, because 0x58+8 = 96.

The name is `efi-main` rather than `main` because `kotoba.compiler.frontend`
rejects any `main` that takes arguments, for every target. Relaxing that
globally to admit one target's firmware ABI would be a language change made by
a packager. The target profile already declares `:entry :efi_main`; this uses
that name. A module with no `efi-main` packages through its `main` on the
zero-arity contract, exactly as before.

**Derived section placement.** `data-rva`, `reloc-rva` and `image-size` are
computed from the real `.text` and context sizes, the way
`package-embedded-kernel` in the same namespace always did. kotoba-object
ADR-0002 adds the RVA-overlap and SizeOfImage checks to `encode-image` in the
same change set, so a caller that freezes its addresses now fails at build
time instead of on the machine.

**A target gate, in two places.** `kotoba.compiler.uefi-operations` refuses
`kernel-system-table`, `kernel-load-ptr`, `kernel-uefi-call2` and
`kernel-jump-to` outside `:x86_64-aiueos-uefi-v1`, and both compile routes
call it -- `kotoba.compiler.core` on the JVM and `kotoba.compiler.nbb.cli` on
the JDK-free one -- because a gate on one route is not a gate. kotoba-verifier
ADR-0020 refuses them independently.

## Evidence

`examples/aiueos-uefi-console.kotoba` compiles to a 2560-byte PE32+ EFI
application on both routes, **byte-identical**
(`sha256 8f7c1659e8fb5b60dabe37442cc2b8d694b6be25e11a7421328b27f02f296032`,
`clojure -M:run compile` and `bin/amu ... --jvm-free`).

It was **booted**, on 2026-09-02, under QEMU 10.1.0 with OVMF
(`/opt/homebrew/share/qemu/edk2-x86_64-code.fd`), `q35`, `accel=tcg`, the
image on a `fat:rw:` ESP as `/EFI/BOOT/BOOTX64.EFI`. The `isa-debugcon` at
port 0xe9 captured

```
KHSTCAZ
```

and QEMU exited with status **33**, which is `isa-debug-exit`'s
`(16 << 1) | 1` for the value the Kotoba program wrote to port 0xf4. Each
letter is one assertion the firmware answered:

| byte | what it proves |
|---|---|
| `K` | the image entry ran |
| `H` | RCX (ImageHandle) survived the shim -- v1's discarded it |
| `S` | RDX (SystemTable) survived it |
| `T` | `kernel-load-ptr` read the real `EFI_SYSTEM_TABLE` signature `"IBI SYST"` at +0 |
| `C` | ConOut is at SystemTable+0x40 and is not null |
| `A` | `kernel-uefi-call2` called `ConOut->SetAttribute` and got `EFI_SUCCESS` |
| `Z` | `kernel-system-table` still answers AFTER that call -- R9, the guest's hidden context, survived a Microsoft x64 call in which R9 is an argument register |

A hang, a fault or a triple fault all look different from exit 33, so the exit
status is itself an assertion.

### The markers discriminate

Seven letters appearing is only evidence if six could have appeared. Two
variants of the same fixture, each differing in one constant, were built and
booted the same way:

| variant | change | markers | reading |
|---|---|---|---|
| baseline | -- | `KHSTCAZ` | |
| signature | expected `EFI_SYSTEM_TABLE` signature off by one | `KHSCAZ` | `T` gone, nothing else. `kernel-load-ptr` really read the firmware's word |
| attribute | `SetAttribute(ConOut, 4095)` instead of `15` | `KHSTCZ` | `A` gone, nothing else. `kernel-uefi-call2` really returns the firmware's status -- `EFI_SUCCESS` for a legal attribute, non-zero for an illegal one |

Both still exit 33, so the failure is the assertion and not the boot.

## Consequences

- `aiueos/os/aiueos/scripts/verify-kotoba-native-boot.py` is NOT affected: it
  verifies `package-aiueos-boot`'s output (`package-embedded-kernel`), which
  this change does not touch, and its `sections != 3` rule still holds there.
  `package-efi` also still emits exactly three sections.
- What is NOT done, and is the next thing to do: **rodata**. There is no way
  for Kotoba source to obtain the address of a UTF-16LE literal, a GUID or a
  byte vector, so `ConOut->OutputString(ConOut, L"AIUEOS")` cannot be written
  -- the fixture calls `SetAttribute`, which takes no pointer. That needs a
  `:gmir/rodata-address` op lowering to `lea dst,[rip+disp32]`, mirroring the
  `:gmir/data-address` plumbing that already exists; the bytes can live at the
  end of `.text`, which rip-relative addressing reaches, so no fourth PE
  section and no relocation is required.
- `kernel-uefi-call2` carries exactly two UEFI arguments. `GetMemoryMap`
  (five) and `OpenProtocol` (six) need an argument channel that does not fit
  in the four-register scratch tier, which is a separate decision.
- The x86-64 backend's non-word-typed fallback emitter does not implement the
  four operations. UEFI entry paths are word-typed throughout, so this has not
  bitten; a function that mixed them with a string would fail as an unknown
  call target.
