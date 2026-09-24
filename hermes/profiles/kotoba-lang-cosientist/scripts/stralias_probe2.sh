#!/bin/bash
set -eu
CP=$(cat /tmp/langcos/cp_final.txt)
cd ~/github/com-junkawasaki/orgs/kotoba-lang/amu
nbb --classpath "$CP" -e "(require '[kotoba.sema :as sema]) (prn (second (first (:functions (sema/analyze \"(ns p (:export [t]))(defn t [s :string] :string (str s \\\"-ok\\\" \\\"!\\\"))\")))))"
