# Static launcher receipts (ADR 0371 step 4, JUN-313)

`--format launcher` builds `tools/static_launcher.kotoba` into a loaderless
static image that starts the GPU provider and the guest, relays the guest's
stdout, waits with a wall-time kill and writes one EDN receipt line
(`:kotoba.static-launcher/v1`). The contract is in `seed/X86_64-LINUX-ABI`
("Static launcher"); the design is ADR 0371 Decision 6 (amended) and step 4.

## Files

* `aarch64-linux.json`: `scripts/seed/check-static-launcher.py` on arm64 Linux
  (podman machine, applehv, native kernel; no emulation). `--compiler` was the
  pinned root F `2f7be2a0…` (ADR 0375 slice 1, the B2 image format), and
  `--previous-root` was main's root, F `06b99a4f…`.
* `x86_64-linux.json`: the same check on a native x86_64 kernel (gad, Linux 7.0, no emulation). It ran through
  `check-x86_64-native.py --tier pr`, as the `qualify-x86_64` job of `selfhost-native.yml` does, with the x86_64
  compiler X2 that the pinned root builds. It is from an earlier base of the B2 branch (main `6deb9969`, see
  `b2-image-20261024/`) and is not refreshed for the current head: the PR's native x86_64 job runs the check.
* Both receipts include the scripted provider's report of its environment:
  exactly `MESA_SHADER_CACHE_DISABLE=true` and
  `VK_LOADER_LAYERS_DISABLE=~all~` (ADR 0371 step 6).
* `selfhost-bootstrap.json` (the canonical copy is
  `docs/evidence/selfhost-bootstrap-aarch64-20261022/`): the second bootstrap
  run (`--tier pr`), F rebuilds itself (F' = root).

## What the receipts show

* **Unchanged formats.** The previous root and the new compiler emit the same
  bytes for a static guest and for the runner: the launcher runtime text is
  appended only in the launcher format. Whether the previous root refuses
  `--format launcher` is recorded, not asserted. A root from before step 4
  refuses it (E7100); `f782f3f2…` has the format, with the launcher text
  before the provider environment. The runner's bytes (`80b757e1…`) are
  main's current runtime runner (`native-cdci-20261023/current-scope.json`).
* **Receipt functions.** 30 Kotoba cases; the control fails exactly one.
* **Runs.** 14, each checked against the receipt and the bytes Python sees:
  * guest alone: ok, trap, arguments, the built environment, descriptors
    0 1 2 only (plus the directory `ls` opens), `NoNewPrivs: 1`, the wall kill
    (`:timeout`, exit 122, about 2000 ms);
  * the launcher's `Seccomp:` field reads 2 while it waits;
  * with the scripted provider: an INFO round trip, the provider sees
    descriptors 0..4 and the grant's exact bytes on fd 3, the guest sees
    `KEXE_CAP_RESOURCES_42=3,4`; a crashing provider (the guest traps,
    `:guest-failed`); a lingering one (killed after its 5 s grace,
    `:provider-failed`); an invalid and an oversized report.
* **Refusals.** 15, before anything starts, each with its stderr line and exit
  status.

## Limits

* The provider in these runs is a python3 script. It is test scaffolding for
  the descriptors and the protocol, not the product provider (ADR 0371 steps
  5 and 6), and its hash in the receipt is python3's.
* The guest that calls wire 42 is built by the product compiler, which admits
  wire 42 since step 3 (#1477, signed off 2026-10-22). Before that the script
  used the test-only compiler of `check-gpu-runtime-transport.py`; it still
  falls back to that only when the compiler under test refuses wire 42.
* Through binfmt_misc, `execveat` of a close-on-exec memfd fails with ENOENT,
  so the launcher cannot start an image of another ISA under emulation. The
  x86_64 receipt comes from a native kernel for that reason.
* Not covered: a relay failure (the launcher's stdout closed), because the
  receipt could not be written either.
