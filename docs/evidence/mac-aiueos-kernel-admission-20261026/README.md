# Mac selfhost AIUEOS kernel admission (2026-10-26)

This is a source-locked kernel **artifact candidate** made on Apple Silicon. It
does not qualify EFI packaging, QEMU boot, Itonami input, release media, or a
physical device. JUN-417 remains In Progress.

## Source and runtime boundary

- The Kotoba runtime source is `seed/macos-fs2-runtime-packager.kotoba`.
  SHA-256: `1ec39ead9c3b0ec575a13d954cd577cf8d588a1e3397a97f08c33728be5923f9`.
- The Mac F5 selfhost compiler that compiled this source had signed Mach-O
  SHA-256 `78a006e488b72ea75542bfc592bf80c9a31f9be441df8e98ddb41950ca373717`.
  The general Kotoba Mac packager wrapped the extracted compiler code.
- The resulting signed arm64 Mac full compiler was 3,317,888 bytes, SHA-256
  `e56548a0717e819c411f56393fa8657c06d28e3028213f4de231eaca87fd3d63`.
  `codesign --verify --strict` passed and `otool -L` listed no dylibs. Its
  native product build did not invoke a Linux guest, JVM, Node, or C compiler.
- FD3 is the only filesystem scope. Source paths are canonical virtual
  absolutes such as `/os/aiueos/native/kernel.kotoba`, mapped beneath FD3;
  `openat` uses `O_RESOLVE_BENEATH | O_NOFOLLOW_ANY`. The KSL1 read callback
  accepts only a scoped basename lock path and a regular file of at most 1 MiB.
  The original relative-path lock was invalid under KSL1 and was not used.
- The `*.derivation.s` files document the reviewed arm64 instruction words;
  they are not runtime or packager build inputs. The separate
  `check_macos_fs2_derivation.py` check compared 184 D/A words and 198 KSL1
  words to assembled derivations, excluding only the explicit Kotoba branch
  relocation slots.

## Locked AIUEOS graph and result

The 15 discovered modules were staged from AIUEOS source commit
`ec0ca6793819e05ed781438f6c167d171038ee99` and its pinned owner files.
The canonical virtual KSL1 lock was 2,015 bytes, SHA-256
`f5d6176903fbac88bb9d2389a249ac418dd7ac1fdf18196c0417993594a99ed6`.
The gate `scripts/seed/check_macos_aiueos_kernel.py` pinned both compiler and
lock, copied and rechecked every locked source byte, ran native `modules`, and
compiled the whole graph twice at fuel `1073741824`. The two kernel ELF files
were byte-identical: 700,696 bytes, SHA-256
`651de56408ef003bbb0c80f81ed2565231f38dc86efcfdc5b087470c01d0e62f`.
Independent ELF inspection found x86-64 static executable entry `0x101000`,
563,968 text bytes, 131,072 data bytes, and the requested fuel in the context.

The same gate observed refusals for wrong/missing lock, lock traversal, a
symlink lock, altered lock hash, transitive source drift, and existing output.
Traversal terminates with a trap (`-5`); the other lock/source cases return
diagnostic errors. No refused build created an output or overwrote the
sentinel. The source files and lock were read back unchanged. All 10 native
calls, output digests, and diagnostics are in `kernel-admission.json`; the exact lock is
`kernel-virtual.ksl` beside it.

## Earlier probe and correction

The earlier Mac F5 compiler produced a 385,536-byte static x86-64 Linux ELF
from `seed/macos-utf8-main.kotoba`, SHA-256
`1e61a5c1f7593e174bd5b40b64dadf88e553aea3f5eda7b844e8a76af4196a8b`,
byte-identical to the pinned ARM Linux compiler's output. This checked target
codegen only. The AIUEOS [module list](modules.stdout) contained 15 modules
(SHA-256 `3dd1c58fd87f2cffd4e36478b9790f89d276bdab6e51b802d879e14af884c6ab`).
The first [lock](kernel.ksl) used relative paths, 1,991 bytes, SHA-256
`cbcb077f4d9a8e54715073daa304f151003c155697985c5d42a5f5d72ce53d6b`.
KSL1 requires absolute paths, so that lock was invalid. The new virtual
absolute lock above corrects the contract while keeping FD3 as the sole
filesystem scope.

Reproduction requires a signed Mac compiler image and a source tree containing
the virtual `os/` and `owners/` files named in the KSL1 lock. The command is:

```sh
python3 scripts/seed/native_build_queue.py -- \
  python3 scripts/seed/check_macos_aiueos_kernel.py \
    --compiler "$MAC_FULL_COMPILER" --compiler-sha256 "$MAC_FULL_SHA256" \
    --source-root "$VIRTUAL_SOURCE_ROOT" \
    --source-lock "$VIRTUAL_SOURCE_ROOT/kernel-virtual.ksl" \
    --source-lock-sha256 "$KSL1_SHA256" --output "$FRESH_OUTPUT_DIR"
```

The next qualification steps are a Mac fixed-point rebuild of the full
compiler, direct integration into the AIUEOS builder, EFI/font/media output,
Linux comparator bytes for the same graph, then QEMU boot and Itonami input.
