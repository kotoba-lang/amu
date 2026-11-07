# ADR 0407: Self-hosted ephemeral OCI runners for amu CI, selected by one repository variable (JUN-852)

Status: proposed. The workflow change ships inert: with `AMU_RUNNER_PROFILE` unset every job runs on the
same GitHub-hosted runner as before. Installing runners, creating VMs, registering them and setting the
variable are owner actions listed under "Owner decisions".

## Problem

Measured 2026-11-05 over the last 20 runs of each amu native workflow (`selfhost-native`,
`native-definition-graph|build|cid|cids`, `native-checked-source|definition`, `native-capability-names`,
`mac-selfhost-aiueos`; 700+ jobs, `gh api .../actions/runs/<id>/jobs`, created_at -> started_at is queue
wait):

- Median queue wait is small (2-130 s) but the tail is large: p90 is 500-830 s for most `selfhost-native`
  jobs and the maximum is 700-1340 s. Waits arrive in bursts (a push starts 25+ jobs at once), so the
  critical path pays the tail, not the median.
  Examples (median / p90 / max wait, median run): `bootstrap-arm64-root` 56/745/836 s, run 285 s;
  `foundation-starter-arm64` 49/823/909 s, run 17 s; `native-definition-graph headroom-shard`
  87-123/500-750/1343 s, run 260-310 s; `qualify-arm64-gates` 48/639/760 s, run 329 s;
  `mac-root` (macos-15) 17/88/92 s, run 337 s (p90 1277 s).
- Many jobs run for 3-30 s and wait minutes: queue wait dominates them.

Raw table: `qw.txt` in the session notes; regenerate with the `gh api` query above.

## Platform requirements (why not "just any Linux")

- Native gates run machine code of the target ISA without emulation or a loader: `linux-arm64` jobs
  (`ubuntu-24.04-arm`) need an arm64 kernel, `linux-x86_64` jobs (`ubuntu-latest`) need real x86_64.
  Apple-silicon Macs run arm64 Linux VMs natively (Virtualization.framework), so arm64 Linux jobs can move
  to the Macs. x86_64 jobs must NOT run on them (QEMU/Rosetta would be emulation); they need an x86_64
  Linux host or stay hosted.
- `mac-root` (`mac-selfhost-aiueos`) asserts `Darwin`/`arm64` and runs Mach-O programs: a macOS VM (Tart)
  on an Apple-silicon Mac. Apple's licence allows at most two macOS VMs per Mac.
- `qualify-arm64-runtime` runs `docker run` fault injection and `wasm32-browser-chrome` needs
  `google-chrome`; the runner image has neither, so both stay on hosted runners
  (`hosted-only` in `runs_on.cljc`) until a nested-container service / Chrome image is qualified.
  Other tools the hosted images provide implicitly (jq, zip, ...) must exist in the image; a pilot run
  in `selfhosted-arm` is the check.
- `post-merge-repin` holds a bot token: never self-hosted (`scripts/ci-runners/runs_on.py` refuses it).

Job classes after this ADR: `linux-arm64` (12 jobs), `linux-x86_64` (about 15 jobs + matrix legs),
`macos-arm64` (1 job). Light aggregator jobs (3-5 s, ubuntu-latest) are classed `linux-x86_64`; making them
arch-agnostic is a follow-up.

## Decision

### Labels and the single switch

Repository variable `AMU_RUNNER_PROFILE` (Settings > Variables), checked in every covered `runs-on`:

| value | linux-arm64 | macos-arm64 | linux-x86_64 |
| --- | --- | --- | --- |
| unset / `hosted` | `ubuntu-24.04-arm` | `macos-15` | `ubuntu-latest` |
| `selfhosted-arm` | `amu-linux-arm64` | `amu-macos-arm64` | `ubuntu-latest` |
| `selfhosted` | `amu-linux-arm64` | `amu-macos-arm64` | `amu-linux-x86_64` |

Switching back to hosted is `gh variable set AMU_RUNNER_PROFILE --body hosted` (or deleting it); no commit.
The required check names are unchanged (job names are not touched). `scripts/ci-runners/runs_on.py
--check` fails CI-side tooling if any covered line drifts from the template or if a self-hosted label
appears anywhere else; it is the single place the expression is defined.

### Fork pull requests never reach self-hosted runners

The repository is public. Every self-hosted choice is additionally guarded by
`github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository`,
so a fork PR gets the hosted label under every profile. `merge_group`, `push`, `schedule` and
`workflow_dispatch` events come from the base repository. `scripts/ci-runners/test_runs_on.py` evaluates
every rendered expression for push, merge_group, same-repo PR, fork PR and a name-prefix lookalike
(`kotoba-lang/amu-x`) under all four profile values and fails on any deviation (it fails when the guard is
removed). A same-repo PR is by a collaborator with write access, who can already change the workflow; the
isolation below is the answer to that, not the guard.

Defence in depth, owner-side (not enforceable from the repo): put the runners in a runner group limited to
this repository, and set "Require approval for all outside collaborators" for workflows.

### Ephemeral, isolated, tokenless

- One job per VM/container, destroyed afterwards. Runners register with a JIT config
  (`POST /repos/kotoba-lang/amu/actions/runners/generate-jitconfig`, single use, `--ephemeral`
  semantics); no persistent runner registration and no `_work` reuse.
- The JIT config is minted by a small launcher on the host with a credential that never enters the VM:
  the VM receives only the one JIT config blob, via a read-only mount (Tart `--dir`) or container env that
  is not logged (`set +x`). The launcher credential is owner-provided (a fine-grained token or a GitHub
  App with `Administration: write` on this repository only, plus Variables read/write for the monitor) and stored in the host's keychain/secret file,
  never in the repo.
