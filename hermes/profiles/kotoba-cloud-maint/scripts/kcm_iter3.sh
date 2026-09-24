#!/bin/bash
cd ~/github/com-junkawasaki/orgs/kotoba-lang/app-kotoba-cloud
git show kotoba-lang/main:package.json | grep -E '"(wrangler|typescript|@cloudflare/workers-types|vitest|miniflare)"'
for p in typescript vitest miniflare "@cloudflare/workers-types" chicory; do
  echo "$p latest: $(npm view $p version 2>/dev/null)"
done
echo "== last deploy freshness: check /health headers =="
curl -sI https://kotoba.cloud/health --max-time 15 | grep -iE 'cf-ray|last-modified|etag|date'
