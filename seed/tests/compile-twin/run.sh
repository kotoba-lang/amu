#!/bin/zsh
# seed/tests/compile-twin/run.sh <front-objects> [work-dir] [list] -- the compile-twin spike: spike.kotoba runs nbb.cli
# `compile-native!`'s aarch64 steps on the Kotoba route (analyze -> effect-row/check -> kir/lower -> native-program ->
# native.aarch64/emit-program) and writes :code/:exports; each program of LIST (default: the parity corpus dirs of
# seed/amu-main/parity.sh that exist here) is also compiled by `bin/amu compile --target aarch64-macos` and the two are
# compared. Classes: SAME (code and export entries equal, export order ignored: the host prints a large map in hash
# order), CODE-DIFF, EXPORTS-DIFF, BOTH-REFUSE, GUEST-FAILS, GUEST-ONLY.
# bin/amu is the BOOTSTRAP-REFERENCE of the differential only; the guest runs on the seed route with no node/JVM/nbb.
# Seed: CS_SEED (default build/seed-boot/r6m/seed-1.bin, checked against seed/rungs/r6m.record).
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h:h}
[ -d "$1" ] || { echo "usage: run.sh <front-objects> [work-dir] [list]" >&2; exit 2; }
FRONT=${1:A}; W=${2:-$R/build/compile-twin}; mkdir -p $W; W=${W:A}
SB=${CS_SEED:-$R/build/seed-boot/r6m/seed-1.bin}
sha() { shasum -a 256 $1 | cut -c1-64; }
[ -n "$CS_SEED" ] || [ "$(sha $SB)" = "$(sed -n 's/^seed1_sha256 //p' $R/seed/rungs/r6m.record)" ] || { echo "compile-twin: $SB is not rung r6m's seed" >&2; exit 1; }
export SEED_REPO=$R SEED_BUILD=$W/sb SEED_PAIRS=${SEED_PAIRS:-16777216}; mkdir -p $SEED_BUILD; source $R/scripts/seed/lib.sh
run() { SEED_RESOURCES_35=$R:$W SEED_VECTOR_ITEMS=134217728 SEED_SECONDS=1800 seed_run "$@"; }
O=$W/o; rm -rf $O; mkdir -p $O; cp $FRONT/*.kso $O/
comp() { run $SB 0 compile $1 --emit-module "${@:3}" --object-dir $O --output $O/$2.kso > $W/emit-$2.log 2>&1 || { tail -3 $W/emit-$2.log; exit 1; }; }
comp $R/src/kotoba/compiler/bounded_edn.cljk kotoba.compiler.bounded-edn
comp $R/src/kotoba/compiler/nbb/cli_support.cljk kotoba.compiler.nbb.cli-support
# not in the image's frontend objects: the admission check of the compile route
[ -f $O/kotoba.compiler.effect-classification.kso ] || comp $R/src/kotoba/compiler/effect_classification.cljk kotoba.compiler.effect-classification
[ -f $O/kotoba.compiler.effect-row.kso ] || comp $R/src/kotoba/compiler/effect_row.cljk kotoba.compiler.effect-row
comp $R/src/kotoba/compiler/native_admission.kotoba kotoba.compiler.native-admission
comp $H/spike.kotoba cstest.compile --entry
run $SB 0 link $O/cstest.compile.kso --object-dir $O --output $W/spike.kseed > $W/link.log 2>&1 || { tail -3 $W/link.log; exit 1; }
off=$(run $SB 0 extract-native $W/spike.kseed --symbol main --output $W/spike.bin | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
[ -n "$off" ] || { echo "compile-twin: extract-native failed" >&2; exit 1; }
L=$(seed_loader) || exit 2
if [ -n "$3" ]; then files=(${(f)"$(cat $3)"})
else
  files=(); for d in seed/tests/r1/feat seed/tests/r1/conf seed/tests/corpus resources/kotoba/lang-conformance/{values,control,native} \
                    $R/seed/tests/conformance/*(/N) examples test/dual-backend test/nbb/fixtures test/nbb/fixtures/state bench/runtime-comparison; do
    files+=(${${d:A}/#$PWD/$R}/*.kotoba(N)); done
fi
pol=$W/policy.edn; echo '{:allow #{[:cap/call 35] [:cap/call 37] [:cap/call 38] [:cap/call 39]}}' > $pol
mkdir -p $W/h $W/g; : > $W/result.tsv
for f in $files; do
  f=${f:A}; k=${${f#$R/}//\//.}
  (cd $R && bin/amu compile $f --target aarch64-macos --policy $pol --output $W/h/$k.kexe > $W/h/$k.log 2>&1); hs=$?
  # the frontend's budgets as the native image runs them (scripts/seed/launcher/build.sh)
  KEXE_COMMAND=1 KEXE_CAP_RESOURCES_35=$R:$W KEXE_STRING_POOL=1073741824 KEXE_PAIRS=67108864 KEXE_VECTORS=67108864 \
    KEXE_VECTOR_ITEMS=134217728 KEXE_HASHCONS=16 KEXE_KGRAPH=1048576 KEXE_CPU_SECONDS=300 KEXE_WALL_SECONDS=300 \
    $L $W/spike.bin $off 0 aarch64 3,35,37,38,39 -- $f $W/g/$k.edn --policy $pol > $W/g/$k.log 2>&1; gs=$?
  if [ $hs -eq 0 ] && [ $gs -eq 0 ]; then cls=$(python3 $H/compare.py $W/h/$k.kexe $W/g/$k.edn)
  elif [ $hs -ne 0 ] && [ $gs -ne 0 ]; then cls=BOTH-REFUSE
  elif [ $hs -eq 0 ]; then cls=GUEST-FAILS
  else cls=GUEST-ONLY; fi
  printf '%s\t%s\t%s\n' $cls ${f#$R/} "$(head -c 160 $W/g/$k.log | tr '\n\t' '  ')" >> $W/result.tsv
done
cut -f1 $W/result.tsv | sort | uniq -c
