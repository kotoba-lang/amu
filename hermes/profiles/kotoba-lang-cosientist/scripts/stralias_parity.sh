#!/bin/bash
set -eu
CP=$(cat /tmp/langcos/cp_final.txt)
cd ~/github/com-junkawasaki/orgs/kotoba-lang/amu
printf '(ns p (:export [t]))\n(defn t [s :string] :string (str s "-ok" "!"))\n' > /tmp/langcos/str.kotoba
printf '(ns p (:export [t]))\n(defn t [s :string] :string (string-concat (string-concat s "-ok") "!"))\n' > /tmp/langcos/manual.kotoba
printf '(ns p (:export [t]))\n(defn t [s :string] :string (string-concat s "-ok"))\n' > /tmp/langcos/manual2.kotoba
printf '(ns p (:export [t]))\n(defn t [s :string] :string (str s "-ok"))\n' > /tmp/langcos/str2.kotoba
node --stack-size=4096 node_modules/nbb/cli.js --classpath "$CP" src/kotoba/compiler/nbb/wasm_cli.cljs definition-cids /tmp/langcos/str.kotoba
node --stack-size=4096 node_modules/nbb/cli.js --classpath "$CP" src/kotoba/compiler/nbb/wasm_cli.cljs definition-cids /tmp/langcos/manual.kotoba
node --stack-size=4096 node_modules/nbb/cli.js --classpath "$CP" src/kotoba/compiler/nbb/wasm_cli.cljs definition-cids /tmp/langcos/str2.kotoba
node --stack-size=4096 node_modules/nbb/cli.js --classpath "$CP" src/kotoba/compiler/nbb/wasm_cli.cljs definition-cids /tmp/langcos/manual2.kotoba
