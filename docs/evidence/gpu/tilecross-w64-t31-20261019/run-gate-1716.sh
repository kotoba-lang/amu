#!/bin/sh
# Canonical gate for tick 20261019-1716 (JUN-58 W=64 tile-crossing bisection,
# tiles=31 cell at lanes 2,095,104). Run from the worktree root; log lands in
# docs/evidence/gpu/tilecross-w64-t31-20261019/gate.log.
cd "$(dirname "$0")/../../../.." || exit 2
EV=docs/evidence/gpu/tilecross-w64-t31-20261019
kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" run-tests.cljk > "$EV/gate.log" 2>&1
code=$?
echo "GATE-EXIT=$code" >> "$EV/gate.log"
exit 0
