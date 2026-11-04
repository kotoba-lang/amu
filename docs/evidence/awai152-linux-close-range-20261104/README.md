# Linux ARM64 close-range compatibility candidate

Xavier's Linux 5.10.120-tegra returns EINVAL for `close_range(..., 4)`
(CLOSE_RANGE_CLOEXEC), while `close_range(..., 0)` succeeds. The existing
ARM64 process-spawn runtime refuses with `spawn/isolation-unavailable`; the
trap alone does not identify which isolation step failed. The related real
systemd attempt and its limits are recorded in
[Murakumo evidence](https://github.com/kotoba-lang/murakumo/blob/f952ea25b5642adb9141d1a75a147a09a279bbee/docs/evidence/awai150-publication-unknown-20261104/README.md).

The candidate changes ARM64 only. On EINVAL from the CLOEXEC form, it first
performs the existing scope-directory change, marks the child status pipe
close-on-exec, and closes the two ranges around that pipe with flags zero.
All setup errors fail closed and remain classified by stage. Other initial
errors, including ENOSYS and EPERM, still refuse. This preserves the status
pipe for pre-exec failure reporting; the caller must not treat the direct
child as a whole-process-tree or resource boundary.

An independent test-only Python syscall observer on Xavier executed an owned
child. Its success case checked that deliberately inherited FDs 50 and 200
were absent after exec, the scope cwd was correct and `NoNewPrivs` was set.
An injected first-range failure returned status `close-failed`, exit 127 and
no execution marker. The observer is
`scripts/seed/observe-spawn-close-range-legacy.py`; it does not execute the
Kotoba runtime or prove the candidate's actual machine code. Only owned test
processes and temporary files were used.

Four signed local Darwin source-unity diagnostics compiled the actual candidate
functions with syscall stubs and a test-only return of the selected stage.
They observed legacy EINVAL -> exec stage 4, existing fast path -> stage 4,
initial EPERM -> isolation stage 1, and legacy close failure -> stage 1. The
source/image SHA-256 pairs were:

- legacy: `2e9ee034a487999334a30f41aea1d53f9d4f437489ea3fa8abfa6850639e2035` / `d8effd53b3eb791904798b74cbd9ba92b35af0ef5c6c5e8eca322e349df098bd`
- fast: `ecb4255c4b4ce1d97df8a1043c07c13d9e2ecdd592e2c7b73d8a8616fef780b5` / `69ef04e722cc2486c6a57171e6921e1ba4a7a40e7a93c180e3378dd976c4cc62`
- denied: `8e04d972806b2d4ad6a06a6cf9f4f45bb197b4e5e0b5918216ecd73582f3576e` / `1410e7f725809737e031444c4d96a0fdd98e5dd958230c4f8365dd0e10432ea0`
- legacy close failure: `23c8b047b663367e4f6cf2314ce8e27b6d9c15638f8c3142282c94f30194e5c9` / `59d5e45adc4d862850676e6fa2ce0b678e2a57ba7f836a2de2b18fbc97fd4474`

These are selected, stubbed source tests, not a rebuilt Linux compiler or
actual runtime validation. A source-locked selfhost rebuild, actual Xavier
execution, injected failures at each syscall, exact error/status behavior,
other kernel controls, and descriptor-leak/security review remain required.
No generator output, compiler binary, deployed service, or model was changed.

## Candidate-runtime CI gate

The diagnostic script now supports two seccomp-injected cases intended to use
a source-derived `F1.elf` compiler: flags 4 -> EINVAL while flags
0 remains available must execute; flags 4 -> EINVAL plus flags 0 -> EPERM must
refuse before the execution marker. The profiles' errno, argument index and
flag values were checked locally. The Docker/seccomp cases and the candidate runtime have not yet run. A workflow
change exists only in local commit `f9430e6a`: GitHub rejected its push because
the current OAuth token lacks the `workflow` scope. No CI wiring is claimed.

On PR head `a14c1b09`, the `controls` and `qualify` checks failed because the
checked-in root/product source-unity descriptors match the prior runtime
source rather than this change. That is a genuine regeneration/provenance
requirement, not evidence of a passing candidate. Descriptor hashes or compiler
binaries were not hand-edited. The qualified selfhost rebuild and safe
regeneration path remain prerequisites to resolve it.

## Expanded owned-child syscall controls

The updated observer (SHA-256
`5963c29896b73c2d2e6d4b2728b401207a994f682dec4b1819fe94852b36adf3`)
ran on the same Xavier kernel. In separate owned children it injected a
failure at the first close range, second close range, status-pipe fcntl,
scope fchdir and no-new-privileges setup; each returned its expected failure
on the status pipe and did not create the execution marker. A nonexistent
executable produced `exec-failed:2` through the still-open status pipe and no
marker. The success case again verified the two inherited descriptors, cwd
and NoNewPrivs after exec. These are direct syscall diagnostics with
Python-controlled fault selection, not calls through the changed Amu runtime,
seccomp fault profiles, source-locked selfhost output or a qualified governor.

## Low status-descriptor boundaries

The owned-child observer was extended to move the status pipe to FD 3 and FD 4
before the legacy close sequence. Both cases passed on Xavier: the test FDs 50
and 200 were closed, the cwd and NoNewPrivs assertions held, and the
close-on-exec status pipe closed. The prior six failure controls
also passed. Observer SHA-256:
`4be748aafeb73baefc8f04409215c421a18dfc3cae2ae8383cd8b01f5dba4446`.
This exercises direct system calls through the diagnostic observer, not the
candidate Amu runtime or a source-locked compiler build.

## Source-derived runtime on Xavier

The ARM64 bootstrap job of [Actions run 41833823850](https://github.com/kotoba-lang/amu/actions/runs/41833823850)
at PR head `a0dac512` succeeded. Its receipt pins this runtime source SHA-256
`595adeb9fbd706a48b7c1155394f86c49a8e844949e8edb291c0a8b3b1681862`;
F2 and F3 match SHA-256
`46fce6f620a73d91c7ec482687856a3354646f416e05085a6fa61022d37a5e0b`.
The original root did not reproduce the new image, so this is not a root repin
or proof that descriptor identity checks passed.

The F3 compiler built the test-only Kotoba guest
`seed/tests/awai152-linux-close-range/native-spawn-probe.kotoba` (SHA-256
`f77655e5546cc022c8d2dcf79384d71e9c7d8a527a26b09941a49b4ee92e4c56`) to
Linux ARM64 image SHA-256
`1a4de8b2105a92b24c59f0a3e911a65e8f5151c83aa3e9681e61c453e1c2fa45`.
`scripts/seed/observe-spawn-legacy-native.py` (SHA-256
`9eb63b7f9f2d13f5ba4a1f71da9721891849719133dfeaef065133b0ca903c0b`)
staged it on Xavier over host-key-checked Tailscale SSH. The actual generated
runtime spawned a scoped test shell which confirmed that intentionally
inherited FDs 50/200 were absent, cwd was the scope, and NoNewPrivs was set.
A granted nonexistent executable produced exit 126 `spawn/exec-failed`;
a test-only outer seccomp filter denying close_range flags 0 produced exit 126
`spawn/isolation-unavailable`. Both negative cases had no execution marker.
The compiler and guest were limited to 3/4 seconds CPU, 8 GiB virtual address
space and a sampled 200 MiB RSS termination threshold; sampling is not a hard
RSS limit. Only task-owned temporary artifacts were created and retained.

This validates selected real candidate-runtime paths on one old-kernel host,
not all descriptors or failure stages, actual systemd under every failure,
source-lock qualification of the product, descendant containment, resource
governance, or deployment. Full evidence and the separate real systemd count
recovery are in the linked Murakumo evidence above.
