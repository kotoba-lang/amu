#!/bin/zsh
# scripts/seed/float-prog.sh <seed.bin> [work-dir] -- FLOAT (rung r6j) program differential: seed/tests/float/prog.kotoba
# compiled by the seed under test and by STAGE-0 (bootstrap-reference, nice, 2-slot lock); every export run by the C loader
# on the arguments below; exit 1 on any difference. BOOTSTRAP-TOOL (zsh).
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
SEED=${1:?usage: float-prog.sh <seed.bin> [work-dir]}; SOFF=$(cat ${SEED%.bin}.offset 2>/dev/null || echo 0)
W=${2:-$SEED_BUILD/float-prog}; mkdir -p $W
P=$SEED_REPO/seed/tests/float/prog.kotoba
L=$(seed_loader) || exit 2
echo '{:allow #{}}' > $W/pol.edn
seed_run $SEED $SOFF compile $P --target aarch64-macos --output ${W:A}/prog.kseed > $W/seed.log 2>&1 || { echo "float-prog: SEED REFUSED: $(head -c 300 $W/seed.log)"; exit 1; }
seed_slot_take
r=$( nice $SEED_STAGE0 compile $P --target aarch64-macos --jvm-free --policy $W/pol.edn --output $W/prog.kexe 2>&1 )
seed_slot_give
echo "$r" | grep -q ':ok true' || { echo "float-prog: stage-0 refused: $(echo $r | grep -o ':message "[^"]*"')"; exit 2; }
bad=0; n=0
for e in $(sed -n 's/.*(:export \[\([^]]*\)\].*/\1/p' $P); do
  seed_run $SEED $SOFF extract-native ${W:A}/prog.kseed --symbol $e --output ${W:A}/s-$e.bin > $W/s-$e.x 2>&1 || { echo "$e: seed extract failed"; bad=$((bad+1)); continue; }
  seed_slot_take; r=$( nice $SEED_STAGE0 extract-native $W/prog.kexe --symbol $e --output $W/r-$e.bin 2>&1 ); seed_slot_give
  so=$(sed -n 's/.*:offset \([0-9]*\).*/\1/p' $W/s-$e.x); ro=$(echo "$r" | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  for a in 0 1 2 3 7 10 100 12345 -1 -17 1000000007 9007199254740993 -9223372036854775807; do
    sv=$($L $W/s-$e.bin $so 1 aarch64 - $a 2>/dev/null | tail -1) || sv=trap
    rv=$($L $W/r-$e.bin $ro 1 aarch64 - $a 2>/dev/null | tail -1) || rv=trap
    n=$((n+1))
    [ "$sv" = "$rv" ] || { bad=$((bad+1)); echo "  DIFF $e($a) seed=$sv stage0=$rv"; }
  done
  echo "$e done"
done
echo "float-prog: $n runs, $bad differences"
[ $bad -eq 0 ]
