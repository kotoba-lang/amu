#!/bin/zsh
# seed/tests/r6d/gate-r6d.sh [--extra] -- the extra gate of rung R6D (agent R6D, 2026-10-03: R6 source-route fidelity and reach).
# BOOTSTRAP-TOOL (zsh + python generators). Rows:
#   R6D     seed/tests/r6d/check-r6d.sh with seed-1: `when` / `when-not` absence typing ([:option :i64] in a defn whose result is
#           inferred, :i64 where it is declared, [:option T] for other T, :bool kept) -- want = stage-0's native answers; single
#           module and project route byte-identical.
#   KWLINK  seed/tests/r6d/proj (project route): keywords made in the entry and in a second library turned into text by a library
#           that never spells them (the link-wide keyword table); want = stage-0's answer; separate mode (emit + link) gives the
#           same container as the in-process route.
#   DEC     seed/tests/r6d/dec/gen-dec.py: decimal-f64-parse / decimal-f64x3-parse on ~400 strings (edge, random, exact
#           binary64 midpoints, malformed); every result equal to the reference reading (Python float under the ADR 0019
#           grammar; stage-0 refuses both operations natively).
#   FARM    every seed/tests/r6d/farm/*.kotoba compiled on the project route against the R6 scan farm ($SEED_BUILD/r6/src,
#           scripts/seed/r6-scan.sh, run here first); want = stage-0's native answer (kotoba.native.peephole: :option-i64).
#   SCAN    informational: the r6-scan histogram line (the farm is read from other worktrees, so it is not a pass/fail row).
#   R6C-X   seed/tests/r6c/gate-r6c.sh --extra (R6C's cases, LOOPW, LIBSTUB, and through it R6B/R6A/R5B/R5A extras).
# Exit 0 iff every pass/fail row passes.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/../../../scripts/seed/lib.sh"
R=$SEED_REPO; B=${SEED_BUILD:A}; D=$R/seed/tests/r6d; W=$B/gate-r6d; rm -rf $W; mkdir -p $W
bin=$B/seed-1.bin; off=$(cat $B/seed-1.offset 2>/dev/null || echo 0)
L=$(seed_loader) || exit 2; L=${L:A}
SEED_RESOURCES_35=$R:$B
fails=0
row() { printf "%-7s %s\n" $1 "$2"; [ $1 = FAIL ] && fails=$((fails+1)); return 0; }
# runmain <kseed> <tag> -> the value main answers (or trap); larger loader budgets (the decimal cases allocate)
runmain() {
  local x o v
  x=$(seed_run $bin $off extract-native $1 --symbol main --output $W/$2.bin 2>&1); o=$(print -r -- "$x" | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  [ -n "$o" ] || { echo "noextract"; return; }
  v=$(cd $W; KEXE_STRING_POOL=268435456 KEXE_PAIRS=4194304 KEXE_VECTORS=1048576 KEXE_VECTOR_ITEMS=16777216 KEXE_CPU_SECONDS=60 KEXE_WALL_SECONDS=60 \
      $L $W/$2.bin $o 0 aarch64 - 2>/dev/null | tail -1)
  [ -n "$v" ] && echo $v || echo trap
}
want_of() { sed -n 's/^;; want: *\([^ ]*\).*/\1/p' $1 | head -1; }
# R6D
SEED_BUILD=$B zsh $D/check-r6d.sh $bin > $W/check.log 2>&1 && row PASS "R6D $(tail -1 $W/check.log)" \
  || row FAIL "R6D $(grep -E '^FAIL' $W/check.log | head -4 | tr '\n' ' ')"
# KWLINK
want=$(want_of $D/proj/main.kotoba)
seed_run $bin $off compile $D/proj/main.kotoba --source-path $D/proj/src --unpinned --output $W/kw.kseed > $W/kw.log 2>&1
v=$([ -s $W/kw.kseed ] && runmain $W/kw.kseed kw || echo "refused: $(grep -m1 seed: $W/kw.log)")
sep=bad; mkdir -p $W/o
if seed_run $bin $off modules $D/proj/main.kotoba --source-path $D/proj/src > $W/kw.order 2>> $W/kw.log; then
  last=$(tail -1 $W/kw.order | cut -d' ' -f1); ok=1
  while read -r ns fp; do r=(); [ $ns = $last ] && r=(--entry)
    seed_run $bin $off compile $fp --emit-module $r --object-dir $W/o --output $W/o/$ns.kso >> $W/kw.log 2>&1 || ok=0; done < $W/kw.order
  [ $ok -eq 1 ] && seed_run $bin $off link $W/o/$last.kso --object-dir $W/o --output $W/kw-sep.kseed >> $W/kw.log 2>&1 && cmp -s $W/kw.kseed $W/kw-sep.kseed && sep=same
fi
[ "$v" = "$want" ] && [ $sep = same ] && row PASS "KWLINK main = $v (stage-0 $want), separate mode == in-process ($(wc -l < $W/kw.order | tr -d ' ') modules)" \
  || row FAIL "KWLINK main '$v' want $want, separate mode $sep"
# DEC
n=$(python3 $D/dec/gen-dec.py $W/dec.kotoba 300)
seed_run $bin $off compile $W/dec.kotoba --output $W/dec.kseed > $W/dec.log 2>&1
v=$([ -s $W/dec.kseed ] && runmain $W/dec.kseed dec || echo "refused: $(grep -m1 seed: $W/dec.log)")
[ "$v" = 0 ] && row PASS "DEC $n cases = the reference reading (decimal-f64-parse, decimal-f64x3-parse)" || row FAIL "DEC main '$v' (mismatches*100000 + first index), $n cases"
# FARM (+ SCAN)
SEED_BUILD=$B zsh $R/scripts/seed/r6-scan.sh > $W/scan.log 2>&1
if [ -d $B/r6/src ]; then
  for f in $D/farm/*.kotoba(N); do
    lab=${f:t:r}; want=$(want_of $f)
    seed_run $bin $off compile $f --source-path $B/r6/src --unpinned --output $W/farm-$lab.kseed > $W/farm-$lab.log 2>&1
    v=$([ -s $W/farm-$lab.kseed ] && runmain $W/farm-$lab.kseed farm-$lab || echo "refused: $(grep -m1 seed: $W/farm-$lab.log)")
    [ "$v" = "$want" ] && row PASS "FARM $lab main = $v (stage-0 $want)" || row FAIL "FARM $lab main '$v' want $want"
  done
  row INFO "SCAN $(head -1 $W/scan.log)"
else row FAIL "FARM no scan farm ($(tail -1 $W/scan.log))"; fi
# R6C-X
SEED_BUILD=$B zsh $R/seed/tests/r6c/gate-r6c.sh --extra > $W/r6c.log 2>&1 && row PASS "R6C-X $(tail -1 $W/r6c.log)" \
  || row FAIL "R6C-X $(grep -E '^FAIL' $W/r6c.log | head -3 | tr '\n' ' ')"
echo "gate-r6d: $([ $fails -eq 0 ] && echo READY || echo "NOT READY ($fails failed)") (load $(uptime | sed 's/.*averages: //'))"
[ $fails -eq 0 ]
