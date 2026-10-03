#!/bin/zsh
# seed/tests/r5/check-r5.sh [seed.bin [offset]] -- the R5 conformance gate, test-first (owner R5D). BOOTSTRAP-TOOL (zsh).
# For every case of cases.tsv + feat-cases.tsv the SEED (default $SEED_BUILD/seed-1.bin) runs, in loader command mode:
#     compile <entry> [--source-path <dir> --unpinned] --policy <{:allow #{}}> --output <x.kseed>  (R5 CLI; the oracle policy)
#     extract-native <x.kseed> --symbol <fn> --output <x.bin>
# and the C loader runs <fn> with the case's i64 arguments. Verdicts:
#   positive (oracle value, or r5.spec where stage-0 refused): PASS iff the value is equal; FAIL otherwise (a seed refusal
#     of a positive FAILS).
#   negative (oracle `refused`): PASS iff the seed refuses (one stderr line "seed: E<code> <text> (byte N)", no output);
#     for neg/ (texts pinned by kotoba-lang with =) also TEXT-OK iff <text> equals column 6 of cases.tsv, else TEXT-DIFF
#     (reported, counted separately: the R5 gate requires TEXT-OK for all 16 neg/ cases).
# Exit 0 iff every case PASSes and every neg/ case is TEXT-OK. Prints one line per case and a summary.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/../../../scripts/seed/lib.sh"
R=$SEED_REPO; D=$R/seed/tests/r5; W=$SEED_BUILD/check-r5; mkdir -p $W
bin=${1:-$SEED_BUILD/seed-1.bin}; off=${2:-$(cat ${bin%.bin}.offset)}
[ -s $bin ] || { echo "check-r5: no compiler $bin" >&2; exit 2; }
L=$(seed_loader) || exit 2
export SEED_RESOURCES_35=$R:$W
echo '{:allow #{}}' > $W/pol.edn
typeset -A ORA SPEC
while IFS=$'\t' read -r lab v msg; do ORA[$lab]=$v; done < $D/r5.oracle
grep -v '^;;' $D/r5.spec | grep . | while read -r lab v; do SPEC[$lab]=$v; done
pass=0 fail=0 tok=0 tdiff=0
local stem want kind r v rc got o
local -a spo av
cat $D/cases.tsv $D/feat-cases.tsv | grep -v '^#' | grep . | while IFS=$'\t' read -r lab entry sp fn args text; do
  stem=${lab//\//_}; want=${ORA[$lab]}; kind=pos; spo=(); av=()
  [ "$sp" != - ] && spo=(--source-path $D/$sp --unpinned)
  [ "$args" != - ] && av=(${(s:,:)args})
  if [ "$want" = refused ]; then
    if [ -n "${SPEC[$lab]}" ]; then want=${SPEC[$lab]}; else kind=neg; fi
  fi
  rm -f $W/$stem.kseed $W/$stem.bin
  r=$( (cd $D; seed_run $bin $off compile $D/$entry $spo --policy $W/pol.edn --output $W/$stem.kseed) 2>&1 )
  rc=$?
  if [ $kind = neg ]; then
    if [ $rc -ne 0 ] && [ ! -s $W/$stem.kseed ] && echo "$r" | grep -q '^seed: E[0-9]'; then
      pass=$((pass+1)); got=$(echo "$r" | grep '^seed: E' | head -1 | sed -e 's/^seed: E[0-9]* //' -e 's/ (byte [0-9-]*)$//')
      if [[ $lab == neg/* ]]; then
        if [ "$got" = "$text" ]; then tok=$((tok+1)); echo "PASS TEXT-OK $lab"; else tdiff=$((tdiff+1)); echo "PASS TEXT-DIFF $lab: $got"; fi
      else echo "PASS $lab: $got"; fi
    else fail=$((fail+1)); echo "FAIL $lab: not refused (rc=$rc) $(echo $r | head -c 160)"; fi
    continue
  fi
  if [ $rc -ne 0 ]; then fail=$((fail+1)); echo "FAIL $lab: seed refused: $(echo $r | head -c 200)"; continue; fi
  r=$(seed_run $bin $off extract-native $W/$stem.kseed --symbol $fn --output $W/$stem.bin 2>&1)
  o=$(echo "$r" | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  [ -n "$o" ] || { fail=$((fail+1)); echo "FAIL $lab: extract: $(echo $r | head -c 160)"; continue; }
  v=$(KEXE_CPU_SECONDS=20 KEXE_WALL_SECONDS=20 $L $W/$stem.bin $o ${#av} aarch64 - $av 2>/dev/null | tail -1); rc=${pipestatus[1]}
  [ $rc -eq 0 ] || v=trap
  if [ "$v" = "$want" ]; then pass=$((pass+1)); echo "PASS $lab $v"; else fail=$((fail+1)); echo "FAIL $lab: got $v want $want"; fi
done
echo "check-r5: PASS $pass FAIL $fail; neg/ texts: TEXT-OK $tok TEXT-DIFF $tdiff (seed $bin)"
[ $fail -eq 0 ] && [ $tdiff -eq 0 ]
