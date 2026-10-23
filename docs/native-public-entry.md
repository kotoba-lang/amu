# Native public entry and CDCI scope

The product identity is [native-product.json](../native-product.json).
`bin/amu`, `bin/kotoba` and `bin/kotoba-compiler` resolve to the same
8,434,176-byte Linux x86_64 ELF, SHA-256
`47e90db27ba64c60212ae149877be6b45a07200b87e509d3e79f76e4e1d862a3`.
The source revision is `5d66b129`; metadata/entry retirement commits can
follow without changing this compiler source or image.

## Artifact qualification

The complete 26-module compiler includes the adopted 18-module core and
all Linux emitter/factory/entry modules in `seed/FULL-MANIFEST`.
Native ARM F1=F2=F3 payloads and independently packed images agree.
Native x86 F1=F2=F3 loaderless images agree with the ARM cross-built ELF.
Pinned public `check` and `compile`, exact native role/image reproduction,
all24 fixture-image builds and named public refusals were measured.
The native process environment uses `PATH=/nonexistent`.

The adopted current core source is `2524a4c5`, container `88540e78`,
native payload `a8513d51`. Warm G1=G2=G3, an independent cold C0
rebuild and immutable-lock single-unity rebuilding produce the same
container. The cold C0 uses the preceding 8MiB bootstrap capacity profile;
the complete product and its three-generation rebuild use the 12MiB
static OUT profile. No core source module is omitted in either route.
The adopted normal-core memory layout and heap size are preserved.

The 12MiB static OUT replaces an observed E7104 refusal at 8MiB for the
complete compiler with current TCP/spawn. MM-WORDS is 28,442,624, below
the native per-vector limit of 2^25. This changes capacity, not expected
results, grants or fixture count.

Full original source/corpus and prior receipts remain identifiable.
The exact final F2 image passed fresh all19 Embench correctness, MIR
normal and all seven large entries, GMIR all eight entries, and resource/
pin refusals. All 33 MIR files/three roots and 12 GMIR files/two roots
were retained and their KSL digests checked. MIR whole-large ended with
zero tracked arena use after 155,688,217 scope releases. The receipt is
`docs/evidence/native-cdci-20261023/final-f-correctness.json`; correctness
is recorded separately from compiler fixed points. No new performance score,
full historical assertion parity, general sandbox certificate or live
service cutover follows from these bounded qualifications.

## Public command boundary

The measured public lane covers canonical `.kotoba`, pinned `check`,
explicit-target compilation and native Linux fixture emission. KSL1
project compilation retains every declared source root and exact file
set. The lock bytes can additionally be fixed by `--source-lock-sha256`.

An omitted target is currently `E2`, not an implicit AArch64 selection.
Unsupported verbs/flags are `E1`; unsupported lock forms and unpinned
project requests are `E6015`. Unknown forms are named `E2101` rather than
SIGILL. Usage errors can exit2, while semantic/lock refusals exit1.
Default Kototama output, Definition CIDs/module/package locking, profile/
seal and unimplemented worker/test/inspect routes remain explicit work.
The former README's JVM/NBB parity and public-command claims are
historical and are not carried over as current qualification.

## Controller and two gates

`seed/cdci/runtime.kotoba`, `controller.kotoba` and `kotoba-gate.kotoba`
are the native implementation. `seed/79-native-cdci.kotoba` builds only
the exact source-pinned privileged roles. It rejects arbitrary replacement
source and existing outputs. The Amu gate is the complete adopted core
compiled to native x86; it is not an independently implemented compiler.

The controller accepts an exact19-line KCDCI1 manifest, a same-UID0700
root, bounded regular files and immutable image/source pins. Kernel
openat2 restrictions reject escape and symlinks. Verified static ELF
bytes execute from sealed memfds with fixed argv/env, redirected stdio,
descriptor handling, no-new-privileges, limits, wait/timeout and parent-
death cleanup. It runs Amu selfhost then Kotoba native and writes a
content-bound receipt only after both succeed.

The Kotoba gate accepts exactly172 ledger lines and all24 embedded
source/image/result/exit/fuel vectors. Callers cannot substitute a green
stub or alter expected values. These controls bind bytes and observations;
caller-supplied hashes are not external authentication or signatures.

The current TCP/spawn controller completed both native roles, all24 cases,
18 refusal probes and parent-death child cleanup on x86. The public Git
entry and both aliases also passed pinned check/compile, generated ELF
execution and named refusals. Hosted workflow completion is recorded
separately when terminal. GitHub Actions/Python stage and
observe processes; native role code owns the ordered semantic verdict.
No production route or branch-protection change is part of this work.

## Retirement

The complete11-file,352,080-byte historical text archive records every
original byte, Git blob and SHA-256. Node/NBB public launchers, KBB,
the old re-disassembler entry, package manifests and JVM deps are removed
from active discovery. Existing source and test corpus files remain for
native migration. Archived text has no executable bit and is not used by
the native manifests or workflow.

Old local/x86 CLJK poller/supervisor processes were absent at readback.
Amu repository-specific runner registration was empty. A surviving idle
legacy runner belongs to a separate repository with queued non-gate
workflows and no instantiated jobs. It is outside these two native roles;
this change does not cancel those workflows, stop their infrastructure or
claim deregistration. Its detailed inventory remains in the operations
record, separate from native compiler qualification.

## Current main CI integration

The tiered bootstrap and F root from main are preserved. The complete
compiler verifier accepts that rebuilt F as its native baseline when a
PR tier omits S3/P; it still derives Pw and checks F1=F2=F3, packing,
all24 cases, core adoption and exact privileged-role images. The x86
job also executes the published product and both aliases. Scheduled
full-tier provenance and main-tier runner checks remain in place.
