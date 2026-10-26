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
next exact-head run.

The [new-head native run](https://github.com/kotoba-lang/amu/actions/runs/40267772245)
on `b1d3e1f8ae71d72ffb8fa8457b346501c60213eb` completed successfully.
ARM bootstrap reproduced the pinned root
`4a614fb717d897ae7e42dfcc9948321e9dc6345f4318294c2202123f370ae0c6`;
the combined compiler returned F1=F2=F3 with container
`e340265239c5ba6a619ff96bfa192f75dbd6a26c1cfa24d8dde12f577e708f2e`.
The ARM transport gate bound the current source, root, compiler and receipts.
The native x86 compiler returned F1=F2=F3
`7010e5d9230ba8c45d16b54fffebad628d4de20ad97d349dfde23c479cd505a9`,
identical to `bin/amu`. The x86 controller passed 24 cases, 18 refusals and
parent-death cleanup; the public product gate exercised all three aliases,
pinned check/compile, native execution and named refusals. The independent
ARM and x86 qualification jobs and the Mac selfhost, checked-definition and
definition-CID workflows all finished green on that head. A later metadata
commit must be read back on its own head before the PR is merged.

The AIUEOS kernel and QEMU gate separately verify the guest call, full Goal
envelope, one-use local choice, restore, and modified-slot refusal. This Amu
gate only proves native compiler output. It does not qualify canonical
`:llm/generate`, human consent, a full agent loop, release, or hardware.
