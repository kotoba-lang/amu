#!/bin/sh
# Canonical gate for tick 20261019-1152 (JUN-58 iso-L diagonal slice).
# Run from the worktree root; log lands in docs/evidence/gpu/isodesc-l2048-20261019/gate.log.
cd "$(dirname "$0")/../../../.." || exit 2
EV=docs/evidence/gpu/isodesc-l2048-20261019
kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" run-tests.cljk > "$EV/gate.log" 2>&1
code=$?
echo "GATE-EXIT=$code" >> "$EV/gate.log"
exit 0
