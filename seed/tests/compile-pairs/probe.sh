#!/bin/zsh
# seed/tests/compile-pairs/probe.sh build <objects-dir> <out-dir> | run <out-dir> <stage> <source> [policy]
#   build: seed rung r6n compiles probe.kotoba (entry) against a COPY of <objects-dir> (an image's object dir, e.g.
#          build/fp/g3/o of scripts/seed/image/rebuild.sh), links it and extracts `main` into <out-dir>.
#   run:   one stage with the native image's budgets (pairs 64 Mi, vectors 64 Mi, items 128 Mi, kgraph 1 Mi) and
#          KEXE_ARENA_USE; stdout is the stage's line, stderr the loader's KEXE_ARENA_USE / KEXE_TRAP lines.
# Seed: PROBE_SEED (default build/seed-boot/r6n/seed-1.bin). Loader: seed_loader (tools/kexe_loader.c).
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h:h}
export SEED_REPO=$R SEED_BUILD=${PROBE_SB:-$R/build/compile-pairs-sb}; mkdir -p $SEED_BUILD; source $R/scripts/seed/lib.sh
L=$(seed_loader) || exit 2
case $1 in
  build)
    O0=${2:A}; W=${3:A}; O=$W/o; mkdir -p $W; rm -rf $O; cp -R $O0 $O
    SB=${PROBE_SEED:-$R/build/seed-boot/r6n/seed-1.bin}
    run() { KEXE_COMMAND=1 KEXE_CAP_RESOURCES_35=$R:$O:$W KEXE_STRING_POOL=268435456 KEXE_PAIRS=16777216 KEXE_VECTORS=65536 \
              KEXE_VECTOR_ITEMS=134217728 KEXE_CPU_SECONDS=1800 KEXE_WALL_SECONDS=1800 $L $SB 0 0 aarch64 35,37,38,39 -- "$@"; }
    run compile $H/probe.kotoba --emit-module --entry --object-dir $O --output $O/cstest.compile-pairs.kso > $W/emit.log 2>&1 || { tail -3 $W/emit.log; exit 1; }
    run link $O/cstest.compile-pairs.kso --object-dir $O --output $W/probe.kseed > $W/link.log 2>&1 || { tail -3 $W/link.log; exit 1; }
    run extract-native $W/probe.kseed --symbol main --output $W/probe.bin > $W/extract.log 2>&1 || { cat $W/extract.log; exit 1; }
    sed -n 's/.*:offset \([0-9]*\).*/\1/p' $W/extract.log > $W/offset; echo "probe $(wc -c < $W/probe.kseed | tr -d ' ') bytes" ;;
  run)
    W=${2:A}; src=${4:A}; pol=${5:-$W/policy.edn}
    [ -f $pol ] || echo '{:allow #{[:cap/call 35] [:cap/call 37] [:cap/call 38] [:cap/call 39]}}' > $pol
    KEXE_ARENA_USE=1 KEXE_COMMAND=1 KEXE_CAP_RESOURCES_35=$R:$W:${src:h} KEXE_STRING_POOL=1073741824 KEXE_PAIRS=67108864 \
      KEXE_VECTORS=67108864 KEXE_VECTOR_ITEMS=134217728 KEXE_HASHCONS=16 KEXE_KGRAPH=1048576 KEXE_CPU_SECONDS=1800 \
      KEXE_WALL_SECONDS=3600 $L $W/probe.bin $(cat $W/offset) 0 aarch64 3,35,37,38,39 -- $3 $src --policy $pol ;;
  *) echo "usage: probe.sh build <objects-dir> <out-dir> | run <out-dir> <stage> <source> [policy]" >&2; exit 2 ;;
esac
