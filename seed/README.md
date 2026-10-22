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
