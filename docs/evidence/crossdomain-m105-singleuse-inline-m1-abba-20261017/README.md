# Single-use inline candidate: loaded M1 ABBA screen

Status: exact outputs, fuel, and arena accounting passed; exploratory timing only.

## Question and artifacts

This screen compared the preceding fixed-point compiler with the single-use
inline candidate on three changed Embench-derived ports. Statemate, whose image
was identical between compiler arms, served as a same-image timing control.
The base compiler SHA-256 is
`ef2ceb749edfa8a3aeae3845612d377d9fcfcb498e4775f926f7ccaff8e6b541`; the
candidate is `1544a204b003bd3b5ec9831be008fcbd5ffa5a91c44f922a4ca13a1dca539588`.
Both use loader SHA-256
`05798f17613db2936cf8fe29c16590c8c2b7513fc80e5b2334e89d16b482f7aa`.
Only `picojpeg`, `sglib-combined`, and `xgboost` images changed; the other 16
of 19 matched byte-for-byte.

The recorded host was Darwin arm64, macOS 26.4, identified for this run as the
user's M1 Max. It was deliberately measured under load, without a quiet-host
gate. Five blocks rotated workload order. Each workload used base, candidate,
candidate, base. All 80 timed invocations returned the expected result and
matched benchmark fuel, verify fuel, and arena accounting.

## Results

Each block ratio is the mean of the two candidate times divided by the mean of
the two base times; below 1.0 means candidate faster.

| Workload | Changed image? | Median candidate/base | Median after same-image control |
|---|---:|---:|---:|
| picojpeg | yes | 1.0202 | 0.9813 |
| sglib-combined | yes | 1.0155 | 0.9866 |
| xgboost | yes | 0.9892 | 0.9695 |
| statemate control | no | 1.0371 | — |

For the control-adjusted column, each workload's block ratio was divided by
Statemate's ratio in that same block, then the five values were summarized by
their median. This is a drift diagnostic, not a causal correction: the
same-image control itself moved by about 3.7%, and the workload ratios changed
direction across blocks. Start-of-block load1 ranged from 25.28 to 37.80.

The candidate remains unpromoted. There was no C arm, so this run says nothing
about C parity or an Embench score. It is also not a quiet-host performance
qualification.

## Data boundary

[`sanitized-report.json`](sanitized-report.json) retains every timed sample,
result, fuel value, arena-use line, and load snapshot. It omits local timer
paths and binaries. The source runner is in the ignored local work area and
depends on the pinned image workspaces, so this file is a measurement record,
not a standalone reproduction package.
