#!/bin/zsh
# seed/tests/r5a/gate-r5a.sh [--update-golden] -- the gate of rung R5 part A (modules and linking; owner R5A). BOOTSTRAP-TOOL (zsh).
# Uses $SEED_BUILD/seed-{0,1,2}.bin (seed-0 = the previous rung's seed, seed-1 = seed-0 compiles the unity, seed-2 = seed-1 compiles
# it; scripts/seed/build.sh 1 / 2) and runs, in order:
#   PREV   scripts/seed/gates.sh --rung r4 --no-build --skip G3: BUILD ERR G1 G2 G4 G5 GR(r1 r3 r4) -- every previous gate
#   G3     scripts/seed/g3.sh --rung r5a: refusal texts against seed/tests/golden/refusal-r5a.txt (R5A moved 10 refusals of
#          refusal-r4: files with :require now reach discovery, attr-map/facet files reach their bodies; --update-golden records)
#   R5A    seed/tests/r5/check-r5.sh with seed-1, restricted to the part-A cases (every case except the effect programs listed in
#          seed/tests/r5a/part-b.txt): all PASS; the part-B cases are reported, not judged
#   SPLIT  the rung proof on the project route: seed/split/gen-split.py --check (the namespace split is current); seed-1 compiles
#          seed/split/seed/main.kotoba --source-path seed/split --unpinned -> split-1; split-1 compiles it again -> split-2;
#          split-1 == split-2 (fixed point of the namespace-split seed), and split-1 compiles the unity to the same container as
#          seed-1 does (seed-2.kseed): the linked seed behaves as the unity seed on its own source
#   SPLIT-G1/G2  scripts/seed/g1.sh / g2.sh with split-1 (19 ports, corpus) and the containers compared with seed-1's
#   SEP    seed/tests/r5a/sep-r5a.sh: separate mode (compile --emit-module per module, `seed link`) == the in-process container
# Exit 0 iff every row passes.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/../../../scripts/seed/lib.sh"
R=$SEED_REPO; B=${SEED_BUILD:A}; D=$R/seed/tests/r5a; S=$R/scripts/seed
upd=0; [ "$1" = --update-golden ] && upd=1
fails=0
GS=$B/gates/r5a; mkdir -p $GS; : > $GS/summary.tsv
# row STATUS "NAME detail": the table line, and the gate summary row (rung-report.sh --record r5a reads $SEED_BUILD/gates/r5a)
row() { printf "%-5s %s\n" $1 "$2"; [ $1 = FAIL ] && fails=$((fails+1)); printf '%s\t%s\t0\t%s\n' "${2%% *}" $1 "${2#* }" >> $GS/summary.tsv; return 0; }
for k in 0 1 2; do [ -s $B/seed-$k.bin ] || { echo "gate-r5a: no $B/seed-$k.bin" >&2; exit 2; }; done

# PREV
SEED_BUILD=$B zsh $S/gates.sh --rung r4 --no-build --skip G3 > $B/gate-r5a-prev.log 2>&1 && row PASS "PREV gates --rung r4 (G3 skipped): $(grep 'rung r4' $B/gate-r5a-prev.log)" \
  || row FAIL "PREV: $(grep -E 'FAIL|rung r4' $B/gate-r5a-prev.log | tr '\n' ' ' | cut -c1-300)"
# G3
if [ $upd = 1 ]; then SEED_BUILD=$B zsh $S/g3.sh --rung r5a --update $B/seed-1.bin > $B/gate-r5a-g3.log 2>&1
else SEED_BUILD=$B zsh $S/g3.sh --rung r5a $B/seed-1.bin > $B/gate-r5a-g3.log 2>&1; fi \
  && row PASS "G3 $(tail -1 $B/gate-r5a-g3.log)" || row FAIL "G3 $(tail -1 $B/gate-r5a-g3.log)"
