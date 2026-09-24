#!/bin/bash
cd ~/github/com-junkawasaki/orgs/kotoba-lang/app-kotoba-cloud
echo "=== public/ on main (top) ==="
git ls-tree --name-only kotoba-lang/main:public | head -40
echo "=== index.html? ==="
git ls-tree -r --name-only kotoba-lang/main:public | grep -E '^public/(index\.html|en/|ja/)' | head -10
echo "=== recent commits touching public/index.html ==="
git log --oneline -5 kotoba-lang/main -- public/index.html
echo "=== does 404-page.html exist ==="
git ls-tree -r --name-only kotoba-lang/main:public | grep 404 | head -5
