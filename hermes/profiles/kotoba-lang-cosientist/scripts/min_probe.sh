#!/bin/bash
# lang-cosientist iteration 7 probe: does `(min a b)` qualify on the pinned
# sema (63d7661)? Expected per iteration 6: REJECT. `u` is the hand-patch twin.
set -u
AMU=~/github/com-junkawasaki/orgs/kotoba-lang/amu
cd "$AMU"
CP="src:resources:$(cat /tmp/langcos/cp.txt)"
printf '(ns p (:export [t] [u]))\n(defn t [a :i64 b :i64] :i64 (min a b))\n(defn u [a :i64 b :i64] :i64 (if (< a b) a b))\n' > /tmp/langcos/min.kotoba
node --stack-size=4096 node_modules/nbb/cli.js --classpath "$CP" src/kotoba/compiler/nbb/wasm_cli.cljs check /tmp/langcos/min.kotoba 2>&1
echo "CHECK_EXIT=$?"
