#!/bin/bash
# Control: same min4 probe against unpatched sema base (wt-kwproj = 9898f0e + kwproj patch, min/max unaffected)
set -u
AMU=~/github/com-junkawasaki/orgs/kotoba-lang/amu
cd "$AMU"
WT=~/github/wt-kwproj
BASE=$(tr ':' '\n' < /tmp/langcos/cp-kw.txt | grep -v 'kotoba-sema' | paste -sd: -)
CP="$AMU/src:$AMU/resources:$BASE:$WT/src:$WT/resources"
node --stack-size=4096 node_modules/nbb/cli.js --classpath "$CP" src/kotoba/compiler/nbb/wasm_cli.cljk check /tmp/langcos/min4.kotoba
echo "CONTROL_EXIT=$?"
