# Current Amu selfhost native entry

The full46 public `bin/amu` is a static Linux x86_64 ELF. Its exact size,
SHA256 and source revision are recorded in `native-product.json`; the exact
manifest source pins are bound by the current native execution receipts.
`bin/kotoba` and `bin/kotoba-compiler` are relative aliases of that image.
The native ARM root is separately pinned in
`seed/bootstrap/aarch64-linux-static-root.json`.

All18 normal adopted core modules remain byte-identical. Static capacities:
TOK786432/NODE589824/MM-WORDS29491200/LitB1MiB/OUT12MiB/heap1765120 words.

The native workflow measures independent canonical Pw, matching full ARM
containers and root reproduction, without an old language host, C compiler
or C loader. The product includes current main's Kototama i64 AOT and
call-site/base-length memory hardening together with image/EFI packaging.

## Adoption and native verdict

Current evidence belongs in
`docs/evidence/kototama-i64-receipt-20261024/`. Earlier full30 snapshots retain
their historical source binding. Acceptance requires the
actual native x86 full compiler F1=F2=F3, current-source unity identity,
clock/entropy/refusal/resource checks, both mandatory native CDCI roles
and exact public-product/alias/source-lock readback. Exact-final-head PR CI,
merge, merged-main CI and final tree/pin/mode checks are separate gates.
An old matching descriptor or a Python observation is not that verdict.

The controller and gates rebuild byte-identically with this compiler:

* controller `54e7c9fc5b39cb788dd670a22c9abb5b6e3163e417c172bb05f910d1469e8197`
* Amu selfhost `d69dcbe783846c7c22c4d7957be10a66fed7b6f82e35f5affb27b2b171162c53`
* Kotoba native `e015c387cc87b14022781c94474104ffe0ff113a2623ae5882a72ce6c3212b80`

Fresh native receipts bind those exact images and their input ledger to the
new compiler. The fixed24 corpus and complete core are unchanged. No new
comparative performance score is published. Earlier all19/MIR/GMIR and
provider-environment evidence remains historical in its original directories.

All14 main47 kernel packaging suites and memory admission/guard checks also
pass with this compiler. Their reports retain explicit guest/live-kernel
exclusions; they do not qualify a live kernel or deployment.

## AIUEOS scope

The new native image/EFI diagnostics run on the qualified x86 generations
as well as the native ARM bootstrap. Source/image pin mismatches and absent
fixed-point proof refuse; post-adoption ARM root=F1 is accepted only when
the measured rebuild reproduces the pinned root. See
`docs/native-aiueos-image.md` for the supported bounded ABI.

The QEMU entry probe does not qualify the complete AIUEOS kernel graph,
module locks, ISR/live runtime, native media, desktop/input, Browser/CSSOM
or Itonami. These remain JUN-31/JUN-93 dependencies.

Engine-neutral defaults, broader CLI/package/resolver compatibility and
general FS fault/race parity remain separate work. Platform-linked/C-runtime
providers remain refused in mandatory native CDCI. The earlier RANGE
out-of-file SIGILL observation is not named-refusal parity. No legacy
runtime or emulation fallback is introduced by this adoption.

The current JUN-371 integration appends the cache module (FULL47) to main7eb.
Main46 root/product pins are provisional build inputs until fresh FULL47
ARM/x86/profile/host/controller/public qualification and artifact adoption.
The former FULL41 local/CI evidence remains bound to its historical source.
