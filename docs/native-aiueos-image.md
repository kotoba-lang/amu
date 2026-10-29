# AIUEOS native image and transition loader candidate

JUN-31, 2026-10-24. These commands extend the adopted compiler lineage in
`seed/FULL-MANIFEST`; the current root and public-entry candidates include them. Adoption requires
the exact native x86 and native-controller/public-product receipts.
The adopted core and its generation-one image stay unchanged. No Node/NBB,
JVM, C compiler, C loader or foreign linker is a fallback.

## Image packaging

```
NATIVE_CANDIDATE compile SOURCE.kotoba --target x86_64-aiueos-kernel-v1 --artifact image --output NEW.ELF --fuel 1024
NATIVE_CANDIDATE package-aiueos-boot NEW.ELF --output NEW.EFI
NATIVE_CANDIDATE package-aiueos-boot NEW.ELF --output NEW-PAYLOAD.EFI --payload DATA
```

`--artifact object` retains the original object ABI; omitting it preserves
the existing object command. Arguments have the declared order. Unsupported
flags, invalid fuel, unknown artifact kinds and existing output files refuse.
The runtime's file capability must explicitly include the inputs and output.

**Object route, multiple exports (JUN-556).** `--artifact object` (the default)
now emits up to eight exports in one ELF64 ET_REL object: one shim per export,
back to back, each loading the same private 80-byte context and replenishing
its own fuel; one `R_X86_64_PC32` addend -4 relocation per shim at offset 3; one
public `GLOBAL FUNC` per export after the local `context` symbol. A single
export is byte-identical to what the route always produced. More than eight
refuse (`E7102`); the image route below is unchanged and still takes one
export. `scripts/seed/check-aiueos-object-exports.py` pins the single-export
digest and reads a two-export object back with an independent parser, and the
Mac CI job runs it. The aiueos-side verifier takes the export list
(kotoba-lang/kotoba, `verify-kotoba-kernel-object.py`). The header comment of
`seed/74-x86_64-aiueos-object.kotoba` still says "exactly one public GLOBAL
FUNC"; it is a comment, and editing it moves the source pin, so it waits for
the next change to that file.

**Object route, window accesses at other widths (JUN-556 B).** Besides
`kernel-load-u32` and friends, a source may use `kernel-load-u8`,
`kernel-store-u8`, `kernel-load-u16`, `kernel-store-u16`, `kernel-load-u64` and
`kernel-store-u64`, each at the 512-byte tier with the same rooted-base and
paired-length rules (E7106 otherwise). They follow kotoba-native's
`emit-kernel-load-u8`, `emit-kernel-store-u8` and `emit-memwidth-window`: the
length is at most 512, the base is non-null, the index is below the length,
and above one byte `length - index >= width` (without wrapping) and the index
is aligned; every branch lands on a `ud2` before memory is touched. The six
stubs are appended only to a source that names one of them, so every other
source compiles to the bytes it always had (the exports gate pins one). Locked
projects and the image route's source library are not changed. The machine
code is decoded by `scripts/seed/check-aiueos-object-windows.py` (Mac CI job),
not executed.

The image emitter currently admits the existing scalar kernel profile with
one zero-argument export. It retains the complete admitted source and all
helper functions. Multiple exports (ISR/live ValueRuntime included), the
complete kernel source graph, unsupported intrinsics, module locks and the
project linker remain open. Do not trim a component to this profile and call
it a completed port.

The image is ELF64 ET_EXEC/EM_X86_64 with exactly two load segments, RX and
RW. Its entry at `0x101000` uses an image-owned stack, installs the GDT/TSS,
saves the loader's boot-info pointer, initializes r9 and calls the export.
The compiler writes the fuel word once. This is image metadata and entry
mechanism, not proof of enforced page permissions or a complete OS runtime.

The native boot packager implements the ordinary transition loader from
`src/kotoba/compiler/packaging/pe32plus.cljk`: bounded ELF admission,
position-independent PE32+, firmware GOP metadata, two AllocateAddress
regions and CopyMem, a fifteen-page kernel scratch allocation, bounded
GetMemoryMap, ExitBootServices and handoff. The optional payload is at most
512 KiB. Input bytes are read once and copied into the generated image.
Resident/K16 tender modes remain unsupported and refuse; the command never
silently substitutes its ordinary transition mode for them.

## Evidence and qualification

`scripts/seed/selfhost-bootstrap.py --tier pr` rebuilds the full candidate to
a fixed point, verifies the adopted core image, and runs the unchanged 24
native runtime fixtures. It emits browser Wasm fixtures too; compilation
alone does not qualify their execution. The native compiler performs each
compile/pack operation; Python only orchestrates and inspects receipts.

`scripts/seed/check-aiueos-image-native.py` compares image bytes across the
two fixed-point generations, checks the boot/context/ELF ABI independently,
exercises source/flag/output refusals and corrupt-image controls, and reruns
the existing object ABI corpus.

