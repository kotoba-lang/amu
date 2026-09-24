#!/bin/bash
# tick15: amu/sema landing diff + key probe re-measure (jvm-dep-migrator)
OUT=/tmp/jvm_tick15_probe.txt
: > "$OUT"
cd ~/github/com-junkawasaki/orgs/kotoba-lang/amu || exit 1
{
echo "amu HEAD: $(git rev-parse --short HEAD)  origin/main: $(git rev-parse --short origin/main)"
git fetch origin -q
git log --oneline origin/main -6
echo "sema pin: $(grep -o 'kotoba-sema[^\"]*\"[0-9a-f]\{8,\}' deps.edn | head -1)"
echo "sema main HEAD: $(git -C ~/github/com-junkawasaki/orgs/kotoba-lang/kotoba-lang rev-parse --short main 2>/dev/null || echo n/a)"
} >> "$OUT" 2>&1
for p in p05 p07 p08 p19 p06 p13; do
  f="/tmp/q9probe3/$p.kotoba"
  if [ -f "$f" ]; then
    ./bin/amu check --jvm-free "$f" > /dev/null 2>&1
    echo "$p rc=$?" >> "$OUT"
  else
    echo "$p MISSING" >> "$OUT"
  fi
done
echo DONE >> "$OUT"
