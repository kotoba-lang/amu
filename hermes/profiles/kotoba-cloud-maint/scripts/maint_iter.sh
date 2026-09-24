#!/bin/bash
cd ~/github/com-junkawasaki/orgs/kotoba-lang/app-kotoba-cloud
echo "=== HEALTH PROBE ==="
for p in / /en/ /health; do
  echo "-- GET https://kotoba.cloud$p"
  curl -s -o /dev/null -w "%{http_code}\n" --max-time 20 "https://kotoba.cloud$p"
done
echo "-- body /health:"; curl -s --max-time 20 https://kotoba.cloud/health
echo
echo "-- random 404 path /maint-probe-$(date +%s):"
curl -s -o /dev/null -w "%{http_code}\n" --max-time 20 "https://kotoba.cloud/maint-probe-$(date +%s)"
echo "-- api.kotoba.cloud/v1/control-plane:"
curl -s -o /dev/null -w "%{http_code}\n" --max-time 20 https://api.kotoba.cloud/v1/control-plane

echo "=== GIT SYNC ==="
git fetch kotoba-lang 2>&1 | tail -1
echo "local HEAD: $(git rev-parse HEAD)"
echo "remote main: $(git rev-parse kotoba-lang/main)"
git rev-list --count HEAD..kotoba-lang/main 2>/dev/null | xargs echo "behind by:"

echo "=== ISSUES ==="
gh issue list --repo kotoba-lang/app-kotoba-cloud --state open --limit 20 2>&1
echo "=== PRS ==="
gh pr list --repo kotoba-lang/app-kotoba-cloud --state open --limit 20 2>&1
echo "=== DEPS ==="
echo "package.json (remote main):"
git show kotoba-lang/main:package.json
echo "npm latest wrangler: $(npm view wrangler version 2>/dev/null)"
