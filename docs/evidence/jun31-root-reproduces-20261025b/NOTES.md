# JUN-31: rootReproduces true against the re-pinned merged-tree root (2026-10-25)

The re-measurement promised by the re-pin commit `c237bedb9` and
`../jun31-merge-fixpoint-20261025/NOTES.md`: `scripts/seed/selfhost-bootstrap.py
--tier main` on the tree of the re-pin commit (root pair placeholder
`508fa92a` -> measured fixed point `ac3cf40e`), arm64 podman
python:3.12-alpine (Linux 6.15.10-200.fc42.aarch64), C-free, no emulation.
118 recorded steps, all ran: `PASS_LOADERLESS_SELFHOST_BOOTSTRAP`.

* **rootReproduces: true.** F1's image is byte-identical to the re-pinned root
  in one generation: 3,400,192 B, sha256
  `ac3cf40ec99e45eaa26a2f18efa567a5c368462ee127b0585620b96c5e8bd537`
  (container `4ef3db19129e21ab…`, 3,102,819 B). F1-compile 102.0s, F1-pack
  2.0s. This supersedes `../jun31-root-reproduces-20261025/` (which measured
  the pre-full33 pin `fc48f9fa` of merge `67f938f51`; that pin is superseded
  by this merged-tree pin and stays in history).
* G1 = G2 = G3 (adoption image): native 2,588,088 B, sha256
  `813f660e3f364d7e0b25728d458d8d456b0870f1198f6c7df8c14c7a72764b98`;
  container `39627006848eae23…`. Packed P
  `2b6df97b221cc8d0e003d316d249e55f72a34a867fb35f63da576ff9b6c84f90`
  (2,884,096 B) extracts to the same native. Linux selfhost closure
  S = S2 = `2cb6ebc0c6cb2657…` (1,765,888 B).
* 24 runtime cases: 19 exit 0, 5 trap by design with exit 120;
  `PASS_RUNTIME_BOUNDARY` (175 named refusals, 7 positives; capabilities
  granted 7 / refused 120); hardening probes trap as designed (SIGSYS /
  SIGXCPU / SIGALRM / SIGSEGV, exit 120); diagnostic probe refuses by name
  (`E2101`, exit 1), `E7105` among the named refusals.
* wasm32: 27 modules compiled, not executed (no Chromium on this host; the
  qualify-x86_64 job executes them).
* cCompilerOrLoader / JVMNodeOrGraalFallback / emulation: all false.

Raw receipt: `selfhost-bootstrap.json` (264,303 B, sha256
`c72e04cb10fca8689ca36ea573cb49ceba14c0c2143a810b9c7617de192d0b78`) plus the
per-step stdout/stderr logs in `raw/` in this directory.

Open blocker (unchanged): **qualify-x86_64 FAIL** at
`check-aiueos-image-native.py:159` — `AssertionError: ('object bytes changed',
'probe')`. The complete-x86 fixed-point producers disagree with the committed
baseline `bin/amu` on object fixture bytes; `bin/amu` + `native-product.json`
need re-adoption to the new x86 fixed point from the `x86_64-native-receipt`
CI artifact (native Linux x86_64, no emulation) in this same PR. Until then
PR #1561 stays unmerged. M2 (desktop input D1/D3) remains blocked on owner
judgment (ADR-0180/0131); JUN-31 acceptance NOT MET (M1 only).
