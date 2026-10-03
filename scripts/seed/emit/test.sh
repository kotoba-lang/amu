#!/bin/zsh
# scripts/seed/emit/test.sh <seed.bin> [work-dir] -- tests of `compile-kir --emit-module` (agent EMIT, 2026-10-04).
# BOOTSTRAP-TOOL (zsh). Only the given seed runs (under the C loader).
#   E1 a KIR library (seed/tests/emit/lib.kir: i64 and string exports, a private helper, a string literal = an L line) becomes
#      a KSEEDO1 object with 3 E lines, 1 L line, 3 X lines, no R line
#   E2 a source entry (seed/tests/emit/src/emt/main.kotoba) compiles against it (--emit-module --entry), `seed link` joins
#      both, the image runs: main = 0 (every cross-route call answered as the KIR computes)
#   E3 the same entry with `:else (+ 100 (k/add3 1 2 3))` answers 115 (the control: a wrong link cannot pass E2 by exit 0)
#   E4 usage (status 2): no --ns; --metered; --output -
#   E5 a refused KIR program is refused with --emit-module as without it (seed/tests/kir/neg/04-format.kir: status 1, same line)
emulate -L zsh; setopt pipefail
R=$(cd "$(dirname "$0")/../../.." && pwd)
SB=${1:?usage: test.sh <seed.bin> [work-dir]}; SB=${SB:A}
W=${2:-$R/build/emit/test}; rm -rf $W; mkdir -p $W/o $W/c/src/emt; W=${W:A}
export SEED_REPO=$R SEED_BUILD=$W/sb SEED_RESOURCES_35=$R SEED_VECTOR_ITEMS=67108864; mkdir -p $SEED_BUILD
source $R/scripts/seed/lib.sh
pass=0; fail=0
ok() { echo "PASS $1"; pass=$((pass+1)); }
no() { echo "FAIL $1: $2"; fail=$((fail+1)); }
T=$R/seed/tests/emit
O=$W/o

seed_run $SB 0 compile-kir $T/lib.kir --emit-module --ns emt.kirlib --object-dir $O --output $O/emt.kirlib.kso > $W/e1.log 2>&1
k=$O/emt.kirlib.kso
if [ -s $k ] && [ "$(head -2 $k | tr '\n' ' ')" = "KSEEDO1 N emt.kirlib " ] && [ $(grep -c '^E ' $k) = 3 ] && [ $(grep -c '^L ' $k) = 1 ] \
   && [ $(grep -c '^X ' $k) = 3 ] && [ $(grep -c '^R ' $k) = 0 ] && grep -q '^E 1 [0-9]* add3 \[p0 :i64 p1 :i64 p2 :i64\] :i64 (SEEDSELF p0 p1 p2)$' $k
then ok E1; else no E1 "$(cat $W/e1.log)"; fi

img() {  # <entry.kotoba> <dir> -> runs the linked image, prints its status
  local f=$1 d=$2 off
  seed_run $SB 0 compile $f --emit-module --entry --object-dir $d --output $d/emt.main.kso > $d/c.log 2>&1 || { echo "compile"; return; }
  seed_run $SB 0 link $d/emt.main.kso --object-dir $d --output $d/img.kseed > $d/l.log 2>&1 || { echo "link"; return; }
  off=$(seed_run $SB 0 extract-native $d/img.kseed --symbol main --output $d/img.bin | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  [ -n "$off" ] || { echo "extract"; return; }
  seed_run $d/img.bin $off > $d/run.log 2>&1; echo $?
}
r=$(img $T/src/emt/main.kotoba $O); [ "$r" = 0 ] && ok E2 || no E2 "status $r"
cp $k $W/c/; sed 's/:else 0))/:else (+ 100 (k\/add3 1 2 3))))/' $T/src/emt/main.kotoba > $W/c/src/emt/main.kotoba
r=$(img $W/c/src/emt/main.kotoba $W/c); [ "$r" = 115 ] && ok E3 || no E3 "status $r"

u=0
seed_run $SB 0 compile-kir $T/lib.kir --emit-module --output $W/x.kso > /dev/null 2>&1; [ $? = 2 ] && u=$((u+1))
seed_run $SB 0 compile-kir $T/lib.kir --emit-module --ns a.b --metered --output $W/x.kso > /dev/null 2>&1; [ $? = 2 ] && u=$((u+1))
seed_run $SB 0 compile-kir $T/lib.kir --emit-module --ns a.b --output - > /dev/null 2>&1; [ $? = 2 ] && u=$((u+1))
[ $u = 3 ] && ok E4 || no E4 "$u of 3 usage refusals"

seed_run $SB 0 compile-kir $R/seed/tests/kir/neg/04-format.kir --emit-module --ns a.b --output $W/n.kso > $W/e5.log 2>&1; st=$?
seed_run $SB 0 compile-kir $R/seed/tests/kir/neg/04-format.kir --output $W/n.kseed > $W/e5.ref 2>&1; st0=$?
if [ $st = 1 ] && [ $st0 = 1 ] && cmp -s $W/e5.log $W/e5.ref && [ ! -e $W/n.kso ]; then ok E5; else no E5 "status $st/$st0 $(cat $W/e5.log)"; fi
echo "emit tests: $pass passed, $fail failed"
[ $fail = 0 ]
