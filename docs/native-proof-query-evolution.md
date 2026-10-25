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


## Subsequent matched screens

| Candidate | Host/workload | Baseline median | Candidate median | Ratio | Decision |
|---|---|---:|---:|---:|---|
| H18 predicate ordering | actual x86 EPYC7763, frozen current core/KSL1 |470.3321s|458.1952s|0.97420|Superseded by H34 candidate|
| H34 high-byte class filter | actual x86 EPYC9V45, same frozen current core/KSL1 |155.8593s|140.4722s|0.90128|Select for production integration/qualification|
| H34 high-byte class filter | local native ARM, same frozen current core/KSL1 |17.8036s|15.5340s|0.87252|Supports x86 selection|
| H36 scalar SHA working state | local native ARM, same frozen current core/KSL1 |17.6218s|17.5556s|0.99624|Defer; no meaningful gain|

The H34 native grid covers131072 cases, including all256 high bytes crossed
with256 low-pattern samples. Four separately built mutants (word bound,
ADRP refusal, ADR-class bit, literal-class bit) actually exited1 on both ISAs.
All four frozen-core output containers equal6ad407c2. The immutable mask
only skips classes with no PC-relative checks; every relevant instruction
still takes the original full predicate. It reads CODE on every query, with
no prefix cache, no invalidation assumptions and no authority change.

H36 passed14 SHA vectors (padding boundaries, empty/abc and million-a),
four built/executed mutants and all four frozen-core outputs. It is retained
as a negative result, not selected for production. No actual x86 gain is claimed.

H33 core-role/public screen on one native x86 EPYC7763 measured460.364/471.652s.
The initial gap did not cross the predeclared10% ABBA trigger; this is two
calls only, with no full controller sandbox, and does not justify changing
the production role. H35 old/new runtime source-lock screen on one EPYC9V74
measured256.157/255.229s (ratio0.99638); its5% trigger likewise did not fire.
Both screens produced the same normal-core bytes.

Results across different hosts are not causal comparisons. H18 run40225170884,
H34 run40228774252, H33 run40226774761 and H35 run40228776657 retain their
exact producer/input/CPU/environment in the adjacent JSON observations.
The initial H34/H35 dispatches40228336057/40228692459 stopped before native
execution because workflow driver paths were wrong; corrected436dc85c
re-dispatches succeeded. Failed harness attempts are excluded from samples.
These experiments never replace mandatory production qualification.
