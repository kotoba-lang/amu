#!/bin/bash
set -eu
AMU=~/github/com-junkawasaki/orgs/kotoba-lang/amu
LOCALSEMA=~/github/com-junkawasaki/orgs/kotoba-lang/kotoba-sema
BASE=$(tr '\n' ':' < /tmp/langcos/cp.txt)
BASE=$(printf '%s' "$BASE" | tr ':' '\n' | grep -v 'kotoba-sema' | paste -sd: -)
CP="$AMU/src:$AMU/resources:$BASE:$LOCALSEMA/src:$LOCALSEMA/resources"
printf '%s' "$CP" > /tmp/langcos/cp_final.txt
cd "$AMU"
printf '(ns p (:export [t]))\n(defn t [s :string] :string (str s "-ok" "!"))\n' > /tmp/langcos/str.kotoba
node --stack-size=4096 node_modules/nbb/cli.js --classpath "$CP" src/kotoba/compiler/nbb/wasm_cli.cljs check /tmp/langcos/str.kotoba
echo "CHECK_EXIT=$?"
node --stack-size=4096 node_modules/nbb/cli.js --classpath "$CP" src/kotoba/compiler/nbb/wasm_cli.cljs compile /tmp/langcos/str.kotoba --target wasm32 --output /tmp/langcos/str.wasm
echo "COMPILE_EXIT=$?"
ls -la /tmp/langcos/str.wasm
