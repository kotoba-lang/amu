# JUN-31: merged-tree fixed point measured (2026-10-24)

Merged origin/main (0486b715e, JUN-354) into hermes/jun31-seed-boot-ops-20261024
(merge commit 67f938f51). Conflict was exactly the root pin pair; main's pair
(482398a4) was taken as placeholder (hand-merging the generated pair is not an
option). Everything else merged clean.

`scripts/seed/selfhost-bootstrap.py --tier main` on the merged tree (arm64
podman python:3.12-alpine, C-free, no emulation; 120 steps) passed:
`PASS_LOADERLESS_SELFHOST_BOOTSTRAP main F fc48f9faeedcc8a7 root differs
(re-pin to F2) adoption image 24 cases wasm32-browser compiled`.

* Merged-tree fixed point: **F1 = F2 = `fc48f9fa…`** (3,293,696 B; container
  `d2b5363b…`, 3,057,811 B) — distinct from both parents' pins (branch
  `86da3c52`, main `482398a4`), as expected for the combined closure.
* rootReproduces: false against the placeholder pin (expected: re-pin to F2
  is the next step).
* Linux selfhost closure S = `43313cde…`; core route G1 = G2 = G3 = `6d94e9b5…`
  (the adoption image, unchanged); 24 runtime cases, runtime boundary corpus
  and hardening probes pass; wasm32 modules compiled (no browser on host).

Raw receipt: `selfhost-bootstrap.json` in this directory. Pending (next tick):
re-pin `seed/bootstrap/aarch64-linux-static-root.{elf,json}` to F2 = `fc48f9fa`,
then the rootReproduces re-measurement, then push and PR #1561 mergeable.
