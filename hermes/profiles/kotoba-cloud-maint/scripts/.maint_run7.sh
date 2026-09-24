#!/bin/bash
cd ~/github/com-junkawasaki/orgs/kotoba-lang/app-kotoba-cloud
echo "=== where do assets live (index.html anywhere on main) ==="
git ls-tree -r --name-only kotoba-lang/main | grep -E 'index\.html$' | head
echo "=== 404-page ==="
git ls-tree -r --name-only kotoba-lang/main | grep -E '404' | head
echo "=== en/ja dirs ==="
git ls-tree -r --name-only kotoba-lang/main | grep -E '/(en|ja)/index\.html' | head
echo "=== mktg branches: what new branches do (recent activity) ==="
git log --oneline -3 kotoba-lang/mktg/sitemap-twin-20260918
echo "=== deploy-related commits last 48h (main) ==="
git log --oneline --since="2026-09-17" kotoba-lang/main | head -15
