# Kernel audit of the m93 compiler (be7f0ce3)

Policy: [`KERNEL-POLICY.md`](KERNEL-POLICY.md), "same algorithm only" (user decision, 15 October 2026). A certified kernel
may change how a source function's work is executed, never what work is executed; unsure cases count as substitution.

Audit tables (one row per kernel; by author):

| file | covers |
|---|---|
| [`kernels-a.md`](kernels-a.md) | kernels written or tuned by kernels agent A |
| [`kernels-b.md`](kernels-b.md) | kernels written or rewritten by kernels agent B |
| [`kernels-c.md`](kernels-c.md) | kernels written or rewritten by kernels agent C |
| [`kernels-other.md`](kernels-other.md) | codex-lineage kernels and certified code-generation rules |

The tables audit the development compiler up to later snapshots (m97 to m101), so they also list kernels that are not in
the measured m93 compiler. Which rows apply to m93 is stated in the package README ("Audit findings for the m93 compiler");
each was checked by its presence in `seed/41-a64gen.kotoba` at `be7f0ce3`.

The rest of this package keeps reproducing the published round exactly as measured, whatever the audit finds. After
changing files here, regenerate `SHA256SUMS` with `python3 tools/make_sums.py`.
