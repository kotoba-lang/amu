# Native x86_64 Linux — evidence

Latest runtime/selfhost qualification: `runtime-selfhost-qualification.json`,
source/test head `112b8a7b23f4f8eb6094fb804f5cf9c8fd7dd49f`, successful CI
https://github.com/kotoba-lang/amu/actions/runs/38717513906 (all four jobs).

The source-only x86 compiler rebuilds itself twice on actual x86_64 Linux.
Native payloads and tagged containers are identical across G1/G2/G3 and the
independent local Rosetta run. Native SHA256:
`698b280b0cc80678b85a7af029a06624ee6b510a454d8995a04b26a532a36cb6`.
Twenty-four runtime programs agree with AArch64 on result/trap and remaining
fuel; six refusal/preservation cases pass. The current full optional cross
closure also passes G1/G2 identity,55 actual Linux ELF executions,14 refusals,
and three unchanged legacy AArch64 containers. Three input mutation controls
are mock-only orchestration checks. A separate local512 KiB launch-stack
diagnostic regenerates the exact same compiler container.

`runtime-selfhost-results.tgz` contains compiler generations/source, raw
compile/execution logs and input pins, the current scalar suite, plus separate
historical Linux failures and the older AArch64 leaf-trap fuel observation.
The exact digest and report bindings are in the qualification JSON. The Linux
bootstrap wrapper includes the pinned trusted loader unchanged, reserves512
KiB of stack below its1 MiB budget, and uses glibc startup heap headroom. Its
syscall filter, grants and process limits stay unchanged. No JVM/Node/Graal
fallback, C-free, performance, Q9, release or main-adoption claim is made.
The optional source compiler currently refuses project/KIR/float routes.

The records below describe the earlier scalar-only qualification.

Earlier scalar qualification: review-fix-qualification.json, source/test head
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
main adoption claim follows from those historical scalar-only records.
