# Sglib combined kernel experiment (2026-10-17)

Status: exploratory and not promoted. This combines the earlier list pointer-cache kernel and tree-insert path-cursor skip, then measures their interaction against the same M105 compiler predecessor.

The source changes are on separate lines in the shared seed file. The combined candidate reached a G1=G2=G3 fixed point at `98c7af4b3ed13a290a61e0d95e6b24135aad5ce8d9a5d818cfe4418df0872a70`. Compiling all 19 pinned ports from the same predecessor changed only `sglib-combined`; the other 18 images, KSEEDs, and exports remained identical. Registered Sglib exactness passed at `n=253952`, including benchmark fuel `3858038786`, verify fuel 605, and matching arena. This and the unchanged images establish effective exactness for all 19 ports.

The combined image used `[28886414971, 28897753554, 28883227448]` dynamic-instruction counts across three diagnostics, median `28886414971` (93.2700% of the control median, or about 6.73% fewer). The count-gate status is FAIL because the preregistered unchanged-image diagnostic rejects changes beyond 2%; output, fuel, and arena exactness passed separately.

Ten exploratory same-host ABBA/BAAB blocks had `8/10` candidate-faster blocks and median candidate/control elapsed ratio `0.97083`. Ratios ranged from `0.88254` to `1.42249`; load1 ranged from `27.36` to `50.04`. All 42 runs, including two warmups, passed exactness. Because this was a loaded M1 Max sample, it is not qualified performance evidence. No C comparison or official Embench score was made.

The result supports further work on Sglib's generated native kernels, but it does not establish that Amu is faster than C on Sglib or other workloads. Next gates are a quiet-host paired rerun and a same-cycle C comparison. Raw scripts, source candidate, reports, and hashes are in `raw/` and `summary.json`; reproduction workspace: `scratch/workspaces/codex/amu-sglib-combined-kernels-20261017/attempt-2`.
