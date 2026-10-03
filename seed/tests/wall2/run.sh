#!/bin/zsh
# seed/tests/wall2/run.sh SEED OBJDIR [work] -- WALL2's native tests of the typed (Kotoba-reading) ports of amu src
# modules (agent WALL2, 2026-10-04). BOOTSTRAP-TOOL (zsh). Only the seed runs: each test entry is compiled from
# source with `--emit-module --entry` against OBJDIR (the selfbuild scan's objects: every module of the image the seed
# compiled, incl. the port under test), linked and extracted by the same seed, and run by the C loader.
#   SEED    a seed binary (offset 0), e.g. the r6l seed 54b87cf6
#   OBJDIR  object dir holding <ns>.kso of the test's closure (copied, never written)
# Cases: <name>.kotoba with the expected exit status in the table below. Prints one line per case and a total.
emulate -L zsh
setopt pipefail
S=${1:?seed}; O0=${2:?objdir}; T=${0:A:h}; R=${T:h:h:h}; W=${3:-$R/build/wall2/tests}
export SEED_PAIRS=${SEED_PAIRS:-16777216} SEED_SECONDS=${SEED_SECONDS:-600} SEED_BUILD=$W SEED_RESOURCES_35=$R:$W
source $R/scripts/seed/lib.sh
rm -rf $W; mkdir -p $W/o; cp $O0/*.kso $W/o/
pass=0; fail=0
# name expected-exit
cases=(capnames 0 capnames-refuse 0)
for name want in $cases; do
  D=$W/$name; mkdir -p $D
  ns=$(grep -m1 -o '(ns [^ )]*' $T/$name.kotoba | cut -c5-)
  st=x
  if seed_run $S 0 compile $T/$name.kotoba --emit-module --entry --object-dir $W/o --output $W/o/$ns.kso > $D/emit.log 2>&1 &&
     SEED_VECTOR_ITEMS=67108864 seed_run $S 0 link $W/o/$ns.kso --object-dir $W/o --output $D/image.kseed > $D/link.log 2>&1 &&
     SEED_VECTOR_ITEMS=67108864 seed_run $S 0 extract-native $D/image.kseed --symbol main --output $D/code.bin > $D/extract.log 2>&1; then
    off=$(sed -n 's/.*:offset \([0-9]*\).*/\1/p' $D/extract.log)
    SEED_GRANT=3,35,37,38,39 seed_run $D/code.bin $off > $D/run.out 2>&1; st=$?
  else
    print -r -- "$name BUILD-FAIL $(grep -h -m1 -E 'seed: E|KEXE_TRAP|E[0-9]{4}' $D/*.log | cut -c1-120)"; fail=$((fail+1)); continue
  fi
  ok=0
  if [ $want = nonzero ]; then [ $st -ne 0 ] && ok=1; else [ $st -eq $want ] && ok=1; fi
  if [ $ok -eq 1 ]; then print -r -- "$name PASS (exit $st)"; pass=$((pass+1))
  else print -r -- "$name FAIL (exit $st, want $want) $(head -c 200 $D/run.out)"; fail=$((fail+1)); fi
done
print -r -- "wall2 tests: $pass PASS, $fail FAIL"
[ $fail -eq 0 ]
