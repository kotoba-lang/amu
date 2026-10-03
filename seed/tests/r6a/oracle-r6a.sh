#!/bin/zsh
# seed/tests/r6a/oracle-r6a.sh -- stage-0 verdicts for cases-r6a.tsv -> stage0-verdicts.tsv (agent R6A). BOOTSTRAP-TOOL: stage-0 is the
# JVM-built native image (bootstrap-reference); run only to record the reference's verdicts, never in a gate. 2 stage-0 slots, nice.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/../../../scripts/seed/lib.sh"
R=$SEED_REPO; D=$R/seed/tests/r6a; W=${SEED_BUILD:A}/oracle-r6a; mkdir -p $W
L=$(seed_loader) || exit 2
: > $W/new
grep -v '^#' $D/cases-r6a.tsv | grep . | while IFS=$'\t' read -r lab entry sp fn want; do
  st=${lab//\//_}
  seed_slot_take
  r=$( ulimit -s 65500; cd $D; nice $SEED_STAGE0 compile $D/$entry --source-path $D/$sp --unpinned --target aarch64-macos --jvm-free --output $W/$st.kexe 2>&1 )
  echo "$r" | grep -q ':ok true' && r=$( nice $SEED_STAGE0 extract-native $W/$st.kexe --symbol $fn --output $W/$st.bin 2>&1 )
  seed_slot_give
  if ! echo "$r" | grep -q ':ok true'; then
    printf '%s\trefused\t%s\n' $lab "$(echo $r | grep -o ':message "\([^"\\]\|\\.\)*"' | head -1 | cut -c11- | sed 's/"$//')" >> $W/new; continue
  fi
  o=$(echo "$r" | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  v=$(KEXE_CPU_SECONDS=20 KEXE_WALL_SECONDS=20 $L $W/$st.bin $o 0 aarch64 - 2>/dev/null | tail -1)
  printf '%s\t%s\n' $lab "${v:-trap}" >> $W/new
done
{ echo "# stage-0 ($(shasum -a 256 $SEED_STAGE0 | cut -c1-16), bootstrap-reference) verdicts, $(date '+%F'), load $(uptime | sed 's/.*averages: //')"; cat $W/new; } > $D/stage0-verdicts.tsv
cat $D/stage0-verdicts.tsv
