#!/bin/sh
# IN-SESSION TWO-BATCH SIGN PROBE, MAX-FEASIBLE GAP (JUN-58, tick 20261019-2254):
# run the flip cell (w64t32) and its anchor (w64t31) as TWO batches of 3
# runs each, BOTH INSIDE ONE cron session, separated by the longest
# probe-idle gap that fits this platform's 1800 s run budget.
#
# WHY THE GAP IS NOT >=30 MIN. The 2221 tick designed a strictly-inside-tick
# probe with a >=30 min gap; that design is INFEASIBLE here: the agent run
# budget is 1800 s (agent.log: "Run budget wrap-up notice injected
# (budget=1800s, ...)"; executions.db: no tick has ever run past 30.4 min),
# and setup + two batches + analysis + PR already consume ~15 min. So the
# strict ">=30 min inside one tick" question cannot be answered on this
# platform as designed. This probe asks the largest in-session question that
# IS answerable: can the w64t32 sign flip between two batches inside one
# session at a multi-minute probe-idle gap? A FLIP here bounds the flip
# timescale from above and proves no session boundary is required; a no-flip
# is the first within-session sign-stability datum across a multi-minute gap
# (every earlier session only ran one ~1.5 min batch) and bounds nothing
# against a stochastic flip rate -- reported as such.
#
# SHAPE/PROTOCOL. Byte-identical probe (sha256 3696ca0d...) and fixtures
# (w64 a25a6931..., w32 0cf6c406..., w128 c7931718..., w256 087107f9...,
# as printed by every SHAPE line) to the #1369/#1377/#1378/#1380 chain.
# lanes 2,095,104 for both cells; 3 runs per cell per batch, cell order
# rotated per run-pair (t31,t32 / t32,t31 / t31,t32); fresh kbb process
# per run; `date; uptime` recorded per run. Idempotent: a run whose log
# exists is skipped. Usage: run-sweep.sh A|B
set -e
cd "$(dirname "$0")/../../../.."
EV=docs/evidence/gpu/insession-gap-w64t32-20261019
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
