#!/bin/sh
# CROSS-TICK TWO-BATCH SIGN PROBE, LONG GAP (JUN-58, tick 20261020-0530):
# batch A already exists -- the 0006 tick's batch B logs (00:08:36--00:09:48
# JST, Oct 20), copied here byte-identical as run-A-*.log (sha256 in
# README). This script runs batch B NOW, in a later cron tick / fresh
# process, hours after batch A ended.
#
# WHY CROSS-TICK. The 2254 tick proved a >=30 min gap cannot fit this
# platform's 1800 s run budget INSIDE one tick (3 evidences); the 2337 tick
# bounded within-session stability at a 6m52s gap (no flip); the 0006 tick
# added the first >=30 min cross-tick datum (70m26s, no flip). The flip-RATE
# question needs more cross-session transitions (0006 README), and each
# cross-tick batch adds exactly one. This probe is explicitly labeled
# CROSS-SESSION and cannot isolate "gap" from "session restart"; a FLIP or a
# no-flip is reported as a cross-tick datum only. A no-flip bounds nothing
# against a stochastic flip rate.
#
# PROBE IDENTITY. The probe bytes are the chain's pinned sha256 3696ca0d...
# (the 2254/2337/0006 runs all used these exact bytes). origin/main's
# scripts/test-gpu-subgroup-reduce-chunksweep.cljk has SINCE ADVANCED
# (3c965429 gap signs from paired round samples, 55da4342 COULD-NOT-RUN,
# 25089b82 bound the init dispatch grid; 66742df7 at this tick's base) and
# computes GAP differently -- so batch B runs the PINNED copy
# scripts/gpu-subgroup-reduce-chunksweep-pinned-3696ca0d.cljk (byte-identical
# to the chain, verified by sha256 before every use). Its root resolution
# (script dir / .. = repo root) is why the pinned copy lives under scripts/.
# Fixtures identical to the chain (w64 a25a6931..., self-printed by every
# SHAPE line).
#
# BASE NOTE. Batch A ran on origin/main 068ec02d; batch B runs on e8f2ae61.
# Runtime code delta between the bases is only tools/kexe_gpu_vulkan.c
# (KGPU_MAX_KEPT 4 -> 8 kept command-buffer slots; this probe keeps slots
# 0..2, so the submitted command buffers and the executed dispatch path are
# identical). Everything else in the delta is src compiler namespaces the
# probe does not consult (runner_*), test/docs/scripts.
#
# GAP PROVENANCE. The wall-clock window between batch A (ended 00:09:48 Oct
# 20) and batch B (this run) carried NO GPU probe traffic recorded by any
# amu-gpu evidence dir; the intervening ticks 0028/0347/0422/0445 were
# kernel-emission and CPU gate-suite work. Other sessions' traffic on this
# host is not ruled out.
#
# SHAPE/PROTOCOL. lanes 2,095,104 for both cells; 3 runs per cell, cell
# order rotated per run-pair (t31,t32 / t32,t31 / t31,t32); fresh kbb
# process per run; `date; uptime` recorded per run. Idempotent: a run whose
# log exists is skipped. Usage: run-sweep.sh B
set -e
cd "$(dirname "$0")/../../../.."
EV=docs/evidence/gpu/crosstick-gap-0006B-w64t32-20261020
PROBE=scripts/gpu-subgroup-reduce-chunksweep-pinned-3696ca0d.cljk
mkdir -p "$EV"
B="$1"
case "$B" in B) ;; *) echo "usage: $0 B" >&2; exit 2;; esac

# the probe bytes are the chain's or nothing: refuse to run anything else
echo "3696ca0db0e28c5b41fa5c8551df2ae1302deb190e91722408117a06077ef652  $PROBE" | shasum -a 256 -c - >/dev/null

run() { # pair-pos cell W chunks
  log="$EV/run-$B-$1-$2.log"
  if [ -f "$log" ] && grep -q "RESULT\tverified=true" "$log"; then echo "skip $log"; return 0; fi
  echo "run $log"
  (date; uptime; time kbb --backend sci "$PROBE" "$3" 2095104 "$4") > "$log" 2>&1
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
