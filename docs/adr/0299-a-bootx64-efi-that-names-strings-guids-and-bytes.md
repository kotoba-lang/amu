# ADR-0299: A BOOTX64.EFI that names strings, GUIDs and bytes

- Status: accepted
- Date: 2026-09-02

## Context

ADR-0291 booted a Kotoba BOOTX64.EFI and closed with two things it could not
do. `ConOut->OutputString(ConOut, L"AIUEOS")` was unwritable, because it takes
a `CHAR16 *` and Kotoba had no way to obtain the address of anything. And a
firmware call carried exactly two arguments, so `GetMemoryMap` (five) and
`OpenProtocol` (six) were out of reach.

## Decision

**Two target gates rather than one, because they are different sentences.**

`kernel-uefi-call4` and `kernel-uefi-call6` join `uefi-only-operations`: they
call through a pointer read out of firmware memory, and the only difference
from `kernel-uefi-call2` is how many arguments go with it.

`ucs2`, `guid`, `bytes-literal` and `bytes-literal-length` get their own gate,
`reject-rodata-literals-outside-native-targets!`, and a WIDER target set. None
of them is dangerous. What they need is a BACKEND that places a literal pool
and an instruction that reaches it, and only the x86-64 native backend has one.
So the set is the aiueos x86-64 native targets -- firmware AND kernel -- and it
is DERIVED from `kotoba.kir.target`'s own profiles rather than written out, so
a new aiueos x86-64 target does not silently lack the pool its backend already
has. Saying "require the aiueos UEFI target" about `(guid "...")` on the Wasm
target would name the wrong requirement.

Both routes call both gates, because a gate on one route is not a gate.

## Evidence

`examples/aiueos-uefi-literals.kotoba` compiles to a 3072-byte PE32+ EFI
application on both routes, **byte-identical**
(`sha256 0dfb97cbace0ba3e19beee91d127240e774bdff0a1bbe91675ca738c80bcc916`,
`clojure -M:run compile` and `bin/amu ... --jvm-free`).

It was **booted**, on 2026-09-02, under QEMU with OVMF
(`/opt/homebrew/share/qemu/edk2-x86_64-code.fd`), `q35`, `accel=tcg`, the image
on a `fat:rw:` ESP as `/EFI/BOOT/BOOTX64.EFI`. The `isa-debugcon` at port 0xe9
captured

```
KHSTCUGLWOZ
```

and QEMU exited with status **33**. The serial console captured, from the
firmware's own console driver:

```
AIUEOS
```

Each letter is one assertion the firmware answered. `K` `H` `S` `T` `C` `Z` are
ADR-0291's. The new ones:

| byte | what it proves |
|---|---|
| `U` | `ConOut->OutputString(ConOut, (ucs2 "AIUEOS\r\n"))` returned `EFI_SUCCESS`. The firmware read UTF-16LE code units out of THIS image's `.text` and rendered them -- and the serial log is a second, independent observation of the same bytes |
| `G` | the first eight bytes of `(guid EFI_LOADED_IMAGE_PROTOCOL_GUID)`, read back through `kernel-load-ptr` on the machine that is running, are the MIXED-ENDIAN ones. A hex decode of the canonical text would start `5b 1b 31 a1` |
| `L` | `(bytes-literal "0102030405060708")` and `(bytes-literal-length ...)` agree: the bytes are where the address says and there are as many as the count says |
| `W` | `BS->SetWatchdogTimer(0, 0, 0, 0)` through `kernel-uefi-call4` returned `EFI_SUCCESS` -- four UEFI arguments, six operands |
| `O` | `BS->OpenProtocol(ImageHandle, that GUID, 0, ImageHandle, 0, 4)` through `kernel-uefi-call6` returned `EFI_SUCCESS` -- six UEFI arguments, eight operands, the last two delivered on the stack |

`O` is the strong GUID assertion: the firmware compared our sixteen bytes
against the protocol installed on our own image handle.
`EFI_OPEN_PROTOCOL_TEST_PROTOCOL` (4) is what makes it need no writable memory
-- with it the firmware ignores the `Interface` out-parameter.

### The markers discriminate

Five variants, each differing in one constant, built and booted the same way:

| variant | change | markers | reading |
|---|---|---|---|
| baseline | -- | `KHSTCUGLWOZ` | |
| guid-head | the expected GUID head word off by 0x70972d842176 | `KHSTCULWOZ` | `G` gone, nothing else. Found by accident -- the first constant written down was wrong, and `O` stayed green, which said the BYTES were right and the arithmetic was not |
| guid | `5B1B31A1` -> `5B1B31A2` | `KHSTCUGLWZ` | `O` gone. The firmware really compared our sixteen bytes |
| attr0 | `Attributes` 4 -> 0 | `KHSTCUGLWZ` | `O` gone. The SIXTH argument, at `[rsp+0x28]`, reaches the firmware |
| swap56 | arguments 5 and 6 exchanged | `KHSTCUGLWZ` | `O` gone. The two stack slots are not interchangeable |
| slot264 | `kernel-uefi-call4` slot 256 -> 264 | `KHSTCUGLOZ` | `W` gone. The wide frame calls through `[base+slot]` and returns THAT function's status |

All six exit 33, so the failure is the assertion and not the boot.

## Consequences

- **Not done, and the next thing to do: writable guest memory.** `AllocatePages`,
  `HandleProtocol` and `GetMemoryMap` all take an out-pointer, and a Kotoba
  UEFI application has no address it may write. The literal pool is in `.text`,
  which is `0x60000020` -- read and execute. `kernel-boot-info` returns the
  ImageHandle under contract v2, not the context address, so the `.data`
  section the entry shim parks R9 at is unreachable from source. The smallest
  thing that unblocks all three is an operation returning the address of a
  scratch area in that section (`lea r10,[r9+0x60]`, four bytes) plus a
  `.data` virtual size that reserves it -- and `kotoba.compiler.frontend`'s
  region-provenance rule would have to admit it as a root, beside
  `kernel-boot-info`.
- **Also not done: executing `kernel-jump-to`.** It is still encoded, gated and
  never executed. Reaching it needs the address of a Kotoba function in the
  same image, and there is no operation that produces one. The literal pool's
  machinery is what a `(kernel-function-address f)` would reuse: the layout
  pass already knows every function's label, and `lea dst,[rip+disp32]` already
  resolves against one.
- The two gates are separate functions on purpose. Merging them would make one
  of the two refusals name the wrong requirement.
