# Mac selfhost user payload slot candidate

The 47-module Amu source graph rebuilds to the same F1/F2 Mac native
compiler. That compiler emits the fixed-address AIUEOS scalar user ELF and
packages it into a 512 KiB boot slot. The root descriptor is updated to the
new source graph, so the repository-local default gate can repeat the build:

```sh
python3 scripts/seed/native_build_queue.py -- \
  python3 scripts/seed/check-aiueos-user-macos-native.py \
  --output "$NEW_PRIVATE_WORKSPACE"
```

The [native gate receipt](mac-selfhost.json) records the 47 source pins,
F1/F2 compiler and packager fixed points, ELF and slot digests. The slot
contains a 64-byte header, the exact ELF and zero padding. Existing output,
missing input and an oversized source each refuse without creating a new
slot. The compiler, slot and EFI formats are produced by Kotoba/Amu native
programs; Python stages inputs and checks outputs. The gate ran on Apple
Silicon without Linux, JVM, Node or a C compiler in this build closure.

This is a diagnostic compiler and packaging candidate. The paired AIUEOS
QEMU gate checks execution and tamper refusal separately. A fixed image hash
is not a signature or release authority. Full exact-head native qualification,
Itonami agent execution and physical hardware acceptance remain open.

## Mac-produced Linux candidates

CI [run 40243658294](https://github.com/kotoba-lang/amu/actions/runs/40243658294)
repeated the Mac root gate and produced native ARM/x86 compiler candidates.
The [CI Mac root](mac-ci.json) and local receipt have equal canonical source,
compiler container, raw code and unsigned Mach-O bytes. Their ad hoc signed
Mach-O files differ across hosts; both produced byte-identical Linux outputs.
The [cross artifact record](cross-ci.json) binds the ARM root SHA-256
`6eab89430c68df43d17f0a4b4c4700660915163b5ef81ebac5ab6b8a520b822d`
and x86 full compiler SHA-256
`9c076f3d5f6d04c812361b12160499a83c2d56c789a1ae4988da34f4779cda48`.
The [ARM](native-arm-ci.json) and [x86](native-x86-ci.json) native receipts
each prove two further generations match the Mac-produced ELF byte for byte.
Independent local Mac output matched all four CI Linux artifacts. The
Linux runs verified candidates; they did not produce them.

Those exact bytes are pinned as **unqualified candidates** in the draft
repository root and public `bin/amu`. Source/image preflight passes. The
complete native corpus, controller, public consumer and exact-head CI gates
must pass before the qualification fields can be promoted. Previous CCF
qualification covers different source and image bytes.
