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
