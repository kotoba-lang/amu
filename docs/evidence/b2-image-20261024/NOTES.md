# The route B2 image format on main 6deb9969 (ADR 0375 slice 1, JUN-377)

This branch adds one thing to main: `--format b2`, the static x86_64 image of route B2 (seed module 98; the E1 SysV
entry thunks and export table, the E2 16/32-bit loads and stores, the `kxrt-b-` API and `xs-rt-b2`). It changes the
compiler's source (`seed/FULL-MANIFEST` has 31 modules, main's 30 and `seed/98-x86_64-b2.kotoba`), so the root, the public x86_64 image (`bin/amu`,
`native-product.json`) and `current-scope.json` are regenerated, as in `provider-environment-20261024/`.

## What changes, and what does not

* **Root F `e53b6076…`** (from main's `c95b8441…`). F1 = F2, and the root reproduces itself
  (`selfhost-bootstrap.py --tier pr`; `selfhost-bootstrap-aarch64-20261022/`).
* **Public image `85713104…`** (`bin/amu` and its two aliases), from main's `23e714db…`. `check-complete-x86.py`
  gives F1 = F2 = F3 = it, and `check-public-native-product.py` accepts the descriptor (`public-product.json`).
* **Unchanged:** the core source and container, the runtime runner, the native controller and the two CDCI gate
  images (`seed/cdci/policy.json`; `check-one-compiler.py` asserts the gate pins).
* **Output bytes of the other formats are unchanged.** `check-b2-image.py --previous-compiler` compiles the same
  sources with main's compiler (`S-x86_64.elf` built by main's root `c95b8441…`) and this branch's, for x86_64 static, kx64-runner and
  launcher and for aarch64 static and launcher: the same bytes (`b2-image.json`, `results.unchangedFormats`).
  `check-static-launcher.py` also compares with main's root as `--previous-root`.

## Where the checks ran

* **arm64.** podman machine (applehv, a native arm64 kernel; no emulation): the bootstrap twice (the second time
  with the new root, which it reproduces; the artifacts of both runs are the same bytes), the static launcher (with
  main's root as `--previous-root`) and one-compiler.
* **x86_64.** gad, a native x86_64 Linux 7.0 kernel with no emulation: `check-x86_64-native.py --tier pr`,
  `check-complete-x86.py`, `check-native-clock-entropy.py`, `check-native-cdci.py`, `check-public-native-product.py`,
  main's `check-kototama-i64.py` (with this branch's complete compiler) and the new `check-b2-image.py` (with the
  complete compiler, as CI runs it).
* **Not run here:** `check-wasm32-browser.py`, because the x86_64 host has no Chrome. CI runs it.

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
