#!/bin/bash
set -eu
CP=$(cat /tmp/langcos/cp_final.txt)
cd ~/github/com-junkawasaki/orgs/kotoba-lang/amu
probe() {
  printf '(ns p (:export [t]))\n%s\n' "$2" > /tmp/langcos/p.kotoba
  if node --stack-size=4096 node_modules/nbb/cli.js --classpath "$CP" src/kotoba/compiler/nbb/wasm_cli.cljs check /tmp/langcos/p.kotoba >/dev/null 2>&1; then echo "PASS: $1"; else echo "REJECT: $1"; fi
}
probe 'str empty (must reject)' '(defn t [s :string] :string (str))'
probe 'str 1 arg identity' '(defn t [s :string] :string (str s))'
probe 'str int parts (must reject, fail closed)' '(defn t [n :i64] :string (str n "-suffix"))'
probe 'str non-string arg (must reject)' '(defn t [n :i64] :string (str "a" "b" n))'
probe 'str many parts' '(defn t [s :string] :string (str s "1" "2" "3" "4" "5" "6" "7" "8" "9"))'
