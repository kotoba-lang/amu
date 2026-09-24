#!/bin/bash
cd ~/github/com-junkawasaki/orgs/kotoba-lang/app-kotoba-cloud
echo "== log HEAD..main =="
git log --oneline HEAD..kotoba-lang/main | head -10
echo "== main package.json wrangler =="
git show kotoba-lang/main:package.json | grep -E '"wrangler"'
echo "== recent merged PRs =="
gh pr list --repo kotoba-lang/app-kotoba-cloud --state merged --limit 5
echo "== recent issues (all) =="
gh issue list --repo kotoba-lang/app-kotoba-cloud --state all --limit 5
