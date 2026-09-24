#!/bin/bash
set -eu
LOCALSEMA=~/github/com-junkawasaki/orgs/kotoba-lang/kotoba-sema
CP="$( { tr ':' '\n' < /tmp/langcos/cp.txt | grep -v "kotoba-sema/"; echo "$LOCALSEMA/src"; echo "$LOCALSEMA/resources"; } | paste -sd: -)"
printf '%s' "$CP" > /tmp/langcos/cp_final.txt
cd ~/github/com-junkawasaki/orgs/kotoba-lang/amu
nbb --classpath "$CP" -e "(require '[kotoba.sema :as sema]) (prn (mapv :operations (:functions (sema/analyze \"(ns p (:export [t]))(defn t [s :string] :string (str s \\\"-ok\\\" \\\"!\\\"))\"))))"
