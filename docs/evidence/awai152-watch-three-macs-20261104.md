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
