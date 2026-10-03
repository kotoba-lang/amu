#!/bin/zsh
# seed/tests/f64/test.sh [seed.bin [offset]] -- decimal-f64-parse on the KIR route (agent F64, 2026-10-04). BOOTSTRAP-TOOL
# (zsh, python3). No stage-0: the seed under test compiles
#   parse.kir    (compile-kir; 38 cases, gen-cases.py)   and   parse.kotoba (compile, the R6D source prelude)
# and export t must answer 1 on both under the C loader (1000+i names the first disagreeing case). gen-dec.py --check
# proves 12-kirread's dec group is the generated port of 21-check's prelude. Exit 0 iff all three pass.
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h:h}
export SEED_REPO=${SEED_REPO:-$R}; source $R/scripts/seed/lib.sh
bin=${1:-$SEED_BUILD/seed-1.bin}; off=${2:-$(cat ${bin%.bin}.offset)}
W=$SEED_BUILD/f64-test; rm -rf $W; mkdir -p $W; cp $H/parse.kir $H/parse.kotoba $W/
L=$(seed_loader) || exit 2
seed() { SEED_RESOURCES_35=$W seed_run $bin $off "$@"; }
fail=0
python3 $H/gen-dec.py --check || fail=1
python3 $H/gen-cases.py > /dev/null && cmp -s $H/parse.kir $W/parse.kir && cmp -s $H/parse.kotoba $W/parse.kotoba \
  || { echo "f64: parse.kir/parse.kotoba are not what gen-cases.py writes"; fail=1; }
for r in kir kotoba; do
  if [ $r = kir ]; then seed compile-kir $W/parse.kir --output $W/p-$r.kseed > $W/$r.log 2>&1
  else seed compile $W/parse.kotoba --target aarch64-macos --output $W/p-$r.kseed > $W/$r.log 2>&1; fi
  o=$(seed extract-native $W/p-$r.kseed --symbol t --output $W/p-$r.bin 2>> $W/$r.log | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  v=$( [ -n "$o" ] && KEXE_FUEL=100000000 $L $W/p-$r.bin $o 0 aarch64 - 2>&1 | tail -1 )
  echo "f64: $r route t -> ${v:-COMPILE-FAIL $(tail -1 $W/$r.log)}"
  [ "$v" = 1 ] || fail=1
done
[ $fail -eq 0 ] && echo "f64: PASS" || echo "f64: FAIL"
exit $fail
