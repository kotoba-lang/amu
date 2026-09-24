#!/bin/bash
set -eu
CP=$(cat /tmp/langcos/cp_final.txt)
cd ~/github/com-junkawasaki/orgs/kotoba-lang/amu
nbb --classpath "$CP" -m kotoba.compiler.nbb.cli -- check /tmp/langcos/str.kotoba
