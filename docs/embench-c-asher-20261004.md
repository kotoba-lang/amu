# C and Kotoba compiled by Amu: Embench comparison

Measured on 2026-10-04 JST on Tailscale host asher (Apple M4, 10 cores, 16 GiB RAM, macOS 26.2). C uses Apple Clang 17.0.0, -O2, without LTO. Kotoba uses the r6m unified Amu image abcc1318957af7d3a09cfd66c06d17821b5cf47f4c47d02b5620e9e92a24f02e. Amu is the compiler of the measured Kotoba programs, not another independent language entry.

## C reference and score

The C sources, upstream main and verification functions are unchanged at upstream commit 09c2ed8c3b7008c95d08b038de4a3f6dc103ed70 (Embench 2.0rc2 workload sources). Each measured interval begins at start_trigger and ends at stop_trigger. Cache warmup and output verification are outside that interval. Five samples per workload are measured; the global scale value is calibrated separately for each program to approximately four seconds and each value is disclosed in comparison.csv/json. This is a custom platform runner, not an execution of the official benchmark_speed.py driver or a result published by the Embench organization.

Using the upstream speed formula `baseline_ms / measured_ms * gsf` across all 19 workloads gives:

| C metric | Measured value |
|---|---:|
| Speed, geometric mean | 38387.81 |
| Geometric standard deviation | 1.910 |
| One geometric standard deviation range | 20101.99–73307.35 |
| Maximum recorded load | 3.28 |

No speed/MHz value is estimated because the effective M4 clock during these runs is not measured. No official code-size score is inferred from raw extraction bytes.

Published official C results for context:

| Embench version | Platform and C toolchain | MHz | Speed | Speed/MHz | Size |
|---|---|---:|---:|---:|---:|
| 0.5 | Cortex-M4, GCC 9.2, -O2 | 16 | 16.00 | 1.00 | 1.15 |
| 1.0 | SweRV-EH2, GCC 10.2, -O2 | 50 | 66.50 | 1.33 | 1.26 |

These published scores use older workload sets and baselines. They are not divided into the current M4 score to claim a speedup. The repository README says it holds only 0.5 results, but the SweRV record itself declares 1.0; the per-result version is retained here.

Sources: [official result repository](https://github.com/embench/embench-iot-results), [upstream scoring method](https://github.com/embench/embench-iot/blob/09c2ed8c3b7008c95d08b038de4a3f6dc103ed70/doc/README.md).

## Paired nine-workload reference comparison

C time below is its timed benchmark body divided by LOCAL_SCALE_FACTOR × GLOBAL_SCALE_FACTOR. Kotoba time is a warmed repeated correctness export, including verification inside that export and per-call ABI arena/fuel reset. Both sides use the complete input/output of these nine translations. Their timing boundaries and data representations are not identical, so this is a port-level reference comparison, not a pure compiler/language efficiency estimate or an official Kotoba Embench score. The ten adapted ports are excluded.

| Workload | C body (µs/iteration) | Kotoba with Amu r6m (µs/correctness call) | Kotoba time / C time |
|---|---:|---:|---:|
| aha-mont64 | 0.670 | 1.062 | 1.58x |
| crc32 | 2.735 | 4.552 | 1.66x |
| depthconv | 0.035 | 2.684 | 75.99x |
| matmult-int | 0.906 | 18.641 | 20.58x |
| md5sum | 2.593 | 12.148 | 4.69x |
| nettle-sha256 | 0.225 | 4.301 | 19.15x |
| tarfind | 2.042 | 14.518 | 7.11x |
| ud | 0.054 | 2.986 | 55.17x |
| xgboost | 167.868 | 16393.463 | 97.66x |

Geometric mean of these nine time ratios: **13.43x** (smaller is better; C = 1). This is not the full Embench suite score. The base64 decoding used for static byte data in several Kotoba ports, runtime representations, output verification, and generated machine code all contribute to the gap.

An official-equivalent Kotoba/Amu full-suite score remains unavailable: ten full upstream bodies, exact initialization/repetition/timing boundaries and a dummy-subtracted size metric remain to be implemented and audited. Reusing the prior single-call stage-0 ratios or scaling them by a published C score would not produce that score.

Evidence: docs/evidence/embench-c-asher-20261004/raw-results.tgz contains unchanged-source hashes, build commands, executable hashes, all timing samples and load checks. The C measurements were calibrated a second time using the warmed initial data; initial-rows.json retains that first run. The nine native batches are retained from the initial run.

Subsequent research, separately measured: [depthconv](coscientist-depthconv-20261004.md)
has a matched batch alternative 24.597x faster than its Base64 reference but
2.901x slower than C. [EDN](coscientist-edn-20261004.md) now has a complete
eight-operation alternative with 5,427 state-cell matches, measuring 14.357x
slower than C. Nine adapted workloads remain without complete alternatives.
These additions do not revise the historical table, its geometric mean, or
produce an official full-suite score.

[Huffbench](coscientist-huffbench-20261004.md) now has a complete selfhost
500-byte codec alternative with 3,309 matching C state cells and a separate
matched-batch comparison: 60,339.107 ns/body versus C 8,278.511 ns (7.289x
slower). Eight adapted workloads remain without complete alternatives. The
historical table and geometric mean remain unchanged; no official full-suite
score or C-or-better claim follows. Two rejected prototype raw reports await
recovery from offline asher; the baseline report is archived locally.

[NSichneu](coscientist-nsichneu-20261004.md) now has a complete sequential
alternative for all 126 upstream transitions, with 17,272 stage-state matches
and 136 production-chain final-state matches. It is unmeasured while asher is
offline, so there is no new performance ratio. Seven adapted workloads remain
without complete alternatives; historical timings and full-suite score claims
remain unchanged. C volatile globals and owned Kotoba vectors differ in access
semantics; the evidence establishes the recorded sequential state comparisons.

[Nettle-AES](coscientist-aes-20261004.md) now has a complete AES-256 alternative
including both schedules, inversion, and 256-byte encryption/decryption.
12,680 phase-state values and 634 production-body final values match C.
It is unmeasured while asher is offline. Six adapted workloads still lack
complete alternatives; no historical timing or geometric mean is changed
and no official full-suite score or C-or-better claim follows.

[Statemate](coscientist-statemate-20261004.md) now has a complete selfhost
window-controller alternative. All 2,028 staged state values, 169 actual-body
values and 676 repeated-body values match unchanged C. Native check/compile,
batches and bounds/fuel checks pass. It remains unmeasured while asher is
offline; five adapted workloads still lack complete alternatives. The
historical timing table and geometric mean remain unchanged.
