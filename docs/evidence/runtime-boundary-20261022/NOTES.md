# Guest code cannot reach the static runtime by name (JUN-325), 2026-10-22

## The defect

A static image is the guest's source with the runtime text (`seed/76`,
`seed/77`) appended. Both are compiled as one unit, so a runtime name
resolves from guest code. `seed/75` refuses a guest call of a runtime
function (E7101), and it emits the nine `kxrt-` intrinsics (raw loads and
stores, `kxrt-syscall`, `kxrt-ctx`, ...) inline.

It decided "runtime function" by the position of the **symbol's first
appearance** in the source. A guest that named a runtime function therefore
made that function a guest function. The E7101 rule then did not apply, and
the intrinsics are selected by function index alone, so they were emitted
inline in guest code.

This affected `--format static`, the runner and the launcher, on both
targets. It was found on 2026-10-22 while building ADR 0371 step 5.

## What the previous root admitted

`aarch64-linux.json` is `check-runtime-boundary.py` with `--previous-root` set
to `98d4bcb7…`, main's root before this fix. Every earlier root has the same
logic. That root compiled guests calling 8 intrinsics directly:

* `kxrt-call-at` and `kxrt-call-main`;
* `kxrt-ctx`;
* `kxrt-load8`, `kxrt-store8` and `kxrt-store64`;
* `kxrt-syscall`;
* `kxrt-trap`.

Non-intrinsic runtime functions were refused (E7101). A guest naming
`kxrt-load64` broke the intrinsic scan instead (E7102).

**Impact, measured.** The `previousImpact` row runs a guest compiled by the
previous root:
* the guest is granted `KEXE_ALLOW=37,38,39`;
* it sets every allow bit in its context with `kxrt-store64`;
* it then calls wire 3 (`:hash/sha256`), which it was not granted;
* the call succeeds (`:result 64`).

So a guest could grant itself any capability that needs no syscall outside
the image's seccomp filter. It could also read and write any memory of its
own process, and issue raw syscalls inside that filter. The filter still
held: a raw `kxrt-syscall` outside it died of SIGSYS.

## The fix

`xs-rt?` now uses the definition's position: the first token of the def form
(`FF-NODE` → `NF-TOK` → `TF-START`). A program that does not name runtime
functions is classified exactly as before. The `sameBytes` rows show that a
plain guest gives the same bytes from both compilers, for static and launcher
images on both targets.

## Receipts

* `aarch64-linux.json`, native arm64. Every probe is refused with E7101:
  * 15 probes for `--format static` and `--format launcher`, plus 2
    launcher-only probes;
  * on aarch64-linux and x86_64-linux;
  * 64 compiles in all, with no image written.

  The positive control compiles.
* The check runs in both native CI jobs.
* Root re-pinned C-free from `98d4bcb7…` to `8ee8dbed…`, together with the
  launcher of ADR 0371 step 4 (#1484). The old root built S1 = S2 = S3, and a
  second bootstrap shows root = S1 = S2 = S3. Rerun on the new root: the
  static launcher, the wire-42 transport, protocol and admission checks.
