# Current Amu selfhost native entry

The full31 public `bin/amu` is a static Linux x86_64 ELF. Its exact size,
SHA256 and source revision are recorded in `native-product.json`; the exact
manifest source pins are bound by the current native execution receipts.
`bin/kotoba` and `bin/kotoba-compiler` are relative aliases of that image.
The native ARM root is separately pinned in
`seed/bootstrap/aarch64-linux-static-root.json`.

All 18 adopted core modules remain. Static capacities are unchanged:
TOK786432/MM-WORDS29,491,200/LitB1MiB/OUT12MiB/heap1765120 words.
The native workflow measures independent canonical Pw, matching full ARM
containers and root reproduction, without an old language host, C compiler
or C loader. The product includes current main's Kototama i64 AOT and
call-site/base-length memory hardening together with image/EFI packaging.

## Adoption and native verdict

Current evidence belongs in
`docs/evidence/aiueos-aot-adoption-20261024/`. Earlier full30 snapshots retain
their historical source binding. Acceptance requires the
actual native x86 full compiler F1=F2=F3, current-source unity identity,
clock/entropy/refusal/resource checks, both mandatory native CDCI roles
and exact public-product/alias/source-lock readback. Exact-final-head PR CI,
merge, merged-main CI and final tree/pin/mode checks are separate gates.
An old matching descriptor or a Python observation is not that verdict.

The controller and gates rebuild byte-identically with this compiler:

* controller `39a500374e27d3a04404573cbf455eef56b2dbb6aa473279e3cd75cae9a1263a`
* Amu selfhost `e6dcf6189b527208bd65cd53d8f05d07008fb6adc0dc4e1e37dc1e92df334700`
* Kotoba native `39fac666f5eb57b4adf69c1efe1770758e78dd7f51c368cbbdefeda14ee6d995`

Fresh native receipts bind those exact images and their input ledger to the
new compiler. The fixed24 corpus and complete core are unchanged. No new
comparative performance score is published. Earlier all19/MIR/GMIR and
provider-environment evidence remains historical in its original directories.

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
