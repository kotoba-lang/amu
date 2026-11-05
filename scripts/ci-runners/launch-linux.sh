#!/bin/sh
# Keep N ephemeral amu runner containers alive on this host (inside the Linux VM). One JIT runner per
# container, container removed when its job ends. Dry-run unless --apply. Not run by CI.
#   launch-linux.sh --label amu-linux-arm64 --image <registry>/amu-ci-runner@sha256:... --slots 2 [--apply]
# Credential: GH_TOKEN must already be in the environment (owner-provided, repo-scoped); never printed.
set -eu
REPO=kotoba-lang/amu
label= image= slots=2 apply=0
while [ $# -gt 0 ]; do case $1 in
  --label) label=$2; shift 2;; --image) image=$2; shift 2;; --slots) slots=$2; shift 2;;
  --apply) apply=1; shift;; *) echo "unknown $1" >&2; exit 2;; esac; done
[ -n "$label" ] && [ -n "$image" ] || { echo "need --label and --image" >&2; exit 2; }
case $image in *@sha256:*) ;; *) echo "image must be pinned by digest" >&2; exit 2;; esac
if [ "$apply" = 0 ]; then
  echo "dry-run: would keep $slots containers of $image as label $label for $REPO"; exit 0; fi
: "${GH_TOKEN:?GH_TOKEN required}"
run_one() {
  name="amu-$label-$(hostname -s)-$$-$1-$(date +%s)"
  jit=$(gh api -X POST "repos/$REPO/actions/runners/generate-jitconfig" \
        -f name="$name" -F runner_group_id=1 -f 'labels[]='"$label" -f work_folder=_work --jq .encoded_jit_config)
  # JIT blob goes to the container by env only; no token, no mounts, tmpfs work dir, no extra caps.
  ACTIONS_RUNNER_JITCONFIG=$jit podman run --rm --name "$name" --cpus 4 --memory 4g --pids-limit 4096 \
      --cap-drop ALL --security-opt no-new-privileges --read-only --tmpfs /home/runner/_work:rw,exec,size=24g \
      --tmpfs /tmp:rw,exec,size=4g -e ACTIONS_RUNNER_JITCONFIG "$image" || true
}
i=0
while :; do
  while [ "$(podman ps -q --filter name="amu-$label-" | wc -l)" -ge "$slots" ]; do sleep 2; done
  i=$((i + 1)); run_one "$i" &
  sleep 1
done
