# Platform-linked image receipts (ADR 0371 step 5, JUN-322)

`--format platform-linked` writes an x86_64 ELF that the host's dynamic linker
loads. Only the GPU provider is built this way. The contract is
`seed/X86_64-LINUX-ABI` ("Platform-linked image"); the design is ADR 0371
Decision 5 and step 5.

## Files

* `x86_64-linux-qemu.json`: `scripts/seed/check-platform-linked.py`.
  * The build phase ran on arm64 Linux (podman machine, native), with the
    re-pinned root F (F1 of the bootstrap) as `--compiler` and step 4's root
    F `710b6ae6…` as `--previous-root`.
  * The run phase ran in an x86_64 Debian 12 container (glibc 2.36) under
    qemu-user.
* The native x86_64 run comes from this PR's `qualify-x86_64` CI job
  (`check-x86_64-native.py` runs `check-platform-linked.py all` with X2). It
  adds the provider skeleton under the launcher, which emulation cannot start.

## What the receipts show

* **Structure, parsed from the bytes.** The 7 program headers in order, the
  interpreter, W^X, the exact dynamic tag set, `DF_BIND_NOW` and `DF_1_NOW`,
  and GLOB_DAT relocations inside the RELRO page.
* **Imports.**
  * The hello, arguments, RELRO and provider images import
    `__libc_start_main` from `libc.so.6` only.
  * The image that calls `kxrt-p-vkgipa` adds `libvulkan.so.1`
    `vkGetInstanceProcAddr`.
* **The allowlist check's own control.** A test-only compiler, patched in
  memory and never written to `seed/`, makes import 1 libc's `snprintf`. The
  allowlist check refuses its image.
* **Runs on glibc.**
  * hello: exit 7, and the structured line;
  * the arguments;
  * `snprintf(buf, 256, fmt, 1 .. 11)` through `kxrt-ccall`: 14 arguments (6
    registers and 8 stack words, varargs) give "1 2 3 4 5 6 7 8 9 10 11" and
    23;
  * a GOT write dies of SIGSEGV (RELRO).
* **Refusals.**
  * calling a runtime function outside `kxrt-p-` is E7101;
  * the platform API in `--format static` does not resolve (E2101);
  * the format on aarch64-linux is E7100.
* **Unchanged formats.** Static, runner and launcher outputs are the same
  bytes as the previous root's, on both targets, and the previous root
  refuses the new format.

## Limits

* The libvulkan image is never executed here. By the owner's decision of
  2026-10-22, the libvulkan probe runs on GPU hosts only, and libc-only images
  may run in the native x86_64 CI job.
* The provider's string hand-off (the protocol table and wire-42 answers as
  Kotoba strings) and its environment are step 6.
