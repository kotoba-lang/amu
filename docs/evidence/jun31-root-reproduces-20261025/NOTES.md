# JUN-31: rootReproduces true against the re-pinned F2 root (2026-10-25)

The re-measurement promised by `../jun31-merge-fixpoint-20261024/NOTES.md`:
`scripts/seed/selfhost-bootstrap.py --tier main` on the tree of the re-pin
commit (root pair `482398a4`/`86da3c52` -> `fc48f9fa`), arm64 podman
python:3.12-alpine (Linux 6.15.10-200.fc42.aarch64), C-free, no emulation.
118 recorded steps, all ran: `PASS_LOADERLESS_SELFHOST_BOOTSTRAP`.

* **rootReproduces: true.** F1's image is byte-identical to the re-pinned root
  in one generation: 3,293,696 B, sha256 `fc48f9faeedcc8a78d0df70a070e3639c0b94c690a82490a9be3b7072b8ad195`
  (F1 container `d2b5363b…`, 3,057,811 B). F1-compile 100.9s, F1-pack 1.8s.
* G1 = G2 = G3 (adoption image): native 2,576,096 B, sha256
  `6d94e9b5a1c0241fb28139c9e0a6a2dd373655c74ad2fc1f6e1659988a838b54`;
  container `086f85db…`. gen1 producedBy F (91.5s), gen2/gen3 by the runner
  (91.4/91.3s) — self-hosted generations agree.
* P packed: image 2,810,368 B (`7d6b69f0…`), same native `6d94e9b5…`;
  Linux selfhost closure S = 1,663,488 B, sha256 `43313cde…`.
* 24 runtime cases pass; `PASS_RUNTIME_BOUNDARY` (175 named refusals, 7
  positives; capabilities granted 7 / refused 120); hardening probes trap as
  designed (SIGSYS / SIGXCPU / SIGALRM / SIGSEGV, exit 120); diagnostic probe
  refuses by name (`E2101 unknown or unsupported form 'nope-fn'`, exit 1).
* wasm32: 27 modules compiled, not executed (no Chromium on this host; the
  qualify-x86_64 job executes them).
* cCompilerOrLoader / JVMNodeOrGraalFallback / emulation: all false.

Raw receipt: `selfhost-bootstrap.json` (132,288 B, sha256
`8f9a3fcc5e053e2355b211c308ce1705b4d447e7d551b8fc197863f86a2c1135`) plus the
per-step stdout/stderr logs in `raw/` in this directory.

CI after push (run 40104099681): bootstrap-arm64 PASS; **qualify-x86_64 FAIL**
at `check-aiueos-image-native.py:159` —
`AssertionError: ('object bytes changed', 'probe')`. The complete-x86
fixed-point producers (F2/F3) disagree with the committed baseline `bin/amu`
on object fixture bytes. The `probe` fixture is trivial (`:i64 42`, no
kernel-out) and is just the first failing case: 228455e7b's xk-lib stub change
(XK-INTR-N 4 -> 6) changes every object image's bytes, so `bin/amu` +
`native-product.json` need re-adoption to the new x86 fixed point in this same
PR (the complete-x86 pipeline asserts native Linux x86_64; no emulation).
Until then PR #1561 stays unmerged. M2 (desktop input D1/D3) remains blocked
on owner judgment (ADR-0180/0131); JUN-31 acceptance NOT MET (M1 only).
