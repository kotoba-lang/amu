# JUN-31: merged-tree fixed point of the full33 merge (2026-10-25)

`scripts/seed/selfhost-bootstrap.py --tier main` on the merged tree of
origin/main `dd7ba1877` (full33) into `hermes/jun31-seed-boot-ops-20261024`
(merge `9b3418ce4`; the root pin pair conflicted and main's `508fa92a` pair
was taken as placeholder at the merge — hand-merging the generated pair is not
an option). arm64 podman python:3.12-alpine (Linux 6.15.10-200.fc42.aarch64),
C-free, no emulation. 120 recorded steps, all ran:
`PASS_LOADERLESS_SELFHOST_BOOTSTRAP`. Raw receipt and per-step logs in
`run1/` in this directory.

* **Fixed point F1 = F2** byte-identical in two generations: 3,400,192 B,
  sha256 `ac3cf40ec99e45eaa26a2f18efa567a5c368462ee127b0585620b96c5e8bd537`
  (container `4ef3db19129e21ab…`, 3,102,819 B). F1-compile 102.5s, F2-compile
  102.8s. `rootReproduces: false` against the placeholder input root
  `508fa92a…` — expected: this run *measures* the new fixed point, it is not a
  reproduction of the placeholder. The pair is re-pinned to `ac3cf40e…` in
  commit `c237bedb9`; the reproduction run against that pin is
  [`../jun31-root-reproduces-20261025b/`](../jun31-root-reproduces-20261025b/).
* G1 = G2 = G3 (adoption image): native 2,588,088 B, sha256
  `813f660e3f364d7e0b25728d458d8d456b0870f1198f6c7df8c14c7a72764b98`;
  container `39627006848eae23…`, 2,588,115 B. gen1 producedBy F, gen2/gen3 by
  the runner — self-hosted generations agree.
* P packed: `2b6df97b221cc8d0e003d316d249e55f72a34a867fb35f63da576ff9b6c84f90`
  (2,884,096 B), extracts to the same native `813f660e…`.
* Linux selfhost closure S = S2 = 1,765,888 B, sha256
  `2cb6ebc0c6cb2657040e33c55c9e051de1a259253f0bd499d8039fe4bc5e4e2c`.
* Built runners: aarch64 runner `f30e807d…` (295,424 B), x86_64 compiler
  `ec7850ad…` (2,122,240 B), x86_64 runner `08cf188c…` (373,248 B) — built
  here, adopted by the x86 CI pipeline only after exact-head native Linux
  x86_64 qualification (see the blocker note in
  `../jun31-root-reproduces-20261025b/NOTES.md`).
* 24 runtime cases: 19 exit 0; 5 trap by design with exit 120
  (`vector-negative`, `vector-oob`, `string-oob`, `string-boundary`,
  `capability-denied`). `PASS_RUNTIME_BOUNDARY`: 175 named refusals,
  7 positives; capabilities granted 7 / refused 120.
* Hardening probes trap as designed: SIGSYS / SIGXCPU / SIGALRM / SIGSEGV,
  exit 120 (`seccompDefault` exit 0). Diagnostic probe refuses by name
  (`E2101 unknown or unsupported form 'nope-fn'`, exit 1); the packed-payload
  arity refusal `E7105 the packed payload's main must take no arguments` is
  among the named refusals.
* wasm32: 27 modules compiled, not executed (no Chromium on this host; the
  qualify-x86_64 job executes them).
* cCompilerOrLoader / JVMNodeOrGraalFallback / emulation: all false.