`scripts/seed/check-aiueos-boot-native.py` compares ordinary/payload/boundary
EFI images from those same generations. It checks PE sections, embedded
kernel identity and boot-info, and refuses corrupted ELF, oversized payload,
unsupported modes and output overwrites. The historical hosted owner oracle
is unavailable in the permitted closure; structural inspection and the
AIUEOS boot ABI verifier are separate evidence, not a claim of full oracle
parity.

`scripts/seed/check-aiueos-entry-qemu.py` boots the exact generated pair in
QEMU/OVMF with scratch-only writable media and no network. It requires
RIP=`0x10104b`, RAX=`42`, the exact remaining fuel of the literal-only
program, guest boot-info v5 and firmware GOP metadata. A different return
value must fail the check. The JSON receipt binds kernel, EFI and firmware
hashes and the actual QEMU version.

That is an **entry probe**. It does not qualify the complete AIUEOS kernel,
GOP desktop rendering, input, GPT/release media, physical hardware,
Browser/CSSOM or Itonami dapps. A firmware framebuffer descriptor is not a
rendered desktop. Existing C/reference boots and hosted compiler results
remain separate historical evidence.

The root/public-product pins are updated with the full31 artifacts. Controller
and two gate binaries rebuild byte-identically; current native execution
receipts must bind them to this compiler. The native x86 diagnostics accept
`--complete COMPLETE_DIR`; ARM diagnostics also accept a measured root=F1
fixed point after adoption. Neither route bypasses source or image pin checks.
Python diagnostics and QEMU do not replace the native CDCI verdict.
Actual native x86 qualification, exact-head PR/main CI and readback are
separate acceptance gates; see `evidence/aiueos-aot-adoption-20261024/`.
Earlier adoption receipts predate the current call-site/base-length policy
and retain their historical source binding. The current image route calls
the same canonical memory checker as the object route.

## Declared extern functions (JUN-556 D1, ADR 0380)

A private function named `extern-<symbol>` in a source for the object route
declares a function of another object. Each call of it is emitted as the
arguments in rdi, rsi, rdx, rcx, r8, `call rel32` (displacement 0), and
`mov r9,[rbp-8]` (a callee may destroy the context register the fuel charge
reads), with an `R_X86_64_PLT32` addend -4 relocation against an undefined
GLOBAL NOTYPE symbol `<symbol>` that comes after the exports in `.symtab`
(`sh_info` still names the first global). At most 16 externs and five parameters
each; more is refused (E7102). A source with no declaration compiles to the same
bytes as before. The Mac gate `scripts/seed/check-aiueos-object-externs.py`
reads the object back with an independent ELF parser and checks the symbols,
the three relocations of a two-extern source and the bytes after every call.

Not shown: no x86 machine has run an object that calls through this sequence,
the callee is the linker's business and is unverified by this route, and
`verify-kotoba-kernel-object.py` in the kotoba repository still refuses
undefined symbols, so no extern-declaring object can enter the image until that
verifier and its ledger follow. An extern's arguments are not checked as
memory windows (pointer arguments are the open E7106 design in ADR 0380).

## Data cells (JUN-556 D3, ADR 0380)

Private functions `cell-load-<k> []` and `cell-store-<k> [v]` (k below 64, canonical decimal, placeholder body
`0`) name an 8-byte cell at `.data` offset `80 + 8k`, after the private context. A load compiles to
`mov rax,[rip+disp]` and a store to `mov [rip+disp],rax`; each access has an `R_X86_64_PC32` relocation against the
context symbol with addend `80 + 8k - 4` and a zero displacement. `.data` is `80 + 8 * (highest named cell + 1)`
bytes of zeros; sections and symbols are unchanged, and a source without a cell compiles to the bytes it always
did. A malformed name, a wrong parameter count, a body other than `0`, or a cell on the image route is refused
(E7102). `scripts/seed/check-aiueos-object-cells.py` reads the object back with an independent ELF parser.

Not shown: no x86 machine ran these accesses, and `verify-kotoba-kernel-object.py` in the kotoba repository does not
accept cell relocations or a `.data` larger than the 80-byte context yet, so an object with cells cannot enter the image
until it does.

## Fixed-address MMIO accesses (JUN-556 D4, ADR 0380)

Private functions `mmio-load32-<addr> []` and `mmio-store32-<addr> [v]` (placeholder body `0`) address one of five
local-APIC registers: `addr` is eight lowercase hex digits and must be `fee00020`, `fee000f0`, `fee00320`,
`fee00380` or `fee003e0`. A load is `movabs rax,addr; mov eax,[rax]` and a store `movabs rcx,addr; mov [rcx],eax`;
the address is an immediate, so the object gets no relocation, symbol or data. Any other address, a malformed one,
a wrong parameter count, a body other than `0`, or use on the image route is refused (E7102).
`scripts/seed/check-aiueos-object-mmio.py` reads the object back and checks the exact byte sequences.

Not shown: no x86 machine ran these accesses; the list is the five registers `kernel/apic.c` touches and grows only
by an edit here; the ioapic registers, ports and privileged instructions (`cpuid`, `mov cr4`, `xgetbv`) are not
covered yet.
