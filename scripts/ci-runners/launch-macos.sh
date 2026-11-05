#!/bin/sh
# One ephemeral macOS VM per job with Tart (ADR 0407). Dry-run unless --apply. Not run by CI.
#   launch-macos.sh --image <registry>/amu-macos@sha256:... [--apply]     (max 2 concurrent VMs per host)
# The base image has the Actions runner at /Users/admin/actions-runner and a LaunchDaemon that runs
#   run.sh --jitconfig "$(cat /Volumes/My Shared Files/jit/config)" then powers off.
set -eu
REPO=kotoba-lang/amu
LABEL=amu-macos-arm64
image= apply=0
while [ $# -gt 0 ]; do case $1 in
  --image) image=$2; shift 2;; --apply) apply=1; shift;; *) echo "unknown $1" >&2; exit 2;; esac; done
case $image in *@sha256:*) ;; *) echo "image must be pinned by digest" >&2; exit 2;; esac
if [ "$apply" = 0 ]; then echo "dry-run: would run one tart VM per job from $image as $LABEL"; exit 0; fi
: "${GH_TOKEN:?GH_TOKEN required}"
tart pull "$image"
while :; do
  vm="amu-$(hostname -s)-$(date +%s)"; dir=$(mktemp -d); chmod 700 "$dir"
  gh api -X POST "repos/$REPO/actions/runners/generate-jitconfig" -f name="$vm" -F runner_group_id=1 \
     -f 'labels[]='"$LABEL" -f work_folder=_work --jq .encoded_jit_config > "$dir/config"
  tart clone "$image" "$vm"
  # softnet blocks tailnet/LAN; the VM sees only the public internet.
  tart run --no-graphics --dir="jit:$dir:ro" --net-softnet \
      --net-softnet-block=100.64.0.0/10,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,169.254.0.0/16 "$vm" || true
  tart delete "$vm"; rm -rf "$dir"
done