- No secrets are mounted; the workflows already use `permissions: contents: read` and
  `persist-credentials: false`.
- Network: the VM/container must not reach the tailnet (100.64.0.0/10), RFC 1918 LAN, link-local or the
  host's loopback; this is what `netpolicy.nft` and Tart softnet enforce. Public internet egress is NOT
  restricted to GitHub and registries by this change (arbitrary job code can reach any public host); a
  default-drop allowlist needs a controlled egress proxy and is a required follow-up before `selfhosted`
  is used for anything beyond the pilot. Reachable-by-design hosts: `api.github.com`, `github.com`,
  `*.actions.githubusercontent.com`, the Actions cache/artifact blob hosts and the registries used.
  Why the private ranges matter: the Mac forwards VM traffic, so a NATed VM can otherwise reach every tailnet node.
  Linux VM: nftables rules in `scripts/ci-runners/netpolicy.nft` (drop for those ranges).
  Tart: `--net-softnet` with `--net-softnet-block` of the same ranges.
- Images are OCI artifacts pinned by digest: the Linux runner image (`scripts/ci-runners/linux/Containerfile`,
  built per ISA, runner tarball verified against a SHA-256 supplied at build time) and the macOS base
  image (`tart pull <registry>/<name>@sha256:...`, then `tart clone` per job). Digests are recorded by the
  owner when the images are built; nothing in this repo pretends to know them.

### Layout on the Macs

Fleet inventory (read-only SSH probe, 2026-11-05): 11 Mac mini M4 class nodes (`Mac16,10`, 10 cores, 16 GB,
228 GB disk): asher, benjamin, dan, issachar, jacob, joseph, judah, levi, naphtali, simeon, zebulun, all
online, load 1.5-3.5 (they run other work). 21mbp is a MacBook Pro (not a runner host). `limactl` is
present on all minis, `podman` on jacob, `docker`+`colima` on benjamin; no `tart` anywhere. `benjamin`
already runs a persistent service runner for another project (`mithril-actions`): it must not be reused
or touched, and amu runners there need distinct names and labels. Disk free varies (jacob 20 GB).
Linux nodes `aiueos-6600hs-1` (online), `aiueos-node-260910`, `xavier`: SSH as `junkawasaki` is denied by
tailnet policy, so CPU/RAM are unknown.

Per mini, two slots (CI jobs assume 4 vCPU):

- Linux slots: one Lima (vz) arm64 Ubuntu 24.04 VM, 8 vCPU / 9 GB, rootless podman; the launcher keeps
  N containers (`--rm`, 4 vCPU, 4 GB, `--network` restricted by netpolicy) each running one JIT runner.
- macOS slot: Tart VM `--cpu 4 --memory 6144` per job (`tart clone` of the pinned image, `tart run
  --no-graphics --net-softnet`, `tart delete` after). A mini hosts either 2 Linux slots, or 1 Linux slot +
  1 macOS VM (RAM bound); at most 2 macOS VMs per host (licence).
- x86_64: needs an x86_64 Linux host (`aiueos-6600hs-1`, specs unknown). Stay hosted until it is measured.

Capacity: the `selfhost-native` run has about 12 arm64 jobs and 15 x86_64 jobs in flight at once. To keep
every arm64 job under ~1 min wait on a burst, the arm64 pool needs at least 12 slots, i.e. 6 minis
at 2 slots, ideally 8 for a second concurrent PR or merge-group run. Fewer slots turn queue wait into
self-induced queueing (2 minis = 4 slots would make wait worse than today's median). 10 reachable minis
gives 20 slots on paper; real capacity depends on the other work those machines do. The launcher should be
started on a few nodes first and capacity added until measured p90 wait < 60 s.

### Monitoring and fail-over

- `scripts/ci-runners/capacity.py` (read-only by default) lists online runners per label with
  `gh api repos/kotoba-lang/amu/actions/runners` and queued jobs older than a threshold. If no runner
  with a needed label is online, or queued self-hosted jobs wait longer than 120 s, `--apply` sets
  `AMU_RUNNER_PROFILE=hosted`. Jobs already queued for a dead label need a re-run (`gh run rerun
  --failed`); the script prints them. It runs from a scheduled job on a host the owner chooses, with the
  same launcher credential. Switching back to self-hosted is manual.
- The queue-wait table above is the acceptance measurement: re-run the query after cut-over.

## Rollout (each step after the owner's go-ahead)

1. Merge this ADR, the variable-driven `runs-on` and the tooling (inert).
2. Build images, install Lima/podman or Tart, start the launcher on 2 nodes, register nothing permanent.
3. Set `AMU_RUNNER_PROFILE=selfhosted-arm` for one day: compare wait/run time and gate results to hosted.
4. Add nodes to reach >= 12 arm64 slots; then decide x86_64 and `selfhosted`.

## Not changed

Gates, argv, required check names, caching and the 20-30 minute timeouts. Pin regeneration (ADR 0404)
and artifact reuse are other work. Nothing here removes the hosted fallback.

## Owner decisions

- Which nodes host runners, and permission to install Lima/podman and Tart there.
- A launcher credential scoped to this repository (Administration write for JIT runners; `capacity.py` also needs Actions read and Variables read/write) or an App, kept on the hosts.
- Runner group restricted to this repository; workflow approval setting for outside collaborators.
- SSH access to the Linux nodes (or their specs) to decide x86_64.
- Apple macOS licence limit (2 VMs per host) and Tart licence terms accepted for this fleet.
