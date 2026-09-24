#!/bin/bash
# tick8: run amu check --jvm-free over all probes, collect verdicts
cd ~/github/com-junkawasaki/orgs/kotoba-lang/amu || exit 1
OUT=/tmp/tick8-checks.txt
: > "$OUT"
for f in /tmp/q9probe3/p*.kotoba; do
  b=$(basename "$f")
  err=$(./bin/amu check --jvm-free "$f" 2>&1)
  rc=$?
  if [ $rc -eq 0 ]; then
    echo "$b PASS" >> "$OUT"
  else
    reason=$(echo "$err" | grep -oE ':kotoba\.error/[a-z0-9-]+' | head -1)
    msg=$(echo "$err" | grep -iE 'reject|error|no admitted|unsupported|unknown' | head -2 | tr '\n' ' ' | cut -c1-160)
    echo "$b FAIL rc=$rc $reason | $msg" >> "$OUT"
  fi
done
echo DONE >> "$OUT"
