#!/bin/bash
# Shared coordination signal for amu co-scientist cowork bots.
# Prints a deterministic, timestamp-free snapshot of the tournament state.
cd ~/github/com-junkawasaki/orgs/kotoba-lang/amu || exit 1
git fetch -q origin 2>/dev/null
echo "=== NEXT ==="
grep -m1 "NEXT:" docs/codegen-coscientist.md || echo "none"
echo "=== OPEN HYPOTHESES ==="
grep -E "^\| H-" docs/codegen-coscientist.md | grep -E "open|pending" | cut -c1-160 || echo "none"
echo "=== LAST ADR ==="
ls docs/adr 2>/dev/null | tail -3 || ls 90-docs/adr 2>/dev/null | tail -3
echo "=== HOST LOAD ==="
uptime
echo "=== IN-FLIGHT (uncommitted) ==="
git status --porcelain | head -10
