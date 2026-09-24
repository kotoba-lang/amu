#!/bin/bash
# tick12 amu subset re-probe (jvm-dep-migrator)
cd ~/github/com-junkawasaki/orgs/kotoba-lang/amu || exit 1
out=/tmp/q9probe3_res.txt
: > "$out"
for f in /tmp/q9probe3/*.kotoba; do
  r=$(bin/amu check --jvm-free "$f" 2>&1 | tail -1)
  if echo "$r" | grep -q '"ok":true'; then
    echo "PASS $(basename "$f")" >> "$out"
  else
    code=$(echo "$r" | grep -o 'kotoba.error/[a-z-]*' | head -1)
    echo "FAIL $(basename "$f") ${code:-?}" >> "$out"
  fi
done
echo "PASS count: $(grep -c PASS "$out")" >> "$out"
echo DONE >> "$out"
