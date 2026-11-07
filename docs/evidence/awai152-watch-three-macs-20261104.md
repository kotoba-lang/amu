# Experimental watcher observation on three Macs

On 2026-11-04, a signed watcher fixture from GitHub Actions run
[41785922426](https://github.com/kotoba-lang/amu/actions/runs/41785922426)
was checked on naphtali, benjamin and judah. SSH used the existing pinned
host keys and Tailscale addresses. The CI artifact and log agreed on the
signed image SHA-256
`7e77d7b5ae33a10aea7a47237f9edd66356d8dfe7d8a9c3f3f4aef99c4e6c50a`,
and its source matched the local source SHA-256
`43e5eebcbc7c3d0ee86d2175b8ab4c01c94de7f5e693da4a8bcd4f641a75b9d3`.
Strict codesign verification passed locally and on each target. The target
observer and its staging helper had respective SHA-256 values
`a5f942dc3436541e47eb248644161af137fea11ca33dc7928e1097777b1420cd`
and `dc0da377c5c8f6c92f741c8bc7dc5d5c01ee442c4aa1f41970f9c9a7539b5de9`.

All three reported arm64, macOS build `25G332`, and passed one bounded
owned-child observation: exact exit-event frame, rejection of a different
start time while the child was live, rejection after a one-second timeout
while it remained live, and rejection after it had been reaped. Each SSH
invocation created a private task-owned temporary directory and removed it
on exit. No model, persistent service, or build was started on the targets.

This is a one-run ABI and framing observation, not evidence of complete
descendant termination, daemon containment, lock lifetime, memory/CPU
enforcement, crash recovery, durable reservation, or a qualified governor.
It does not authorize inference dispatch or FIFO release.

On the same date a second run on all three hosts repeated the cases above
and used a separate owned child killed with SIGKILL after watcher startup.
Each watcher returned its exact exit-event frame while an independent
`wait` returned SIGKILL. The frame itself carries no successful workload
result and must never be used as one. The observer in this run had SHA-256
`8844e3bb812a42d411b048b4b006041dff98cf2cc40b7bed61949359a4c9388d`;
the signed watcher and staging helper pins were unchanged. The fixed-delay
test does not establish all possible registration races or crash recovery.
# Ready frame and stopped-child transitions

On 2026-11-04, GitHub Mac job [41793197780](https://github.com/kotoba-lang/amu/actions/runs/41793197780) produced a signed watcher from source SHA-256 `a387d7ec0d4b991ffdc2b29b83bdd3d948af3b9a4a5cd5badbbee5c261c9cf2c`. The CI log, artifact receipt, and downloaded signed image agreed on SHA-256 `0c7d6496a9b25ca9781152e6046751d259ee67433d87e92fb7d3ce5b04ff6dbf`; strict code signature verification passed. This source is identical to the current watcher source; the later host test used the updated stopped-child test harness from commit `58bd6748`, not the older CI test harness.

The pinned watcher and the task-owned observer were sent over host-key-pinned Tailscale SSH to naphtali, benjamin and judah, all Darwin ARM64 build `25G332`. Each host verified the hash and signature and returned the expected normal exit event, rejected a wrong birth identity, timeout and already reaped PID, and observed that a SIGKILLed child also produces an exit event. In separate owned-child tests, the harness observed the child stopped, started the watcher, checked its exact request-bound ready frame while it was alive, resumed the child and triggered an exec or fork. Both events caused the watcher to refuse a successful final frame on each host. Temporary files were removed and children reaped.

Observer SHA-256: `abcf4a24552963861cd3ac46d162ce5edb80dec613653cef6c40c00ab17ae776`; imported test harness SHA-256: `fa178f85028c30ea12c903b2149b294310da2e16bd19fee184326253636f5770`. These are bounded event observations. They do not prevent exec or fork, prove complete process-tree termination, enforce a workload budget or GPU memory, authenticate a production supervisor, handle crash recovery, or qualify the governor. A watcher exit event does not establish successful workload completion. No model or persistent service was run.
