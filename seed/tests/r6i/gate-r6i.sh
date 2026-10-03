#!/bin/zsh
# seed/tests/r6i/gate-r6i.sh [--extra] -- the extra gate of rung R6I (agent LET, 2026-10-04: a repeated `_` binder, aborting
# exports whose error type is a record across modules, string-contains?). BOOTSTRAP-TOOL (zsh). Rows:
#   R6I     seed/tests/r6i/check-r6i.sh with seed-1: feat/*.kotoba (hand-derived values; positives single-module == project route).
#   ABRT    seed/tests/r6i/proj: an importer catches a record-typed abort of an import (was E6017); project route value = want,
#           and separate mode (emit every module, then link) gives the same container as the in-process route.
#   R6H-X   seed/tests/r6h/gate-r6h.sh --extra (R6H's rows, and through it R6F .. R5A).
# Exit 0 iff no row FAILs.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/../../../scripts/seed/lib.sh"
R=$SEED_REPO; B=${SEED_BUILD:A}; D=$R/seed/tests/r6i; W=$B/gate-r6i; rm -rf $W; mkdir -p $W
bin=$B/seed-1.bin; off=$(cat $B/seed-1.offset 2>/dev/null || echo 0)
L=$(seed_loader) || exit 2; L=${L:A}
SEED_RESOURCES_35=$R:$B
fails=0
row() { printf "%-7s %s\n" $1 "$2"; [ $1 = FAIL ] && fails=$((fails+1)); return 0; }
runmain() {
  local x o v
  x=$(seed_run $bin $off extract-native $1 --symbol main --output $W/$2.bin 2>&1); o=$(print -r -- "$x" | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  [ -n "$o" ] || { echo "noextract"; return; }
  v=$(cd $W; KEXE_CPU_SECONDS=60 KEXE_WALL_SECONDS=60 $L $W/$2.bin $o 0 aarch64 - 2>/dev/null | tail -1)
  [ -n "$v" ] && echo $v || echo trap
}
want_of() { sed -n 's/^;; want: *\([^ ]*\).*/\1/p' $1 | head -1; }
# R6I
SEED_BUILD=$B zsh $D/check-r6i.sh $bin > $W/check.log 2>&1 && row PASS "R6I $(tail -1 $W/check.log)" \
  || row FAIL "R6I $(grep -E '^FAIL' $W/check.log | head -4 | tr '\n' ' ')"
# ABRT
want=$(want_of $D/proj/main.kotoba)
seed_run $bin $off compile $D/proj/main.kotoba --source-path $D/proj/src --unpinned --output $W/ab.kseed > $W/ab.log 2>&1
v=$([ -s $W/ab.kseed ] && runmain $W/ab.kseed ab || echo "refused: $(grep -m1 seed: $W/ab.log)")
sep=bad; mkdir -p $W/o
if seed_run $bin $off modules $D/proj/main.kotoba --source-path $D/proj/src > $W/ab.order 2>> $W/ab.log; then
  last=$(tail -1 $W/ab.order | cut -d' ' -f1); ok=1
  while read -r ns fp; do r=(); [ $ns = $last ] && r=(--entry)
    seed_run $bin $off compile $fp --emit-module $r --object-dir $W/o --output $W/o/$ns.kso >> $W/ab.log 2>&1 || ok=0; done < $W/ab.order
  [ $ok -eq 1 ] && seed_run $bin $off link $W/o/$last.kso --object-dir $W/o --output $W/ab-sep.kseed >> $W/ab.log 2>&1 && cmp -s $W/ab.kseed $W/ab-sep.kseed && sep=same
fi
[ "$v" = "$want" ] && [ $sep = same ] && row PASS "ABRT main = $v (want $want), record error type across modules, separate mode == in-process ($(wc -l < $W/ab.order | tr -d ' ') modules)" \
  || row FAIL "ABRT main '$v' want $want, separate mode $sep"
# R6H-X
SEED_BUILD=$B zsh $R/seed/tests/r6h/gate-r6h.sh --extra > $W/r6h.log 2>&1 && row PASS "R6H-X $(tail -1 $W/r6h.log)" \
  || row FAIL "R6H-X $(grep -E '^FAIL' $W/r6h.log | head -3 | tr '\n' ' ')"
echo "gate-r6i: $([ $fails -eq 0 ] && echo READY || echo "NOT READY ($fails failed)") (load $(uptime | sed 's/.*averages: //'))"
[ $fails -eq 0 ]
