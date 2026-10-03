#!/bin/zsh
# seed/tests/r5a/sep-r5a.sh [seed.bin] -- separate mode (60-proj, design 3.3 option C) against the in-process route (owner R5A).
# BOOTSTRAP-TOOL (zsh). For every positive project of seed/tests/r5 (cases with a source path, part A) and for the seed's own
# namespace split (seed/split): `seed modules` gives the compile order; each module is compiled alone
# (`compile <file> --emit-module [--entry] --object-dir O --output O/<ns>.kso`, one loader process per module) and
# `seed link O/<entry>.kso --object-dir O --output X` writes the container, which must be byte-identical to the in-process
# `compile <entry> --source-path .. --unpinned --output Y`. Exit 0 iff every project is identical.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/../../../scripts/seed/lib.sh"
R=$SEED_REPO; B=${SEED_BUILD:A}; bin=${1:-$B/seed-1.bin}; off=$(cat ${bin%.bin}.offset); W=$B/sep-r5a; rm -rf $W; mkdir -p $W
export SEED_RESOURCES_35=$R:$W
same=0 diff=0
one() {  # one <label> <entry> <srcpath>
  local lab=$1 entry=$2 sp=$3 d=$W/${1//\//_} ns fp last r
  mkdir -p $d/o
  seed_run $bin $off compile $entry --source-path $sp --unpinned --output $d/inproc.kseed > $d/log 2>&1 || { echo "FAIL $lab in-process: $(grep seed: $d/log | head -1)"; diff=$((diff+1)); return; }
  seed_run $bin $off modules $entry --source-path $sp > $d/order 2>> $d/log || { echo "FAIL $lab modules"; diff=$((diff+1)); return; }
  last=$(tail -1 $d/order | cut -d' ' -f1)
  while read -r ns fp; do
    r=(); [ $ns = $last ] && r=(--entry)
    seed_run $bin $off compile $fp --emit-module $r --object-dir $d/o --output $d/o/$ns.kso >> $d/log 2>&1 || { echo "FAIL $lab emit $ns: $(grep seed: $d/log | tail -1)"; diff=$((diff+1)); return; }
  done < $d/order
  seed_run $bin $off link $d/o/$last.kso --object-dir $d/o --output $d/linked.kseed >> $d/log 2>&1 || { echo "FAIL $lab link: $(grep seed: $d/log | tail -1)"; diff=$((diff+1)); return; }
  if cmp -s $d/inproc.kseed $d/linked.kseed; then same=$((same+1)); echo "SAME $lab $(wc -l < $d/order | tr -d ' ') modules, $(wc -c < $d/linked.kseed | tr -d ' ') bytes"
  else diff=$((diff+1)); echo "DIFF $lab"; fi
}
T=$R/seed/tests/r5
grep -v '^#' $T/cases.tsv $T/feat-cases.tsv -h | grep . | awk -F'\t' '$3 != "-" {print $1, $2, $3}' | while read -r lab entry sp; do
  grep -q "^$lab	[0-9-]" $T/r5.oracle || grep -q "^$lab " $T/r5.spec || continue
  one $lab $T/$entry $T/$sp
done
one seed-split $R/seed/split/seed/main.kotoba $R/seed/split
echo "sep-r5a: $same identical, $diff not (compiler $bin)"
[ $diff -eq 0 ]
