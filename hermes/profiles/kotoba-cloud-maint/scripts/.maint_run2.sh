#!/bin/bash
cd ~/github/com-junkawasaki/orgs/kotoba-lang/app-kotoba-cloud
echo "=== / headers ==="
curl -s -D - -o /tmp/root_body.txt --max-time 20 https://kotoba.cloud/ | head -30
echo "=== / body head ==="
head -c 500 /tmp/root_body.txt; echo
echo "=== other paths ==="
for p in /index.html /ja/ /404-page /pricing /about; do
  echo -n "$p -> "; curl -s -o /dev/null -w "%{http_code}\n" --max-time 15 "https://kotoba.cloud$p"
done
echo "=== routes in remote main worker ==="
git show kotoba-lang/main:build/worker.js 2>/dev/null | grep -n -m20 -E "pathname|route|'/'|\"/\"" | head -30
echo "=== assets in remote main ==="
git ls-tree --name-only kotoba-lang/main | head -20
git ls-tree --name-only kotoba-lang/main:assets 2>/dev/null | head -20
echo "=== wrangler.toml ==="
git show kotoba-lang/main:wrangler.toml 2>/dev/null | head -40
