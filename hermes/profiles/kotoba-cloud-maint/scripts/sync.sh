#!/bin/bash
cd ~/github/com-junkawasaki/orgs/kotoba-lang/app-kotoba-cloud || exit 1
R=kotoba-lang
{
echo "=== diff HEAD..main (files) ==="
git diff --stat HEAD $R/main | tail -15
echo "=== wrangler pin on main ==="
git show $R/main:package.json | node -e "let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{const p=JSON.parse(d);console.log('wrangler:',p.devDependencies.wrangler)})"
echo "=== bot branch state ==="
git branch -a | grep bot/ || echo "no local bot branches"
echo "=== bot branch merged? ==="
git log --oneline $R/main -3 --grep="4.129" 2>&1
} > ~/.hermes/profiles/kotoba-cloud-maint/scripts/sync.txt 2>&1
exit 0
