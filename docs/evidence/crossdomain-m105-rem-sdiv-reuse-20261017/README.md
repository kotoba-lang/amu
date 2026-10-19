# Deep-spill remainder divisor reuse probe

Status: **FALSIFIED for the tested fixture; no generated-code change.**

The diagnostic `kernel_deep` workload keeps 24 remainder results live until a
final sum. Its AArch64 code has a 512-byte frame and spills several results.
The candidate attempted to keep the divisor in `x17` across a signed divide
and reuse it for the fused remainder `msub`.

## Evidence

- Source: `bench/runtime-comparison/kernel_deep.kotoba`, SHA-256
  `9856127a6259fb66ba4568056580d23e047965876a83e4d0522d299641c5e5ce`.
- Candidate selfhost source unity SHA-256:
  `f11ccd1fc5b47ff324e25f20580cf484f3ccee0b198f589c2748cc92db1023ad`.
- Native G1, G2, and G3 all reached the same 2,555,504-byte compiler image,
  SHA-256 `69947f20b5152663e03ecf6d42a12edfc38d94cf1a3d5a89e7446debd6f1efa4`.
  The build used the adopted native bootstrap and pinned C loader, without a
  JVM, Node, or Graal fallback.
- Baseline and candidate `kernel_deep` native payloads were both 2,508 bytes
  with SHA-256
  `b0504891847dc501050dad4a5a51e5c46faecfb7407bebcb8484a66f5303d985`.
- Two one-generation diagnostics relaxed the IR identity requirement and then
  tried an exact prior-`sdiv` machine-word match. Both still produced the same
  payload. These diagnostic compilers were not fixed points and were not run.
- No timing or native execution comparison was performed. The host remained
  heavily loaded, and identical machine code cannot test the speed hypothesis.

Raw builds, call logs, and disassemblies are preserved under
`scratch/workspaces/codex/amu-rem-sdiv-reuse-20261017/`,
`.../amu-rem-sdiv-reuse-diag2-20261017/`, and
`.../amu-rem-sdiv-reuse-diag3-20261017/`.

## Next pressure hypothesis

Inspection of `t2-positions`, `t2-scan`, and `t2-e-vals` shows both linear-scan
allocation and ordinary block emission traverse values in ascending IR ID
order. The fixture defines all 24 lane remainders before its final sum, so
their result values remain live across the other lane calculations. The
allocator's spill heuristic cannot shorten those live ranges on its own. A
candidate must change the safe instruction schedule or fold ready terms into
the running sum, while preserving division traps, fuel accounting, and all
other observable effects. This inspection is a hypothesis for a separate
experiment, not a demonstrated speedup.

This probe establishes no performance benefit and does not explain the M104
translated-port comparison.
