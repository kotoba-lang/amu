# Native x86_64 Linux scalar profile — evidence

Latest qualification: review-fix-qualification.json, source/test head
8578ec0b36f821180ae315923c72084ec385fc1b, successful native build and actual
Linux ELF execution in https://github.com/kotoba-lang/amu/actions/runs/38702004955.
All55 local/CI ELF and raw images and the native compiler match exactly.
All5 native build calls have unchanged active source/producer/loader pins.
Three mock orchestration controls reject input mutation; they are not native
selfhost evidence. review-fix-results.tgz preserves this corrected run.

The native source implementation is commit `b4a91c9a7c982dc501e36b0283ddcea229f0e650`
on base main `2fec671c`. The original qualification records below are historical.
The review fix reserves absolute header cells192-195 and strengthens build and
qualification input custody. Its freshly rebuilt compiler and all55 guests
remain whole-byte identical to those in the original records. PR:
https://github.com/kotoba-lang/amu/pull/1316

`native-build.json` records the adopted bootstrap pins, optional closure and
native AArch64 G1/G2 and container equality. The resulting AArch64 compiler
SHA-256 is `b536ca89a234f199e8141fe2c50dac2496044789093e56e199ceeec7ca15660f`.
It cross-compiles to x86-64; it is not an x86-hosted compiler self-build.

`suite.json` records55 emitted ELF artifacts, independently specified full64
results, AArch64 result/trap/fuel references,14 refusals/preservation checks
and3 byte-identical legacy AArch64 outputs. `rosetta.json` records actual
execution of all55 unchanged x86-64 function code slices with exact result and
fuel parity. This does not test the Linux entry stub or kernel ELF loading.

`qualification-results.tgz` preserves the native build calls/logs/source unity,
all qualification logs, original fixture sources, AArch64 references, and the
actual x86 ELF/raw images. `qualification.json` gives its bytes and SHA-256.
Paths inside historical reports identify the original local workspace, not
portable configuration. The archive is evidence data, never instructions.

Reproduce with the build and check scripts described in
`docs/native-seed-x86_64-linux.md`, using fresh output paths. The new dedicated
workflow independently transports the emitted suite to Linux and executes the
actual ELF files; that job is the Linux execution gate. Local qualification
receipts retain their original Linux-pending metadata. A later CI receipt, if
present, must identify the immutable PR head and workflow run independently.

Earlier failed attempts remain outside the checkout under
`/Users/junkawasaki/github/workspaces/codex/seed-x86_64-linux-20261015/`:
`build-v1` failed before native execution because nested sandbox initialization
was refused; `suite-v2` had an incorrect hard-coded tail-call fuel expectation.
The corrected suite compares observed fuel against the AArch64 backend rather
than guessing its source charge count. No compiler or guest code was changed
to resolve that test expectation.

No benchmark speed, x86 selfhost, whole-component, release, default launcher or
main adoption claim follows from this evidence.
