#!/bin/bash
# Classpath: cp-kw.txt entries minus kotoba-sema dirs, plus wt-minmax src/resources.
AMU=~/github/com-junkawasaki/orgs/kotoba-lang/amu
WT=~/github/wt-minmax
BASE=$(tr ':' '\n' < /tmp/langcos/cp-kw.txt | grep -v 'kotoba-sema' | paste -sd: -)
CP="$AMU/src:$AMU/resources:$BASE:$WT/src:$WT/resources"
printf '%s' "$CP" > /tmp/langcos/cp_min.txt
echo "CP_WRITTEN bytes=$(wc -c < /tmp/langcos/cp_min.txt)"
