#!/bin/bash
cd ~/github/com-junkawasaki/orgs/kotoba-lang/app-kotoba-cloud || exit 1
{
echo "=== remotes ==="
git remote -v
echo "=== branches ==="
git branch -a | head -10
echo "=== status ==="
git status -sb | head -5
} > ~/.hermes/profiles/kotoba-cloud-maint/scripts/remotes.txt 2>&1
