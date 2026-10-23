# Static launcher receipts (ADR 0371 step 4, JUN-313)

`--format launcher` builds `tools/static_launcher.kotoba` into a loaderless
static image that starts the GPU provider and the guest, relays the guest's
stdout, waits with a wall-time kill and writes one EDN receipt line
(`:kotoba.static-launcher/v1`). The contract is in `seed/X86_64-LINUX-ABI`
("Static launcher"); the design is ADR 0371 Decision 6 (amended) and step 4.

## Files

* `aarch64-linux.json`: `scripts/seed/check-static-launcher.py` on arm64 Linux
  (podman machine, applehv, native kernel; no emulation), with the re-pinned
  root as `--compiler` and main's root before this PR, `cd85f3fc…`, as
  `--previous-root`.
* `x86_64-linux.json`: the same check on a native x86_64 kernel, from the
  `qualify-x86_64` job of `selfhost-native.yml` (run through
  `check-x86_64-native.py` with the self-built x86_64 compiler X2): CI run
  39799020895 at `4e1e0e1d`, before main's static-profile merge. The
  launcher text did not change after it; this PR's final CI run checks it
  again.
* `selfhost-bootstrap.json` (the canonical copy is
  `docs/evidence/selfhost-bootstrap-aarch64-20261022/`): the second bootstrap
  run, root = S1 = S2 = S3.

## What the receipts show

* **Unchanged formats.** The previous root refuses `--format launcher`
  (E7100). It and the new compiler emit the same bytes for a static guest and
  for the runner: the launcher runtime text is appended only in the new
  format. The compiler image itself is a static image, which is why the old
  root built S1 equal to S2 and S3.
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
