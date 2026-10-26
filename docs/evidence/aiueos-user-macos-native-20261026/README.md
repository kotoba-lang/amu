# Mac native AIUEOS user ELF gate (2026-10-26)

[`check-aiueos-user-macos-native.py`](../../../scripts/seed/check-aiueos-user-macos-native.py)
rebuilt the 47-module Amu source on Apple Silicon using a signed Mac native
Amu compiler (SHA-256
`e56548a0717e819c411f56393fa8657c06d28e3028213f4de231eaca87fd3d63`)
and a signed Kotoba Mac packager (SHA-256
`45febd669218fd74c032a0a86a8dd03504311e2d2bf55b02c206ca60822e751c`).
Both inputs passed strict code-signature and undeclared-dylib checks before
creating output. The Mac compiler/packager candidate comes from
[Amu #1580](https://github.com/kotoba-lang/amu/pull/1580); this gate used
the AIUEOS user-target source of [Amu #1574](https://github.com/kotoba-lang/amu/pull/1574).

The exact 47-module unity is 3,458,845 bytes, SHA-256
`93666c1f66d2f81c872989f85d0d0ff37d2f5b761a9789773b89f31c7e312f6c`.
F1 and F2 emitted identical native compiler containers
(`dec8649a9d095b1f144ecf86dd176a32703a637c4999aa634537978369bc4c18`),
raw code and unsigned Mach-O bytes. Their separately signed wrappers have
different signatures, so the fixed-point comparison is over the native
program bytes before signing. The [source-bound receipt](mac-user-target.json)
and [single-slot native queue admission](native-queue-admission.json) record
the stages.

F2 compiled a pure scalar Kotoba source to the 8,280-byte
[`x86_64-aiueos-user-v1` ELF](scalar.elf), SHA-256
`7f5a8c0a31b5bdf191410f007973413d16e497a20ae7fe86c734b9fea85808b1`.
The ELF passed the existing independent shape verifier. The undeclared
effect was rejected with `E7101` and left no artifact. A deliberately wrong
compiler digest was rejected before output creation ([refusal](wrong-pin.json)).
The Mac ELF is byte-identical to the pinned fixture used in
[AIUEOS #505](https://github.com/kotoba-lang/aiueos/pull/505), whose earlier
QEMU gate observed CPL3 result 42 ([parity](aiueos-505-parity.json)). This
gate did not rerun guest execution.

To repeat, provide the two signed Mac native inputs at the digests above,
choose a fresh `OUT` under `github/workspaces/`, and run from this Amu
checkout:

```sh
python3 scripts/seed/native_build_queue.py \
  --phase amu-mac-user-target --output "$OUT.admission.json" -- \
  python3 scripts/seed/check-aiueos-user-macos-native.py \
    --compiler-image "$COMPILER" \
    --compiler-sha256 e56548a0717e819c411f56393fa8657c06d28e3028213f4de231eaca87fd3d63 \
    --packager-image "$PACKAGER" \
    --packager-sha256 45febd669218fd74c032a0a86a8dd03504311e2d2bf55b02c206ca60822e751c \
    --output "$OUT"
```

Python stages source and checks bytes; the compiler and packager execute as
Kotoba/Amu produced Mach-O programs. No Linux, JVM, Node or C compiler
process ran in this gate. The historical initial Mac bootstrap provenance
is separate.

This establishes a Mac native compiler route for the current #1574 source,
not its integration with newer Amu main. #1574 currently conflicts on the
checked-in compiler/root binaries and descriptor; a combined source rebuild
and new exact-head CI are still required. The v1 user ELF has no strings,
heap or model/tool effect. Normal signed app admission, a trusted operation
approval, an Itonami turn, restart persistence, release and physical AIUEOS
remain open.
