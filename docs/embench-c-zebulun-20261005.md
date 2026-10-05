# Native selfhost Kotoba versus C on zebulun

All 19 original active profiles completed 30 accepted paired samples each.
C: Apple Clang 17 -O2; Kotoba: pinned native selfhost r6m Amu.
Geometric mean Kotoba/C time ratio: 11.1274. No workload meets C-or-better.

These are custom whole-call ratios, not official Embench scores.
CPU evidence encloses setup/warmup; background idle is an estimate.
All rejected pairs are retained. Own-source 100% selfhost qualification remains unmet.

| Workload | Kotoba/C time | Kotoba ns/body | C ns/body | Attempts / accepted pairs |
|---|---:|---:|---:|---:|
| aha-mont64 | 1.963 | 1068.8 | 544.5 | 34 / 30 |
| crc32 | 2.310 | 3942.3 | 1706.4 | 30 / 30 |
| depthconv | 3.497 | 120.4 | 34.4 | 30 / 30 |
| edn | 15.933 | 11941.2 | 749.5 | 31 / 30 |
| huffbench | 7.357 | 54020.4 | 7342.9 | 30 / 30 |
| matmult-int | 24.569 | 23161.1 | 942.7 | 30 / 30 |
| md5sum | 6.851 | 17163.7 | 2505.4 | 31 / 30 |
| nettle-aes | 18.525 | 25954.2 | 1401.1 | 30 / 30 |
| nettle-sha256 | 15.294 | 3344.7 | 218.7 | 31 / 30 |
| nsichneu | 14.719 | 1158.4 | 78.7 | 31 / 30 |
| picojpeg | 32.678 | 364558.6 | 11156.1 | 30 / 30 |
| qrduino | 12.346 | 273604.4 | 22162.3 | 31 / 30 |
| sglib-combined | 7.708 | 44662.6 | 5794.0 | 32 / 30 |
| slre | 7.580 | 7857.2 | 1036.5 | 30 / 30 |
| statemate | 78.412 | 2467.6 | 31.5 | 30 / 30 |
| tarfind | 19.613 | 19727.5 | 1005.9 | 31 / 30 |
| ud | 12.776 | 689.9 | 54.0 | 30 / 30 |
| wikisort | 17.001 | 257438.6 | 15142.7 | 30 / 30 |
| xgboost | 7.410 | 1371006.2 | 185015.6 | 31 / 30 |

Highest gap: statemate; next experiment tests generic direct scalar tail calls.
No return values, bounds checks or fuel accounting are replaced by expected answers.
