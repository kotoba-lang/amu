#!/bin/bash
cd ~/github/com-junkawasaki/orgs/kotoba-lang/app-kotoba-cloud
git fetch kotoba-lang
echo "fetch rc=$?"
git show kotoba-lang/main:package.json | grep -A4 devDependencies
echo "npq: $(npm view @noble/post-quantum version)"
echo "shadow: $(npm view shadow-cljs version)"
git log -1 --format='%ci %h' kotoba-lang/main
