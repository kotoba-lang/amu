#!/bin/zsh
# seed/tests/compile-twin/run.sh <front-objects> [work-dir] [list] -- the compile-twin spike: spike.kotoba runs nbb.cli
# `compile-native!` for aarch64-macos on the Kotoba route through kotoba.compiler.native-artifact (gates, admission,
# kir/lower, native-program, aarch64/emit-program, the sealed artifact, provenance, the verifier step) and writes the
# .kexe, its .provenance.edn and the verifier's message; each program of LIST (default: the parity corpus dirs of
# seed/amu-main/parity.sh that exist here) is also compiled by `bin/amu compile --target aarch64-macos` and the two are
# compared with compare_artifact.py (seal first, then the artifact and provenance maps key by key; never by text: the
# host prints a large map in hash order). Classes: BOTH-ACCEPT (with seal/provenance SAME or DIFF and the differing
# keys), GUEST-VERIFY-REFUSES, GUEST-FAILS, BOTH-VERIFY-REFUSE, HOST-VERIFY-ONLY, GUEST-ONLY, BOTH-REFUSE.
# FRONT-OBJECTS must carry a kotoba.kir.target whose Kotoba profile table the seed's document reader reads (see the
# 2026-10-09 addendum of docs/selfhost-compile-twin-spike-20261008.md) and the oracle interpreter port.
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
comp $R/src/kotoba/compiler/native_artifact.kotoba kotoba.compiler.native-artifact
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
  f=${f:A}; k=${${f#$R/}//\//.}; rm -f $W/h/$k.kexe* $W/g/$k.kexe*
  (cd $R && bin/amu compile $f --target aarch64-macos --policy $pol --output $W/h/$k.kexe > $W/h/$k.log 2>&1); hs=$?
  # the frontend's budgets as the native image runs them (scripts/seed/launcher/build.sh)
  KEXE_COMMAND=1 KEXE_CAP_RESOURCES_35=$R:$W KEXE_STRING_POOL=1073741824 KEXE_PAIRS=67108864 KEXE_VECTORS=67108864 \
    KEXE_VECTOR_ITEMS=134217728 KEXE_HASHCONS=16 KEXE_KGRAPH=1048576 KEXE_CPU_SECONDS=600 KEXE_WALL_SECONDS=900 \
    $L $W/spike.bin $off 0 aarch64 3,35,37,38,39 -- $f $W/g/$k.kexe --policy $pol > $W/g/$k.log 2>&1; gs=$?
  he=$(sed -n 's/.*:error \(:[a-z-]*\).*/\1/p' $W/h/$k.log | head -1)
  cmp=(- - - -)
  if [ $hs -eq 0 ] && [ $gs -ne 65 ] && [ -f $W/g/$k.kexe ]; then cmp=($(python3 $H/compare_artifact.py $W/h/$k.kexe $W/g/$k.kexe)); fi
  if [ $hs -eq 0 ] && [ $gs -eq 0 ]; then cls=BOTH-ACCEPT
  elif [ $hs -eq 0 ] && [ $gs -eq 66 ]; then cls=GUEST-VERIFY-REFUSES
  elif [ $hs -eq 0 ]; then cls=GUEST-FAILS
  elif [ "$he" = ":verify" ] && [ $gs -eq 66 ]; then cls=BOTH-VERIFY-REFUSE
  elif [ "$he" = ":verify" ] && [ $gs -eq 0 ]; then cls=HOST-VERIFY-ONLY
  elif [ $gs -eq 0 ]; then cls=GUEST-ONLY
  else cls=BOTH-REFUSE; fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' $cls $cmp ${f#$R/} "$(head -c 160 $W/g/$k.log | tr '\n\t' '  ')" >> $W/result.tsv
done
cut -f1-3,5 $W/result.tsv | sort | uniq -c
