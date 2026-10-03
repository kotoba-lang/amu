#!/bin/zsh
# seed/tests/r6f/gate-r6f.sh [--extra] -- the extra gate of rung R6F (agent TMPL, 2026-10-04: templates compiled on their own and
# the next seed-refused source-route features of the R6 scan). BOOTSTRAP-TOOL (zsh). Rows:
#   R6F     seed/tests/r6f/check-r6f.sh with seed-1: every feat/*.kotoba (hand-derived values; stage-0 d2cb84f6 `check` admits
#           every positive and refuses every negative with the reference's reason; its NATIVE route refuses most of them:
#           "typed values currently require ..."). Single-module and project route byte-identical.
#   TMPL    seed/tests/r6f/proj: a namespace template (:params [elem :keyword]) required without :with is its default
#           instantiation; project route value = want, and separate mode (emit every module, the template on its own, then
#           link) gives the same container as the in-process route.
#   R6D-X   seed/tests/r6d/gate-r6d.sh --extra (R6D's rows, and through it R6C/R6B/R6A/R5B/R5A extras).
# Exit 0 iff every row passes.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/../../../scripts/seed/lib.sh"
R=$SEED_REPO; B=${SEED_BUILD:A}; D=$R/seed/tests/r6f; W=$B/gate-r6f; rm -rf $W; mkdir -p $W
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
# R6F
SEED_BUILD=$B zsh $D/check-r6f.sh $bin > $W/check.log 2>&1 && row PASS "R6F $(tail -1 $W/check.log)" \
  || row FAIL "R6F $(grep -E '^FAIL' $W/check.log | head -4 | tr '\n' ' ')"
# TMPL
want=$(want_of $D/proj/main.kotoba)
seed_run $bin $off compile $D/proj/main.kotoba --source-path $D/proj/src --unpinned --output $W/tp.kseed > $W/tp.log 2>&1
v=$([ -s $W/tp.kseed ] && runmain $W/tp.kseed tp || echo "refused: $(grep -m1 seed: $W/tp.log)")
sep=bad; mkdir -p $W/o
if seed_run $bin $off modules $D/proj/main.kotoba --source-path $D/proj/src > $W/tp.order 2>> $W/tp.log; then
  last=$(tail -1 $W/tp.order | cut -d' ' -f1); ok=1
  while read -r ns fp; do r=(); [ $ns = $last ] && r=(--entry)
    seed_run $bin $off compile $fp --emit-module $r --object-dir $W/o --output $W/o/$ns.kso >> $W/tp.log 2>&1 || ok=0; done < $W/tp.order
  [ $ok -eq 1 ] && seed_run $bin $off link $W/o/$last.kso --object-dir $W/o --output $W/tp-sep.kseed >> $W/tp.log 2>&1 && cmp -s $W/tp.kseed $W/tp-sep.kseed && sep=same
fi
[ "$v" = "$want" ] && [ $sep = same ] && row PASS "TMPL main = $v (want $want), template compiled on its own, separate mode == in-process ($(wc -l < $W/tp.order | tr -d ' ') modules)" \
  || row FAIL "TMPL main '$v' want $want, separate mode $sep"
# R6D-X
SEED_BUILD=$B zsh $R/seed/tests/r6d/gate-r6d.sh --extra > $W/r6d.log 2>&1 && row PASS "R6D-X $(tail -1 $W/r6d.log)" \
  || row FAIL "R6D-X $(grep -E '^FAIL' $W/r6d.log | head -3 | tr '\n' ' ')"
echo "gate-r6f: $([ $fails -eq 0 ] && echo READY || echo "NOT READY ($fails failed)") (load $(uptime | sed 's/.*averages: //'))"
[ $fails -eq 0 ]
