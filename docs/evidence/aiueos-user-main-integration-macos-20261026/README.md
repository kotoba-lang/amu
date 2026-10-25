# AIUEOS user target on current Amu main source, macOS arm64

This is a source-integration candidate based on Amu `origin/main`
`0ff0d4b23d26f482e045a3312a26a4cce6d1a6b7`. It applies the
`seed/74-x86_64-aiueos-object.kotoba` and `seed/78-full-entry.kotoba`
user-target changes from Amu PR #1574 head
`a064a454a379705e9de1487efa6d0748415e1293`, plus that PR's two
user-target gate scripts. The generated root, public compiler, and product
descriptor are still those of main; this candidate does not qualify them.

The signed Mac Amu compiler (`e56548a0...fd3d63`) compiled the combined
47-module source (`91174177...9fd58d7`) to F1 and F2. Their container,
extracted program, and unsigned Mach-O bytes were each identical. The
container SHA-256 is `90b1c43c973108a6976b9f25c71d24b918e1bf35878be26ab7385278c03b61e0`.
The F2 Mac executable compiled the scalar `x86_64-aiueos-user-v1` fixture
to the attached 8,280-byte ELF, SHA-256
`7f5a8c0a31b5bdf191410f007973413d16e497a20ae7fe86c734b9fea85808b1`.
The native gate checked the ELF envelope and refused an undeclared
`:io/write` effect with E7101 and no output artifact. Python staged bytes,
launched native programs, and recorded observations. No Linux, JVM, Node,
or C compiler process was used in this Mac gate.

Reproduce from this candidate with
`scripts/seed/check-aiueos-user-macos-native.py`, using signed compiler
and packager images matching the full SHA-256 pins in the JSON receipt.
The gate must run via `scripts/seed/native_build_queue.py` with a new output
directory. The source file list, input and output digests, fixed-point
generations, and refusal result are in `mac-aiueos-user-target.json`;
`native-queue-admission.json` records the shared slot and terminal exit.

This gate did not boot AIUEOS, run an Itonami turn, rebuild the combined
ARM bootstrap root or public x86 compiler, run exact-head CI, or qualify a
release. PR #1574 still has generated-artifact conflicts with current main.
Resolving those files requires a rebuild from the combined source and
native admission; selecting either historical artifact is not a resolution.
