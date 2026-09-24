#!/bin/bash
# tick12 amu subset re-probe, corrected EDN parse (jvm-dep-migrator)
cd ~/github/com-junkawasaki/orgs/kotoba-lang/amu || exit 1
out=/tmp/q9probe3_res2.txt
: > "$out"
for f in /tmp/q9probe3/*.kotoba; do
  o=$(bin/amu check --jvm-free "$f" 2>&1)
  code=$?
  first=$(echo "$o" | head -1)
  case "$first" in
    "{:ok true"*) echo "PASS $(basename "$f")" >> "$out" ;;
    *) e=$(echo "$o" | grep -o 'kotoba.error/[a-z-]*' | head -1)
       echo "FAIL $(basename "$f") ${e:-exit$code}" >> "$out" ;;
  esac
done
echo "PASS count: $(grep -c PASS "$out")" >> "$out"
echo DONE >> "$out"
