#!/bin/bash
OUT=/tmp/jvm_tick15_sema2.txt
: > "$OUT"
SEMA=~/github/com-junkawasaki/orgs/kotoba-lang/kotoba-sema
git -C "$SEMA" branch -a 2>&1 | head -10 >> "$OUT"
git -C "$SEMA" log --oneline -5 2>&1 >> "$OUT"
git -C "$SEMA" merge-base --is-ancestor 63d76616e35347dacc8db57a81a6d58cca4ff633 HEAD && echo "pin ancestor of sema local HEAD: YES" >> "$OUT" || echo "pin ancestor of sema local HEAD: NO" >> "$OUT"
git -C "$SEMA" cat-file -t 63d76616e35347dacc8db57a81a6d58cca4ff633 2>&1 >> "$OUT"
echo DONE >> "$OUT"
