# The route B2 image format on main e2428ce59 (ADR 0375 slice 1, JUN-377)

This branch adds one thing to main: `--format b2`, the static x86_64 image of route B2 (`seed/98-x86_64-b2.kotoba`;
the E1 SysV entry thunks and export table, the E2 16/32-bit loads and stores, the `kxrt-b-` API and `xs-rt-b2`).
It changes the compiler's source (`seed/FULL-MANIFEST` has 48 modules, main's 47 and this one), so the root and the
public x86_64 image (`bin/amu`, `native-product.json`) are regenerated, as in `provider-environment-20261024/`.

## What changes, and what does not

* **Root F `2f7be2a0…`** (from main's `06b99a4f…`). F1 = F2, and a second bootstrap with this root reproduces
  it; the artifacts of both runs are the same bytes (`selfhost-bootstrap-aarch64-20261022/`).
* **Public image `32a10910…`** (`bin/amu` and its two aliases): the x86_64 compiler that the root builds from the full
  source (`check-one-compiler.py`'s `F-x86_64.elf`). On the earlier base of this branch the native x86_64 fixed point
  (`check-complete-x86.py`) gave F1 = F2 = F3 = exactly this construction's bytes, so the public image is the
  cross-built compiler; this head's native fixed point is the CI job's check.
* **Output bytes of the other formats are unchanged.** `check-static-launcher.py` compiles the static, runner and
  launcher images of both ISAs with main's root and with this one, and the bytes are the same
  (`static-launcher-20261022/aarch64-linux.json`).

## Where the checks ran

* **arm64.** podman machine (applehv, a native arm64 kernel; no emulation): the bootstrap twice, the static
  launcher (main's root as `--previous-root`) and one-compiler (F1 = F2 = F3; the CDCI gate pins hold).
* **x86_64.** None for this head: gad was unreachable when the pins were regenerated after the last merge of main.
  **On the earlier base** (main `7eb52a0e`, merged into this branch on 2026-10-25) gad (native x86_64, Linux 7.0)
  ran `check-x86_64-native.py --tier pr`, `check-complete-x86.py` (F1 = F2 = F3), `check-native-clock-entropy.py`,
  `check-native-cdci.py` (24 cases, 18 refusals), `check-public-native-product.py`, main's `check-kototama-i64.py`,
  its AIUEOS, FS2, kernel-memory and live-ABI checks, and `check-b2-image.py` with this branch's compiler: all passed.
  Those receipts were committed at `f867a7f61` and removed here, because the pins they describe moved. The x86_64
  checks of this head are the PR's native x86_64 job (the `b2-image` gate is in `seed/native-gate-plan.json`).
* **Not run here:** `check-wasm32-browser.py` (no Chrome on gad); CI runs it.

## What `check-b2-image.py` shows

* The structure of the images and of every thunk, from their bytes, with four negative controls (a damaged thunk
  epilogue, fuel immediate and export name, and a wrong context word, each refused).
* 8 refusals: a runtime call outside `kxrt-b-` (E7101), `kxrt-b-` outside the format (E2101), a `:string`
  parameter, an empty export name, an empty version (E7102), 17 parameters (E2178), the format on aarch64 (E7100).
  A `cx-` name outside `--format b2` changes nothing (the same bytes under another name).
* On the native kernel: a call through the thunks with 14 words (six registers and eight stack words), the
  callee-saved registers unchanged (a hand-assembled C caller, and a control that clobbers rbx, detected), a
  stack-alignment probe (and a caller that misaligns the stack, which faults), the per-call fuel budget (a
  3,000,000-iteration spin under `KEXE_FUEL=1000000`) with the caller's meter restored (the caller then runs out),
  and the 16/32-bit stores touching exactly their bytes.

The loader, the libc subset and the libvulkan run are in the next PR.
