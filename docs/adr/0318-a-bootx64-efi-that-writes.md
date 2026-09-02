# ADR-0318: A BOOTX64.EFI that writes, and a jump that arrives

- Status: accepted
- Date: 2026-09-02

## Context

ADR-0299 booted a Kotoba BOOTX64.EFI that could name strings, GUIDs and bytes,
and closed with two things it could not do. Both were the same missing noun --
an ADDRESS the program is allowed to name.

Every remaining UEFI boot service takes an OUT-POINTER. `AllocatePages`,
`HandleProtocol` and `GetMemoryMap` all write through a pointer the caller
supplies, and a Kotoba UEFI application had no address it was allowed to
write: the literal pool is in `.text`, which this packager marks `0x60000020`
-- read and execute -- and `kernel-boot-info` answers with the ImageHandle the
firmware handed over, not with the address of the context slot it was parked
in. `OpenProtocol` was reachable only because
`EFI_OPEN_PROTOCOL_TEST_PROTOCOL` makes the firmware ignore its `Interface`
out-parameter.

And `kernel-jump-to` had been encoded, gated and NEVER EXECUTED since the
firmware boundary landed, because nothing produced the address of a Kotoba
function.

## Decision

**`package-efi` reserves 16 KiB past the context, and declares it.** `.data`'s
virtual size is `context-size + scratch-size`, the raw bytes are emitted rather
than left to the loader's zero-fill, and both numbers come from
`kotoba.native.image-scratch` -- the namespace the ENCODER reads to build
`lea r10,[r9+0x60]`. One var, two readers, the discipline
`kotoba.native.interrupt-abi` established for the interrupt entry's stride.

The reservation is UNCONDITIONAL. Sizing it by whether the program names the
region would make the operation lie in exactly the case that matters -- a
module that gains a `(kernel-scratch-region)` after the packager decided it
needed none -- and 16 KiB of zeros is cheap next to that. A load-time assertion
refuses a context that ever grows past the offset the encoder assumes, because
the emitted `lea` does not know how big the context is.

**Two gates, and they are not the same gate.**
`kernel-scratch-region` joins `uefi-only-operations`, the NARROW set.
`kernel-function-address` joins the literals' set, which is wider (the aiueos
x86-64 native targets, firmware AND kernel). The difference is measured rather
than chosen: a function's address needs only a backend that resolves a label
with `lea dst,[rip+disp32]`, and a kernel image has one. The region's answer is
a displacement off the hidden context, and **in the aiueos kernel image that
displacement is the global descriptor table** (`kernel-gdt-offset` is 96, the
same 0x60, with the GDTR at 152 and the TSS at 168). That is not "the backend
cannot answer" -- it answers, and the answer is wrong.

**The frontend's ceiling and the packager's reservation are asserted equal
here.** kotoba-sema admits a window over the region up to
`image-scratch-bytes`; this packager reserves
`image-scratch/bytes-reserved`. If the first were larger, a program would
compile with a window past the end of `.data` and no emitted check would catch
it -- the check compares an index against the length the SOURCE declared, and
the source would be right about a region that is not there. amu is the only
repository with both on its classpath.

## Evidence

`examples/aiueos-uefi-scratch.kotoba` compiles to a 22,528-byte PE32+ EFI
application on both routes, **byte-identical** (`sha256
d806bd193881e5aec535de611d9f71e5f8db300fb56bbfb5334135fd47504555`,
`clojure -M:run compile` and `bin/amu … --jvm-free`).

It was **booted**, on 2026-09-02, under QEMU with OVMF
(`/opt/homebrew/share/qemu/edk2-x86_64-code.fd`), `q35`, `accel=tcg`, the image
on a `fat:rw:` ESP as `/EFI/BOOT/BOOTX64.EFI`. The `isa-debugcon` at port 0xe9
captured

```
KHSTCUGLWOZRAPMJ
```

and QEMU exited with status **33**. The serial console captured `AIUEOS`.

