#!/bin/bash
OUT=/tmp/jvm_tick15_probe3.txt
: > "$OUT"
SEMA=~/github/com-junkawasaki/orgs/kotoba-lang/kotoba-sema
if [ -d "$SEMA" ]; then
  git -C "$SEMA" fetch origin -q
  git -C "$SEMA" merge-base --is-ancestor 63d76616e35347dacc8db57a81a6d58cca4ff633 origin/main && echo "sema-pin ancestor of sema origin/main: YES" >> "$OUT" || echo "sema-pin ancestor of sema origin/main: NO" >> "$OUT"
  echo "sema origin/main HEAD: $(git -C "$SEMA" rev-parse --short origin/main)" >> "$OUT"
  echo "sema HEAD: $(git -C "$SEMA" rev-parse --short HEAD)" >> "$OUT"
else
  echo "no local kotoba-sema repo" >> "$OUT"
fi
# amu local HEAD vs origin/main diff summary
cd ~/github/com-junkawasaki/orgs/kotoba-lang/amu || exit 1
echo "amu local HEAD 771f3728 vs origin/main 197bdc95: $(git rev-list --count 771f3728..197bdc95 2>/dev/null) commits behind" >> "$OUT"
echo DONE >> "$OUT"
