# Current Amu selfhost native entries

`bin/amu`, `bin/kotoba` and `bin/kotoba-compiler` resolve to the
Amu-built native Mac ARM64 host CLI at
`seed/bootstrap/aarch64-macos/amu-cli.macho`, pinned by `cli.json` in that
directory. It implements ordinary `check`, `compile` and `run`, selects the
Mac target explicitly, and manages a private source snapshot, KSL1 lock,
native compilation, packaging and platform signing. The user supplies no
FD3. Follow the [Mac first run](../examples/foundation-starter/MACOS-ARM64.md).

The CLI contains the exact adopted lexer/reader/namer/checker to validate
one exported `main [] :i64`; it delegates compilation to the hash-pinned full
root. The low-level compiler at `amu-full-root.macho` and packager remain
pinned by `root.json`, retain their FD3-scoped bootstrap interfaces, and are
not substituted by another compiler or hosted launcher. Their native fixed
points and the public CLI's fresh native payload reproduction are checked
separately. A changed root, packager or CLI source invalidates the public
CLI gate until it is rebuilt and repinned.

The native CLI host has filesystem/process authority for its explicit local
operations. Generated programs have only CLI/stdout/stderr grants. Children
receive a minimal environment and no inherited FD >=3; compiler helpers alone
receive the private work directory as FD3. An exec-preserved kernel timer
bounds guests to5s, compiler helpers to120s and platform signing to30s.
The original compiler/runtime resource limits and Linux gates remain intact.

`compile` includes the exact source in an LC_NOTE-named region of the signed
Mach-O. `run PROGRAM` treats supplied bytes as untrusted data: it recompiles
the embedded source with the pinned compiler, checks the entire signed image
against the input, and executes the regenerated private image. It never
executes an arbitrary supplied program. Program output includes the complete
signed i64 result followed by a newline; successful return exits0.
Source is limited to1MiB, raw code to4MiB. Symlink/nonregular input, unsupported
flags, incompatible main ABI and existing output paths refuse. Import/project
CLI parity, full Darwin runtime and independent-user release remain open.

Native Darwin ABI provenance: Apple's [syscall declarations](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/syscalls.master),
[process information implementation](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/proc_info.c),
and [ARM64 fork return registers](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/arm64/status.c).
`seed/macos-fs2-runtime-packager.kotoba` emits the adapter using the existing
native Kotoba packager, with no assembler, C compiler or loader dependency.

The unchanged static Linux x86_64 ELF is `bin/amu-linux-x86_64`, with
`bin/kotoba-linux-x86_64` and `bin/kotoba-compiler-linux-x86_64` aliases.
`native-product.json` remains the Linux descriptor and names those entries;
its Linux qualification flags do not qualify the Mac entry. The separate
Linux ARM root is pinned by `seed/bootstrap/aarch64-linux-static-root.json`.

The complete source manifest has 49 modules, including all18 normal adopted
core modules. The core adoption image is unchanged.
The static compiler profile is TOK786432/NODE786432/SIR589824/MM-WORDS31457280,
LitB1MiB/OUT12MiB/heap1765120 words. No compiler, target or declaration is
removed to reduce the graph. No new comparative performance score is claimed.

## Native qualification

The [historical 48-module qualification record](qualification/starter-native-20261029.json)
does not qualify the current 49-module image in `native-product.json`. The record binds native CI receipts and their
artifact digests to exact source and compiler bytes. It distinguishes
compiler reproduction, controller execution, workflow completion and
independent user/host qualification. A new image needs its own record;
an older successful run does not qualify it.

Acceptance requires terminal exact-head native ARM/x86 CI, complete x86
F1=F2=F3, native controller/public checks, exact aliases/source locks, actual
shared-component execution, then merge/main/pin readback. Pending CI does not
qualify a new public image. Current controller and role identities are in
`native-product.json` and `seed/cdci/policy.json`; historical digests are not
current pins. `sourceRevision` identifies a Git tree whose complete compiler
sources were reproduced; `null` (the regenerated state, ADR 0388) means the
descriptor's own commit. It does not identify the historical first producer
or establish independent clean-host qualification.

The controller's two roles and fixed24 corpus remain. Python and GitHub Actions
stage/hash/transport and observe native processes; they do not substitute for
the controller or the checked-in Kotoba verdicts. Historical hosted/C-loader
receipts retain their original source binding and are not current qualification.

## Locked typed x86 projects

`compile ENTRY --target x86_64-linux --format kx64-v1 --output NEW` now has
an explicit project path when source paths/locks are supplied. Exact source
locks, namespace/export/schema checks, dependency order, typed interfaces,
normal checking/lowering and all source/resource bounds remain owned by the
adopted core. The new adapter links the existing backend's module bytes and
relocates code-base-relative string literals for the existing native runner.

The external payload entry is zero-argument `main -> i64`. Internal typed
strings, vectors, schemas, keywords, callbacks and document helpers retain
their existing contracts. Effects and unsupported floating operations refuse;
this does not add a kernel value runtime, privilege, app server or fallback.
The native project gate exercises imported values/closures and refusal controls.
The shared component gate independently pins the actual text/DOM/text-edit
owners. The text owner is `kotoba/lib/kotoba.text`; its old repository is archived.

## AIUEOS and app boundary

The complete46 foundation separately qualified the full kernel/live ABI,
native media and diagnostic full30 desktop with keyboard/mouse/redraw in QEMU
(Amu #1564, AIUEOS #498). Complete47 must retain those admission/refusal gates.
See `docs/native-aiueos-image.md` for the bounded image ABI.

JUN-93 requires the actual shared Browser/CSSOM graph to replace Browser-frame2.
The new text/DOM/text-edit component gate does not qualify CSSOM/layout, the
shared surface/input kernel integration, Itonami agent-first dapps, broker
consent, persistent restart/crash restoration or reference hardware. Keep these
acceptance criteria open. Broader public CLI/package/resolver parity and general
FS fault/race parity likewise remain separate work. Platform-linked/C-runtime
providers remain refused in mandatory native CDCI.
