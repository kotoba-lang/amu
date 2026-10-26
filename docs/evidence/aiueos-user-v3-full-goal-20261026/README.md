# Amu user-v3 full Goal request (2026-10-26)

The native user-v3 target now emits a version-2, 104-byte syscall 5 request
containing the complete 1–51 byte Goal, rather than its final character.
The source-bound Mac selfhost [root receipt](mac-root.json) rebuilt the complete
47-module graph twice to the same unsigned compiler container. The updated
`root.json` pins that source graph and fixed point. The [user-v3 receipt](mac-user-v3.json)
reproduced ELF SHA-256
`108174e896008ac4b523450acd57d16b2b37ba3eb31f6b21d3ad3874344ca4ec`
twice and refused the v3-only operation on the v2 target.
The same signed Mac F2 produced [static ARM/x86 cross candidates](mac-cross.json)
without an ELF interpreter. Those Linux-target images were generated, not
executed or qualified by this Mac gate.

The [native ARM bootstrap run](https://github.com/kotoba-lang/amu/actions/runs/40266481132)
regenerated `F2.elf` from the prior checked-in root and matched the Mac ARM
candidate exactly (`4a614fb717d897ae7e42dfcc9948321e9dc6345f4318294c2202123f370ae0c6`).
Its ARM qualification job then stopped before execution because the previous
root descriptor still pinned `bc9c295119b597a6de8356d8ad2a1421e94ad514e4aef091150e624dfdbff756`.
The source-bound candidate has therefore been staged as the new root for the
next exact-head run. The x86 native fixed point and complete ARM/x86 gates
remain to be read back before qualifying either staged image.

The AIUEOS kernel and QEMU gate separately verify the guest call, full Goal
envelope, one-use local choice, restore, and modified-slot refusal. This Amu
gate only proves native compiler output. It does not qualify canonical
`:llm/generate`, human consent, a full agent loop, release, or hardware.
