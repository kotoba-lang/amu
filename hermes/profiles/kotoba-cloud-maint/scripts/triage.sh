#!/bin/bash
cd ~/github/com-junkawasaki/orgs/kotoba-lang/app-kotoba-cloud || exit 1
R=kotoba-lang
{
echo "=== fetch ==="
git fetch $R --prune 2>&1 | head -20
echo "=== origin/main log (last 8) ==="
git log --oneline $R/main -8 2>&1
echo "=== HEAD vs main ==="
git rev-parse HEAD; git rev-parse $R/main
echo "=== CI runs (kotoba-lang) ==="
gh api repos/kotoba-lang/app-kotoba-cloud/actions/runs --jq '.workflow_runs[0:8][] | "\(.created_at) \(.name) \(.conclusion) \(.head_branch)"' 2>&1
echo "=== open issues ==="
gh issue list --repo kotoba-lang/app-kotoba-cloud --state open --limit 30 2>&1
echo "=== open PRs ==="
gh pr list --repo kotoba-lang/app-kotoba-cloud --state open --limit 30 2>&1
} > ~/.hermes/profiles/kotoba-cloud-maint/scripts/triage.txt 2>&1
exit 0
