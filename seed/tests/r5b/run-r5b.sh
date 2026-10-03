#!/bin/zsh
# seed/tests/r5b/run-r5b.sh [seed.bin] -- the extra R5B cases of expect.tsv (owner R5B). BOOTSTRAP-TOOL (zsh).
# Each case: `seed compile <file> [--policy P] --output x.kseed`; a number is compared with main's value under the C loader
# (extract-native, then the loader), an `E<code> <text>` with the single refusal line (" (byte N)" dropped, no output left).
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/../../../scripts/seed/lib.sh"
R=$SEED_REPO; D=$R/seed/tests/r5b; W=${SEED_BUILD:A}/run-r5b; mkdir -p $W
bin=${1:-$SEED_BUILD/seed-1.bin}; bin=${bin:A}; off=$(cat ${bin%.bin}.offset)
L=$(seed_loader) || exit 2
export SEED_RESOURCES_35=$R:$W
pass=0 fail=0
grep -v '^#' $D/expect.tsv | grep . | while IFS=$'\t' read -r lab f pol want; do
  stem=${lab//\//_}; rm -f $W/$stem.kseed $W/$stem.bin
  po=(); [ "$pol" != - ] && po=(--policy $D/$pol)
  r=$(seed_run $bin $off compile $D/$f $po --output $W/$stem.kseed 2>&1); rc=$?
  if [[ $want == E* ]]; then
    got=$(echo "$r" | grep '^seed: E' | head -1 | sed -e 's/^seed: //' -e 's/ (byte [0-9-]*)$//')
    if [ $rc -ne 0 ] && [ ! -e $W/$stem.kseed ] && [ "$got" = "$want" ]; then pass=$((pass+1)); echo "PASS $lab"
    else fail=$((fail+1)); echo "FAIL $lab: rc=$rc got [$got] $(echo $r | head -c 160)"; fi
    continue
  fi
  if [ $rc -ne 0 ]; then fail=$((fail+1)); echo "FAIL $lab: refused: $(echo $r | head -c 200)"; continue; fi
  o=$(seed_run $bin $off extract-native $W/$stem.kseed --symbol main --output $W/$stem.bin 2>&1 | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  v=$(KEXE_CPU_SECONDS=20 KEXE_WALL_SECONDS=20 $L $W/$stem.bin $o 0 aarch64 37 2>/dev/null | tail -1)
  if [ "$v" = "$want" ]; then pass=$((pass+1)); echo "PASS $lab $v"; else fail=$((fail+1)); echo "FAIL $lab: got $v want $want"; fi
done
echo "run-r5b: PASS $pass FAIL $fail (seed $bin:t)"
[ $fail -eq 0 ]
