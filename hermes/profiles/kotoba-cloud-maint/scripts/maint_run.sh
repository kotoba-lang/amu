#!/bin/bash
cd ~/github/com-junkawasaki/orgs/kotoba-lang/app-kotoba-cloud
echo "=== health probe ==="
for p in / /en/ /health; do
  echo "--- $p"; curl -s -o /dev/null -w "%{http_code}\n" -m 15 "https://kotoba.cloud$p"
done
curl -s -m 15 "https://kotoba.cloud/health"; echo
echo "--- 404 check /random-xyz-123"; curl -s -o /dev/null -w "%{http_code}\n" -m 15 "https://kotoba.cloud/random-xyz-123"
echo "--- api"; curl -s -o /dev/null -w "%{http_code}\n" -m 15 "https://api.kotoba.cloud/v1/control-plane"
echo "=== git state ==="
git remote -v | head -4
git log --oneline -3 kotoba-lang/main
git status -sb | head -3
echo "=== package.json deps ==="
cat package.json
echo "=== latest npm versions ==="
for p in wrangler; do echo -n "$p: "; npm view $p version 2>/dev/null; done
echo "=== issues ==="
gh issue list --repo kotoba-lang/app-kotoba-cloud --state open --limit 20
echo "=== prs ==="
gh pr list --repo kotoba-lang/app-kotoba-cloud --state open --limit 20
echo "=== deploy freshness (latest commit date vs worker) ==="
git log -1 --format='%ci %h %s' kotoba-lang/main
curl -sI -m 15 https://kotoba.cloud | grep -iE 'cf-ray|last-modified|etag' | head -5
