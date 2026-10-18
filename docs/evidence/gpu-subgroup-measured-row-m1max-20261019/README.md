# gpu-subgroup-measured-row-m1max-20261019 — the first measured row in accelerator-targets

Evidence for the first `:measured?` row flip in
`kotoba.compiler.accelerator-targets` (JUN-56 follow-up / JUN-58): the
`apple` row's **execution width** (subgroup size) is a hardware fact, not a
design assumption. The row's workgroup SIZE stays provisional.

## What is measured (all three runs)

`gl_SubgroupSize` = **32** at W = 64 (NGS = 2), plus the two op-admission
rungs the `:subgroup-reduce` emission leans on:

- `subgroupAdd(1u)` == 32 == S (arithmetic fold admitted)
- `subgroupBallotBitCount(subgroupBallot(true))` == 32 == S (ballot admitted)

## Provenance

- Command per run: `kbb --backend sci scripts/test-gpu-subgroup-probe.cljk`
  (three fresh processes, 2026-10-19 JST, this worktree). Logs are
  run-1.log .. run-3.log, verbatim stdout; every run answers
  `RESULT S=32 NGS=2 W=64 geometry=ok arith=ok ballot=ok` and exits 0.
- Protocol: `scripts/test-gpu-subgroup-probe.cljk`, byte-identical (sha256
  `123103347e7f9596e3f613cfb5e6bda8d3693b00c930782f666907c31abdd5d8`) to
  the probe first run on branch `bot/amu-gpu-20261019-0416` (PR #1343). The
  probe is re-run here so the row flip carries its own in-tree evidence; the
  numbers agree with that first measurement.
- Host: Apple M1 Max, macOS 26.4, aarch64-macos. MoltenVK, Vulkan 1.3.357.
  INFO answer `Apple M1 Max|1.3.357|1024|1`.
- Verification: the probe verifies every read-back record-by-record (S,
  subgroup id, NGS, r*S base, sentinel 0xC0FFEE^id) with S*NGS == W checked
  mechanically; the script self-tests before touching the GPU (all passed at
  every invocation).
- Toolchain note (measured): glslang 11:16.6.0 rejects the umbrella
  `GL_KHR_shader_subgroup`; per-category `GL_KHR_shader_subgroup_basic /
  _arithmetic / _ballot` are what this toolchain admits.

## What the flip is, and is not

- IS: `:apple` `:execution-width-measured? true` in
  `kotoba.compiler.accelerator-targets`, basis naming this directory. The
  answer-level `:measured?` in `recommend` stays **false** everywhere,
  because every workgroup size is still provisional.
- IS NOT: a measurement of Intel (JUN-59) or ARM (JUN-60) subgroup sizes —
  they stay UNMEASURED and their flags stay false. One Apple device was
  measured; the row says so in its basis.
- IS NOT: a tuning result. No timing is measured or claimed here, and no
  workgroup size (256 or any other) is endorsed. The size rows' flip bar is
  recorded in ADR-0355 and remains unmet.

## Suite state at this commit

The gate (`kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)"
run-tests.cljk`) is run for this diff; the result is recorded in the PR. The
touched suite namespace is `kotoba.compiler.accelerator-targets` (+ its
test); a targeted run of that namespace passes 5 tests / 120 assertions.
