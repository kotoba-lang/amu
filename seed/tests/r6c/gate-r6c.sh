#!/bin/zsh
# seed/tests/r6c/gate-r6c.sh [--extra] -- the extra gate of rung R6C (agent R6C, 2026-10-03: more R6 source-route features).
# BOOTSTRAP-TOOL (zsh). gates.sh --rung r6c runs it as its XTRA row; BUILD ERR G1 G2 G3 G4 G5 GR (every earlier rung's tests)
# and, with --with-aux --with-unit, UNIT KIR LEXREAD LW A64GEN are gates.sh's own rows. Rows here:
#   R6C     seed/tests/r6c/check-r6c.sh with seed-1: unannotated parameters (refined from the checker's own refusal, as the
#           reference's infer-absent-parameter-types), (- x), a typed catch around a body that cannot abort, vector-drop /
#           vector-take / subvec / into, a map/vector literal as a :document result, the :f64 carrier; negatives: a parameter
#           whose uses disagree, = and + on :f64. Every positive also through the project route (byte-identical image).
#   LOOPW   the loop-node width (FRONT's latent miscompile, fixed in the R6B bridge): seed/tests/r6c/gen-bigloop.py writes a
#           program whose two nested `loop`s are read above node 131,072; seed-1 compiles it and main must answer the value
#           the generator computed (Python, same wrapping arithmetic).
#   LIBSTUB seed/tests/r6c/proj (project route): an importer that also gets a source-library group keeps its import stubs as
#           the last FN records (60-proj, R6C); want = stage-0's answer (d2cb84f6), the R6B seed loops on it.
#   R6B-X   seed/tests/r6b/gate-r6b.sh --extra: R6B's cases, SRCLIB, and (through it) R6A's, R5B's and R5A's extra rows.
# Exit 0 iff every row passes.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/../../../scripts/seed/lib.sh"
R=$SEED_REPO; B=${SEED_BUILD:A}; D=$R/seed/tests/r6c; W=$B/gate-r6c; rm -rf $W; mkdir -p $W
bin=$B/seed-1.bin; off=$(cat $B/seed-1.offset 2>/dev/null || echo 0)
L=$(seed_loader) || exit 2; L=${L:A}
SEED_RESOURCES_35=$R:$B   # for this script's own seed_run calls only (not exported: g1.sh etc. set their own)
fails=0
row() { printf "%-7s %s\n" $1 "$2"; [ $1 = FAIL ] && fails=$((fails+1)); return 0; }
# runmain <kseed> <tag> -> the value main answers (or trap)
runmain() {
  local x o v
  x=$(seed_run $bin $off extract-native $1 --symbol main --output $W/$2.bin 2>&1); o=$(print -r -- "$x" | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  [ -n "$o" ] || { echo "noextract"; return; }
  v=$(cd $W; KEXE_CPU_SECONDS=20 KEXE_WALL_SECONDS=20 $L $W/$2.bin $o 0 aarch64 - 2>/dev/null | tail -1)
  [ -n "$v" ] && echo $v || echo trap
}
SEED_BUILD=$B zsh $D/check-r6c.sh $bin > $B/gate-r6c-check.log 2>&1 && row PASS "R6C $(tail -1 $B/gate-r6c-check.log)" \
  || row FAIL "R6C $(grep -E '^FAIL' $B/gate-r6c-check.log | head -4 | tr '\n' ' ')"
# LOOPW
g=$(python3 $D/gen-bigloop.py $W/bigloop.kotoba); node=${${g#nodes }%% *}; want=${g##* }
seed_run $bin $off compile $W/bigloop.kotoba --output $W/bigloop.kseed > $W/bigloop.log 2>&1
v=$([ -s $W/bigloop.kseed ] && runmain $W/bigloop.kseed bigloop || echo "refused: $(grep -m1 seed: $W/bigloop.log)")
if [ "$v" = "$want" ] && [ $node -gt 131072 ]; then row PASS "LOOPW first loop read at node $node > 131072, main = $v (generator: $want)"
else row FAIL "LOOPW node $node, main '$v', want $want"; fi
# LIBSTUB
want=$(sed -n 's/^;; want: *\([^ ]*\).*/\1/p' $D/proj/main.kotoba | head -1)
seed_run $bin $off compile $D/proj/main.kotoba --source-path $D/proj/src --unpinned --output $W/libstub.kseed > $W/libstub.log 2>&1
v=$([ -s $W/libstub.kseed ] && runmain $W/libstub.kseed libstub || echo "refused: $(grep -m1 seed: $W/libstub.log)")
[ "$v" = "$want" ] && row PASS "LIBSTUB main = $v (stage-0 $want)" || row FAIL "LIBSTUB main '$v', want $want"
SEED_BUILD=$B zsh $R/seed/tests/r6b/gate-r6b.sh --extra > $B/gate-r6c-r6b.log 2>&1 && row PASS "R6B-X $(tail -1 $B/gate-r6c-r6b.log)" \
  || row FAIL "R6B-X $(grep -E '^FAIL' $B/gate-r6c-r6b.log | head -3 | tr '\n' ' ')"
echo "gate-r6c: $([ $fails -eq 0 ] && echo READY || echo "NOT READY ($fails failed)") (load $(uptime | sed 's/.*averages: //'))"
[ $fails -eq 0 ]
