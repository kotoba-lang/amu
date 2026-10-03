#!/bin/zsh
# scripts/seed/emit/same.sh <old-seed.bin> <new-seed.bin> [work-dir] -- the EMIT block adds a command branch only: every other
# command must answer byte-identically under both seeds (agent EMIT, 2026-10-04). BOOTSTRAP-TOOL (zsh). Only seeds run.
# Cases: compile-kir of the 19 Embench port KIRs (KIR_DIR, default build/r6b-gate/kir-gate-seed-1) and of seed/tests/kir/pos
# and neg; compile of the 19 port sources; compile --emit-module of the 14 seed/split modules in order (SPLIT_DIR);
# compile of a seed unity (UNITY, default build/emit/b/seed-unity.kotoba) and extract-native of its main. Compared: exit status, stdout+stderr (output paths normalised), and the written file.
emulate -L zsh; setopt pipefail
R=$(cd "$(dirname "$0")/../../.." && pwd)
A=${1:?old seed}; B=${2:?new seed}; A=${A:A}; B=${B:A}
W=${3:-$R/build/emit/same}; rm -rf $W; mkdir -p $W/a $W/b; W=${W:A}
KD=${KIR_DIR:-$R/build/r6b-gate/kir-gate-seed-1}
P=${SEED_PORTS:-/Users/junkawasaki/github/kotoba-lang/amu-embench/bench/embench/ports}
export SEED_REPO=$R SEED_BUILD=$W/sb SEED_RESOURCES_35=$R:${P:h:h:h:h} SEED_VECTOR_ITEMS=67108864; mkdir -p $SEED_BUILD
source $R/scripts/seed/lib.sh
same=0; diff=0; n=0
one() {  # <name> <args..> with OUT standing for the output file
  local nm=$1 s; shift; n=$((n+1))
  for s in a b; do
    local bin=$A; [ $s = b ] && bin=$B
    local args=("${(@)${(@)argv//ODIR/$W/$s/o}//OUT/$W/$s/$nm.out}")
    seed_run $bin 0 $args > $W/$s/$nm.log 2>&1; echo $? >> $W/$s/$nm.log
    sed -i '' "s|$W/$s/|W/|g" $W/$s/$nm.log
  done
  if cmp -s $W/a/$nm.log $W/b/$nm.log && { [ ! -e $W/a/$nm.out ] && [ ! -e $W/b/$nm.out ] || cmp -s $W/a/$nm.out $W/b/$nm.out; }
  then same=$((same+1)); else diff=$((diff+1)); echo "DIFF $nm"; fi
}
for f in $KD/*.kir; do one kir-${f:t:r} compile-kir $f --output OUT; done
for f in $R/seed/tests/kir/pos/*.kir $R/seed/tests/kir/neg/*.kir; do one kt-${f:h:t}-${f:t:r} compile-kir $f --output OUT; done
for f in $P/*.kotoba; do one src-${f:t:r} compile $f --target aarch64-macos --output OUT; done
S=${SPLIT_DIR:-$R/seed/split}
mkdir -p $W/a/o $W/b/o
for m in mem io lex read kirread names check lower enc gen layout out proj main; do
  one so-$m compile $S/seed/$m.kotoba --emit-module --object-dir ODIR --output ODIR/seed.$m.kso
  cmp -s $W/a/o/seed.$m.kso $W/b/o/seed.$m.kso || { diff=$((diff+1)); echo "DIFF object seed.$m"; }
done
U=${UNITY:-$R/build/emit/b/seed-unity.kotoba}
one unity compile $U --target aarch64-macos --output OUT
one x-unity extract-native $W/a/unity.out --symbol main --output OUT
echo "same: $same of $n cases identical, $diff differ; $(ls $W/b/*.out(N) $W/b/o/*.kso(N) | wc -l | tr -d ' ') outputs written by the new seed"
[ $diff = 0 ]
