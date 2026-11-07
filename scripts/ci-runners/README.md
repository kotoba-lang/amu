# amu self-hosted CI runners (ADR 0407, JUN-852)

Design: `docs/adr/0407-self-hosted-ephemeral-oci-runners-for-amu-ci.md`. Nothing here is run by CI except
the two checks below; the launchers are dry-run unless `--apply` and are meant to be started by the owner.

| file | purpose |
| --- | --- |
| `runs_on.cljc` | single definition of the variable-driven `runs-on`; `--write` renders, `--check` verifies |
| `test_runs_on.cljc` | fork-PR / profile matrix over the rendered workflow text (negative controls) |
| `capacity.cljc`, `test_capacity.cljc` | online-runner and queue monitor; sets `AMU_RUNNER_PROFILE=hosted` on `--apply` |
| `linux/Containerfile` | arm64 / x64 runner image; `RUNNER_VERSION`, `RUNNER_SHA256`, `RUNNER_ARCH` required |
| `launch-linux.sh` | keeps N one-job JIT runner containers alive (podman, digest-pinned image) |
| `launch-macos.sh` | one Tart VM per job from a digest-pinned OCI image, softnet blocks tailnet/LAN |
| `netpolicy.nft` | nftables drop of tailnet/LAN/link-local for the Linux runner VM |

Checks (python3 only, no JVM/nbb):

```sh
basilisp run scripts/ci-runners/runs_on.cljc -- --check
PYTHONPATH=scripts/ci-runners basilisp test --rootdir scripts/ci-runners scripts/ci-runners/test_runs_on.cljc
PYTHONPATH=scripts/ci-runners basilisp test --rootdir scripts/ci-runners scripts/ci-runners/test_capacity.cljc
```

## Switch

`AMU_RUNNER_PROFILE` (repository variable): unset or `hosted` = GitHub-hosted (default),
`selfhosted-arm` = arm64 Linux + macOS on `amu-linux-arm64` / `amu-macos-arm64`, `selfhosted` = also
x86_64 on `amu-linux-x86_64`. Fork PRs always stay hosted. Back to hosted:
`gh variable set AMU_RUNNER_PROFILE --body hosted -R kotoba-lang/amu`.

## Caveats the owner must handle

- `netpolicy.nft` hooks `forward`. Rootless podman with pasta/slirp4netns does not traverse it; use
  netavark with a bridge network (rootful podman in the VM, or `--network` with the rules applied to that
  bridge), then verify from inside a container that `curl 100.x`/LAN addresses fail and github.com works.
  This verification is part of acceptance before any runner is registered.
- Public egress is not allowlisted yet (see ADR); only private ranges are blocked.
- `qualify-arm64-runtime` (docker) and `wasm32-browser-chrome` (Chrome) stay hosted.
- Monitor token needs Administration, Actions read and Variables read/write.
- Do not reuse the persistent `mithril-actions` runner on benjamin.
- Never put the launcher token into the VM, an image layer or a log; JIT blobs are single use.
- Image digests and the runner tarball SHA-256 are filled in by whoever builds the images.