# R5A
SEED_BUILD=$B zsh $R/seed/tests/r5/check-r5.sh $B/seed-1.bin > $B/gate-r5a-r5.log 2>&1
partb=$(grep -v '^#' $D/part-b.txt | grep .)
na=0 nfa=0 nb=0 nbp=0
for l in $(grep -E '^(PASS|FAIL) ' $B/gate-r5a-r5.log | awk '{print $1 "|" ($2 ~ /TEXT/ ? $3 : $2)}' | sed 's/:$//'); do
  v=${l%%|*}; lab=${l#*|}; lab=${lab%:}
  if echo "$partb" | grep -qx -- "$lab"; then nb=$((nb+1)); [ $v = PASS ] && nbp=$((nbp+1))
  else na=$((na+1)); [ $v = FAIL ] && { nfa=$((nfa+1)); echo "  part-A FAIL: $(grep -F " $lab" $B/gate-r5a-r5.log | head -1)"; }; fi
done
[ $nfa -eq 0 ] && [ $na -gt 0 ] && row PASS "R5A part-A cases: $((na-nfa))/$na pass (part B, not judged: $nbp/$nb pass)" || row FAIL "R5A part-A cases: $((na-nfa))/$na pass"
# SPLIT
python3 $R/seed/split/gen-split.py --check > $B/gate-r5a-split.log 2>&1 || row FAIL "SPLIT gen-split --check: $(cat $B/gate-r5a-split.log | head -2)"
spl() {   # spl <compiler.bin> <out-prefix>
  local bin=$1 out=$2 off=$(cat ${1%.bin}.offset) r
  rm -f $out.kseed $out.bin
  seed_run $bin $off compile $R/seed/split/seed/main.kotoba --source-path $R/seed/split --unpinned --output $out.kseed >> $B/gate-r5a-split.log 2>&1 || return 1
  r=$(seed_run $bin $off extract-native $out.kseed --symbol main --output $out.bin) || return 1
  echo "$r" | sed -n 's/.*:offset \([0-9]*\).*/\1/p' > $out.offset
}
sha() { shasum -a 256 $1 | cut -c1-16; }
if spl $B/seed-1.bin $B/split-1 && spl $B/split-1.bin $B/split-2; then
  if cmp -s $B/split-1.bin $B/split-2.bin; then row PASS "SPLIT fixed point split-1 == split-2 $(sha $B/split-1.bin) ($(wc -c < $B/split-1.bin | tr -d ' ') bytes; unity seed-1 $(wc -c < $B/seed-1.bin | tr -d ' '))"
  else row FAIL "SPLIT split-1 $(sha $B/split-1.bin) != split-2 $(sha $B/split-2.bin)"; fi
  seed_run $B/split-1.bin $(cat $B/split-1.offset) compile $B/seed-unity.kotoba --output $B/split-unity.kseed >> $B/gate-r5a-split.log 2>&1
  cmp -s $B/split-unity.kseed $B/seed-2.kseed && row PASS "SPLIT split-1 compiles the unity to seed-2.kseed (identical)" || row FAIL "SPLIT split-1 on the unity differs from seed-2.kseed"
  zsh $S/g1.sh $B/split-1.bin > $B/gate-r5a-g1.log 2>&1 && row PASS "SPLIT-G1 $(tail -1 $B/gate-r5a-g1.log)" || row FAIL "SPLIT-G1 $(tail -1 $B/gate-r5a-g1.log)"
  zsh $S/g2.sh $B/split-1.bin > $B/gate-r5a-g2.log 2>&1 && row PASS "SPLIT-G2 $(tail -1 $B/gate-r5a-g2.log)" || row FAIL "SPLIT-G2 $(tail -1 $B/gate-r5a-g2.log)"
  nd=0; nc=0
  for f in $B/g1-split-1/*.kseed(N) $B/g2-split-1/*.kseed(N); do
    g=${f/split-1/seed-1}; [ -f $g ] || continue; nc=$((nc+1)); cmp -s $f $g || nd=$((nd+1))
  done
  [ $nd -eq 0 ] && [ $nc -gt 0 ] && row PASS "SPLIT-G4 split-1 vs seed-1 containers: $nc identical" || row FAIL "SPLIT-G4 $nd of $nc containers differ"
else row FAIL "SPLIT compile: $(grep '^seed:' $B/gate-r5a-split.log | head -1)"; fi
# SEP: separate mode (one process per module + seed link) gives the in-process image on every multi-module positive and the split seed
SEED_BUILD=$B zsh $D/sep-r5a.sh $B/seed-1.bin > $B/gate-r5a-sep.log 2>&1 && row PASS "SEP $(tail -1 $B/gate-r5a-sep.log)" || row FAIL "SEP $(grep -v '^SAME' $B/gate-r5a-sep.log | head -3 | tr '\n' ' ')"
echo "gate-r5a: $([ $fails -eq 0 ] && echo READY || echo "NOT READY ($fails failed)") (load $(uptime | sed 's/.*averages: //'))"
[ $fails -eq 0 ]
