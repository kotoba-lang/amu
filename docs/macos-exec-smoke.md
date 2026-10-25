# Kotoba Mach-O executable loader smoke

`seed/macos-exec-smoke.kotoba` emits a fixed, thin arm64 `MH_EXECUTE` image.
Its entry returns 42. This is a format and loader probe, not a compiler or
Amu runtime. The executable requires `MH_NOUNDEFS | MH_DYLDLINK |
MH_TWOLEVEL | MH_PIE` (`0x00200085`); omitting the first three leaves a
structurally recognizable, signable image that macOS kills before the entry.

## 2026-10-25 local evidence

| Input or result | SHA-256 / observation |
| --- | --- |
| Source | `61c8ed26deeda37227f3a538dbb2e586eff3e209dd770d20f460a32e266dfad8` |
| Pinned Amu ARM Linux selfhost root | `cd65664a146bb0eea13577d5d9687467a22700fe91820a12001f1ddb0dc9b4c9` |
| Selfhost-built emitter, `aarch64-linux` static ELF | `286ab00f4a1988bb2a0851710ac708ddb159edf1a44d6d87613d9aed4c6f9462` |
| Kotoba-emitted unsigned Mach-O | `7480b497c217dc2f3249d4bc50ef2516b468559b84b16e5c231202be8d547d92` |
| macOS arm64 signed diagnostic copy | `codesign --verify --strict` passed; exit `42` |
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
diagnostic signing. It does not remove the Linux build-host dependency, provide
a macOS Amu full compiler, implement Darwin capabilities, self-rebuild F1–F3,
or qualify AIUEOS media/release. Those are separate JUN-417 gates.
