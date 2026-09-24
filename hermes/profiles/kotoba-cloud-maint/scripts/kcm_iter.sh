#!/bin/bash
cd ~/github/com-junkawasaki/orgs/kotoba-lang/app-kotoba-cloud
for p in / /en/ /health /definitely-not-a-page-xyz; do
  code=$(curl -s -o /tmp/body.txt -w "%{http_code}" --max-time 15 "https://kotoba.cloud$p")
  echo "$p -> $code $(head -c 120 /tmp/body.txt | tr -d '\n')"
done
echo "api: $(curl -s -o /tmp/api.txt -w '%{http_code}' --max-time 15 https://api.kotoba.cloud/v1/control-plane) $(head -c 200 /tmp/api.txt)"
echo "== issues =="
gh issue list --repo kotoba-lang/app-kotoba-cloud --state open
echo "== prs =="
gh pr list --repo kotoba-lang/app-kotoba-cloud --state open
echo "== deps =="
grep -E '"(wrangler|typescript|@cloudflare/workers-types)"' package.json
npm view wrangler version
echo "== git =="
git fetch kotoba-lang main 2>&1 | tail -1
git rev-parse HEAD
git rev-parse kotoba-lang/main
