#!/bin/zsh
# seed/tests/r6m/gate-r6m.sh [--extra] -- the extra gate of rung R6M (agent SEEDLANG, 2026-10-04): language behind the 47
# compile refusals of the CMD corpus run (seed/amu-main/README.md section 7). BOOTSTRAP-TOOL (zsh). Only seeds and the C
# loader run (the goldens were recorded once from stage-0 d2cb84f6, BOOTSTRAP-REFERENCE, and are compared here by content).
# Rows:
#   EXPT   seed/tests/r6m/xport/xp.kotoba: exports of :string / :vector-i64 / :bool results, a :string parameter and a variant
#          result, run under the C loader (KEXE_STRUCTURED_REPORT, KEXE_RESULT_TYPE per xp.runs); every report == xp.expected
#          (stage-0's code gives the same reports; handle numbers are not compared)
#   V47    `seed check` of the 47 programs of seed/tests/r6m/p47.txt (stage-0 compiles all 47; the r6l seed refused all 47):
#          the verdict lines == p47.expected (ACCEPT or the refusal line). Their behaviour against stage-0 is measured by
#          seed/amu-main/parity.sh (seed/rungs/r6m.record), not here.
#   R6L-X  seed/tests/r6l/gate-r6l.sh --extra (R6L's rows, and through it R6K .. R5A)
# Exit 0 iff no row FAILs. --update rewrites p47.expected (review the git diff).
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/../../../scripts/seed/lib.sh"
R=$SEED_REPO; B=${SEED_BUILD:A}; D=$R/seed/tests/r6m; W=$B/gate-r6m; rm -rf $W; mkdir -p $W
upd=0; [ "$1" = --update ] && upd=1
bin=$B/seed-1.bin; off=$(cat $B/seed-1.offset 2>/dev/null || echo 0)
L=$(seed_loader) || exit 2
fails=0
row() { printf "%-7s %s\n" $1 "$2"; [ $1 = FAIL ] && fails=$((fails+1)); return 0; }
# EXPT
run1() {   # run1 <bin> <offset> <arity> <result-type> [arg]: the loader's report without fuel (and without handle numbers)
  local b=$1 o=$2 a=$3 t=$4 x=$5
  KEXE_STRUCTURED_REPORT=1 KEXE_RESULT_TYPE=$t KEXE_FUEL=16777216 $L $b $o $a aarch64 35,37,38,39 $x 2>/dev/null | grep '^{:status' \
    | sed -e 's/ :fuel {.*//' | if [ $t = i64 ]; then cat; else sed -e 's/ :result -\{0,1\}[0-9][0-9]*//'; fi
}
SEED_RESOURCES_35=$R:$W seed_run $bin $off compile $D/xport/xp.kotoba --target aarch64-macos --output $W/xp.kseed > $W/xp.log 2>&1
: > $W/xp.out
if [ -s $W/xp.kseed ]; then
  while read -r s a t x; do
    o=$(SEED_RESOURCES_35=$R:$W seed_run $bin $off extract-native $W/xp.kseed --symbol $s --output $W/xp.$s.bin 2>/dev/null | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
    print -r -- "$s $x	$(run1 $W/xp.$s.bin $o $a $t $x)" >> $W/xp.out
  done < $D/xport/xp.runs
fi
if cmp -s $W/xp.out $D/xport/xp.expected; then row PASS "EXPT $(wc -l < $W/xp.out | tr -d ' ') export runs == xp.expected (stage-0's reports)"
else row FAIL "EXPT $(diff $D/xport/xp.expected $W/xp.out | grep '^>' | head -2 | tr '\n' ' ' | cut -c1-200) $(grep -m1 seed: $W/xp.log)"; fi
# V47
: > $W/p47.out
while read -r f; do
  [ -n "$f" ] || continue
  SEED_RESOURCES_35=$R seed_run $bin $off check $R/$f > $W/c.out 2> $W/c.err; c=$?
  if [ $c = 0 ]; then v=ACCEPT; else v="REFUSED $(head -1 $W/c.err)"; fi
  print -r -- "$f	$v" >> $W/p47.out
done < $D/p47.txt
[ $upd = 1 ] && cp $W/p47.out $D/p47.expected
na=$(grep -c '	ACCEPT$' $W/p47.out)
if cmp -s $W/p47.out $D/p47.expected; then row PASS "V47 $na of $(wc -l < $W/p47.out | tr -d ' ') accepted, verdicts == p47.expected"
else row FAIL "V47 $(diff $D/p47.expected $W/p47.out | grep '^>' | head -2 | tr '\n' ' ' | cut -c1-200)"; fi
# R6L-X
if [ -f $R/seed/tests/r6l/gate-r6l.sh ]; then
  SEED_BUILD=$B zsh $R/seed/tests/r6l/gate-r6l.sh --extra > $W/r6l.log 2>&1 && row PASS "R6L-X $(tail -1 $W/r6l.log)" \
    || row FAIL "R6L-X $(grep -E '^FAIL' $W/r6l.log | head -3 | tr '\n' ' ' | cut -c1-300)"
fi
[ $fails -eq 0 ] && echo "gate-r6m: READY" || echo "gate-r6m: $fails FAIL"
exit $(( fails > 0 ))
