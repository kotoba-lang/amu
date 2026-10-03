#!/bin/zsh
# s0j.sh <file>: stage-0 check, the diagnostic's line and message (cp-walls classpath)
# BOOTSTRAP-REFERENCE (stage-0, the JVM-built native image): classifies a source wall, builds nothing.
cd "$(dirname "$0")/../../.."; K=/private/tmp/wt-K-kotoba-lang; CP=$(cat ${WALL_CP:-build/walls/cp-walls.txt}); SP="$(echo "$CP" | tr ':' '\n' | grep '/src$' | sed 's/^/--source-path /' | tr '\n' ' ') --source-path $PWD/src --source-path $K/lang/compat"; ulimit -s 65500
r=$(nice build/native-image/amu-native check $1 --policy $K/lang/selfhost-compiler-grant.edn ${=SP} --json --no-definitions 2>&1)
if echo "$r" | grep -q ':ok true\|:format :kotoba.check/v1'; then echo "$1 OK"; else echo "$r" | grep -o ':source "[^"]*"\|:line [0-9]*\|:message "[^"]*' | tr '\n' ' ' | cut -c1-400; echo; fi
