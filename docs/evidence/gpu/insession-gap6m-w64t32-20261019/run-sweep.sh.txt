#!/bin/sh
# IN-SESSION TWO-BATCH SIGN PROBE AT A 6-MIN PROBE-IDLE GAP (JUN-58, tick 20261019-2337):
# run the flip cell (w64t32) and its anchor (w64t31) as TWO batches of 3
# runs each, BOTH INSIDE ONE cron session, separated by a ~6 min
# probe-idle gap.
#
# WHY 6 MIN. The 2254 tick proved a >=30 min gap cannot fit this platform's
# 1800 s run budget (agent.log budget notices + executions.db: longest tick
# ever 30.4 min + the budget notice arriving while holding the gap). Its
# handoff sized the maximum feasible in-session gap at ~8-10 min after
# setup + two ~2 min batches + analysis + commit + PR. This tick takes a
# 6 min hold to keep the wrap-up inside the budget with margin (the 2221
# and 2254 ticks both died during their gap hold). A FLIP here bounds the
# flip timescale from above at ~6 min and proves no session boundary is
# required; a no-flip is a within-session sign-stability datum at a
# multi-minute gap and bounds nothing against a stochastic flip rate --
# reported as such.
#
# SHAPE/PROTOCOL. Byte-identical probe (sha256 3696ca0d...) and fixtures
# (w64 a25a6931..., w32 0cf6c406..., w128 c7931718..., w256 087107f9...,
# as printed by every SHAPE line) to the #1369/#1377/#1378/#1380/#1382
# chain. lanes 2,095,104 for both cells; 3 runs per cell per batch, cell
# order rotated per run-pair (t31,t32 / t32,t31 / t31,t32); fresh kbb
# process per run; `date; uptime` recorded per run. Idempotent: a run
# whose log exists AND carries its RESULT line is skipped; a partial log
# (interrupted kbb) is re-run. Usage: run-sweep.sh A|B
#
# BASE NOTE. This worktree is based on origin/main 3b4ea5ea, which merges
# KEXE_GPU_BARRIER_TRACKED (dispatch barriers via driver hazard tracking,
# MoltenVK -25.7%) AFTER the chain's base. Absolute ns/dispatch values are
# therefore not comparable to the chain's sessions; the within-tick A/B
# comparison is self-consistent on one base.
set -e
cd "$(dirname "$0")/../../../.."
EV=docs/evidence/gpu/insession-gap6m-w64t32-20261019
mkdir -p "$EV"
B="$1"
case "$B" in A|B) ;; *) echo "usage: $0 A|B" >&2; exit 2;; esac

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
