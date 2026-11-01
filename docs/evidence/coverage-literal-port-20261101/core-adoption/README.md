# AWAI-47 coverage literal core adoption (2026-11-01)

The `document-set-conj` seed core change is admitted by the Mac native full-compiler fixed point and the Linux ARM loaderless selfhost PR-tier bootstrap.

- Mac: `mac-core-adoption.json` reports `PASS_MAC_CORE_ADOPTION_FIXED_POINT`, with the changed 18-module core at G1=G2=G3.
- Linux ARM: `linux-selfhost-bootstrap.json` reports `PASS_LOADERLESS_SELFHOST_BOOTSTRAP`; the generated root reproduces the adoption image. The receipt records no reuse, C compiler/loader, JVM/Node/Graal fallback, or emulation.
- These results do not qualify exact-head hosted CI, cold C0, native CDCI/controller, public CLI, guest runtime, release, or performance.
