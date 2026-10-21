# Generic compare-zero branch fusion

Status: **selfhost fixed point and exactness passed; loaded-host performance is inconclusive; not promoted**.

## Hypothesis and control

The generic `gn-cmp-br` emitter used `cmp` plus `b.cond` for a fused equality
branch. When equality compares a nonconstant operand with literal zero, the
candidate emits `cbz` or `cbnz` on the nonconstant register. The counter-hypothesis
is that Apple cores already handle `cmp` plus conditional branch efficiently,
and that branch layout or register pressure can offset the one-instruction
reduction.

The candidate was isolated to one copied `seed/41-a64gen.kotoba` hunk. The
no-fusion control was made by reversing that hunk and verified byte-identical
to the shared `seed/41-a64gen.kotoba` snapshot. Both versions used the same
other seed files and the same preceding selfhost compiler. Neither experiment
modified the shared seed.

The no-fusion control reached a G1=G2=G3 fixed point at SHA-256
`1544a204b003bd3b5ec9831be008fcbd5ffa5a91c44f922a4ca13a1dca539588`. The
candidate reached a fixed point at
`c534cf38cbb5fd14745b95864856edb8e762b9b94e545a77e79de3337026844f`.
Recompiling the same 19 pinned Embench ports changed 18 native payloads;
`depthconv` remained byte-identical. The full fixed-point reports and image
receipts are retained under
`workspaces/codex/amu-generic-cmp-zero-fusion-20261017/`.

## Exactness

The official C reference exactness harness passed all 18 changed images,
including result, fuel, and arena accounting. The full report is
`workspaces/codex/amu-generic-cmp-zero-fusion-20261017/attempt-1/exactness-vs-control/report.json`.

## Loaded-host timing

Five ABBA blocks were run for each changed workload, with four invocations per
block and identical timers/caps for the no-fusion control and candidate. All
360 invocations passed result, fuel, and arena checks. The load1 values before
runs ranged from 22.07 to 78.34 (median 33.05), so this is an unqualified
exploratory comparison on the user-authorized loaded M1 Max, not a performance
claim.

The median of the 18 per-workload median candidate/control ratios was `0.993`;
11 workload medians favored the candidate, and five were below `0.98`. The
signal was not consistent: `edn` was `0.943`, while `huffbench` was `1.113` and
`statemate` was `1.047`. Several workloads had large pair-to-pair outliers,
including `tarfind` at `1.724` and `ud` from `0.629` to `1.080`. These data do
not establish a speedup. Retain the candidate as an experiment only; repeat on
a qualified quiet host before promotion.

Per-workload hashes, paired ratios, load observations, and summary statistics
are in [`summary.json`](summary.json). Raw timing records are in
`workspaces/codex/amu-generic-cmp-zero-fusion-20261017/attempt-1/timing-all18-abba/report.json`.

## Reproduction

From the repository root, the recorded steps were:

```sh
python3 workspaces/codex/amu-generic-cmp-zero-fusion-20261017/control-1/build-selfhost.py
python3 workspaces/codex/amu-generic-cmp-zero-fusion-20261017/attempt-1/build-selfhost.py
python3 workspaces/codex/amu-generic-cmp-zero-fusion-20261017/control-1/compile-ports.py
python3 workspaces/codex/amu-generic-cmp-zero-fusion-20261017/attempt-1/compile-ports.py
python3 bench/embench/reproduce-20261015/c_exactness.py \
  --out workspaces/codex/amu-generic-cmp-zero-fusion-20261017/attempt-1/exactness-vs-control \
  --images workspaces/codex/amu-generic-cmp-zero-fusion-20261017/attempt-1/all19-candidate \
  --only aha-mont64,crc32,edn,huffbench,matmult-int,md5sum,nettle-aes,nettle-sha256,nsichneu,picojpeg,qrduino,sglib-combined,slre,statemate,tarfind,ud,wikisort,xgboost
python3 workspaces/codex/amu-generic-cmp-zero-fusion-20261017/attempt-1/time-all18-abba.py
```

`summary.json` was generated from those reports. The shared
`seed/41-a64gen.kotoba` remains unchanged by this experiment.
