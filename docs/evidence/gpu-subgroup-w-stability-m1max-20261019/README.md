# gpu-subgroup-w-stability-m1max-20261019 — is the measured execution width a property of the device or of the dispatch?

**Question.** The one flipped fact in `kotoba.compiler.accelerator-targets`
(ADR-0355) is `:apple :execution-width 32`, measured at **W = 64 only**
(`docs/evidence/gpu-subgroup-measured-row-m1max-20261019`, PR #1344). The
dispatch table's apple workgroup default is **256**. If `gl_SubgroupSize`
moved with W, a row measured at 64 and dispatched at 256 would be citing
evidence from a configuration the table never selects. This sweep answers
one question: **is gl_SubgroupSize W-invariant over the :subgroup-reduce
domain W >= 32 on this host?**

**Answer (measured, this host only):** YES — `gl_SubgroupSize` = **32 at
every W in {32, 64, 128, 256}**, all three rungs (geometry / arith / ballot)
admitted and verified at every W. `INVARIANT=yes` in all three runs.

| W   | S  | NGS | geometry | arith | ballot |
|-----|----|-----|----------|-------|--------|
| 32  | 32 | 1   | ok       | ok    | ok     |
| 64  | 32 | 2   | ok       | ok    | ok     |
| 128 | 32 | 4   | ok       | ok    | ok     |
| 256 | 32 | 8   | ok       | ok    | ok     |

W = 64/NGS = 2 reproduces the flipped row's basis exactly, which ties the
two evidence sets together; W = 256 is the configuration the dispatch table
actually selects for `:apple`.

## Machine / stack

- Apple M1 Max (Apple Silicon), macOS 26.4, aarch64-macos
- Vulkan via MoltenVK: device answer `Apple M1 Max|1.3.357|1024|1`
  (device | api version | maxComputeWorkGroupSize[0] | unified memory),
  printed verbatim as `GPU-SUBGROUP-WSWEEP\tINFO` in each run log
- Execution: `:gpu/compute` (wire 42) through `tools/kexe_gpu_vulkan.c`, the
  repo's only GPU execution path

## Method

`scripts/test-gpu-subgroup-wsweep.cljk` is derived from
`scripts/test-gpu-subgroup-probe.cljk` (the probe first run on
`bot/amu-gpu-20261019-0416`, PR #1343, and re-run in-tree on
`bot/amu-gpu-20261019-0451`, PR #1344; that probe's sha256 is
`123103347e7f9596e3f613cfb5e6bda8d3693b00c930782f666907c31abdd5d8`, and it
was checked here before deriving). The record protocol is unchanged: one
workgroup, one dispatch, each subgroup's invocation 0 writes one 8-word
record; verification is mechanical (`S*NGS == W`, per-record identity, the
rung's own fold word `== S`, sentinel). The one thing the probe held fixed —
the workgroup size W — is swept over {32, 64, 128, 256}, with the read
window widened to 32 records so an NGS past the window answers WIDEN-READ by
name instead of verifying a truncated tail. The verifier's synthetic
self-tests run at three (W, S, NGS) shapes before any dispatch, so a
W-shaped bug in the sweep parameterization is caught before hardware is
asked. This script's sha256 is
`4aae7daa8e4d5b361cf1e1d964b1398536989ede9c7fe2e29a06a0f31fc551fd`.

Each of `run-1.log` .. `run-3.log` is one fresh `kbb` process running the
whole sweep; all three exited 0 and are **byte-identical**
(sha256 `dda8582f17087f77102e4bb0c95e8f35dac9beffda90cc3e1662dcff19755042`,
verified with `shasum -a 256` 2026-10-19; the SHA-1 of the same bytes is
`8b05c4b8088c6eab1aafda59877000a6e8c7182e`, which earlier versions of this
line mislabeled as sha256). Repetition here is reproducibility of a deterministic
geometry, not a statistical claim — there is no timing in this measurement
at all.

## What this does NOT say

- **Not a workgroup-size tuning result.** Nothing here measures time. The
  size rows stay provisional (`:size-measured? false`) for every vendor;
  this sweep found no size effect because it was not looking for one. The
  size flip bar in ADR-0355 stays unmet.
- **One device, one vendor.** Apple M1 Max only. It says nothing about
  Intel (JUN-59) or ARM (JUN-60) widths, which stay UNMEASURED — no
  hardware — and nothing about other Apple GPUs.
- **The invariance claim's scope is W ∈ {32, 64, 128, 256}.** W = 1024
  (the device's max) and non-powers of two were not asked.
- **No code flip in this branch.** The `:execution-width-basis` strings and
  the ADR-0355 honest-state text that this evidence extends live in
  PRs #1343/#1344, which are still open; editing the same hunks here would
  conflict with in-flight work for no gain. The basis update ("measured at
  W = 64; W-invariant over W = 32..256 on the same host, see
  gpu-subgroup-w-stability-m1max-20261019") is a one-line follow-up once
  those land. Until then this evidence is exactly what it is: a measurement,
  recorded, not yet cited by the table.

## Verdict semantics

- exit 0: every W's geometry rung measured and verified; other rungs OK or
  NOT-ADMITTED by name; the INVARIANT line is computed from the numbers,
  never assumed.
- exit 1: a rung the device admitted failed verification.
- exit 3: nothing measurable here (toolchain/device), printed by name.

All three runs answered exit 0 with `INVARIANT=yes`.
