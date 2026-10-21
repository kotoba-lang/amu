# Seed tools in Kotoba (JUN-243)

Owner decision (JUN-243): "sh に相当するものも kotoba で". The seed's bootstrap
tooling is Kotoba, compiled by the committed seed and run under the pinned C
loader. No `.sh` file remains besides main's reviewed native gate
(`scripts/seed/check-native-source-recovery.sh`, the `native-gates` allowlist
of `scripts/check-workflows.cljk`).

## The tools

| file | replaces | what it does |
| --- | --- | --- |
| `seed/tools/lib.kotoba` | `scripts/seed/lib.sh` | argv, stdout/stderr, files (wire 35: read, write, append with the token-safe split, exists, mkdir), `:process/spawn` (wire 20, TAB-separated argv), SHA-256 of text (wire 3) and of binary files (FIPS 180-4 in Kotoba: wire 3 takes a text), record/manifest line helpers |
| `seed/tools/bootstrap.kotoba` | `scripts/seed/bootstrap.sh`, the node-free steps of `scripts/seed/build.sh` | R0 -> every `seed/rungs/*.record` in lineage order (unity from git, bridge, seed-1, seed-2, every recorded hash, size and fixed point), then the head unity checked against the adoption receipt; `--head` (A/B/C), `--upto`, `--commit`, `--work`, `--image` |
| `seed/tools/package.kotoba` | `scripts/seed/package.sh` | a seed as a KEXE_EMBEDDED command: header with the code array (byte-identical to `xxd -i`) + `cc` |
| `seed/tools/scan.kotoba` | the reader helpers of `scripts/seed/r6_scan.py`, `reach-twins.py`, `scripts/selfhost-wall/reach-list.py` | ns form, `#?`/`#?@` resolution (first `:kotoba`/`:default`), requires, the reach-list block and names; UTF-8 byte offsets kept on code point boundaries |
| `seed/tools/selfbuild.kotoba` | `scripts/seed/selfbuild.sh --no-link`, `r6-scan.sh`, `selfbuild-inputs.sh`, `farm-from-lock.py`, `reach-twins.py`, `selfbuild.py` (summary) | JUN-202, gate S2: farm from the lock with `git restore`, reach list, reach-twins, dependency order, per-module seed compile (OK / REFUSED / TRAP / BLOCKED), `report.txt`, `selfbuild.edn`, `inputs.txt` (seed/README.md "Selfbuild scan") |
| `seed/tools/image.kotoba` | `scripts/seed/image/front.sh` | the front object dir of the unified image (`front`); stops at the first refusal |

Entry commands (no script file): `seed/README.md`, section "Seed lineage
bootstrap". The process tree is the loader (supervisor and guest), `cc` (once,
for `seed/bootstrap/seed-loader-v11.c`), `git` and the lineage loader running
each seed. The loader gives a spawned child at most 10 s of wall time and
16 KiB of stdout: every lineage compile fits (r6n: about 1.3 s), file contents
go through files (`git restore --source=<commit> --worktree` into a scratch
work tree, never the index), not stdout. The adopted compiler's own
three-generation self-build (about a minute per compile) does not fit the
spawn budget, so those generations stay plain loader commands that the tool
checks (`--image`).

## Verified (2026-10-21, the owner's Mac, macOS arm64, branch head 7d0d8b7a)

The `seed/README.md` commands, with `--work build/seed-boot-k2` (and that loader
path in the spawn grant) so the earlier `build/seed-boot` stays untouched:

```
bootstrap: loader da5d6e742862 (seed/bootstrap/seed-loader-v11.c), work dir .../build/seed-boot-k2
bootstrap: R0 seed (committed)  187186 bytes  sha256 fe2c20aefa02f4f91f5b8394c8ad8a31e75325242050aaf7964b0eab73a39dd6
  ... r0 r1 r2 r3 r4 r4b r5a r5b r6a r6b r6c r6c-kir r6d .. r6m: every FIXED POINT == record ...
bootstrap: r6n bridge (unity of 1cf67ec9a)  856728 bytes  sha256 f11b6ce3afb5a9912f23cc4c5275cfce5f82d61c14504561201d374bc5721ce9
bootstrap: r6n seed-1  860296 bytes  sha256 b3f46d32a01780fe26e63cda2bc3b402d2bdfbadb09474c48105181529fa467a
bootstrap: r6n seed-2 (by seed-1)  860296 bytes  sha256 b3f46d32a01780fe26e63cda2bc3b402d2bdfbadb09474c48105181529fa467a
bootstrap: r6n FIXED POINT == record b3f46d32a01780fe
bootstrap: head unity (working tree): 41811 lines, sha256 a6906f3b48825aeca44607de5bd4c67305e2ef8bc9ac4cbef3074236f4b2ae0d
bootstrap: head unity == seed/adoption-20261017.json sourceUnitySHA256
bootstrap: OK                                    (exit 0, 34 s wall for the whole lineage)
```

