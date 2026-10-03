#!/bin/zsh
# seed/tests/r6a/check-r6a.sh [seed.bin] -- the R6A feature gate (agent R6A, 2026-10-03). BOOTSTRAP-TOOL (zsh).
# For every case of cases-r6a.tsv: the in-process project route and the separate mode (seed modules -> compile --emit-module per
# module -> seed link) must give byte-identical containers, and main must answer the expected value (a negative: both routes
# refuse with the expected E-code). Exit 0 iff every case passes.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/../../../scripts/seed/lib.sh"
R=$SEED_REPO; D=$R/seed/tests/r6a; B=${SEED_BUILD:A}; W=$B/check-r6a; rm -rf $W; mkdir -p $W
bin=${1:-$B/seed-1.bin}; off=$(cat ${bin%.bin}.offset 2>/dev/null || echo 0)
L=$(seed_loader) || exit 2
export SEED_RESOURCES_35=$R:$W
pass=0 fail=0
grep -v '^#' $D/cases-r6a.tsv | grep . | while IFS=$'\t' read -r lab entry sp fn want; do
  st=${lab//\//_}; d=$W/$st; mkdir -p $d/o
  r1=$(seed_run $bin $off compile $D/$entry --source-path $D/$sp --unpinned --output $d/in.kseed 2>&1)
  # separate mode
  r2=""; ok2=1
  if seed_run $bin $off modules $D/$entry --source-path $D/$sp > $d/order 2>$d/order.err; then
    last=$(tail -1 $d/order | cut -d' ' -f1)
    while read -r ns fp; do
      e=(); [ $ns = $last ] && e=(--entry)
      r2=$(seed_run $bin $off compile $fp --emit-module $e --object-dir $d/o --output $d/o/$ns.kso 2>&1) || { ok2=0; break; }
    done < $d/order
    [ $ok2 = 1 ] && { r2=$(seed_run $bin $off link $d/o/$last.kso --object-dir $d/o --output $d/sep.kseed 2>&1) || ok2=0; }
  else ok2=0; r2=$(cat $d/order.err); fi
  if [[ $want == E* ]]; then
    c1=$(print -r -- "$r1" | sed -n 's/^seed: \(E[0-9]*\).*/\1/p' | head -1); c2=$(print -r -- "$r2" | sed -n 's/^seed: \(E[0-9]*\).*/\1/p' | head -1)
    if [ ! -s $d/in.kseed ] && [ "$c1" = $want ] && [ "$c2" = $want ]; then pass=$((pass+1)); echo "PASS $lab refused $want: $(print -r -- "$r1" | grep '^seed:' | head -1)"
    else fail=$((fail+1)); echo "FAIL $lab: want $want, in-process '$c1', separate '$c2'"; fi
    continue
  fi
  [ -s $d/in.kseed ] || { fail=$((fail+1)); echo "FAIL $lab in-process: $(print -r -- "$r1" | head -1)"; continue; }
  [ $ok2 = 1 ] && [ -s $d/sep.kseed ] || { fail=$((fail+1)); echo "FAIL $lab separate: $(print -r -- "$r2" | grep seed: | head -1)"; continue; }
  cmp -s $d/in.kseed $d/sep.kseed || { fail=$((fail+1)); echo "FAIL $lab: in-process and separate images differ"; continue; }
  x=$(seed_run $bin $off extract-native $d/in.kseed --symbol $fn --output $d/in.bin 2>&1); o=$(print -r -- "$x" | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  v=$(KEXE_CPU_SECONDS=20 KEXE_WALL_SECONDS=20 $L $d/in.bin $o 0 aarch64 - 2>/dev/null | tail -1)
  if [ "$v" = "$want" ]; then pass=$((pass+1)); echo "PASS $lab $v ($(wc -l < $d/order | tr -d ' ') modules, $(wc -c < $d/in.kseed | tr -d ' ') bytes, separate = in-process)"
  else fail=$((fail+1)); echo "FAIL $lab: got '$v' want $want"; fi
done
echo "check-r6a: PASS $pass FAIL $fail (compiler $(shasum -a 256 $bin | cut -c1-16), load $(uptime | sed 's/.*averages: //'))"
[ $fail -eq 0 ]
