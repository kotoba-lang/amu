#!/bin/zsh
# scripts/seed/float-diff.sh <seed.bin> [work-dir] -- FLOAT (rung r6j) differential of the seed's f64/f32 operations.
# BOOTSTRAP-TOOL (zsh). For every operation of seed/tests/float/ops.txt a one-export probe `(t a b)` over bit patterns is
# compiled (a) by the seed under test and (b) by STAGE-0 (bootstrap-reference; at most 2 stage-0 processes, nice), and
# both are run by the C loader on every (a, b) of seed/tests/float/vectors.txt (f64 or f32 patterns by the op's kind,
# i64 values for conversions from i64). Operations stage-0 refuses natively (f32-min/max, *-to-i64-truncating) are
# compared with seed/tests/float/oracle-c.c (C on this aarch64 host: fmin/fmax and the saturating (int64_t) cast =
# fcvtzs, the JVM's Math.min/max and (long) semantics up to NaN payloads). Prints one line per op and a total; exit 1 on
# any difference. FLOAT_OPS="op .." limits the run to those ops. Loaded-host timings are not results.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
SEED=${1:?usage: float-diff.sh <seed.bin> [work-dir]}; SOFF=$(cat ${SEED%.bin}.offset 2>/dev/null || echo 0)
W=${2:-$SEED_BUILD/float-diff}; mkdir -p $W/s0 $W/sd
T=$SEED_REPO/seed/tests/float
L=$(seed_loader) || exit 2
echo '{:allow #{}}' > $W/pol.edn
cc -O0 -o $W/oracle-c $T/oracle-c.c || exit 2
body() { case $2 in
 B64) echo "(f64-to-bits ($1 (f64-from-bits a) (f64-from-bits b)))";;
 U64) echo "(f64-to-bits ($1 (f64-from-bits a)))";;
 C64) echo "(if ($1 (f64-from-bits a) (f64-from-bits b)) 1 0)";;
 B32) echo "(f32-to-bits ($1 (f32-from-bits a) (f32-from-bits b)))";;
 U32) echo "(f32-to-bits ($1 (f32-from-bits a)))";;
 C32) echo "(if ($1 (f32-from-bits a) (f32-from-bits b)) 1 0)";;
 X64I) echo "($1 (f64-from-bits a))";;
 XI64) echo "(f64-to-bits ($1 a))";;
 X6432) echo "(f32-to-bits ($1 (f64-from-bits a)))";;
 X3264) echo "(f64-to-bits ($1 (f32-from-bits a)))";;
 XI32) echo "(f32-to-bits ($1 a))";;
 X32I) echo "($1 (f32-from-bits a))";;
esac; }
vecs() { case $1 in X3264|X32I) grep '^s ' $T/vectors.txt;; *64|X64I|X6432) grep '^d ' $T/vectors.txt;; XI64|XI32) grep '^i ' $T/vectors.txt;; *) grep '^s ' $T/vectors.txt;; esac | cut -c3-; }
bad=0; tot=0
while read op k; do
  [ -z "$op" ] && continue
  [ -n "${FLOAT_OPS:-}" ] && [[ " $FLOAT_OPS " != *" $op "* ]] && continue
  printf '(ns q (:export [t]))\n(defn t [a :i64 b :i64] :i64 %s)\n' "$(body $op $k)" > $W/sd/$op.kotoba
  # the seed
  seed_run $SEED $SOFF compile ${W:A}/sd/$op.kotoba --target aarch64-macos --output ${W:A}/sd/$op.kseed > $W/sd/$op.log 2>&1 \
    && seed_run $SEED $SOFF extract-native ${W:A}/sd/$op.kseed --symbol t --output ${W:A}/sd/$op.bin > $W/sd/$op.x 2>&1 \
    || { echo "$op SEED-REFUSED $(head -c 200 $W/sd/$op.log)"; bad=$((bad+1)); continue; }
  so=$(sed -n 's/.*:offset \([0-9]*\).*/\1/p' $W/sd/$op.x)
  # the reference: stage-0 natively, else the C oracle
  ref=s0
  if [ ! -s $W/s0/$op.bin ]; then
    seed_slot_take
    r=$( nice $SEED_STAGE0 compile $W/sd/$op.kotoba --target aarch64-macos --jvm-free --policy $W/pol.edn --output $W/s0/$op.kexe 2>&1 )
    echo "$r" | grep -q ':ok true' && r=$( nice $SEED_STAGE0 extract-native $W/s0/$op.kexe --symbol t --output $W/s0/$op.bin 2>&1 )
    seed_slot_give
    echo "$r" | grep -q ':ok true' && echo "$r" | sed -n 's/.*:offset \([0-9]*\).*/\1/p' > $W/s0/$op.off || rm -f $W/s0/$op.bin
  fi
  [ -s $W/s0/$op.bin ] || ref=c
  n=0; d=0; sn=0
  while read a b; do
    [ -z "$b" ] && b=0
    sv=$($L $W/sd/$op.bin $so 2 aarch64 - $a $b 2>/dev/null | tail -1) || sv=trap
    if [ $ref = s0 ]; then rv=$($L $W/s0/$op.bin $(cat $W/s0/$op.off) 2 aarch64 - $a $b 2>/dev/null | tail -1) || rv=trap
    else rv=$($W/oracle-c $op $a $b); fi
    n=$((n+1))
    if [[ $rv == snan* ]]; then sn=$((sn+1)); rv=${rv#snan }; [ "$sv" != "$rv" ] && continue; fi
    if [ "$sv" != "$rv" ]; then d=$((d+1)); [ $d -le ${FLOAT_SHOW:-3} ] && echo "  DIFF $op a=$a b=$b seed=$sv ref($ref)=$rv"; fi
  done < <(vecs $k)
  tot=$((tot+n))
  if [ $d -eq 0 ]; then echo "$op SAME $n ($ref)$( [ $sn -gt 0 ] && echo " ($sn runs with an sNaN operand: the quieted NaN accepted, see oracle-c.c)")"; else echo "$op DIFF $d/$n ($ref)"; bad=$((bad+1)); fi
done < $T/ops.txt
echo "float-diff: ${FLOAT_OPS:-$(grep -c . $T/ops.txt)} ops, $tot runs, $bad ops differ or refused"
[ $bad -eq 0 ]
