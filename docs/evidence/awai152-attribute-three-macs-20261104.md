# Native spawn attribute readback on three Macs

On 2026-11-04, GitHub Actions Mac job
[41787944611](https://github.com/kotoba-lang/amu/actions/runs/41787944611)
compiled the Kotoba diagnostic emitter and checked its output bytes. Its
artifact, CI log and local hash agreed on the 248-byte attribute SHA-256
`b12a84b3612e3e81416007a043b20535c6e1a70b699df37fa2146f02c632c6ec`.
The source SHA-256 was
`76ee750007f03732bb98a7dd6daef98d189c662575d81deb509e072c830c8a63`;
the emitter fixture SHA-256 was
`27ab6f932ac1407f16f3a1219f67fb75954b675c72b0a76877d414658a48a36d`.

The exact attribute bytes were sent to naphtali, benjamin and judah over
Tailscale SSH with previously pinned host keys. On each ARM64 Mac build
`25G332`, the diagnostic used those bytes in Darwin spawn syscall 244 for
one owned `/usr/bin/true`. The child was observed stopped; an independent
privileged `memorystatus_control` readback returned active/inactive limits
`[64, 1, 64, 1]`. After resume the child exited 0 and was reaped. Each
task-owned temporary directory was removed by its SSH invocation. The
target observer SHA-256 was
`e7c064de03e033ef98d56ecf9aee6cb7e2892d60f143d57f3c31866ef7dc7016`.

This confirms a single attribute-setting/readback sample per host. It does
not exercise a memory limit, GPU/unified memory, actual inference, children
or descendants, daemon containment, a scheduler, restart recovery, or a
qualified governor. No target build, model, or persistent service was run.
