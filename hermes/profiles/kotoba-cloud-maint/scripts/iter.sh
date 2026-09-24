#!/bin/bash
cd ~/github/com-junkawasaki/orgs/kotoba-lang/app-kotoba-cloud
echo "=== date ==="; date
echo "=== / ==="; curl -s -o /dev/null -w "%{http_code}" https://kotoba.cloud/; echo
echo "=== /en/ ==="; curl -s -o /dev/null -w "%{http_code}" https://kotoba.cloud/en/; echo
echo "=== /health ==="; curl -s -w "\n%{http_code}" https://kotoba.cloud/health; echo
echo "=== 404 probe ==="; curl -s -o /dev/null -w "%{http_code}" https://kotoba.cloud/404-page; echo
echo "=== random 404 ==="; curl -s -o /dev/null -w "%{http_code}" https://kotoba.cloud/zz-maint-$(date +%s); echo
echo "=== api ==="; curl -s -w "\n%{http_code}" https://api.kotoba.cloud/v1/control-plane; echo
echo "=== issues ==="; gh issue list --repo kotoba-lang/app-kotoba-cloud --state open --limit 20 2>&1
echo "=== prs ==="; gh pr list --repo kotoba-lang/app-kotoba-cloud --state open --limit 20 2>&1
echo "=== runs ==="; gh api repos/kotoba-lang/app-kotoba-cloud/actions/runs --jq '.workflow_runs|length' 2>&1
echo "=== git ==="; git fetch kotoba-lang main 2>&1; git log -1 --format='%h %ad %s' kotoba-lang/main
echo "=== deps ==="; grep -E '"(wrangler|chicory|[^"]*)": *"' package.json | head -20
npm view wrangler version 2>&1
