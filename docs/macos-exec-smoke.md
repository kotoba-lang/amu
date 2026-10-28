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
Darwin capability contract. **As of the 2026-10-25 evidence above**, it did not
remove the Linux build-host dependency, provide a macOS Amu full compiler,
implement its file/clock/memory/authority capabilities, self-rebuild F1–F3, or
qualify AIUEOS media/release. Those were separate JUN-417 gates. The first
two have since been closed; see the status update below.

## Status update, 2026-10-28 (JUN-417)

Code and receipts supersede the sentence above on two points. Read against
`seed/bootstrap/aarch64-macos/root.json` (status `diagnostic-candidate`) and
[`docs/evidence/mac-no-linux-reproduction-20261028/`](evidence/mac-no-linux-reproduction-20261028/README.md):

* **A macOS Amu full compiler exists.** `amu-full-root.macho` (arm64 Mach-O)
  rebuilds the 48-module FULL source on Apple Silicon: F1 and F2 containers are
  identical (`e031180f…`), the packager rebuilds itself, and the AIUEOS user
  target is emitted. Reproduced on an Apple M1 Max, macOS 26.4, in 32 s with no
  Linux, JVM, Node or C compiler process.
* **The Linux build host is not needed to produce the Linux compilers.** From
  that Mac fixed point, `check-macos-cross-linux-candidates.py` produces an
  x86_64 compiler byte-identical to `bin/amu` (`b8652a6d…`) and an aarch64 root
  byte-identical to `seed/bootstrap/aarch64-linux-static-root` (`20dd57c6…`);
  its receipt records `linuxProcessInThisGate: false`. The produced ELFs were
  not executed on Linux in that gate (`MAC_NATIVE_CROSS_ARTIFACTS_UNEXECUTED`).

Still open, and not claimed here: the Mac runtime is a diagnostic profile, not
a qualified one (`arena-scope` segfaults under `fs2-cli-stdio-general`, exit
139: the generated code loads context ABI slots 224 and 232, the scope enter
and leave routines of `docs/native-source-lock-and-scalar-scopes.md`, and calls
them; the Mac wrapper installs neither, so the call lands on address 0, as the
crash report shows. JUN-546); the Mac root's status is `diagnostic-candidate`, and updating the pinned
descriptors still needs a hand-run staged bootstrap (JUN-545); the AIUEOS
release bundle's own build is tracked separately; physical hardware and release
qualification are separate gates.
