# Kotoba Mach-O loader and Darwin I/O smoke

`seed/macos-exec-smoke.kotoba` emits a fixed, thin arm64 `MH_EXECUTE` image.
Its entry reads at most 16 bytes from stdin into its stack through the
observed Darwin arm64 `x16` syscall selector and `svc #0x80`, writes exactly
those bytes to stdout, then exits 42. EOF exits 43. A separate
Clang-assembled control gave the same outcomes on this Mac before the Kotoba
source was changed. This is a format, loader, and minimal host-I/O probe, not a
compiler or Amu runtime. The executable requires
`MH_NOUNDEFS | MH_DYLDLINK | MH_TWOLEVEL | MH_PIE` (`0x00200085`);
omitting the first three leaves a
structurally recognizable, signable image that macOS kills before the entry.

## 2026-10-25 local evidence

| Input or result | SHA-256 / observation |
| --- | --- |
| Source | `b5fec1a80ea43645cd549d5e57c54802cbdef1eb048300a1a95c62b7bd9a776c` |
| Pinned Amu ARM Linux selfhost root | `cd65664a146bb0eea13577d5d9687467a22700fe91820a12001f1ddb0dc9b4c9` |
| Selfhost-built emitter, `aarch64-linux` static ELF | `0906ceed0d5db556c4ecb49973517355876941920c1dc94ad4f3d2f112065ced` |
| Kotoba-emitted unsigned Mach-O | `cd82530784cae0c2b9b42125fb82f2a3725269b62a34cccb53c2199664109644` |
| macOS arm64 signed diagnostic copy | `codesign --verify --strict` passed; `abc\n` echoed with exit 42; empty stdin exited 43; 17-byte stdin returned the first 16 bytes with exit 42; signed SHA-256 `2d845d80db12777bf4c942566125887e6cbce8f7c266a30e17555f0c4a113bbd` |
| Signed copy missing dynamic-link flags | signature passed; exit `-9` in Python subprocess |
| FS2 write outside granted root | emitter exit `3`; no output file |

The emitter was built and run by the pinned selfhost root in a network-disabled
ARM Linux container, under `scripts/seed/native_build_queue.py`. Two independent
emissions had identical unsigned bytes. On Apple Silicon,
`scripts/seed/check-macos-exec-smoke.py UNSIGNED_MACHO NEW_OUTPUT_DIR` signs
**copies** with the system `codesign`, verifies them, executes the positive and
negative controls, and writes a JSON receipt. Python stages and observes; it
does not emit the Mach-O. The negative control changes only the header flags.

This proves that Kotoba can emit bytes accepted by the Mac loader after local
diagnostic signing and perform one bounded Darwin stdin/stdout/exit sequence. The
raw syscall sequence is local ABI evidence, not a general or release-qualified
Darwin capability contract. It does not remove the Linux build-host dependency,
provide a macOS Amu full compiler, implement its file/clock/memory/authority
capabilities, self-rebuild F1–F3, or qualify AIUEOS media/release. Those are
separate JUN-417 gates.
