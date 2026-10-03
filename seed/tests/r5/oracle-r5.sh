#!/bin/zsh
# seed/tests/r5/oracle-r5.sh [label-substring ...] -- record STAGE-0 (bootstrap-reference) verdicts for the R5 cases.
# BOOTSTRAP-TOOL (zsh), owner R5D. Reads seed/tests/r5/cases.tsv and feat-cases.tsv (gen-feat.py); for each case stage-0
# (build/native-image/amu-native, never -next) compiles the entry (--target aarch64-macos, --source-path when the case
# names one, policy {:allow #{}}), extracts the case's function and the C loader runs it with the case's i64 arguments.
# Writes seed/tests/r5/r5.oracle: `<label>\t<value>|trap|refused\t<stage-0 message>` (sorted). At most 2 stage-0
# processes machine-wide (lib.sh slots), nice. With label substrings only those lines are recomputed and merged.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/../../../scripts/seed/lib.sh"
R=$SEED_REPO; D=$R/seed/tests/r5; W=$SEED_BUILD/oracle-r5; mkdir -p $W
echo '{:allow #{}}' > $W/pol.edn
L=$(seed_loader) || exit 2
only="$*"
verdict() {   # verdict <label> <entry> <srcpath> <fn> <args>
  local lab=$1 entry=$D/$2 sp=$3 fn=$4 args=$5 stem=${1//\//_} r v rc off n
  local -a spo av
  [ "$sp" != - ] && spo=(--source-path $D/$sp --unpinned)   # stage-0 refuses an unpinned multi-module compile without --unpinned
  # stage-0 refuses a native `main` with parameters ("main must take zero arguments"; the seed admits it). For a case
  # that calls main with arguments the oracle compiles a copy with main renamed oracle-main (export vector included)
  # and runs that; the line is marked "adapted". Only the name changes (and, for a file without an ns form, the line
  # `(ns oracle (:export [oracle-main]))` is prepended: stage-0 needs an explicit export list once there is no main).
  local adapted=""
  if [ "$fn" = main ] && [ "$args" != - ]; then
    mkdir -p $W/adapt/${entry:h:t}; cp $entry $W/adapt/${entry:h:t}/${entry:t}
    sed -i '' -e 's/(defn main /(defn oracle-main /g' -e 's/\[main\]/[oracle-main]/g' $W/adapt/${entry:h:t}/${entry:t}
    if ! grep -q '(ns ' $W/adapt/${entry:h:t}/${entry:t}; then
      # stage-0: "entryless library requires an explicit non-empty namespace export list"
      { echo '(ns oracle (:export [oracle-main]))'; cat $entry; } | sed -e 's/(defn main /(defn oracle-main /g' > $W/adapt/${entry:h:t}/${entry:t}
      adapted=" (adapted: main renamed oracle-main, ns line added)"
    else adapted=" (adapted: main renamed oracle-main)"; fi
    entry=$W/adapt/${entry:h:t}/${entry:t}; fn=oracle-main
  fi
  [ "$args" != - ] && av=(${(s:,:)args})
  n=${#av}
  seed_slot_take
  r=$( ulimit -s 65500; cd $D; nice $SEED_STAGE0 compile $entry $spo --target aarch64-macos --jvm-free --policy $W/pol.edn --output $W/$stem.kexe 2>&1 )
  if echo "$r" | grep -q ':ok true'; then
    r=$( nice $SEED_STAGE0 extract-native $W/$stem.kexe --symbol $fn --output $W/$stem.bin 2>&1 )
  fi
  seed_slot_give
  echo "$r" > $W/$stem.log
  if ! echo "$r" | grep -q ':ok true'; then
    printf 'refused\t%s%s\n' "$(echo $r | grep -o ':message "\([^"\\]\|\\.\)*"' | head -1 | cut -c11- | sed 's/"$//')" "$adapted"; return
  fi
  off=$(echo "$r" | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  v=$(cd $W; KEXE_CPU_SECONDS=20 KEXE_WALL_SECONDS=20 $L $W/$stem.bin $off $n aarch64 - $av 2>/dev/null | tail -1); rc=${pipestatus[1]}
  if [ $rc -eq 0 ] && [ -n "$v" ]; then printf '%s\t%s\n' $v "${adapted# }"; else printf 'trap\t%s\n' "rc=$rc$adapted"; fi
}
: > $W/new
local hit s
cat $D/cases.tsv $D/feat-cases.tsv | grep -v '^#' | grep . | while IFS=$'\t' read -r lab entry sp fn args expect; do
  if [ -n "$only" ]; then hit=0; for s in ${=only}; do [[ $lab == *$s* ]] && hit=1; done; [ $hit -eq 1 ] || continue; fi
  v=$(verdict $lab $entry $sp $fn $args)
  printf '%s\t%s\n' $lab "$v" >> $W/new
  echo "$lab: ${v%%$'\t'*} (manifest $expect)" >&2
done
out=$D/r5.oracle
if [ -n "$only" ] && [ -f $out ]; then
  awk -F'\t' 'NR==FNR {n[$1]=$0; next} {if ($1 in n) {print n[$1]; delete n[$1]} else print $0} END {for (k in n) print n[k]}' $W/new $out | sort > $out.m && mv $out.m $out
else sort $W/new > $out; fi
echo "oracle-r5: $(wc -l < $out | tr -d ' ') cases, $(grep -c $'\trefused' $out) refused by stage-0, $(grep -c $'\ttrap' $out) trap"
