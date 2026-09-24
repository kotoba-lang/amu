#!/bin/bash
# Build the local-sema classpath: pinned lock dirs minus kotoba-sema, plus the
# local kotoba-sema checkout (bot/lang-min-max-20260904).
AMU=~/github/com-junkawasaki/orgs/kotoba-lang/amu
LOCALSEMA=~/github/com-junkawasaki/orgs/kotoba-lang/kotoba-sema
BASE=$(tr '\n' ':' < /tmp/langcos/cp.txt)
BASE=$(printf '%s' "$BASE" | tr ':' '\n' | grep -v 'kotoba-sema' | paste -sd: -)
CP="$AMU/src:$AMU/resources:$BASE:$LOCALSEMA/src:$LOCALSEMA/resources"
printf '%s' "$CP" > /tmp/langcos/cp_final.txt
echo "CP_WRITTEN"
