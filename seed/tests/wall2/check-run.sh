#!/bin/zsh
# seed/tests/wall2/check-run.sh SEED OBJDIR TWINDIR CASES [work] -- WALL2: the nbb product entry `check`
# (src/kotoba/compiler/nbb/check_cli.cljk, its Kotoba reading) built FROM SOURCE by the seed and run natively on a
# case list (agent WALL2, 2026-10-04). BOOTSTRAP-TOOL (zsh); only the seed and the built image run.
#   SEED     a seed binary (offset 0);  OBJDIR the selfbuild scan's objects (copied, never written)
#   TWINDIR  kotoba-lang lang/compat/kotoba/compiler (project.kotoba, project_files.kotoba)
#   CASES    a file of argument lines (`check <file> [--source-path DIR] [--policy FILE]`), one case per line
# Compiles the twins, capability_names, effect_classification, effect_row, nbb/check_driver and nbb/check_cli
# (--entry) with the seed, links and extracts with the seed, runs every case into <work>/out/<n>.{out,err,status}.
# Compare with: node bin/kbb --backend sci --classpath "$(cat build/walls/cp-walls.txt)" seed/tests/wall2/check-host.cljk CASES <work>/out
emulate -L zsh
setopt pipefail
S=${1:?seed}; O0=${2:?objdir}; TW=${3:?twindir}; C=${4:?cases}; T=${0:A:h}; R=${T:h:h:h}; W=${5:-$R/build/wall2/check-run}
TW=${TW:A}; C=${C:A}
export SEED_PAIRS=${SEED_PAIRS:-16777216} SEED_SECONDS=${SEED_SECONDS:-900} SEED_BUILD=$W SEED_RESOURCES_35=$R:$W:$TW
source $R/scripts/seed/lib.sh
rm -rf $W; mkdir -p $W/o $W/out; cp $O0/*.kso $W/o/
c() { seed_run $S 0 compile $1 --emit-module $3 --object-dir $W/o --output $W/o/$2.kso > $W/$2.log 2>&1 ||
        { echo "check-run: $2 does not compile: $(grep -m1 'seed: E' $W/$2.log)"; exit 1; } }
c $TW/project.kotoba kotoba.compiler.project
c $TW/project_files.kotoba kotoba.compiler.project-files
c $R/src/kotoba/compiler/capability_names.cljk kotoba.compiler.capability-names
c $R/src/kotoba/compiler/effect_classification.cljk kotoba.compiler.effect-classification
c $R/src/kotoba/compiler/effect_row.cljk kotoba.compiler.effect-row
c $R/src/kotoba/compiler/nbb/check_driver.cljk kotoba.compiler.nbb.check-driver
c $R/src/kotoba/compiler/nbb/check_cli.cljk kotoba.compiler.nbb.check-cli --entry
SEED_VECTOR_ITEMS=67108864 seed_run $S 0 link $W/o/kotoba.compiler.nbb.check-cli.kso --object-dir $W/o --output $W/image.kseed > $W/link.log 2>&1 || { echo "check-run: link failed"; exit 1; }
SEED_VECTOR_ITEMS=67108864 seed_run $S 0 extract-native $W/image.kseed --symbol main --output $W/code.bin > $W/extract.log 2>&1 || { echo "check-run: extract failed"; exit 1; }
off=$(sed -n 's/.*:offset \([0-9]*\).*/\1/p' $W/extract.log)
echo "check-run: entry image $(wc -c < $W/code.bin | tr -d ' ') code bytes"
i=0; trap=0
while IFS= read -r line; do
  [ -z "$line" ] && continue
  SEED_RESOURCES_35=${CHECK_SCOPE:-$R:/Users/junkawasaki/github/kotoba-lang/amu-embench} SEED_GRANT=3,35,37,38,39 SEED_VECTORS=67108864 SEED_VECTOR_ITEMS=134217728 SEED_PAIRS=67108864 SEED_POOL=1073741824 \
    seed_run $W/code.bin $off ${=line} > $W/out/$i.out 2> $W/out/$i.err < /dev/null; st=$?
  echo $st > $W/out/$i.status; [ $st -ne 0 ] && [ $st -ne 64 ] && [ $st -ne 65 ] && trap=$((trap+1)); i=$((i+1))
done < $C
echo "check-run: $i cases, $trap other exits (traps); outputs in $W/out"
