#!/bin/bash
cd ~/github/com-junkawasaki/orgs/kotoba-lang/app-kotoba-cloud
echo "=== worker entry file on main ==="
git show kotoba-lang/main:package.json | head -30
echo "=== find worker src ==="
git ls-tree -r --name-only kotoba-lang/main | grep -iE 'worker|index\.(js|ts)' | grep -v assets | head -20
echo "=== '/' route handling ==="
for f in $(git ls-tree -r --name-only kotoba-lang/main | grep -E 'src/.*worker' | head -5); do echo "--- $f"; done
echo "=== last commits ==="
git log --oneline -12 kotoba-lang/main
echo "=== when did health/root change: last commit touching worker routing ==="
git log --oneline -5 kotoba-lang/main -- src/
