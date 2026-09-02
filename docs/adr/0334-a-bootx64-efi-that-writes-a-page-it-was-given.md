# ADR-0334: A BOOTX64.EFI that writes a page it was given

- Status: accepted
- Date: 2026-09-03

## Context

ADR-0318 booted a BOOTX64.EFI that could write -- into 16 KiB of scratch the
packager reserves inside the image's own `.data`. It closed by naming what
that did not buy:

> **A Kotoba UEFI application can allocate a page and cannot write it.** [...]
> the two candidate shapes are an unchecked `kernel-store-ptr` twin, or a way
> to root a window at an address the firmware returned.

Neither was taken. The page is at an address the firmware chose, so it arrives
through a load, and kotoba-sema refuses a base that came from one. An
unchecked store twin would have removed the bound from every write to such a
page; a `(adopt address length)` head would have made the bound an assertion
by the author about a number the author also computed.

## Decision

**The allocation is the producer of the address.**
`kernel-uefi-alloc-region` joins `uefi-only-operations`, the narrow set, and
calls `AllocatePages` with the out-pointer inside its own emitted frame
(kotoba-native ADR-0080). The pages it answers with are a region-provenance
root because there is no shape of source in which they are anything else --
the program cannot present an address to it.

It is in the narrow set, not the literals' wider one, for the sharpest form of
`kernel-uefi-call2`'s reason: it calls through a pointer read out of firmware
memory AND hands back an address kotoba-sema then certifies. Under any other
entry contract the boot services table it indexes is not there, so the call is
through a wild pointer and the root is over whatever came back.

## Evidence

`examples/aiueos-uefi-scratch.kotoba` gains two markers and keeps ADR-0318's
sixteen. It compiles to a **24,576-byte** PE32+ EFI application (sha256
`b0630cf94f49ee5cc48a06716d8cf5c74f937f35804fa22ffb61879ecb63bc5f`) and was
**booted** on 2026-09-03 under QEMU with OVMF
(`/opt/homebrew/share/qemu/edk2-x86_64-code.fd`), `q35`, `accel=tcg`, the
image on a `fat:rw:` ESP as `/EFI/BOOT/BOOTX64.EFI`. The `isa-debugcon` at
port 0xe9 captured

```
KHSTCUGLWOZRAPMFDJ
```

and QEMU exited with status **33**. The serial console captured `AIUEOS`.

| byte | what it proves |
|---|---|
| `F` | **the page is writable.** `(kernel-uefi-alloc-region boot-services 40 0 2 32 0)` -- AllocateAnyPages, EfiLoaderData, 32 pages -- answers with the BASE, and `kernel-store-u64-4k` then `kernel-load-u64-4k` carry `0x0123456789ABCDEF` through the CHECKED family, so the declared window and its emitted bounds check are in the path |
| `D` | **a memory map descriptor out of that page.** `GetMemoryMap(&size, pages, &key, &descsize, &descversion)` fills the firmware-allocated buffer -- `size` set to 131072 first, so this is the call that asks for the MAP rather than for its size -- and descriptor 0 is walked out of it: `NumberOfPages` at +24 is non-zero and is no longer the sentinel stored there before the call, `PhysicalStart` at +8 is 4 KiB aligned, `Type` at +0 is below 16, and the descriptor size is at least 48 |

**Marker `A` is deliberately unchanged.** It allocates the same way through
`kernel-uefi-call4` and READS rather than writes, because that spelling's
answer arrives through a load and still cannot be a base. The two markers
together are the measurement: the same firmware call, one spelling that can
write the page and one that cannot.

### The markers discriminate

| variant | change | console |
|---|---|---|
| baseline | -- | `KHSTCUGLWOZRAPMFDJ` |
| F | the read-back compares `…89ABCDEF` against `…89ABCDF0` | `KHSTCUGLWOZRAPMDJ` |
| D | `NumberOfPages` read from +16 (`VirtualStart`) instead of +24 | `KHSTCUGLWOZRAPMFJ` |

Both exit 33, and each removes exactly one marker. The D variant is the more
interesting: `VirtualStart` is zero in a UEFI memory map until
`SetVirtualAddressMap` is called, so reading the wrong FIELD of the right
descriptor is what the marker refuses -- not merely reading the wrong page.

## Consequences

- Four pins advance, and one of them is not this stream's choice.
  `kotoba-kir` goes to **233bd6bb**, which is kir's main and contains
  fwstore's own d8b0e679; pinning d8b0e679 here resolves a kotoba-kir without
  fuel64's `max-fuel` export, and the kotoba-verifier pinned below now READS
  that var, so the verifier fails to LOAD with `No such var: ir/max-fuel`.
  Measured, not reasoned about.
- `resources/kotoba/lang/guest-grammar.edn` resyncs to **6e1202fd** with the
  head in `:admitted-builtins`, and so does the digest
  `every-classpath-copy-is-the-authority-of-the-resync-wave` pins. **That test
  was RED on main**: ADR 0330's resync moved the FILES to 67561e57 and left
  both digest literals at 3e3f9748. Its byte-equality half was green
  throughout, which is what that half is for -- the two copies agreed with
  each other while both disagreed with the number that ties them to the
  authority.
- `kernel-store-ptr` was NOT added and is not owed. The unchecked read
  `kernel-load-ptr` exists because a firmware structure has to be read at an
  address the compiler cannot bound; a write does not have that excuse, and
  every write this stream needed is bounded.
