#!/bin/sh
# CROSS-TICK TWO-BATCH SIGN PROBE, >=30 MIN GAP (JUN-58, tick 20261020-0006):
# batch A already exists -- the 2254 tick's batch A logs (22:56:23--22:58:10
# JST, Oct 19), copied here byte-identical (sha256 in README). This script
# runs batch B NOW, in a later cron tick / fresh process, >=30 min after
# batch A ended.
#
# WHY CROSS-TICK. The 2254 tick proved a >=30 min gap cannot fit this
# platform's 1800 s run budget INSIDE one tick (3 evidences); the 2337 tick
# bounded within-session stability at a 6m52s gap (no flip). The >=30 min
# question is only reachable across ticks, which also crosses the process
# and cron-session boundary -- this probe is explicitly labeled CROSS-SESSION
# and cannot isolate "gap" from "session restart"; a FLIP or a no-flip is
# reported as a cross-tick datum only. A no-flip bounds nothing against a
# stochastic flip rate.
#
# BASE NOTE. Batch A ran on origin/main 35b45ddf; batch B runs on
# 068ec02d. Runtime code delta between the bases is only
# tools/kexe_gpu_vulkan.c (KEXE_GPU_BARRIER_TRACKED, getenv-gated, DEFAULT
# OFF -- unset here, so the executed dispatch path is identical). The probe
# is byte-identical across bases (sha256 3696ca0d...), fixtures identical
# (w64 a25a6931..., as self-printed by every SHAPE line). The gap is NOT
# probe-idle: the 2337 tick ran its 12 probe runs at 23:37--23:48 inside
# this window.
#
# SHAPE/PROTOCOL. lanes 2,095,104 for both cells; 3 runs per cell, cell
# order rotated per run-pair (t31,t32 / t32,t31 / t31,t32); fresh kbb
# process per run; `date; uptime` recorded per run. Idempotent: a run whose
# log exists is skipped. Usage: run-sweep.sh B
set -e
cd "$(dirname "$0")/../../../.."
EV=docs/evidence/gpu/crosstick-gap-2254A-w64t32-20261020
mkdir -p "$EV"
B="$1"
case "$B" in B) ;; *) echo "usage: $0 B" >&2; exit 2;; esac

unset KEXE_GPU_BARRIER_TRACKED  # batch B must not inherit the caller's override

run() { # pair-pos cell W chunks
  log="$EV/run-$B-$1-$2.log"
  if [ -f "$log" ] && grep -q "RESULT\tverified=true" "$log"; then echo "skip $log"; return 0; fi
  echo "run $log"
  (date; uptime; time kbb --backend sci scripts/test-gpu-subgroup-reduce-chunksweep.cljk "$3" 2095104 "$4") > "$log" 2>&1
  grep -q "RESULT	verified=true" "$log" || { echo "UNVERIFIED $log"; exit 1; }
}

# pair 1: t31,t32   pair 2: t32,t31   pair 3: t31,t32
run 1 w64t31 64 31
run 1 w64t32 64 32
run 2 w64t32 64 32
run 2 w64t31 64 31
run 3 w64t31 64 31
run 3 w64t32 64 32
echo "BATCH-$B-COMPLETE"
