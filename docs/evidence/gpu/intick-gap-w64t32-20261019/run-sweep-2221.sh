#!/bin/sh
# STRICTLY-INSIDE-TICK TWO-BATCH SIGN PROBE (JUN-58, tick 20261019-2221):
# run the flip cell (w64t32) and its anchor (w64t31) as TWO batches of 3
# runs each, BOTH INSIDE ONE CRON SESSION, separated by a >=30 minute
# probe-idle gap held with foreground waits.
#
# CONTEXT. PR #1380 ran the same two batches but batch B fell into the
# FOLLOWING cron session (37 min 28 s wall-clock gap, probe-idle), so its
# conclusion "the sign does not reset at every session boundary" carried an
# explicit protocol deviation: the strict "inside one tick" question was
# left open. This probe closes it: one session, one process tree, one
# worktree, >=30 min gap. Cross-session series at the identical shape
# (w64t32, wg=1023, lanes 2,095,104): + (#1369) / - (#1377) / + (#1378) /
# +/+ (#1380 batches A/B).
#
# SHAPE/PROTOCOL. Byte-identical probe (sha256 3696ca0d...) and fixtures
# (w64 a25a6931..., w32 0cf6c406..., as printed by every SHAPE line) to the
# #1369/#1377/#1378/#1380 chain. lanes 2,095,104 for both cells; 3 runs per
# cell per batch, cell order rotated per run-pair (t31,t32 / t32,t31 /
# t31,t32); fresh kbb process per run; `date; uptime` recorded per run.
# Idempotent: a run whose log exists is skipped. Usage: run-sweep-2221.sh A|B
set -e
cd "$(dirname "$0")/../../../.."
EV=docs/evidence/gpu/intick-gap-w64t32-20261019
mkdir -p "$EV"
B="$1"
case "$B" in A|B) ;; *) echo "usage: $0 A|B" >&2; exit 2;; esac

run() { # pair-pos cell W chunks
  log="$EV/run-$B-$1-$2.log"
  if [ -f "$log" ]; then echo "skip $log"; return 0; fi
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
