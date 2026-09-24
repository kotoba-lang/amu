#!/bin/bash
# iteration 24: min/max re-verify on sema main 9898f0e (branch bot/lang-minmax-20260919 @65a2779)
set -u
AMU=~/github/com-junkawasaki/orgs/kotoba-lang/amu
cd "$AMU"
CP="$(cat /tmp/langcos/cp_min.txt)"
NB="node --stack-size=4096 node_modules/nbb/cli.js --classpath $CP src/kotoba/compiler/nbb/wasm_cli.cljk"
$NB check /tmp/langcos/min4.kotoba
echo "CHECK_EXIT=$?"
echo "=== CIDs ==="
$NB kir-cids /tmp/langcos/min4.kotoba 2>&1 || true
echo "=== check fail-closed min-fc (1-arity min) ==="
$NB check /tmp/langcos/min-fc.kotoba
echo "FC_EXIT=$?"
