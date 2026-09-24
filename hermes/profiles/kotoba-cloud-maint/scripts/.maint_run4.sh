#!/bin/bash
cd ~/github/com-junkawasaki/orgs/kotoba-lang/app-kotoba-cloud
git show kotoba-lang/main:src/app_kotoba_cloud/worker.cljk > /tmp/worker_main.cljk
wc -l /tmp/worker_main.cljk
grep -n -E '"|"|pathname|index\.html|assets|404' /tmp/worker_main.cljk | head -60
