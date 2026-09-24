#!/bin/bash
# kotoba-cloud-maint iteration
cd ~/github/com-junkawasaki/orgs/kotoba-lang/app-kotoba-cloud
echo "=== HEALTH PROBE $(date -u +%FT%TZ) ==="
for u in https://kotoba.cloud/ https://kotoba.cloud/en/ https://kotoba.cloud/health https://kotoba.cloud/maint-probe-404-$RANDOM https://api.kotoba.cloud/v1/control-plane; do
  echo "--- $u"
  curl -s -o /tmp/body.txt -w "status=%{http_code}\n" --max-time 20 "$u"
  head -c 300 /tmp/body.txt; echo
done
echo "=== GIT ==="
git fetch kotoba-lang 2>&1 | tail -2
git log --oneline -1 kotoba-lang/main
git log --oneline -1 HEAD
echo "=== ISSUES ==="
gh issue list -R cloud-kotoba/app-kotoba-cloud --state open --limit 20
echo "=== PRS ==="
gh pr list -R cloud-kotoba/app-kotoba-cloud --state open --limit 20
echo "=== DEPS (remote main) ==="
git show kotoba-lang/main:package.json | grep -A15 '"devDependencies"'
echo "=== NPM LATEST ==="
npm view wrangler version 2>/dev/null
npm view typescript version 2>/dev/null
npm view @cloudflare/workers-types version 2>/dev/null
