#!/bin/zsh
# scripts/seed/oracle.sh <rung> [label-substring ...] -- record STAGE-0 (bootstrap-reference) verdicts for seed/tests/<rung>/.
# BOOTSTRAP-TOOL (zsh), owner GATES. For every program of seed/tests/<rung>/{feat,conf}/*.kotoba stage-0 compiles it
# (--target aarch64-macos, at most 2 stage-0 processes machine-wide, nice), extracts its first export and the C loader
# runs it (arity 0). Writes seed/tests/<rung>/<rung>.oracle, lines `<label>\t<value>|trap|refused\t<stage-0 message>`.
# For seed/tests/<rung>/neg/*.kotoba it writes <rung>-neg.oracle, lines `<label>\trefused|ACCEPTED\t<message>`: ACCEPTED
# means stage-0 would compile the program, i.e. the seed refuses it because its SUBSET is narrower than stage-0's.
# With label substrings only those lines are recomputed and merged.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
rung=${1:?usage: oracle.sh <rung> [label...]}; shift
R=$SEED_REPO; D=$R/seed/tests/$rung; W=$SEED_BUILD/oracle-$rung; mkdir -p $W
echo '{:allow #{}}' > $W/pol.edn
L=$(seed_loader) || exit 2
verdict() {   # verdict <file> -> "<value|trap|refused>\t<message>"
  local p=$1 stem=${1:t:r} sym r v rc
  sym=$(sed -n 's/.*(:export \[\([^] ]*\).*/\1/p' $p | head -1)
  seed_slot_take
  r=$( ulimit -s 65500; nice $SEED_STAGE0 compile $p --target aarch64-macos --jvm-free --policy $W/pol.edn --output $W/$stem.kexe 2>&1 )
  if echo "$r" | grep -q ':ok true'; then
    r=$( nice $SEED_STAGE0 extract-native $W/$stem.kexe --symbol $sym --output $W/$stem.bin 2>&1 )
  fi
  seed_slot_give
  if ! echo "$r" | grep -q ':ok true'; then printf 'refused\t%s\n' "$(echo $r | grep -o ':message "[^"]*"' | head -1 | cut -c11-)"; return; fi
  local off=$(echo "$r" | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  v=$(cd $W; KEXE_CPU_SECONDS=20 KEXE_WALL_SECONDS=20 $L $W/$stem.bin $off 0 aarch64 - 2>/dev/null | tail -1); rc=${pipestatus[1]}
  if [ $rc -eq 0 ] && [ -n "$v" ]; then printf '%s\t\n' $v; else printf 'trap\t\n'; fi
}
merge() {   # merge <outfile> <newlines file>
  local out=$1 new=$2
  if [ $# -gt 0 ] && [ -n "$only" ] && [ -f $out ]; then
    awk -F'\t' 'NR==FNR {n[$1]=$0; next} {print ($1 in n) ? n[$1] : $0}' $new $out > $out.m; cat $new | awk -F'\t' 'NR==FNR {s[$1]=1; next} 1' $out - > /dev/null
    mv $out.m $out
  else cp $new $out; fi
}
only="$*"
sel() { [ -z "$only" ] && return 0; local s; for s in $@; do [[ $1 == *$s* ]] && return 0; done; return 1; }
run_dir() {   # run_dir <subdirs...> > lines
  local f lab
  for sub in $@; do
    for f in $D/$sub/*.kotoba(N); do
      lab=$sub/${f:t:r}
      if [ -n "$only" ]; then local hit=0 s; for s in ${=only}; do [[ $lab == *$s* ]] && hit=1; done; [ $hit -eq 1 ] || continue; fi
      v=$(verdict $f)
      if [ $sub = neg ]; then v=${v/#refused/refused}; case $v in refused*) ;; *) v="ACCEPTED	" ;; esac; fi
      printf '%s\t%s\n' $lab "$v"
      echo "$lab: ${v%%$'\t'*}" >&2
    done
  done
}
run_dir feat conf > $W/pos.new
run_dir neg > $W/neg.new
upd() {   # upd <final> <new>
  if [ -n "$only" ] && [ -f $1 ]; then
    awk -F'\t' 'NR==FNR {n[$1]=$0; next} {if ($1 in n) {print n[$1]; delete n[$1]} else print $0} END {for (k in n) print n[k]}' $2 $1 | sort > $1.m && mv $1.m $1
  else sort $2 > $1; fi
}
upd $D/$rung.oracle $W/pos.new
upd $D/$rung-neg.oracle $W/neg.new
echo "oracle: $rung: $(wc -l < $D/$rung.oracle | tr -d ' ') programs ($(grep -c 'refused' $D/$rung.oracle) refused by stage-0, $(grep -c $'\ttrap' $D/$rung.oracle) trap); neg: $(grep -c refused $D/$rung-neg.oracle) refused, $(grep -c ACCEPTED $D/$rung-neg.oracle) accepted by stage-0"
