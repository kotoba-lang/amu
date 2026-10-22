# Measured compiler core

The sixteen sources in [`MANIFEST`](MANIFEST) are the adopted compiler core,
not an optional benchmark backend. [`compiler-core.json`](compiler-core.json)
pins the measured M104 baseline and current M105 source lineage. Extend this
lineage for Amu selfhost and public `kotoba compile` as required by
[ADR 0370](../docs/adr/0370-embench-measured-compiler-core.md).

The C/JVM/Node compiler and build routes are removed in this candidate.
The old C bootstrap/package/selfbuild/image drivers are no longer available.
See [the retirement inventory and recovery record](../docs/native-compiler-retirement.md).
The former README and driver source remain in the preserved Git ancestor.

The checked-in `bootstrap/adopted-20261012.bin` is historical raw AArch64
code requiring the removed C loader. It is retained as provenance data,
not an executable native compiler. `adoption-20261017.json`, rung records,
self-rebuild receipts and the full historical Embench data retain their
original bytes and meaning. No old C-loader command qualifies the new route.

Native qualification remains incomplete: build the independent initial
compiler and its complete runtime/package closure, self-rebuild/fixed point,
execute all nineteen Embench workloads, and verify public imports/CLI.
Neither source pin verification nor the saved full-19 offline audit satisfies
these execution gates. The sixteen core source modules and test/refusal
inputs are preserved unchanged by the hosted compiler removal.

## Separate loaderless bootstrap root on owning main

Owning main includes `bootstrap/aarch64-linux-static-root.elf` and its fixed
receipt, plus the canonical `X86_64-LINUX-SELFHOST-MANIFEST` closure. Its
source shares the measured frontend/lowering, while its bootstrap stack
emitter is separate from the measured `41-a64gen` product backend. The root
is a bootstrap input to verify, not a replacement for the measured core.
The owning main snapshot must be reproduced separately from this candidate's
FS2/document successor. See `docs/evidence/selfhost-bootstrap-aarch64-20261022/`.
The complete product/packager/controller and public locked import/CLI gates
remain open; the exit-69 public boundary stays in place until they pass.
