#!/bin/bash
cd ~/github/com-junkawasaki/orgs/kotoba-lang/app-kotoba-cloud
echo "--- HEAD vs main ---"
git rev-parse HEAD
git rev-parse kotoba-lang/main
echo "--- deps on main ---"
git show kotoba-lang/main:package.json | sed -n '/devDependencies/,/}/p'
echo "--- npm latest ---"
npm view wrangler version
npm view shadow-cljs version
npm view @noble/post-quantum version
