# Locked scalar project candidate

This native ARM fixed point extends PR1547's source with a byte linker for
the existing explicit `x86_64-aiueos-kernel-v1` image target. It reuses the
adopted project's discovery, exact KSL1 reads, namespace checks, typed
interfaces, checker and lowering. The original AArch64 linker, object ABI
and four bounded kernel intrinsics remain unchanged.

The two native compiler generations emit identical diamond/refer/private
project images. Both execute the lock, source drift, unsupported unused
function, export and overwrite refusal corpus. The full compiler still
reproduces itself and passes the existing 24 cases. No declaration or
dependency is removed to obtain an image.

The two-module fixture in `scope.json` was compiled from the same lock by
both the existing AArch64 project backend and the new x86 linker. Native
AArch64 execution returns 42 with fuel 999999; the native-produced x86
image/EFI pair reaches the QEMU post-return halt with the same values and
valid boot information. The initial expected fuel 999998 was rejected,
and corrected using the independent AArch64 execution. That failing run
wrote no PASS receipt.

These are scalar project diagnostics. Full-kernel intrinsics, multiple
exports/ISR, live runtime, native media and desktop/input remain open.
Public-product adoption and native x86 compiler/CDCI qualification of this
successor have not happened. PR1547's adoption/merge remains the prerequisite.
