#!/bin/zsh
# seed/tests/checkfull/build.sh [work-dir] -- build a test image of `amu check` (amu.cli + amu.check-full + amu.check +
# tmain.kotoba) against the frontend objects compiled from source (CF_FRONT, default build/rebuild/one1/o: REBUILD's r6l
# objects) with the r6l seed (CF_SEED, default build/rebuild/seed-r6l.bin, checked against seed/rungs/r6l.record).
# BOOTSTRAP-TOOL (zsh, cc). No stage-0, JVM, node or nbb at any step. Agent CHECKFULL, 2026-10-04.
emulate -L zsh; setopt pipefail; renice -n 10 $$ > /dev/null
H=${0:A:h}; R=${H:h:h:h}
W=${1:-$R/build/checkfull/t}; mkdir -p $W; W=${W:A}
FRONT=${CF_FRONT:-$R/build/rebuild/one1/o}
SB=${CF_SEED:-$R/build/rebuild/seed-r6l.bin}
sha() { shasum -a 256 $1 | cut -c1-64; }
[ -n "$CF_SEED" ] || [ "$(sha $SB)" = "$(sed -n 's/^seed1_sha256 //p' $R/seed/rungs/r6l.record)" ] || { echo "checkfull: $SB is not rung r6l's seed" >&2; exit 1; }
export SEED_REPO=$R SEED_BUILD=$W/sb SEED_PAIRS=${SEED_PAIRS:-16777216}; mkdir -p $SEED_BUILD; source $R/scripts/seed/lib.sh
run() { SEED_RESOURCES_35=$R:$W SEED_VECTOR_ITEMS=134217728 SEED_SECONDS=1800 seed_run "$@"; }
O=$W/o; rm -rf $O; mkdir -p $O
for k in $FRONT/*.kso; do case ${k:t} in amu.*) ;; *) cp $k $O/ ;; esac; done
S=$W/src/amu; rm -rf $W/src; mkdir -p $S
cp $R/seed/amu-main/src/amu/cli.kotoba $R/seed/amu-main/src/amu/check_full.kotoba $S/
cp $R/seed/amu-main/k/amu/check.kotoba $S/check.kotoba
cp $H/tmain.kotoba $S/tmain.kotoba
comp() { run $SB 0 compile $1 --emit-module "${@:3}" --object-dir $O --output $O/$2.kso; }
for m in cli:amu.cli check_full:amu.check-full check:amu.check; do
  comp $S/${m%%:*}.kotoba ${m#*:} > $W/emit-${m%%:*}.log 2>&1 || { tail -3 $W/emit-${m%%:*}.log; exit 1; }
done
comp $S/tmain.kotoba amu.tmain --entry > $W/emit-tmain.log 2>&1 || { tail -3 $W/emit-tmain.log; exit 1; }
run $SB 0 link $O/amu.tmain.kso --object-dir $O --output $W/t.kseed > $W/link.log 2>&1 || { tail -3 $W/link.log; exit 1; }
off=$(run $SB 0 extract-native $W/t.kseed --symbol main --output $W/t.bin | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
[ -n "$off" ] || { echo "checkfull: extract-native" >&2; exit 1; }
echo $off > $W/t.offset
L=$(seed_loader)
# the runner: the loader with the launcher's budgets and wires; KEXE_CAP_RESOURCES_35 = CF_SCOPE (default: $PWD + /private/tmp)
cat > $W/amu <<EOR
#!/bin/zsh
KEXE_COMMAND=1 KEXE_CAP_RESOURCES_35=\${CF_SCOPE:-\$PWD:/private/tmp:/tmp} KEXE_STRING_POOL=1073741824 KEXE_PAIRS=67108864 \\
  KEXE_VECTORS=67108864 KEXE_VECTOR_ITEMS=134217728 KEXE_CPU_SECONDS=1800 KEXE_WALL_SECONDS=1800 KEXE_HASHCONS=16 \\
  exec $L $W/t.bin $off 0 aarch64 3,35,37,38,39 -- "\$@"
EOR
chmod +x $W/amu
echo "checkfull: test image $W/amu (code $(wc -c < $W/t.bin | tr -d ' ') B, sha $(sha $W/t.bin | cut -c1-16), seed $(sha $SB | cut -c1-16), front $FRONT)"
