#!/bin/zsh
# scripts/seed/float-interp.sh <seed.bin> <scan-dir> [work-dir] -- FLOAT (rung r6j): link seed/tests/float/interp-probe.kotoba
# against the objects of a selfbuild/r6-scan run (<scan-dir>/r6/o: kotoba.kir.interp, kotoba.form, kotoba.kir.kvalue compiled
# from source by the same seed), extract `main`, run it under the C loader. Exit status of the probe = failed checks (0 = all
# 14 pass). BOOTSTRAP-TOOL (zsh); no stage-0, no node/JVM/nbb.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
SEED=${1:?usage: float-interp.sh <seed.bin> <scan-dir> [work-dir]}; S=${2:?scan dir}; SOFF=$(cat ${SEED%.bin}.offset 2>/dev/null || echo 0)
W=${3:-$SEED_BUILD/float-interp}; rm -rf $W; mkdir -p $W/o; W=${W:A}
cp ${S:A}/r6/o/*.kso $W/o/
export SEED_RESOURCES_35=$SEED_REPO:$W:${S:A}
seed_run $SEED $SOFF compile $SEED_REPO/seed/tests/float/interp-probe.kotoba --emit-module --entry --object-dir $W/o --output $W/o/flprobe.kso > $W/emit.log 2>&1 || { echo "float-interp: emit failed: $(head -c 300 $W/emit.log)"; exit 2; }
SEED_VECTOR_ITEMS=${FLOAT_LINK_ITEMS:-16777216} seed_run $SEED $SOFF link $W/o/flprobe.kso --object-dir $W/o --output $W/image.kseed > $W/link.log 2>&1 || { echo "float-interp: link failed: $(head -c 300 $W/link.log)"; exit 2; }
seed_run $SEED $SOFF extract-native $W/image.kseed --symbol main --output $W/code.bin > $W/extract.log 2>&1 || { echo "float-interp: extract failed"; exit 2; }
off=$(sed -n 's/.*:offset \([0-9]*\).*/\1/p' $W/extract.log)
L=$(seed_loader) || exit 2
KEXE_COMMAND=1 KEXE_VECTORS=65536 KEXE_PAIRS=4194304 KEXE_STRING_POOL=268435456 KEXE_VECTOR_ITEMS=16777216 $L $W/code.bin $off 0 aarch64 - > $W/run.out 2>&1; st=$?
echo "float-interp: image $(wc -c < $W/code.bin | tr -d ' ') code bytes, main exit $st ($( [ $st -eq 0 ] && echo 'all 14 checks pass' || echo "$st failed checks or a trap"); $(tail -1 $W/run.out | cut -c1-120))"
exit $st
