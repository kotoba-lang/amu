#!/bin/zsh
# seed/tests/native-admission/run.sh <front-objects> [work-dir] [list] -- differential of kotoba.compiler.native-admission
# (the Kotoba route) against osaho `kotoba.kir/only-native-word-typed-features?` (the host gate nbb.cli applies).
# hostgate.cljs (nbb, BOOTSTRAP-REFERENCE) writes the host verdicts for every function, body sub-form and call mutation
# of the v3 programs in LIST (default: the compile-twin corpus dirs); gate.kotoba, built by seed r6m against
# <front-objects>, recomputes each one. PASS iff every case agrees and the case counts match.
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h:h}
[ -d "$1" ] || { echo "usage: run.sh <front-objects> [work-dir] [list]" >&2; exit 2; }
FRONT=${1:A}; W=${2:-$R/build/native-admission}; mkdir -p $W; W=${W:A}
SB=${CS_SEED:-$R/build/seed-boot/r6m/seed-1.bin}
sha() { shasum -a 256 $1 | cut -c1-64; }
[ -n "$CS_SEED" ] || [ "$(sha $SB)" = "$(sed -n 's/^seed1_sha256 //p' $R/seed/rungs/r6m.record)" ] || { echo "native-admission: $SB is not rung r6m's seed" >&2; exit 1; }
export SEED_REPO=$R SEED_BUILD=$W/sb SEED_PAIRS=${SEED_PAIRS:-16777216}; mkdir -p $SEED_BUILD; source $R/scripts/seed/lib.sh
run() { SEED_RESOURCES_35=$R:$W SEED_VECTOR_ITEMS=134217728 SEED_SECONDS=1800 seed_run "$@"; }
O=$W/o; rm -rf $O; mkdir -p $O; cp $FRONT/*.kso $O/
comp() { run $SB 0 compile $1 --emit-module "${@:3}" --object-dir $O --output $O/$2.kso > $W/emit-$2.log 2>&1 || { tail -3 $W/emit-$2.log; exit 1; }; }
comp $R/src/kotoba/compiler/bounded_edn.cljk kotoba.compiler.bounded-edn
comp $R/src/kotoba/compiler/nbb/cli_support.cljk kotoba.compiler.nbb.cli-support
comp $R/src/kotoba/compiler/native_admission.kotoba kotoba.compiler.native-admission
comp $H/gate.kotoba cstest.gate --entry
run $SB 0 link $O/cstest.gate.kso --object-dir $O --output $W/gate.kseed > $W/link.log 2>&1 || { tail -3 $W/link.log; exit 1; }
off=$(run $SB 0 extract-native $W/gate.kseed --symbol main --output $W/gate.bin | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
[ -n "$off" ] || { echo "native-admission: extract-native failed" >&2; exit 1; }
list=$3
if [ -z "$list" ]; then
  list=$W/list.txt; : > $list
  for d in seed/tests/r1/feat seed/tests/r1/conf seed/tests/corpus resources/kotoba/lang-conformance/{values,control,native} \
           seed/tests/conformance/*(/N) examples test/dual-backend test/nbb/fixtures test/nbb/fixtures/state bench/runtime-comparison; do
    for f in $R/$d/*.kotoba(N); do echo $f >> $list; done
  done
fi
C=$W/cases; rm -rf $C; mkdir -p $C
CP=$(cd $R && node node_modules/nbb/cli.js --classpath src scripts/print-classpath.cljk . | paste -sd: -)
host=$(cd $R && node node_modules/nbb/cli.js --classpath "src:$CP" $H/hostgate.cljs $list $C | tail -1)
echo "host: $host"
want=$(print -r -- "$host" | sed -n 's/.*:cases \([0-9]*\).*/\1/p')
L=$(seed_loader) || exit 2
files=($C/*.edn); agree=0; dis=0; : > $W/mismatch.txt
# at most 40 case files per run (the guest's argv)
for ((i=1; i<=${#files}; i+=40)); do
  out=$(KEXE_COMMAND=1 KEXE_CAP_RESOURCES_35=$R:$W KEXE_STRING_POOL=1073741824 KEXE_PAIRS=67108864 KEXE_VECTORS=67108864 \
        KEXE_VECTOR_ITEMS=134217728 KEXE_HASHCONS=16 KEXE_CPU_SECONDS=900 KEXE_WALL_SECONDS=900 \
        $L $W/gate.bin $off 0 aarch64 3,35,37,38,39 -- ${files[$i,$((i+39))]} $W/mm.txt 2>&1)
  a=$(print -r -- "$out" | sed -n 's/^agree \([0-9]*\) disagree \([0-9]*\)$/\1/p'); d=$(print -r -- "$out" | sed -n 's/^agree \([0-9]*\) disagree \([0-9]*\)$/\2/p')
  [ -n "$a" ] || { echo "native-admission: guest failed: $out" >&2; exit 1; }
  agree=$((agree + a)); dis=$((dis + d)); cat $W/mm.txt >> $W/mismatch.txt
done
echo "guest: agree $agree disagree $dis (host cases $want)"
[ $dis -eq 0 ] && [ $agree -eq $want ] && echo PASS || { echo FAIL; head -c 2000 $W/mismatch.txt; exit 1; }