Process tree under the tool's loader (sampled every 50 ms for the whole run):
`loader` (its guest), `clang` + `ld` (from `/usr/bin/cc`, once), `git`,
`kexe-loader-v11`; nothing else (no sh/zsh, node, nbb, java, python). The
adopted head commands then gave G1 = G2 = G3 = `b10e381344a1f5a8b82cac981c0011bd20ecbcc4b48dd5f5dce97364c74e8a00`
(`--image`: == nativeImageSHA256), about 80 s per generation. `package.kotoba`
packaged the r6n seed (code sha256 `b3f46d32...`) into a command that runs.

## Follow-ups (Linear JUN-243)

Ported (JUN-202): the selfbuild scan (`selfbuild.sh --no-link`, `r6-scan.sh`,
`selfbuild-inputs.sh`, with `farm-from-lock.py`, `reach-twins.py` and
`selfbuild.py`, which are removed) as `seed/tools/selfbuild.kotoba`, checked
module for module against the old route (seed/README.md "Selfbuild scan"), and
`image/front.sh` as `seed/tools/image.kotoba front`.

Still pending: the selfbuild LINK step with `large-m.sh` (`scripts/seed/large_m.py`
stays until then), the three-generation image rebuild (`image/rebuild.sh`) and
the native launcher (`launcher/build.sh`, `test.sh`, with `seed/split/gen-split.py`
and `seed/amu-main/patch-split.py`). The front dir they start from cannot be
built from the current integration sources (the check / compile closures are
not seed-compilable yet), so they are not ported blind. Their last versions are
in git history (`15626731^`).

## Classification of the 173 `.sh` files that were not on main

Counts: KEEP-PORT 4 (ported, then deleted), DELETE with a port follow-up 8,
DELETE 161. No workflow or `package.json` script ran any of them; the
remaining mentions in source are comments.

