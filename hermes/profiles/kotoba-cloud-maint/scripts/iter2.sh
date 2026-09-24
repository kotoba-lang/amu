#!/bin/bash
exec > ~/.hermes/profiles/kotoba-cloud-maint/scripts/out2.txt 2>&1
cd ~/github/com-junkawasaki/orgs/kotoba-lang/app-kotoba-cloud
git show kotoba-lang/main:package.json | grep -n wrangler
git log -1 --format='%ci %h' kotoba-lang/main
date -u +%FT%TZ
echo done
