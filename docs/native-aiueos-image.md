# AIUEOS native image and transition loader candidate

JUN-31, 2026-10-24. These commands extend the adopted compiler lineage in
`seed/FULL-MANIFEST`; they are a candidate, not the installed public entry.
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

Before adoption, regenerate the affected root/public-product/controller
pins and run the actual native x86_64 qualification and both mandatory
native CDCI roles. Python diagnostics and QEMU do not replace that verdict.
The candidate does not change installed compiler artifacts or restart CDCI.