`K H S T C U G L W O Z` are ADR-0299's eleven, re-run unchanged. The new ones:

| byte | what it proves |
|---|---|
| `R` | the scratch region is writable and is ours -- `kernel-store-u64-16k` then `kernel-load-u64-16k` through the CHECKED family, so the declared window and the emitted bounds check are in the path |
| `A` | `AllocatePages(AllocateAnyPages, EfiLoaderData, 1, &addr)` wrote its out-pointer into the region. The slot is ZEROED first, so a nonzero 4 KiB-aligned word there afterwards can only have been written by the firmware through our pointer |
| `P` | `HandleProtocol(ImageHandle, &EFI_LOADED_IMAGE_PROTOCOL_GUID, &iface)` wrote its out-pointer into the region, and `LoadedImage->ImageBase` is this image's own base -- checked by reading `MZ` (0x5a4d) at that address |
| `M` | `GetMemoryMap` wrote THREE out-pointers -- size, key and descriptor size -- into the region. Called with a zero size, which is the call that makes the firmware report what it needs; the required size is nonzero, the descriptor size is at least 48, and it divides the required size exactly |
| `J` | **`kernel-jump-to` arrived.** `(kernel-jump-to (kernel-function-address aiueos-uefi-scratch-second) image-handle)`. The marker AND the `out 0xf4` that ends the run belong to the target function, so a run that fell through instead would not exit at all |

### The markers discriminate

Five variants, each differing in one constant, built and booted the same way:

| variant | change | console | exit |
|---|---|---|---|
| baseline | -- | `KHSTCUGLWOZRAPMJ` | 33 |
| store | the round-trip compares 8241 against 8242 | `KHSTCUGLWOZAPMJ` | 33 |
| alloc | `AllocatePages` slot 0x28 -> 0x30 (`FreePages`) | `KHSTCUGLWOZRPMJ` | 33 |
| base | `ImageBase` at +0x40 -> +0x20 (`FilePath`) | `KHSTCUGLWOZRAMJ` | 33 |
| descriptor | the descriptor-size floor 48 -> 100000 | `KHSTCUGLWOZRAPJ` | 33 |
| jump | the address of `-second` -> the address of `-present` | `KHSTCUGLWOZRAPM` | **124** |

The last row is the strongest of the six. With the address pointing at a
different function, `J` is not written AND the process never exits -- QEMU had
to be killed at sixty seconds. The exit status is not decoration: it is the
assertion that control actually transferred, because the only `out 0xf4` in the
program belongs to the function that was jumped to.

Two of the markers were found missing on the first boot and each named a real
mistake: `AllocatePages` is at boot services +0x28 and +0x40 is
`AllocatePool`; `EFI_LOADED_IMAGE_PROTOCOL`'s `ImageBase` is at +0x40 and +0x20
is `FilePath`. Both were wrong in the fixture and in nothing else, which is
what a marker per assertion buys.

## Consequences

- **A Kotoba UEFI application can allocate a page and cannot write it.** The
  page `AllocatePages` returns is an address the firmware chose, so it reaches
  the program through a load -- and kotoba-sema's region-provenance rule
  refuses a base that came from one, in the caller as well as the callee (the
  taint propagates to the call site by fixpoint). That is the rule working, not
  a defect in it. The consequence is that reading such a page is expressible
  (`kernel-load-ptr` is the unchecked read the firmware boundary already has)
  and writing it is not: there is no unchecked store to match `kernel-load-ptr`
  and the checked family cannot take this base. Marker `A` reads and does not
  write for exactly this reason. **A loader that must place a kernel image into
  pages it allocated needs this closed**, and the two candidate shapes are an
  unchecked `kernel-store-ptr` twin, or a way to root a window at an address
  the firmware returned.
- The fixture is one file. `--source-path` is accepted with `--artifact image`
  for this target, so a loader can be one program with subroutines; this
  fixture did not need it.
