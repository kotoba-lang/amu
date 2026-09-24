#!/bin/bash
cd ~/github/com-junkawasaki/orgs/kotoba-lang/app-kotoba-cloud
echo "== date =="; date
echo "== site probes =="
for p in / /en/ /health /this-path-should-404-xyz; do
  echo "-- $p"; curl -s -o /dev/null -w "%{http_code}\n" --max-time 15 "https://kotoba.cloud$p"
done
echo "-- health body"; curl -s --max-time 15 https://kotoba.cloud/health; echo
echo "-- api"; curl -s -o /dev/null -w "%{http_code}\n" --max-time 15 https://api.kotoba.cloud/v1/control-plane
echo "== git =="
git fetch kotoba-lang -q 2>&1
echo "HEAD:"; git rev-parse HEAD
echo "remote main:"; git rev-parse kotoba-lang/main
echo "behind: $(git rev-list HEAD..kotoba-lang/main --count)"
echo "== deps (remote main) =="
git show kotoba-lang/main:package.json 2>/dev/null | grep -A8 '"dependencies"'
echo "== npm latest =="
for p in wrangler chicory; do echo -n "$p: "; npm view "$p" version 2>/dev/null; done
echo "== gh runs (may be empty) =="
gh api repos/cloud-kotoba/app-kotoba-cloud/actions/runs --jq '.total_count' 2>&1 | head -1
echo "== issues =="
gh issue list -R cloud-kotoba/app-kotoba-cloud --state open --limit 20 2>&1
echo "== prs =="
gh pr list -R cloud-kotoba/app-kotoba-cloud --state open --limit 20 2>&1
