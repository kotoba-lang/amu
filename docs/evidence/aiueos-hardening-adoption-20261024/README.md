# Full30 adoption with current memory hardening

`source.json` binds the integrated source, unchanged complete18 core, full30
unity, packed ARM root and cross-built public x86 compiler. The previous
main root produced native ARM F1=F2. `arm-cross-candidate.json` records native
ARM cross generation of the public compiler and all three CDCI executables.
Controller and gate bytes remain identical to their existing policy pins.
This snapshot does not claim that those x86 executables ran on ARM.

The integration retains PR1539's checker: literals cannot create regions,
private helper parameters require every caller to pass a rooted base with
its matching length, and calls cannot remint exported ABI roots. The native
x86 workflow executes the whole memory admission corpus and emitted guard
diagnostics in addition to image/EFI refusal diagnostics.

The authoritative current execution receipts are artifacts of the terminal
exact-head [PR1547 checks](https://github.com/kotoba-lang/amu/pull/1547/checks)
and merged-main `selfhost-native` run. They measure independent canonical Pw,
native x86 F1=F2=F3, both mandatory native CDCI roles, all24 cases and controller
refusals, public aliases/source-lock controls and browser Wasm execution.
The product descriptor records artifact pins and required checks; it does
not turn an unexecuted candidate into a successful runtime qualification.

The earlier adoption and QEMU entry directories retain their exact historical
source bindings. None of these bounded entry diagnostics qualifies the full
kernel graph, ISR/live runtime, native release media, desktop or input.
