#!/bin/bash
# tick8 amu subset re-probe (jvm-dep-migrator)
cd /tmp/amu-tick8 || exit 1
out=/tmp/tick8_results.txt
: > "$out"
for f in /tmp/q9probe/p*.k* /tmp/q9probe2/*.kotoba; do
  r=$(bin/amu check --jvm-free "$f" 2>&1 | tail -1)
  if echo "$r" | grep -q '"ok":true'; then
    echo "PASS $(basename "$f")" >> "$out"
  else
    code=$(echo "$r" | grep -o 'kotoba.error/[a-z-]*' | head -1)
    echo "FAIL $(basename "$f") ${code:-?}" >> "$out"
  fi
done
echo "PASS count: $(grep -c PASS "$out")"
grep PASS "$out"
