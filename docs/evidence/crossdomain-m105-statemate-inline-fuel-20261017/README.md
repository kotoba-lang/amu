# Statemate body inline with fuel compensation (2026-10-17)

Status: exact at the registered input, slower in all ten exploratory ABBA
pairs on a heavily loaded M1 Max. Reject this candidate. It was not compared
with C.

## Hypothesis

The Statemate benchmark calls `body` 27,279,360 times. Inlining its small
transition chain into `repeats` might remove repeated call and entry work.
The candidate inserts a same-value vector write before `clear-bits` to
preserve the fuel unit previously charged by the call.

## Exactness

The selfhost compiler and loader hashes were
`1544a204b003bd3b5ec9831be008fcbd5ffa5a91c44f922a4ca13a1dca539588` and
`05798f17613db2936cf8fe29c16590c8c2b7513fc80e5b2334e89d16b482f7aa`.
The control native image matches the pinned M105 image.

At registered `n=27279360`, both images returned 1 with benchmark fuel
`20159447042`, verify fuel 66, and the same arena use: one vector, 169 vector
items, and 1368 heap bytes. The control and candidate image hashes are
`6cb09af5443a9e2ce159f2853b92db2e74b887e73a108349c4cde2b65d5e6636` and
`3c6fca0ff43aaa112edb689e491a8a446211c40a1aced103a20f566db407ad50`.

## Timing

Ten base/candidate/candidate/base blocks produced 40 exact runs. Every block
favored the base. The median of paired candidate/base ratios was 1.05573.
Load1 ranged from 23.18 to 35.40, so this is exploratory rather than a
qualified slowdown estimate. It provides no performance case for keeping the
rewrite.

No C executable was measured, no dynamic instruction-count diagnostic was
run, and this result is not an Embench score. It does not explain the separate
M104 translated-port aggregate.

## Reproduction inputs

`raw/base.kotoba` and `raw/candidate.kotoba` are source snapshots.
`raw/artifacts/` contains the tested KSEEDs, native images, and macOS arm64
timers. The timer executables use the local registered benchmark harness.
From this repository checkout, rerun exactness with
`python3 docs/evidence/crossdomain-m105-statemate-inline-fuel-20261017/raw/check-exactness.py`
and the exploratory timing with
`python3 docs/evidence/crossdomain-m105-statemate-inline-fuel-20261017/raw/run-abba.py`.
The scripts import the benchmark helper under
`bench/embench/reproduce-20261015/tools`; they do not rebuild the compiler or
native images. Reports from the recorded run are in `raw/exactness-report.json`
and `raw/abba-report.json`.
