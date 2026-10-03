#!/bin/zsh
# seed/tests/wall2/link-run.sh SEED OBJDIR TWIN FIXTURES [work] -- WALL2's differential of the project linker's guest
# twin against the host (agent WALL2, 2026-10-04). BOOTSTRAP-TOOL (zsh); only the seed and the built image run.
#   SEED      a seed binary (offset 0), e.g. the r6l seed 54b87cf6
#   OBJDIR    object dir with the twin's closure (kotoba.sema and the frontend, kotoba.form), copied, never written
#   TWIN      kotoba-lang lang/compat/kotoba/compiler/project.kotoba
#   FIXTURES  the output dir of seed/tests/wall2/link-host.cljk (one dir per case: <ns>.src, args, host.out)
# The twin and seed/tests/wall2/link.kotoba are compiled by the seed (separate mode), linked and extracted by the seed,
# and the image runs once per case; its stdout is compared byte for byte with host.out.
# Prints one line per case (SAME / DIFF / TRAP <status>) and `link-run: N SAME, M DIFF, T TRAP of K`.
emulate -L zsh
setopt pipefail
S=${1:?seed}; O0=${2:?objdir}; TWIN=${3:?twin}; FX=${4:?fixtures}; T=${0:A:h}; R=${T:h:h:h}; W=${5:-$R/build/wall2/link-run}
FX=${FX:A}
export SEED_PAIRS=${SEED_PAIRS:-16777216} SEED_SECONDS=${SEED_SECONDS:-900} SEED_BUILD=$W SEED_RESOURCES_35=$R:$W:$FX:${TWIN:A:h}
source $R/scripts/seed/lib.sh
rm -rf $W; mkdir -p $W/o; cp $O0/*.kso $W/o/
seed_run $S 0 compile $TWIN --emit-module --object-dir $W/o --output $W/o/kotoba.compiler.project.kso > $W/twin.log 2>&1 ||
  { echo "link-run: the twin does not compile: $(grep -m1 'seed: E' $W/twin.log)"; exit 1; }
seed_run $S 0 compile $T/link.kotoba --emit-module --entry --object-dir $W/o --output $W/o/wall2.link.kso > $W/emit.log 2>&1 ||
  { echo "link-run: the driver does not compile: $(grep -m1 'seed: E' $W/emit.log)"; exit 1; }
SEED_VECTOR_ITEMS=67108864 seed_run $S 0 link $W/o/wall2.link.kso --object-dir $W/o --output $W/image.kseed > $W/link.log 2>&1 ||
  { echo "link-run: link failed: $(tail -1 $W/link.log)"; exit 1; }
SEED_VECTOR_ITEMS=67108864 seed_run $S 0 extract-native $W/image.kseed --symbol main --output $W/code.bin > $W/extract.log 2>&1 ||
  { echo "link-run: extract failed"; exit 1; }
off=$(sed -n 's/.*:offset \([0-9]*\).*/\1/p' $W/extract.log)
echo "image: $(wc -c < $W/code.bin | tr -d ' ') code bytes, twin object $(wc -c < $W/o/kotoba.compiler.project.kso | tr -d ' ') B"
same=0; diff=0; trap=0; n=0
for d in $FX/*/(N); do
  c=${d:t}; n=$((n+1))
  args=("${(@f)$(cat $d/args)}")
  SEED_GRANT=3,35,37,38,39 SEED_VECTORS=${LINK_VECTORS:-67108864} SEED_VECTOR_ITEMS=${LINK_ITEMS:-134217728} SEED_PAIRS=${LINK_PAIRS:-67108864} SEED_POOL=${LINK_POOL:-1073741824} seed_run $W/code.bin $off ${d%/} $args > $W/$c.out 2> $W/$c.err; st=$?
  if [ $st -ne 0 ]; then print -r -- "$c TRAP $st $(head -c 120 $W/$c.err | tr '\n' ' ')"; trap=$((trap+1))
  elif cmp -s $W/$c.out $d/host.out; then print -r -- "$c SAME"; same=$((same+1))
  else print -r -- "$c DIFF"; diff=$((diff+1)); fi
done
print -r -- "link-run: $same SAME, $diff DIFF, $trap TRAP of $n"
[ $diff -eq 0 ] && [ $trap -eq 0 ]
