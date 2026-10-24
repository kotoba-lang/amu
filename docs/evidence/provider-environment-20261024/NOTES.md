# The launcher's provider environment on main 0007e50f (ADR 0371 step 6, JUN-344)

This branch adds one change to main (#1510): the launcher's fixed provider
environment. `MESA_SHADER_CACHE_DISABLE=true` and
`VK_LOADER_LAYERS_DISABLE=~all~` now sit in the launcher runtime text of
seed/76 and seed/77. That text is part of `seed/FULL-MANIFEST`, so the root,
the public x86_64 image (`bin/amu`, `native-product.json`) and this index are
regenerated. `current-scope.json` indexes them as main's
`native-cdci-20261023/current-scope.json` does.

## What changes, and what does not

* **Root F `688324e0…`** (from main's `f782f3f2…`). F1 = F2, and the root
  reproduces itself (`selfhost-bootstrap.py --tier pr`;
  `selfhost-bootstrap-aarch64-20261022/`).
* **Public image `011f1f84…`** (`bin/amu` and its two aliases), from main's
  `67476a25…`. `check-complete-x86.py` gives F1 = F2 = F3 = it, and
  `check-public-native-product.py` accepts the descriptor
  (`public-product.json`).
* **Unchanged:** the core source and container, the runtime runner
  (`80b757e1…`), the native controller (`39a50037…`) and the two CDCI gate
  images (`seed/cdci/policy.json`). The launcher text is appended only in
  the launcher format, so static images are unchanged.
  * `check-one-compiler.py` asserts the gate pins.
  * `check-static-launcher.py` checks the rest, with main's root as
    `--previous-root`: a static guest and the runner come out
    byte-identical.

## Where the checks ran

* **arm64.** podman machine (applehv, a native arm64 kernel; no emulation):
  the bootstrap twice, the static launcher and one-compiler.
* **x86_64.** gad, a native x86_64 Linux 7.0 kernel with no emulation:
  * `check-x86_64-native.py --tier pr` (X2, the 24 cases, and the x86_64
    static launcher receipt in `static-launcher-20261022/x86_64-linux.json`);
  * `check-complete-x86.py`;
  * `check-native-clock-entropy.py`;
  * `check-native-cdci.py`: 24 cases, 18 refusals, parent-death cleanup;
  * `check-public-native-product.py`.
* **Not run here:** `check-wasm32-browser.py`, because the x86_64 host has
  no Chrome. CI runs it.

## The provider route

Main's root refuses the provider's `--format platform-linked` build (`E2
unsupported target (only aarch64-macos)`). Main's AGENTS.md also excludes the
provider's qualifications from mandatory native CDCI. This branch therefore
keeps the gad launcher receipt (`gpu-provider-20261023/`) as historical: the
launcher, guest and provider were built by the root before #1510.

Exact-head PR CI and the merge are separate gates.
