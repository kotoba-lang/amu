# Mac reproduction without Linux (2026-10-28, JUN-417)

Host: Apple M1 Max, macOS 26.4, main at `65da30e26`. Run through
`scripts/seed/native_build_queue.py`; the gate steps are those of
`.github/workflows/mac-selfhost-aiueos.yml`.

1. `check-aiueos-user-macos-native.py --output OUT/mac-root` with the repository
   descriptor (`seed/bootstrap/aarch64-macos/root.json`; compiler `28e73a9d…`,
   packager `2ee30840…`): staged 48 modules (`18e98b76…`), F1 container ==
   F2 container (`e031180f…`), F1 and F2 unsigned Mach-O identical
   (`9a6d0c37…`), `PASS_MAC_NATIVE_USER_TARGET_SELFHOST`, 32 s.
   Receipt: [`mac-aiueos-user-target.json`](mac-aiueos-user-target.json).
2. `check-macos-cross-linux-candidates.py --mac-build OUT/mac-root --output
   OUT/mac-cross`: `MAC_NATIVE_CROSS_ARTIFACTS_UNEXECUTED`. x86_64 full
   compiler `b8652a6d…` equals `bin/amu`; aarch64 root `20dd57c6…` equals the
   pinned `aarch64-linux-static-root` image; `linuxProcessInThisGate` is
   `false`. Receipt: [`cross.json`](cross.json).

What this shows: the Linux compilers on main are reproducible from the Mac
fixed point with no Linux process. What it does not show: the produced ELFs
were not run on Linux here; the Mac runtime is a diagnostic profile; this is
not a release or hardware qualification.

Open gap found while checking (not fixed here): `(if (arena-scope true) 0 1)`
compiled with this root and packaged `fs2-cli-stdio-general` exits 139
(SIGSEGV); `(if true 0 1)` exits 0.
