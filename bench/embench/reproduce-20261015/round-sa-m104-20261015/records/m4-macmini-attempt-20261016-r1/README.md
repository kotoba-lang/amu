# Qualified M104 follow-up on a second Apple M4 Mac mini (16 October 2026)

This is a fresh full-19 cycle of the `sa-m104-20261015` Embench-derived translated-port comparison. It used the repository's unchanged `d_timing.py`, Kotoba and C target modules, and the pinned Embench speed driver. Both campaigns ran in one session, Kotoba first and C second.

## Result

- Kotoba: 19/19 accepted; C: 19/19 accepted.
- All 38 selected samples passed raw-idle and estimated-background-idle gates of at least 70%. All Kotoba outputs matched the round's expected values and stderr; C emitted the required `EMBENCH_NS` line.
- Full-19 geometric mean: **0.7877703355587422** for `(4 / m_w) * Kotoba_elapsed_ns / C_elapsed_ns`.
- Each workload selected the first qualified attempt. The first C `wikisort` timing was rejected for `raw-post-cpu`; its second attempt passed. There is no subset mean.

This is a qualified Embench-derived translated-port comparison, not an official or certified Embench result and not a SPEC score. It is a separate host cycle from the earlier `Joseph (Apple M4)` record (0.821298642657085); the values are not averaged or substituted for one another.

## Host and inputs

- Apple M4 Mac mini, `Mac16,10`, 16 GB; macOS 26.3.1, arm64, 10 logical CPUs.
- C was built fresh with Apple clang 21.0.0 (`clang-2100.1.1.101`, target `arm64-apple-darwin25.3.0`), using the upstream `-O2` build command. No frozen C binaries were reused. The build receipt records each output hash and its difference from the frozen binaries.
- Embench IoT commit `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70`; the 40 source/support files and 6 driver files matched the package hashes (`upstream-verification.txt`).
- The Kotoba arm used the 19 pinned M104 images and expected-accounting values in this package. Protocol and workload multipliers are unchanged.

## Independent record check

`verify-record.py` rechecks the raw attempts against the M104 expected-value ledger, per-attempt CPU gates, C output format, per-workload ratio formula, and full-19 geometric mean. From the repository root, run:

```sh
python3 bench/embench/reproduce-20261015/round-sa-m104-20261015/records/m4-macmini-attempt-20261016-r1/verify-record.py
```

The folder retains `report.json`, the clang build receipt, and every per-workload raw attempt and quiet-admission probe, including each runner's original stdout and stderr. It omits duplicate upstream checkouts and host-built executable binaries; their inputs and output hashes are recorded elsewhere in the package.
