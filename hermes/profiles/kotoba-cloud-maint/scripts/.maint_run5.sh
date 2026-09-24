#!/bin/bash
cd ~/github/com-junkawasaki/orgs/kotoba-lang/app-kotoba-cloud
echo "=== wrangler config ==="
git show kotoba-lang/main:wrangler.jsonc 2>/dev/null | head -50 || git show kotoba-lang/main:wrangler.json 2>/dev/null | head -50
echo "=== root/dispatch in worker ==="
grep -n -E 'route|pathname|"/"' /tmp/worker_main.cljk | grep -viE 'content-type|set-cookie|cache-control' | head -40
echo "=== 'x-content-identity' ==="
grep -rn "x-content-identity" $(git ls-tree -r --name-only kotoba-lang/main | grep -v assets | grep -vE 'docs/|blog/|test/') 2>/dev/null | head -10
