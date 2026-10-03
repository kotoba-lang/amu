#!/bin/zsh
# seed/tests/r6j/gate-r6j.sh [--extra] -- the extra gate of rung R6J (agent FLOAT, 2026-10-04: f64/f32 arithmetic on the source
# route: 36 operations -> SIR BIN/CMP/UN F* codes -> fmov + scalar FP instructions). BOOTSTRAP-TOOL (zsh). Rows:
#   FOPS    scripts/seed/float-diff.sh with seed-1: every operation over every ordered pair of 19 f64 / 18 f32 / 10 i64 patterns
#           (zeros, infinities, quiet/signalling/negative NaNs, denormals, extremes, 2^53+1, 2^63), equal to stage-0's native code
#           (32 ops) or to seed/tests/float/oracle-c.c (f32-min/max, *-to-i64-truncating, which stage-0 refuses natively).
#   FPROG   scripts/seed/float-prog.sh: seed/tests/float/prog.kotoba (lets, loops, f64 loop variables, calls with f64 args,
#           fused compare-and-branch, an operand stack deeper than the register temps), 7 exports x 13 arguments == stage-0.
#   FINTERP scripts/seed/float-interp.sh: kotoba.kir.interp compiled from source by seed-1 (objects of a selfbuild scan by the same
#           seed: FLOAT_SCAN, default $SEED_BUILD/sb; SKIP when absent) linked with seed/tests/float/interp-probe.kotoba: 14 checks.
#   R6I-X   seed/tests/r6i/gate-r6i.sh --extra (R6I's rows, and through it R6H .. R5A) when it exists.
# FLOAT_FAST=1 skips FOPS (5 min of loader runs on a loaded host). Exit 0 iff no row FAILs.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/../../../scripts/seed/lib.sh"
R=$SEED_REPO; B=${SEED_BUILD:A}; W=$B/gate-r6j; rm -rf $W; mkdir -p $W
bin=$B/seed-1.bin
fails=0
row() { printf "%-7s %s\n" $1 "$2"; [ $1 = FAIL ] && fails=$((fails+1)); return 0; }
if [ "${FLOAT_FAST:-0}" = 1 ]; then row SKIP "FOPS FLOAT_FAST=1"
else
  zsh $R/scripts/seed/float-diff.sh $bin $W/fops > $W/fops.log 2>&1 && row PASS "FOPS $(tail -1 $W/fops.log)" \
    || row FAIL "FOPS $(grep -E 'DIFF|REFUSED' $W/fops.log | head -3 | tr '\n' ' ')"
fi
zsh $R/scripts/seed/float-prog.sh $bin $W/fprog > $W/fprog.log 2>&1 && row PASS "FPROG $(tail -1 $W/fprog.log)" \
  || row FAIL "FPROG $(grep -E 'DIFF|REFUSED|refused' $W/fprog.log | head -3 | tr '\n' ' ')"
S=${FLOAT_SCAN:-$B/sb}
if [ -n "$(print -l $S/r6/o/kotoba.kir.interp*.kso(N))" ]; then
  zsh $R/scripts/seed/float-interp.sh $bin $S $W/finterp > $W/finterp.log 2>&1 && row PASS "FINTERP $(tail -1 $W/finterp.log)" \
    || row FAIL "FINTERP $(tail -1 $W/finterp.log)"
else row SKIP "FINTERP no kotoba.kir.interp object under $S/r6/o (run scripts/seed/selfbuild.sh --seed $bin --no-link $S)"; fi
if [ -f $R/seed/tests/r6i/gate-r6i.sh ]; then
  SEED_BUILD=$B zsh $R/seed/tests/r6i/gate-r6i.sh --extra > $W/r6i.log 2>&1 && row PASS "R6I-X $(tail -1 $W/r6i.log)" \
    || row FAIL "R6I-X $(grep -E '^FAIL' $W/r6i.log | head -3 | tr '\n' ' ')"
fi
[ $fails -eq 0 ] && echo "gate-r6j: READY" || echo "gate-r6j: $fails FAIL"
exit $(( fails > 0 ))
