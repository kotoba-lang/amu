#!/bin/zsh
# seed/tests/wall2/effects-run.sh SEED OBJDIR [work] -- WALL2's native run of the Kotoba readings of
# kotoba.compiler.effect-row / effect-classification / capability-names (agent WALL2, 2026-10-04). BOOTSTRAP-TOOL (zsh).
#   SEED    a seed binary (offset 0); OBJDIR the selfbuild scan's objects (copied, never written)
# Compiles src/kotoba/compiler/{effect_classification,effect_row}.cljk and seed/tests/wall2/effects.kotoba with the
# seed, links, extracts, and runs every line of seed/tests/wall2/effects-cases.txt into <work>/out/<n>.out; then
# compare with: node bin/kbb --backend sci --classpath "$(cat build/walls/cp-walls.txt)" seed/tests/wall2/effects-host.cljk <work>/out
emulate -L zsh
setopt pipefail
S=${1:?seed}; O0=${2:?objdir}; T=${0:A:h}; R=${T:h:h:h}; W=${3:-$R/build/wall2/effects-run}
export SEED_PAIRS=${SEED_PAIRS:-16777216} SEED_SECONDS=${SEED_SECONDS:-900} SEED_BUILD=$W SEED_RESOURCES_35=$R:$W
source $R/scripts/seed/lib.sh
rm -rf $W; mkdir -p $W/o $W/out; cp $O0/*.kso $W/o/
for m in capability_names:capability-names effect_classification:effect-classification effect_row:effect-row; do
  seed_run $S 0 compile $R/src/kotoba/compiler/${m%%:*}.cljk --emit-module --object-dir $W/o --output $W/o/kotoba.compiler.${m#*:}.kso > $W/${m#*:}.log 2>&1 ||
    { echo "effects-run: ${m#*:} does not compile: $(grep -m1 'seed: E' $W/${m#*:}.log)"; exit 1; }
done
seed_run $S 0 compile $T/effects.kotoba --emit-module --entry --object-dir $W/o --output $W/o/wall2.effects.kso > $W/emit.log 2>&1 ||
  { echo "effects-run: the driver does not compile: $(grep -m1 'seed: E' $W/emit.log)"; exit 1; }
SEED_VECTOR_ITEMS=67108864 seed_run $S 0 link $W/o/wall2.effects.kso --object-dir $W/o --output $W/image.kseed > $W/link.log 2>&1 || { echo "effects-run: link failed"; exit 1; }
SEED_VECTOR_ITEMS=67108864 seed_run $S 0 extract-native $W/image.kseed --symbol main --output $W/code.bin > $W/extract.log 2>&1 || { echo "effects-run: extract failed"; exit 1; }
off=$(sed -n 's/.*:offset \([0-9]*\).*/\1/p' $W/extract.log)
n=$(grep -c . $T/effects-cases.txt); trap=0
for i in {0..$((n-1))}; do
  SEED_GRANT=3,35,37,38,39 SEED_VECTORS=67108864 SEED_VECTOR_ITEMS=134217728 SEED_PAIRS=67108864 seed_run $W/code.bin $off $T/effects-cases.txt $i > $W/out/$i.out 2> $W/out/$i.err || trap=$((trap+1))
done
echo "effects-run: $n cases run, $trap nonzero exits; outputs in $W/out"
