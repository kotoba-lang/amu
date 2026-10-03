#!/bin/zsh
# seed/tests/r6k/gate-r6k.sh [--extra] -- the extra gate of rung R6K (agent FOLD, 2026-10-04). R6K folds EMIT
# (`compile-kir --emit-module`, the 90-drv EMIT block, whose sources entered at d87d7646b but were never gated by a rung) into
# the rung chain, and answers two seed contract requests: TY-F32 11 in HEADS / drv-tyname (TMPL), and a project-route refusal
# in a module other than the entry names that module's path (MAINS). BOOTSTRAP-TOOL (zsh). Only seeds and the C loader run. Rows:
#   EMIT    scripts/seed/emit/test.sh with seed-1 (E1..E5: KSEEDO1 object from KIR, cross-route link runs, control 115, usage, refusal)
#   SAME    scripts/seed/emit/same.sh <prev rung seed> seed-1: every compile-kir / compile / --emit-module / unity / extract-native
#           case answers byte-identically under the previous rung's seed and seed-1 (R6K adds texts only). SKIP when no
#           previous seed (FOLD_PREV, default $B/seed-0.bin) or no KIR dir (KIR_DIR, default $B/kir-gate-seed-1 of the KIR gate).
#   PJPATH  seed/tests/r6k/pjpath: a reader error in a dependency names its path (" in <path>"); one in the entry keeps the R5A text
#   F32     seed/tests/r6k/f32name.kotoba: the refusal spells the expected type ":f32" (r6j: "?")
#   R6J-X   seed/tests/r6j/gate-r6j.sh --extra (R6J's rows, and through it R6I .. R5A)
# Exit 0 iff no row FAILs.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/../../../scripts/seed/lib.sh"
R=$SEED_REPO; B=${SEED_BUILD:A}; D=$R/seed/tests/r6k; W=$B/gate-r6k; rm -rf $W; mkdir -p $W
bin=$B/seed-1.bin; off=$(cat $B/seed-1.offset 2>/dev/null || echo 0)
SEED_RESOURCES_35=$R:$B
fails=0
row() { printf "%-7s %s\n" $1 "$2"; [ $1 = FAIL ] && fails=$((fails+1)); return 0; }
# EMIT
zsh $R/scripts/seed/emit/test.sh $bin $W/emit > $W/emit.log 2>&1 && row PASS "EMIT $(tail -1 $W/emit.log)" \
  || row FAIL "EMIT $(grep -E '^FAIL' $W/emit.log | head -3 | tr '\n' ' ')"
# SAME
prev=${FOLD_PREV:-$B/seed-0.bin}; kd=${KIR_DIR:-$B/kir-gate-seed-1}
if [ -s $prev ] && [ -n "$(print -l $kd/*.kir(N))" ]; then
  KIR_DIR=$kd UNITY=$B/seed-unity.kotoba zsh $R/scripts/seed/emit/same.sh $prev $bin $W/same > $W/same.log 2>&1 \
    && row PASS "SAME prev $(shasum -a 256 $prev | cut -c1-12): $(tail -1 $W/same.log)" \
    || row FAIL "SAME $(grep -E '^DIFF' $W/same.log | head -4 | tr '\n' ' ') $(tail -1 $W/same.log)"
else row SKIP "SAME no previous seed $prev or no KIR in $kd (run the KIR gate first)"; fi
# PJPATH
P=$D/pjpath
seed_run $bin $off compile $P/dep/src/pk/main.kotoba --source-path $P/dep/src --unpinned --target aarch64-macos --output $W/pd.kseed > $W/pd.log 2>&1; s1=$?
seed_run $bin $off compile $P/entry/src/pk/main.kotoba --source-path $P/entry/src --unpinned --target aarch64-macos --output $W/pe.kseed > $W/pe.log 2>&1; s2=$?
l1=$(grep -m1 '^seed:' $W/pd.log); l2=$(grep -m1 '^seed:' $W/pe.log)
if [ $s1 = 1 ] && [ "$l1" = "seed: E1101 unexpected ')' (byte 41) in $P/dep/src/pk/lib.kotoba" ] && [ $s2 = 1 ] \
   && [[ "$l2" =~ "^seed: E1101 unexpected '\)' \(byte [0-9]+\)$" ]] && [ ! -e $W/pd.kseed ] && [ ! -e $W/pe.kseed ]
then row PASS "PJPATH dependency error names ${P:t}/dep/src/pk/lib.kotoba; entry error text unchanged"
else row FAIL "PJPATH $s1 [$l1] / $s2 [$l2]"; fi
# F32
seed_run $bin $off compile $D/f32name.kotoba --target aarch64-macos --output $W/f.kseed > $W/f.log 2>&1; s=$?
l=$(grep -m1 '^seed:' $W/f.log)
[ $s = 1 ] && [ "$l" = "seed: E2104 type mismatch in 'g': expected :f32 (byte 137)" ] && row PASS "F32 $l" || row FAIL "F32 $s [$l]"
# R6J-X
if [ -f $R/seed/tests/r6j/gate-r6j.sh ]; then
  SEED_BUILD=$B zsh $R/seed/tests/r6j/gate-r6j.sh --extra > $W/r6j.log 2>&1 && row PASS "R6J-X $(tail -1 $W/r6j.log)" \
    || row FAIL "R6J-X $(grep -E '^FAIL' $W/r6j.log | head -3 | tr '\n' ' ')"
fi
[ $fails -eq 0 ] && echo "gate-r6k: READY" || echo "gate-r6k: $fails FAIL"
exit $(( fails > 0 ))
