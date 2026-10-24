# Current Amu selfhost native entry

The full30 candidate public `bin/amu` is an 8,749,568-byte static Linux
x86_64 ELF, SHA-256
`d4932491bb3c18824108577c27caab30de197413beb0311910146852ce379789`.
Its source revision is `87fbc40e19a8bcab5e474a64c25c13bf5cf2e051`;
the exact manifest source pins are bound by the adoption receipts.
`bin/kotoba` and `bin/kotoba-compiler` are relative aliases of that image.
The native ARM root is
`2ebb99ba0dee2be4174c6247f3b9573dc516b8a57142b08d461d52ae72feade5`.

All 18 adopted core modules remain. Static capacities are unchanged:
TOK786432/MM-WORDS29,491,200/LitB1MiB/OUT12MiB/heap1765120 words.
The independently rebuilt canonical Pw and full ARM containers F1=F2=F3
agree; the root reproduces the packed full compiler. GitHub native ARM
run 40065864346 and the local native ARM build produced identical bytes.
Neither build invoked an old language host, C compiler or C loader.

## Adoption and native verdict

Current evidence belongs in
`docs/evidence/aiueos-native-adoption-20261024/`. Acceptance requires the
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
