#!/bin/bash
# Full suite gate for PR #1385 state (ebc57f45) — run to completion.
cd /Users/junkawasaki/github/wt/amu-gpu/gate-1385-20261020-0347
OUT=/Users/junkawasaki/.hermes/profiles/amu-gpu/cache/scratch/gate-1385-full.log
{
  echo "=== gate start $(date '+%F %T %Z') ==="
  echo "=== HEAD $(git rev-parse HEAD) ==="
  kbb --backend sci --classpath "src:test:$(kbb -Spath -M:test)" run-tests.cljk
  echo "=== gate exit $? $(date '+%F %T %Z') ==="
} > "$OUT" 2>&1
