#!/bin/zsh
# scripts/seed/gr-r5.sh <rung> [seed.bin] -- gate GR for the R5 test format (seed/tests/r5: cases.tsv + feat-cases.tsv, driven by check-r5.sh:
# compile with the R5 CLI incl. --source-path/--policy, extract-native, loader run with arguments). BOOTSTRAP-TOOL (zsh), owner HOUSE3.
#   rung r5a  part A only: every case except the effect programs listed in seed/tests/r5a/part-b.txt must PASS (part B is reported, not judged)
#   later     (r5b ...) all cases must PASS and the 16 neg/ refusal texts must be TEXT-OK (check-r5.sh's own exit status)
# Prints the check-r5 case lines, then one summary line starting "GR [r5 ...]"; exit 0 iff the rung's requirement holds.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
rung=${1:?usage: gr-r5.sh <rung> [seed.bin]}; bin=${2:-$SEED_BUILD/seed-1.bin}
R=$SEED_REPO; B=${SEED_BUILD:A}; log=$B/gr-r5-$rung.log
SEED_BUILD=$B zsh $R/seed/tests/r5/check-r5.sh $bin > $log 2>&1; full=$?
if [ "$rung" != r5a ]; then
  grep -E '^(FAIL|check-r5)' $log | head -20
  echo "GR [r5 full]: $(grep '^check-r5' $log | cut -c1-140)"; exit $full
fi
partb=$(grep -v '^#' $R/seed/tests/r5a/part-b.txt | grep .)
na=0; nfa=0; nb=0; nbp=0
for l in $(grep -E '^(PASS|FAIL) ' $log | awk '{print $1 "|" ($2 ~ /TEXT/ ? $3 : $2)}' | sed 's/:$//'); do
  v=${l%%|*}; lab=${l#*|}; lab=${lab%:}
  if echo "$partb" | grep -qx -- "$lab"; then nb=$((nb+1)); [ $v = PASS ] && nbp=$((nbp+1))
  else na=$((na+1)); [ $v = FAIL ] && { nfa=$((nfa+1)); echo "part-A FAIL: $(grep -F " $lab" $log | head -1)"; }; fi
done
echo "GR [r5 part A]: $((na-nfa))/$na part-A cases pass (part B, not judged: $nbp/$nb pass)"
[ $nfa -eq 0 ] && [ $na -gt 0 ]
