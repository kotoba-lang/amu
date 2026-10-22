# ADR 0370: The Embench-measured compiler lineage is the compiler core

Date: 2026-10-22
Status: Accepted owner direction; whole native product qualification remains open

## Decision

Use the adopted Kotoba compiler in `seed/MANIFEST` as the implementation core
for Amu selfhost and public `amu` / `kotoba compile`. Grow that same frontend,
checking, lowering, optimizer and backend lineage to cover the whole product.
Integrate necessary project resolution, admission, packaging and CLI behavior
around it without introducing a second semantic compiler or an optional
benchmark-only path. Preserve the complete public contracts and named refusals.

Review, repair and merge this core integration before unrelated features or
new performance experiments. Preserve existing worktrees, stashes and history.
Amu and other execution foundations retain their separate repositories.
Disabled Actions remain disabled.

This supersedes the integration branch's historical
[ADR 0365](https://github.com/kotoba-lang/amu/blob/89bbf9244ab71c9a332c28edd8d79242e052422f/docs/adr/0365-opt-in-seed-backend-on-the-native-route.md)
optional seed / machine-ir fallback as the end-state design, and
[ADR 0366](https://github.com/kotoba-lang/amu/blob/89bbf9244ab71c9a332c28edd8d79242e052422f/docs/adr/0366-nbb-product-path-reduction-native-check-route-and-one-packaged-entry.md)'s
hosted command selection. They remain preserved in Git history. No hosted
bootstrap or fallback is reauthorized.

## Exact baseline and adopted descendant

[`seed/compiler-core.json`](../../seed/compiler-core.json) records both
identities and the sixteen adopted source-file hashes.

- **Measured reference:** corrected M104, source
  `a9edc1f0d5021efabf6864e70c5b92d59257f348`, compiler payload SHA-256
  `e5fc0ca2b6996deb1bf4722d285790eab2a35ea9724904f5cf2be296943d702d`.
  The saved Apple M4 cycle covers all 19 translated workloads with the
  same-algorithm policy and reports Kotoba/C time ratio
  `0.821298642657085`. It is a historical translated-port result, not a
  certified official score, current-host measurement or C-free runtime proof.
- **Adopted source core:** the M105 source recorded at
  `6103f5cf661252c2031af20778e0a30ca24b7eb2`; the sixteen-file unity is
  2778982 bytes, SHA-256
  `a6906f3b48825aeca44607de5bd4c67305e2ef8bc9ac4cbef3074236f4b2ae0d`.
  These files are byte-identical on the reviewed owning main. The recorded
  subsequent G1/G2/G3 payload is
  `b10e381344a1f5a8b82cac981c0011bd20ecbcc4b48dd5f5dce97364c74e8a00`.
  The checked-in historical bootstrap is separately pinned as `6b158aa8...`;
  it must not be mistaken for that later fixed-point payload.
- **2026-10-22, wire 42 admission round (ADR 0371 step 3).** It changes only
  the capability admission: HEADS, 00-ns, 20-names, 21-check, 30-lower, 60-proj
  and 90-drv. No code-generation module changes.
  - The unity is now `37e4794d…` and G1 = G2 = G3 = `9deed950…`
    (`seed/adoption-20261022.json`, built C-free).
  - The new compiler reproduces all 19 current workload images exactly, and
    passes the nine a64gen controls and certified-54
    (`docs/evidence/wire42-admission-20261022/`).
  - The measured lineage above is unchanged in substance. No new timing was
    taken.

M105 is the implementation descendant to extend, not a reason to attribute
the M104 timing to a different binary. M93's `0.7999` includes substitution
kernels and SHA instructions and is not the same-algorithm baseline. The
xgboost width-two hand patch is an unadopted noisy experiment; do not make it
the compiler core or claim a new score from it.

The source/byte checks performed here and the offline score recomputation
inspect saved data. No compiler, C comparator, timer, self-rebuild or native
runtime is executed by them. Historical loader receipts remain explicitly
distinct from current loaderless acceptance.

## Integration and merge conditions

1. Preserve this core and its source/byte identity when reconciling branches.
   Restore current owning-main authority, retired-host decisions, additive
   exports and lock consistency. Keep novel WIP and historical measurements
   reachable. Do not reintroduce removed GraalVM builders or hosted gates.
2. Review required runtime and ABI implementations, including native #205
   and its #206 string extension, against this core's actual calls, values,
   resources and IO. Integrating source into a draft candidate is not native
   qualification or main/release admission.
3. Materialize a C/JVM/Node-free initial compiler from this lineage, then
   rebuild the complete compiler, CLI, build graph and packager with Amu.
   Record actual process traces, source/lock/Definition-CID pins and native
   artifact hashes across generations. Retain explicit failures; no silent
   fallback, omitted lock option, smaller corpus or unreviewed profile change.
4. Run the complete positive/refusal/lock/resource corpus and all 19 Embench
   workloads with the same compiler identity. Record result, fuel, arena and
   artifact behavior. Obtain fresh quiet-host timing before assigning any
   score to the successor. Verify public import and `kotoba compile` through
   that compiler before main product admission.

Native-only acceptance and the two loaderless native CDCI gates remain in
[selfhost-priority](../selfhost-priority.md). Missing execution evidence stays
open; source integration and documentation never count as passing it.

## Review correction in the saved reproduction package

The offline audit on owning main recomputed the full-19 ratio as
`0.8212986426570839`, within the documented tolerance, but failed two package
hashes. Commit `6103f5cf` had corrected the C comparator's generated output
path from `<out>/<name>` to `<out>/<name>/<name>` in `c/build_c.py` and both
expectations in `d_timing.py`, without updating `SHA256SUMS`.

Update only those two checksums after reviewing the exact three-line path
correction against the hash-pinned `dd332a30` versions. The saved timings,
workloads, compiler images, custody records, expected results and score are
unchanged. This repairs the current archive's integrity check; it does not
execute or qualify its historical C build/timing tools as a product route.

Tracking: [AWAI-66](https://linear.app/kotobalabs/issue/AWAI-66),
[AWAI-43](https://linear.app/kotobalabs/issue/AWAI-43),
[AWAI-64](https://linear.app/kotobalabs/issue/AWAI-64).
