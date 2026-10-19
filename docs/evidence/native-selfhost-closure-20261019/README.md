# JUN-11 selfhost closure — build provenance, execution results, known refusals (2026-10-19)

Records JUN-11 completion condition 3 for the Kotoba-core selfhost closure
(59-module native CLI): build provenance, measured execution results, and the
explicit list of known refusals / unsupported scope. Completion condition 1
(Native-built AMU compiles itself from a pinned source graph) is met and
recorded here; condition 2 (native runtime semantic parity vs the host
runtime contract) is **open** — see the scoreboard.

All numbers below were read from the build `report.json` files or from actual
command stdout on 2026-10-18/19. Nothing here is estimated.

## 1. Build provenance (59-module closure, entry `kotoba.compiler.selfhost-cli`)

| build | role | containerSha256 | nativeImageSha256 | mainOffset | bytes (container / native) |
|---|---|---|---|---|---|
| `native-cli-current-g3-r19cli` | G1 (seed-unity product) | `fe93aa0327b061224c8cb11b4410e97221c1100adc633b4889a65321e1fbf666` | `e540de37f9524dbc654fccc80a4eb49049b3600a48a45c802e862ec9d15355ff` | 6,708,500 | 6,730,513 / 6,730,480 |
| `native-cli-selfrebuild-r19cli` | G2 (G1 compiles the closure) | `357e0a81d315290632f5f3b24a91dbc241258127cb0f967f18afb2d670996dc1` | `2b2a29c25f2b54e020c9add0009b6faa2c443101de230722918a6a0fbfbf86c5` | 6,725,620 | 6,747,793 / 6,747,760 |
| `native-cli-selfrebuild-r19cli-g2` | G3 (G2 compiles the closure) | `357e0a81d315290632f5f3b24a91dbc241258127cb0f967f18afb2d670996dc1` | `2b2a29c25f2b54e020c9add0009b6faa2c443101de230722918a6a0fbfbf86c5` | 6,725,620 | 6,747,793 / 6,747,760 |

- **G2 = G3 byte-identical** (container and native): self-rebuild fixed point.
  Re-executed independently on 2026-10-19 (`verify_native_cli_selfrebuild_r19cli_g2.py`,
  exit 0): `g2EqualsG3: true`, `g2EqualsG3Container: true`.
- **G1 ≠ G2** — known form (the fixed point holds from gen 2), unchanged since r16cli.
- The G1 driver run completed `modules` → `compile` × 59 → `link` → `extract-native`
  in one pass (resumedSkips = 0); closure set/order/path equal the r19cli build report.
- Reproduce: `python3 build_native_cli_selfrebuild_r19cli.py` then
  `python3 build_native_cli_selfrebuild_r19cli_g2.py`, then
  `python3 verify_native_cli_selfrebuild_r19cli_g2.py` (all under
  `kotoba-core-selfhost-refactor-20261017/artifacts/`).

## 2. Pinned source graph verification (self-product, G2 image)

Re-verified 2026-10-19 (exit 0, `identical: true`):

- 59 pins, root `kotoba.compiler.selfhost-cli`; every block CID self-checked
  (CIDv1 raw 0x55 / sha256 0x12 0x20 / base32, per `native_project_files.kotoba`).
- `modules` rc 0 (59) · `check-entry` rc 0 (`semantic ok: entry=kotoba.compiler.selfhost-cli dependency-sources=58`).
- 4 negative probes rc 65 with the same refusal text as G1 (tampered block,
  missing block, missing pin, unpinned root).
- Unpinned module enumeration: 59 lines, sha256
  `2b4dfd6bf3f498999c96ab5b06cd793bc38b1daa362376311b7662549f1f6f07`,
  byte-identical across G1/G2.

JUN-11 completion condition 1 — *"Native-built AMU が pinned source graph から
自身を compile できる"* — is therefore met and reproducible from this record.

## 3. Program codegen (measured, G2)

- aarch64 program codegen 4/4: the x86 evidence suite scalars (answer /
  subtract / quot-neg / bits) compiled with `compile --target aarch64-macos`
  + `extract-native --symbol main` are byte-identical to the suite's
  `aarch64Reference.nativePin` (answer = 12 bytes `5a39545c…`), deterministic
  across two runs. Generation-independent codegen.
- `--emit-module` (decimal-bits module object): rc 0 twice, byte-identical.
- Probe: `probe_codegen_matrix_r19cli_g2.py` → `native-cli-codegen-matrix-r19cli-g2/report.json`.

## 4. Type/refinement regression gate (10 fixtures, run 2026-10-19 on r19cli)

Measured with `jun11-fixture-tick33/run_fixture.py r19cli <entry>`; identical to
the r15unann baseline (2026-10-18):

| fixture | rc | note |
|---|---|---|
| unann_form / unann_i64 | 0 | cross-module unannotated params reach refinement (stderr empty) |
| consumer | 0 | imported-param gate regression fixed at r15unann, still fixed |
| same_unann_form / same_unann_i64 / same_unann_three / nested_unann_form | 0 | |
| badarity | 65 | original arity refusal: `native_import_stub_0 takes 2 arguments; got 1` |
| cross_caller / cross_caller_rev | 65 | `parameter xs of two is unannotated and its uses disagree … [xs at 19:8] / [xs at 13:8]` |

consumer / badarity / cross_caller / cross_caller_rev logs are byte-identical to
the r12useattr baselines apart from the `BUILD=` header (diff 0 lines).

## 5. Known refusals / unsupported scope (explicit)

1. **Targets**: the seed emission gate accepts `aarch64-macos` only.
   `x86_64-linux`, `x86_64-aiueos-kernel-v1`, `wasm32`, `wasm`, `js` are refused
   (`seed: E2 unsupported target (only aarch64-macos)`, rc 1, no artifact) even
   though the names are registered in `target_names` (JUN-30 registration done
   in this tree; the emitter gate still refuses).
2. **ELF64 emitter** exists only in `seed/70-x86_64-linux.kotoba` (a separate
   entry flavor, outside the unity MANIFEST; project inputs are refused there).
   Not reachable from the combined CLI. JUN-19/JUN-29 path.
3. **WASM emitter**: absent from the 59-module closure (frontend name mentions
   only). The JUN-11 condition-2 comparison of WASM output against the host
   runtime contract therefore stays open until an emitter lands.
4. **Cross-module parameter disagreement** is a hard refusal (rc 65,
   `annotate xs`) — intended, not a bug; refinement resolves unannotated
   params only when all uses agree.
5. **Bootstrap trust boundary unchanged**: the x86-64 payload still runs through
   the trusted C loader (`trustedCLoader: true`); C-free seed runner is JUN-29.
6. **Runtime semantic parity (JUN-11 condition 2) is open**: reader / evaluator /
   policy / capability / effect / WASM emitter vs the host runtime contract is
   not yet compared by execution (measurement in progress; the WIP host
   `runtime.cljk` does not load on the host because `kotoba.runtime.reader-depth`
   exists only as `.kotoba`).
7. **This closure is source-built evidence only from the pinned graph**; product
   wide selfhost and Q9 admission are not claimed.

## 6. WIP status of these sources

The selfhost sources behind this record are local work-in-progress across the
selfhost worktrees (amu / kotoba-runtime / artifact-core / kotoba-hir /
kotoba-text + build overlays) and are not yet landed to their repos' default
branches. This evidence file is the first landed artifact of the series; treat
the closure provenance above as the reference for the landing PRs that follow.
