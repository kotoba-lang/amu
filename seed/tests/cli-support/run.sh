#!/bin/zsh
# seed/tests/cli-support/run.sh <front-objects> [work-dir] -- the Kotoba readings of cli-support's policy, build-metadata
# and artifact helpers on the seed route: bounded-edn and cli-support are recompiled from this tree against the frontend
# objects in <front-objects> (e.g. build/seed17/front0), probe.kotoba is linked as the entry and run once per case.
# Seed: CS_SEED (default build/seed-boot/r6m/seed-1.bin, checked against seed/rungs/r6m.record).
# BOOTSTRAP-TOOL (zsh, cc). No stage-0, JVM, node or nbb at any step.
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h:h}
[ -d "$1" ] || { echo "usage: run.sh <front-objects> [work-dir]" >&2; exit 2; }
FRONT=${1:A}; W=${2:-$R/build/cli-support-kotoba}; mkdir -p $W; W=${W:A}
SB=${CS_SEED:-$R/build/seed-boot/r6m/seed-1.bin}
sha() { shasum -a 256 $1 | cut -c1-64; }
[ -n "$CS_SEED" ] || [ "$(sha $SB)" = "$(sed -n 's/^seed1_sha256 //p' $R/seed/rungs/r6m.record)" ] || { echo "cli-support: $SB is not rung r6m's seed" >&2; exit 1; }
export SEED_REPO=$R SEED_BUILD=$W/sb SEED_PAIRS=${SEED_PAIRS:-16777216}; mkdir -p $SEED_BUILD; source $R/scripts/seed/lib.sh
run() { SEED_RESOURCES_35=$R:$W SEED_VECTOR_ITEMS=67108864 SEED_SECONDS=600 seed_run "$@"; }
O=$W/o; rm -rf $O; mkdir -p $O; cp $FRONT/*.kso $O/
comp() { run $SB 0 compile $1 --emit-module "${@:3}" --object-dir $O --output $O/$2.kso > $W/emit-$2.log 2>&1 || { tail -3 $W/emit-$2.log; exit 1; }; }
comp $R/src/kotoba/compiler/bounded_edn.cljk kotoba.compiler.bounded-edn
comp $R/src/kotoba/compiler/nbb/cli_support.cljk kotoba.compiler.nbb.cli-support
comp $H/probe.kotoba cstest.probe --entry
run $SB 0 link $O/cstest.probe.kso --object-dir $O --output $W/probe.kseed > $W/link.log 2>&1 || { tail -3 $W/link.log; exit 1; }
off=$(run $SB 0 extract-native $W/probe.kseed --symbol main --output $W/probe.bin | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
[ -n "$off" ] || { echo "cli-support: extract-native failed" >&2; exit 1; }
printf '{:allow #{[:cap/call 35]} :budgets {:fuel 9} :language-profile :x}\n' > $W/policy.edn
printf '{:format :kotoba.kexe/v1 :code [1 2 3] :exports [main]}\n' > $W/artifact.edn
L=$(seed_loader) || exit 2
guest() { KEXE_COMMAND=1 KEXE_CAP_RESOURCES_35=$R:$W KEXE_STRING_POOL=268435456 KEXE_PAIRS=$SEED_PAIRS KEXE_VECTORS=65536 \
  KEXE_VECTOR_ITEMS=67108864 KEXE_CPU_SECONDS=60 KEXE_WALL_SECONDS=60 $L $W/probe.bin $off 0 aarch64 35,37,38,39 -- "$@"; }
fail=0
check() { local want=$1; shift; guest "$@"; local got=$?; if [ $got = $want ]; then echo "ok   $* -> $got"; else echo "FAIL $* -> $got (want $want)"; fail=1; fi; }
# the entry's status is its i64 result modulo 256 (an abort, -1, is 255)
check 0 checks $W/policy.edn $W/artifact.edn
for f in 0 -5 -0 abc 12x 1234567890123456789; do check 1 refuse $f; done
check 0 refuse 5
exit $fail
