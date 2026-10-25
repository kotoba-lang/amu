# Atomic lock and XCR candidate

The bounded u32 CAS operations retain the owner contract: acquire0->1,
release1->0, return1 exactly when the swap occurred. The4096-byte bound,
width crossing, null and index checks precede the instruction. The owner's
unaligned-access behavior is preserved. Base/length provenance uses the
same canonical checker as all other memory operations.

Native ARM full33 self-rebuild and unchanged24 runtime cases pass. Two
generations emit identical lock/XCR fixtures and refuse literal roots and
lock/unlock length mismatches. The full27 object admission corpus and8
whole-project provenance refusals still pass.

QEMU executes acquisition, repeat-acquire failure, release, repeat-release
failure, refusal to overwrite word2, unaligned acquire/release, and restores
the saved boot-prefix workspace. XCR0 is read and written unchanged with
CR4.OSXSAVE temporarily enabled and CR4 restored. Both return42 with999999
fuel. The current16-argument module-call image also executes with that result.
The oversized atomic operation reaches its exact window guard at0x101103.

These are native-compiler-generated guest fixtures. QEMU execution is
emulation, not native x86 compiler/CDCI successor qualification. Full kernel,
ISR/live runtime, native media, desktop and input remain separate gates.
