#!/bin/bash
# tick15: key probe re-measure with correct filenames (jvm-dep-migrator)
OUT=/tmp/jvm_tick15_probe2.txt
: > "$OUT"
cd ~/github/com-junkawasaki/orgs/kotoba-lang/amu || exit 1
for p in p_bsl p_ubsr p_bitshift p_keys p_keys2 p_keys3 p_contains p_contains2 p_vt p_vector_take p_pop; do
  f="/tmp/q9probe3/$p.kotoba"
  [ -f "$f" ] || { echo "$p MISSING" >> "$OUT"; continue; }
  ./bin/amu check --jvm-free "$f" > /dev/null 2>&1
  echo "$p rc=$?" >> "$OUT"
done
# sema main vs pin ancestry
SEMA=~/github/com-junkawasaki/orgs/kotoba-lang/kotoba-lang
git -C "$SEMA" fetch origin -q 2>>/dev/null
git -C "$SEMA" merge-base --is-ancestor 63d76616e35347dacc8db57a81a6d58cca4ff633 origin/main && echo "sema-pin-is-ancestor-of-origin-main: YES" >> "$OUT" || echo "sema-pin-is-ancestor-of-origin-main: NO" >> "$OUT"
echo "sema origin/main HEAD: $(git -C "$SEMA" rev-parse --short origin/main)" >> "$OUT"
# machine m10 regression
./bin/amu check --jvm-free /tmp/q9machine/m10.kotoba > /dev/null 2>&1
echo "m10 rc=$?" >> "$OUT"
echo DONE >> "$OUT"
