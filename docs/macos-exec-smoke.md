# Kotoba Mach-O loader and Darwin I/O smoke

`seed/macos-exec-smoke.kotoba` emits a fixed, thin arm64 `MH_EXECUTE` image.
Its entry writes `ok\n` to stdout through the observed Darwin arm64 `x16`
syscall selector and `svc #0x80`, then exits 42. A separate Clang-assembled
control gave the same output and exit on this Mac before the Kotoba source
was changed. This is a format, loader, and minimal host-I/O probe, not a
compiler or Amu runtime. The executable requires
`MH_NOUNDEFS | MH_DYLDLINK | MH_TWOLEVEL | MH_PIE` (`0x00200085`);
omitting the first three leaves a
structurally recognizable, signable image that macOS kills before the entry.

## 2026-10-25 local evidence

| Input or result | SHA-256 / observation |
| --- | --- |
| Source | `4d6a014db6352c4ac860e8d888dd04e1d6f658ffbc8733700f53a8e4fffd4aa4` |
| Pinned Amu ARM Linux selfhost root | `cd65664a146bb0eea13577d5d9687467a22700fe91820a12001f1ddb0dc9b4c9` |
| Selfhost-built emitter, `aarch64-linux` static ELF | `ed3ce19b4218f3c653d6fb64bbb93487ec67ad5aee5cf7a8d9287f3797163119` |
| Kotoba-emitted unsigned Mach-O | `badd743552fc678652505fb7d74840a781a0910fc3e51fe69f3f873ec5556058` |
| macOS arm64 signed diagnostic copy | `codesign --verify --strict` passed; stdout `ok\n`, exit `42`; signed SHA-256 `819aa0d4d6c9db894b95ee6e16f7d6ee7399120b31402d1a08d49583a6bebfea` |
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
diagnostic signing and perform one observed Darwin write/exit sequence. The
raw syscall sequence is local ABI evidence, not a general or release-qualified
Darwin capability contract. It does not remove the Linux build-host dependency,
provide a macOS Amu full compiler, implement its file/clock/memory/authority
capabilities, self-rebuild F1–F3, or qualify AIUEOS media/release. Those are
separate JUN-417 gates.
