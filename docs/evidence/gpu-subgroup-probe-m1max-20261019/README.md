# gpu-subgroup-probe-m1max-20261019 — subgroup geometry + op support, measured

First hardware reading of subgroup facts in this repo. Protocol:
`scripts/test-gpu-subgroup-probe.cljk` (this branch). Host: Apple M1 Max,
aarch64-macos, MoltenVK (Vulkan 1.3.357), wire 42 through
`tools/kexe_gpu_vulkan.c`. Three fresh processes (run-1..3.log), identical
results, every read-back verified record-by-record (S, subgroup id, NGS,
r*S base, sentinel 0xC0FFEE^id) with S*NGS == W checked mechanically.

Measured (all three runs):

- gl_SubgroupSize = **32** at W = 64 (NGS = 2)
- subgroupAdd(1u) == 32 == S  (GL_KHR_shader_subgroup_arithmetic admitted)
- subgroupBallotBitCount(subgroupBallot(true)) == 32 == S
  (GL_KHR_shader_subgroup_ballot admitted)

This is vendor evidence for JUN-58 (Apple) only. It says nothing measured
about Intel (JUN-59) or ARM (JUN-60) devices: their subgroup sizes stay
UNMEASURED, and the ADR-0356 row's :measured? false cannot flip on this
data. What it does establish for the :subgroup-reduce emission (PR #1341):
on this host S=32 divides every admissible W >= 32, the runtime
gl_SubgroupSize query reads 32, and the arithmetic fold and ballot stages
the design leans on execute on MoltenVK.

Toolchain note (measured): glslang 11:16.6.0 rejects the umbrella
GL_KHR_shader_subgroup ("'#extension' : extension not supported"); per-
category GL_KHR_shader_subgroup_basic / _arithmetic / _ballot are what this
toolchain admits.

UNMEASURED after this: timing. No speedup is claimed or implied; this probe
measures geometry and op admission, never performance.
