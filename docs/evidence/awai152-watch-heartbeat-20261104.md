# Sequenced Darwin watcher heartbeat diagnostic

The prior experimental `WP02` watcher could remain registered without
providing a way to distinguish progress from a stalled helper. The candidate
now emits a 40-byte `WH01` frame after each empty wait: a nonzero increasing
32-bit sequence followed by the exact 32-byte request. It fails on write
failure, short write or sequence overflow. `WP01` retains its timeout
refusal. A pure native frame checker now accepts `WP02` readiness, checks the
next heartbeat sequence and exact request, and validates a separate final exit
frame. The existing combined WP01 reply classifier remains restricted to
WP01; a caller must validate the entire WP02 stream in order.

On one local Mac, the signed diagnostic watcher emitted and an independent
observer read two ordered heartbeats within a bounded interval, then observed
the exact final exit frame. Fork and exec observations were refused after
heartbeats; WP01 timeout, wrong identity, reaped PID and other existing cases
also passed. A separately built non-repeating watcher was refused, as was a
watcher with a corrupted heartbeat tag. Separately, a signed native fixture
executed the actual pure frame checks with WP01/WP02, wrong request, short
frame, reordered or zero sequence and sequence-range cases; an independently
built sequence-check mutant failed. Pure frame-check fixture source/image
SHA-256: `9dc350267d2bb7ed546599b1218fccf42950bf47a345bf29bd406497ebb54ffd` /
`6aad330aa8e680e89dd282f180ab8343aa580967fa3a20642e80895d8df7dbe0`.

The same locally built watcher was observed on naphtali, benjamin and judah
over host-key-pinned Tailscale SSH. Each Darwin ARM64 build `25G332` verified
its hash and strict ad-hoc signature, then passed the short ordered-heartbeat,
exit, fork and exec cases plus the existing WP01 tests. The test-owned files
were removed. Watcher source SHA-256:
`60243bb75e7824b51e7a866b7f9e19daf09475e5024bdfa470fe4d3bcc1d4e41`;
signed watcher SHA-256:
`1fdff12c551e847948096c96bf4037d91aee540310ca9947f43c9dda20d3869b`;
observer and test helper SHA-256:
`43999a9a4e750d7f62f5b41df40057c82796465ad9e8ec721c9becb1a8ad82c2` /
`eadae9fd7485780fe30fc0cd7bfd877dadac3ea0f54309dff3e3f174317e3f03`.
The compiler and packager were the earlier pinned diagnostic artifacts
`920954769b8fdc51cf50dfcab5c44a4e56cf01f261806a153b21488ba81ac4e6` /
`f726f9dd8a4f169187275797a74d55ad3c62cc5f681cd31f19e1a28d67834f8d`.

A heartbeat is not proof that the workload is safe or stopped. Sequence and
request binding do not authenticate the pipe or prove freshness of buffered
frames. A trusted host must drain and authenticate the pipe, use an independent
monotonic deadline and treat missing, stale, partial, malformed or unavailable
observations as unknown. The helper does not kill a workload, contain
children, enforce resource limits, recover reservations or qualify a governor.
No model or persistent service was started, and no selfhost release artifact
was qualified. These short tests do not prove long-duration reliability.
