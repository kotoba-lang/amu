#!/bin/bash
# compile + run min/max via the upstream main first-class op (control path)
set -u
AMU=~/github/com-junkawasaki/orgs/kotoba-lang/amu
cd "$AMU"
WT=~/github/wt-kwproj
BASE=$(tr ':' '\n' < /tmp/langcos/cp-kw.txt | grep -v 'kotoba-sema' | paste -sd: -)
CP="$AMU/src:$AMU/resources:$BASE:$WT/src:$WT/resources"
NB="node --stack-size=4096 node_modules/nbb/cli.js --classpath $CP"
$NB src/kotoba/compiler/nbb/wasm_cli.cljk compile /tmp/langcos/min-run.kotoba --target wasm32 --output /tmp/langcos/min-run.wasm --fuel 100000000
echo "COMPILE_EXIT=$?"
ls -l /tmp/langcos/min-run.wasm
cat /tmp/langcos/run-main.mjs 2>/dev/null | head -30