| file | verdict | reason |
| --- | --- | --- |
| `scripts/seed-backend/build-wrapper.sh` | DELETE | `--backend seed` test/embench driver of the nbb route (ADR 0365); historical, no caller |
| `scripts/seed-backend/embench.sh` | DELETE | `--backend seed` test/embench driver of the nbb route (ADR 0365); historical, no caller |
| `scripts/seed-backend/test.sh` | DELETE | `--backend seed` test/embench driver of the nbb route (ADR 0365); historical, no caller |
| `scripts/seed/bootstrap-r1.sh` | DELETE | measurement/experiment or superseded chain helper; results are in docs/ and the records |
| `scripts/seed/bootstrap.sh` | KEEP-PORT | ported to seed/tools/bootstrap.kotoba (lineage r0->rN with every record hash, bridges, head unity, --head A/B/C, --upto, --commit) |
| `scripts/seed/build.sh` | KEEP-PORT | its node-free steps (unity, seed-N, lineage, fixed point) are seed/tools/bootstrap.kotoba; its stage-0 steps used the removed JVM image |
| `scripts/seed/ck-gate.sh` | DELETE | rung gate driver (G1-G5, GR, unit, golden); its results are recorded in seed/rungs/*.record; several need the removed stage-0 |
| `scripts/seed/corpus.sh` | DELETE | rung gate driver (G1-G5, GR, unit, golden); its results are recorded in seed/rungs/*.record; several need the removed stage-0 |
| `scripts/seed/embench-rungs.sh` | DELETE | measurement/experiment or superseded chain helper; results are in docs/ and the records |
| `scripts/seed/embench.sh` | DELETE | measurement/experiment or superseded chain helper; results are in docs/ and the records |
| `scripts/seed/emit/build-one.sh` | DELETE | spike/refactor-port helper of a finished agent wave; no caller |
| `scripts/seed/emit/same.sh` | DELETE | spike/refactor-port helper of a finished agent wave; no caller |
| `scripts/seed/emit/test.sh` | DELETE | spike/refactor-port helper of a finished agent wave; no caller |
| `scripts/seed/float-diff.sh` | DELETE | measurement/experiment or superseded chain helper; results are in docs/ and the records |
| `scripts/seed/float-interp.sh` | DELETE | measurement/experiment or superseded chain helper; results are in docs/ and the records |
| `scripts/seed/float-prog.sh` | DELETE | measurement/experiment or superseded chain helper; results are in docs/ and the records |
| `scripts/seed/frontsrc/build-one-src.sh` | DELETE | spike/refactor-port helper of a finished agent wave; no caller |
| `scripts/seed/frontsrc/test.sh` | DELETE | spike/refactor-port helper of a finished agent wave; no caller |
| `scripts/seed/fuel.sh` | DELETE | measurement/experiment or superseded chain helper; results are in docs/ and the records |
| `scripts/seed/g1.sh` | DELETE | rung gate driver (G1-G5, GR, unit, golden); its results are recorded in seed/rungs/*.record; several need the removed stage-0 |
| `scripts/seed/g2.sh` | DELETE | rung gate driver (G1-G5, GR, unit, golden); its results are recorded in seed/rungs/*.record; several need the removed stage-0 |
| `scripts/seed/g3.sh` | DELETE | rung gate driver (G1-G5, GR, unit, golden); its results are recorded in seed/rungs/*.record; several need the removed stage-0 |
| `scripts/seed/g4.sh` | DELETE | rung gate driver (G1-G5, GR, unit, golden); its results are recorded in seed/rungs/*.record; several need the removed stage-0 |
| `scripts/seed/gates.sh` | DELETE | rung gate driver (G1-G5, GR, unit, golden); its results are recorded in seed/rungs/*.record; several need the removed stage-0 |
| `scripts/seed/gen-ns.sh` | DELETE | rung gate driver (G1-G5, GR, unit, golden); its results are recorded in seed/rungs/*.record; several need the removed stage-0 |
| `scripts/seed/golden.sh` | DELETE | rung gate driver (G1-G5, GR, unit, golden); its results are recorded in seed/rungs/*.record; several need the removed stage-0 |
| `scripts/seed/gr-r5.sh` | DELETE | rung gate driver (G1-G5, GR, unit, golden); its results are recorded in seed/rungs/*.record; several need the removed stage-0 |
| `scripts/seed/gr.sh` | DELETE | rung gate driver (G1-G5, GR, unit, golden); its results are recorded in seed/rungs/*.record; several need the removed stage-0 |
| `scripts/seed/image/compare-embench.sh` | DELETE | frozen-runner Embench comparison (measurement); no caller |
| `scripts/seed/image/front.sh` | DELETE (port follow-up) | front object dir of the unified amu image; Kotoba port is a JUN-243 follow-up |
| `scripts/seed/image/rebuild.sh` | DELETE (port follow-up) | three-generation rebuild of the unified amu image; Kotoba port is a JUN-243 follow-up |
| `scripts/seed/io_bytes_check.sh` | DELETE | rung gate driver (G1-G5, GR, unit, golden); its results are recorded in seed/rungs/*.record; several need the removed stage-0 |
| `scripts/seed/io_check.sh` | DELETE | rung gate driver (G1-G5, GR, unit, golden); its results are recorded in seed/rungs/*.record; several need the removed stage-0 |
| `scripts/seed/kir-gate.sh` | DELETE | rung gate driver (G1-G5, GR, unit, golden); its results are recorded in seed/rungs/*.record; several need the removed stage-0 |
| `scripts/seed/kir-stats.sh` | DELETE | measurement/experiment or superseded chain helper; results are in docs/ and the records |
| `scripts/seed/large-m.sh` | DELETE (port follow-up) | large-M seed profile used by selfbuild link; Kotoba port is a JUN-243 follow-up |
| `scripts/seed/launcher/build.sh` | DELETE (port follow-up) | native amu launcher build (python split + cc); Kotoba port is a JUN-243 follow-up |
| `scripts/seed/launcher/test.sh` | DELETE (port follow-up) | native launcher gate, goes with launcher/build.sh; JUN-243 follow-up |
| `scripts/seed/lexread.sh` | DELETE | rung gate driver (G1-G5, GR, unit, golden); its results are recorded in seed/rungs/*.record; several need the removed stage-0 |
| `scripts/seed/lib.sh` | KEEP-PORT | ported to seed/tools/lib.kotoba + bootstrap.kotoba (seed_loader = the cc step, seed_run = the loader spawn, seed_manifest, seed_rung_records); its stage-0 helpers served the removed JVM route |
| `scripts/seed/link-capacity.sh` | DELETE | measurement/experiment or superseded chain helper; results are in docs/ and the records |
| `scripts/seed/lw-corpus-oracle.sh` | DELETE | rung gate driver (G1-G5, GR, unit, golden); its results are recorded in seed/rungs/*.record; several need the removed stage-0 |
| `scripts/seed/lw-gate.sh` | DELETE | rung gate driver (G1-G5, GR, unit, golden); its results are recorded in seed/rungs/*.record; several need the removed stage-0 |
| `scripts/seed/no-host-processes.sh` | DELETE | rung gate driver (G1-G5, GR, unit, golden); its results are recorded in seed/rungs/*.record; several need the removed stage-0 |
| `scripts/seed/oracle.sh` | DELETE | rung gate driver (G1-G5, GR, unit, golden); its results are recorded in seed/rungs/*.record; several need the removed stage-0 |
| `scripts/seed/package.sh` | KEEP-PORT | ported to seed/tools/package.kotoba (KEXE_EMBEDDED header + cc; the code array is byte-identical to xxd -i) |
| `scripts/seed/prove-100.sh` | DELETE | measurement/experiment or superseded chain helper; results are in docs/ and the records |
| `scripts/seed/r6-diff.sh` | DELETE | measurement/experiment or superseded chain helper; results are in docs/ and the records |
| `scripts/seed/r6-scan.sh` | DELETE (port follow-up) | per-module separate-mode scan used by selfbuild; Kotoba port is a JUN-243 follow-up |
| `scripts/seed/refactor/all.sh` | DELETE | spike/refactor-port helper of a finished agent wave; no caller |
| `scripts/seed/refactor/apply-cases.sh` | DELETE | spike/refactor-port helper of a finished agent wave; no caller |
| `scripts/seed/refactor/apply-diff.sh` | DELETE | spike/refactor-port helper of a finished agent wave; no caller |
| `scripts/seed/refactor/build-image.sh` | DELETE | spike/refactor-port helper of a finished agent wave; no caller |
| `scripts/seed/refactor/diff.sh` | DELETE | spike/refactor-port helper of a finished agent wave; no caller |
| `scripts/seed/refactor/lib.sh` | DELETE | spike/refactor-port helper of a finished agent wave; no caller |
| `scripts/seed/refactor/split-cases.sh` | DELETE | spike/refactor-port helper of a finished agent wave; no caller |
| `scripts/seed/refactor/split-diff.sh` | DELETE | spike/refactor-port helper of a finished agent wave; no caller |
| `scripts/seed/refactor/verify-diff.sh` | DELETE | spike/refactor-port helper of a finished agent wave; no caller |
| `scripts/seed/rung-report.sh` | DELETE | rung gate driver (G1-G5, GR, unit, golden); its results are recorded in seed/rungs/*.record; several need the removed stage-0 |
| `scripts/seed/seed-cc.sh` | DELETE | measurement/experiment or superseded chain helper; results are in docs/ and the records |
| `scripts/seed/selfbuild-inputs.sh` | DELETE (port follow-up) | durable selfbuild inputs (git revs + seed17 snapshot); Kotoba port is a JUN-243 follow-up |
| `scripts/seed/selfbuild.sh` | DELETE (port follow-up) | selfbuild scan driver (milestone f); needs python summaries and kotoba-lang inputs; Kotoba port is a JUN-243 follow-up |
| `scripts/seed/t1_jvm.sh` | DELETE | measurement/experiment or superseded chain helper; results are in docs/ and the records |
| `scripts/seed/t2_t3.sh` | DELETE | measurement/experiment or superseded chain helper; results are in docs/ and the records |
| `scripts/seed/unit-all.sh` | DELETE | rung gate driver (G1-G5, GR, unit, golden); its results are recorded in seed/rungs/*.record; several need the removed stage-0 |
| `scripts/seed/unit.sh` | DELETE | rung gate driver (G1-G5, GR, unit, golden); its results are recorded in seed/rungs/*.record; several need the removed stage-0 |
| `scripts/seed/walls/probe.sh` | DELETE | spike/refactor-port helper of a finished agent wave; no caller |
| `scripts/seed/walls/s0j.sh` | DELETE | spike/refactor-port helper of a finished agent wave; no caller |
| `scripts/selfhost-codemod/codemod.sh` | DELETE | codemod/split spike on the nbb host route; historical, no caller |
| `scripts/selfhost-codemod/diff-suite.sh` | DELETE | codemod/split spike on the nbb host route; historical, no caller |
| `scripts/selfhost-codemod/kotoba-route-check.sh` | DELETE | codemod/split spike on the nbb host route; historical, no caller |
| `scripts/selfhost-codemod/pipeline.sh` | DELETE | codemod/split spike on the nbb host route; historical, no caller |
| `scripts/selfhost-codemod/test.sh` | DELETE | codemod/split spike on the nbb host route; historical, no caller |
| `scripts/selfhost-split/run-split.sh` | DELETE | codemod/split spike on the nbb host route; historical, no caller |
| `scripts/selfhost-wall/abort-diff.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/ana-diff.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/analyze-memory.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/bootstrap-boundary.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/boundary-gate.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/build-native.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/bytes-cap.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/case-diff.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/check-native.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/check-one.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/ds-diff.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/ds-gen.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/ds-pass-build.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/e2e-diff.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/front-native.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/golden-cache.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/golden-wrap.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/guest-run.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/hashcons-ab.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/hashcons-test.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/ie-diff.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/kir-backend-diff.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/ledger.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/native-gaps.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/no-host-processes.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/pass-driver.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/run-verify.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/scan-cached-selftest.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/scan-cached.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/scan.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/tm-diff.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/vx-diff.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/wall-cache-conformance.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/selfhost-wall/wall-cache-lib.sh` | DELETE | selfhost wall experiment (host vs native diffs, caches); historical, no caller |
| `scripts/test-refactor.sh` | DELETE | end-to-end refactor check through bin/amu on nbb; no workflow or npm script runs it |
| `seed/amu-front/build.sh` | DELETE | launcher-era builder/parity driver over python helpers; superseded by the adopted seed route; no caller |
| `seed/amu-front/corpus.sh` | DELETE | launcher-era builder/parity driver over python helpers; superseded by the adopted seed route; no caller |
| `seed/amu-front/kir-dump-staged.sh` | DELETE | launcher-era builder/parity driver over python helpers; superseded by the adopted seed route; no caller |
| `seed/amu-main/build-k.sh` | DELETE | launcher-era builder/parity driver over python helpers; superseded by the adopted seed route; no caller |
| `seed/amu-main/build.sh` | DELETE | launcher-era builder/parity driver over python helpers; superseded by the adopted seed route; no caller |
| `seed/amu-main/parity.sh` | DELETE | launcher-era builder/parity driver over python helpers; superseded by the adopted seed route; no caller |
| `seed/amu-main/usage-parity.sh` | DELETE | launcher-era builder/parity driver over python helpers; superseded by the adopted seed route; no caller |
| `seed/tests/check-cli/args.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/check-cli/image.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/checkfull/build.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/checkfull/corpus.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/checkfull/diff.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/checkfull/graph.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/checkfull/refactor-writesep.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/cli-support/run.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/compile-cli/refusals.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/compile-cli/run.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/compile-pairs/probe.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/compile-twin/run.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/f64/test.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/kgraph-capacity/census.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/kgraph-capacity/check.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/kgraph-capacity/loader-variant.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/kgraph-capacity/rerun.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/kir/census.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/kir/flip.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/kir/merge.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/kir/writesep/run.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/native-admission/run.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/r4b/check-caps.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r5/check-r5.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r5/oracle-r5.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r5a/gate-r5a.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r5a/sep-r5a.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r5b/gate-r5b.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r5b/run-r5b.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r6a/check-r6a.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r6a/gate-r6a.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r6a/oracle-r6a.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r6b/check-r6b.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r6b/gate-r6b.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r6c/check-r6c.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r6c/gate-r6c.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r6d/check-r6d.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r6d/gate-r6d.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r6f/check-r6f.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r6f/gate-r6f.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r6h/gate-r6h.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r6i/check-r6i.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r6i/gate-r6i.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r6j/gate-r6j.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r6k/gate-r6k.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r6l/gate-r6l.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r6m/gate-r6m.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r6m/seedc.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/r6n/gate-r6n.sh` | DELETE | per-rung gate/oracle driver; the rung is frozen in seed/rungs/*.record (gate lines) and the seed-r* tags |
| `seed/tests/t3/nbbc.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/text/check-text.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/wall2/check-cases.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/wall2/check-run.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/wall2/effects-run.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/wall2/graph-run.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/wall2/link-run.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
| `seed/tests/wall2/run.sh` | DELETE | one-off test driver of a finished measurement (checkfull/kir/kgraph/wall era); no caller |
