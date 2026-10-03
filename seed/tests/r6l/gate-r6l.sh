#!/bin/zsh
# seed/tests/r6l/gate-r6l.sh [--extra] -- the extra gate of rung R6L (agent FOLD, 2026-10-04): two seed contract requests.
#   (1) FRONTSRC: a keyword made from text at RUN TIME (keyword-from-string, document-keyword-value) keeps its text: it is
#       registered in the loader's kgraph (slots 80/88 through the kind-4 pseudo heads __r6-kgput/__r6-kgget of 21-check) and
#       __r6-kwfind falls back to it after a static miss (r6k: __r6-trap, SIGTRAP).
#   (2) CMD: seed.main of the split exports `drv-compile-file src out` (= the driver's compile, no ok line; MM-QUIET).
# BOOTSTRAP-TOOL (zsh). Only seeds and the C loader run. Rows:
#   KWDYN   seed/tests/r6l/kwdyn.kotoba: main = 0 (7 checks: run-time text, equality with a literal, qualified, 2/3/4-byte
#           UTF-8 code points, two spellings of one keyword, a 1-letter name)
#   KWX     seed/tests/r6l/xmod: kx.lib makes the keywords, kx.main reads their texts; project route main = 0, and separate mode
#           (emit every module, then link) == the in-process container
#   DCF     an entry requiring seed.main (--source-path seed/split) calls drv-compile-file: the kwdyn container == `seed compile`'s,
#           nothing on stdout; then a refused source: status 1, the refusal on stderr, no stdout, no file
#   R6K-X   seed/tests/r6k/gate-r6k.sh --extra (R6K's rows, and through it R6J .. R5A)
# Exit 0 iff no row FAILs.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/../../../scripts/seed/lib.sh"
R=$SEED_REPO; B=${SEED_BUILD:A}; D=$R/seed/tests/r6l; W=$B/gate-r6l; rm -rf $W; mkdir -p $W
bin=$B/seed-1.bin; off=$(cat $B/seed-1.offset 2>/dev/null || echo 0)
SEED_RESOURCES_35=$R:$B
fails=0
row() { printf "%-7s %s\n" $1 "$2"; [ $1 = FAIL ] && fails=$((fails+1)); return 0; }
# img <kseed> <name> -> the status of its main under the loader (stdout/stderr to <name>.out/.err)
img() {
  local o
  o=$(seed_run $bin $off extract-native $1 --symbol main --output $W/$2.bin 2>/dev/null | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  [ -n "$o" ] || { echo noextract; return; }
  seed_run $W/$2.bin $o > $W/$2.out 2> $W/$2.err; echo $?
}
# KWDYN
seed_run $bin $off compile $D/kwdyn.kotoba --target aarch64-macos --output $W/kw.kseed > $W/kw.log 2>&1
v=$([ -s $W/kw.kseed ] && img $W/kw.kseed kw || echo "refused: $(grep -m1 seed: $W/kw.log)")
[ "$v" = 0 ] && row PASS "KWDYN main = 0 (7 run-time keyword text checks)" || row FAIL "KWDYN main = $v $(cat $W/kw.err 2>/dev/null)"
# KWX
X=$D/xmod/src; mkdir -p $W/o
seed_run $bin $off compile $X/kx/main.kotoba --source-path $X --unpinned --target aarch64-macos --output $W/kx.kseed > $W/kx.log 2>&1
v=$([ -s $W/kx.kseed ] && img $W/kx.kseed kx || echo "refused: $(grep -m1 seed: $W/kx.log)")
sep=bad
if seed_run $bin $off modules $X/kx/main.kotoba --source-path $X > $W/kx.order 2>> $W/kx.log; then
  ok=1
  while read -r ns fp; do r=(); [ $ns = kx.main ] && r=(--entry)
    seed_run $bin $off compile $fp --emit-module $r --object-dir $W/o --output $W/o/$ns.kso >> $W/kx.log 2>&1 || ok=0; done < $W/kx.order
  [ $ok = 1 ] && seed_run $bin $off link $W/o/kx.main.kso --object-dir $W/o --output $W/kx-sep.kseed >> $W/kx.log 2>&1 && cmp -s $W/kx.kseed $W/kx-sep.kseed && sep=same
fi
[ "$v" = 0 ] && [ $sep = same ] && row PASS "KWX main = 0 across modules, separate mode == in-process" || row FAIL "KWX main = $v, separate $sep"
# DCF
mkdir -p $W/dcf/dcf
dcf() {   # <expr> -> compiles and runs an entry whose main is <expr>
  printf '(ns dcf.main (:require [seed.main :refer [drv-compile-file]]))\n(defn main [] :i64 %s)\n' "$1" > $W/dcf/dcf/main.kotoba
  seed_run $bin $off compile $W/dcf/dcf/main.kotoba --source-path $W/dcf --source-path $R/seed/split --unpinned --target aarch64-macos \
    --output $W/dcf.kseed > $W/dcf.log 2>&1 || { echo "refused: $(grep -m1 seed: $W/dcf.log)"; return; }
  img $W/dcf.kseed dcf
}
v1=$(dcf "(drv-compile-file \"$D/kwdyn.kotoba\" \"$W/dcf-ok.kseed\")"); o1=$(wc -c < $W/dcf.out | tr -d ' ')
v2=$(dcf "(drv-compile-file \"$R/seed/tests/r6k/f32name.kotoba\" \"$W/dcf-bad.kseed\")"); o2=$(wc -c < $W/dcf.out | tr -d ' ')
e2=$(grep -m1 '^seed:' $W/dcf.err)
if [ "$v1" = 0 ] && [ "$o1" = 0 ] && cmp -s $W/dcf-ok.kseed $W/kw.kseed && [ "$v2" = 1 ] && [ "$o2" = 0 ] && [ ! -e $W/dcf-bad.kseed ] \
   && [ "$e2" = "seed: E2104 type mismatch in 'g': expected :f32 (byte 137)" ]
then row PASS "DCF drv-compile-file: container == seed compile's, no ok line; refusal status 1 on stderr, no file"
else row FAIL "DCF ok: status $v1 stdout $o1 B; refused: status $v2 stdout $o2 B [$e2]"; fi
# R6K-X
if [ -f $R/seed/tests/r6k/gate-r6k.sh ]; then
  SEED_BUILD=$B zsh $R/seed/tests/r6k/gate-r6k.sh --extra > $W/r6k.log 2>&1 && row PASS "R6K-X $(tail -1 $W/r6k.log)" \
    || row FAIL "R6K-X $(grep -E '^FAIL' $W/r6k.log | head -3 | tr '\n' ' ')"
fi
[ $fails -eq 0 ] && echo "gate-r6l: READY" || echo "gate-r6l: $fails FAIL"
exit $(( fails > 0 ))
