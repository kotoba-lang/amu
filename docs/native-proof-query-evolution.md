# Native proof-query hypothesis screening (JUN-27 / JUN-332)

This is a research branch, not a production implementation. H23 (query-local
memo) and H27 (lazy proof operand reads) were screened with the same native
ARM producer, frozen core18 input, lock, CPU affinity and resource limits.
The producer digest is8b795c842333a9c00bb886916c5a003de7729130eb00ddbc00cb3411ecc92478
(the separately staged native runtime candidate). Both candidates preserved all
four core output containers byte for byte. Pass that exact image explicitly
with `--compiler` when reproducing these observations; the research branch's
default producer is an older image and is not the measured local producer.
Neither improved the actual compiler workload, so neither is selected.

| Candidate | Baseline median | Candidate median | Ratio | Decision |
|---|---:|---:|---:|---|
| H23 query-local cost/failed-budget memo |17.9720s|18.2752s|1.01687|Defer; extra cache work outweighs saved walks in this screen|
| H27 lazy operand reads |17.6180s|17.6730s|1.00312|Defer; no measured improvement|

These are local native ARM screens, not actual x86 or whole-CI performance.
No production source/image or qualification is changed. The diagnostic
recursive call count did not establish removable time; marker overhead and
nested spans made it a hypothesis generator, not a performance result.

The original cc-safe evaluator and candidates were compared on524,288
queries covering DAG calls, direct self calls, cycles, budgets/depths,
forbidden/float/unknown instructions and changed input graphs. The open
range is held fixed in this screen; it is not an open-range mutation test.
H23 additionally tests explicit hot-to-insufficient-budget, failed-to-larger
budget, depth and function hash collisions. All four named key/budget mutants
were compiled successfully and actually returned1. H27's work charge, float
exclusion, END owner and depth guard mutants likewise built and returned1.

The first H23 grid let an insufficient-budget mutant survive because ordinary
traversal evicted its positive cache entry before the low-budget revisit.
That attempt is retained as a failed oracle experiment. Explicit paired
queries fixed this weakness; the failed attempt is not a correctness or
performance pass. Cache lifetime is one read-only query only: no result
crosses an M/SIR mutation, T2 rollback or open-range change. This lifetime
observation is not permission to cache a mutable CODE/FIX prefix.

Portable observations are in `docs/evidence/native-proof-query-evolution-20261026/`.
