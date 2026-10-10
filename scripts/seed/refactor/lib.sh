# scripts/seed/refactor/lib.sh -- compile and run Kotoba programs with the seed for the refactor port (agent REFAC, 2026-10-04).
# BOOTSTRAP-TOOL (zsh). The seed (RF_SEED, default build/refac/seed-r6k.bin = rung r6k ab9f8236) compiles from source; no stage-0,
# JVM or node in the compiled program's process.
#   rf_compile <entry.kotoba> <out-prefix> <source-path>...   -> <out>.kseed <out>.bin <out>.offset
#   rf_run <out-prefix> [args...]                              runs main through tools/kexe_loader.c (wires 34,35,37,38,39)
RF_REPO=${RF_REPO:-${${(%):-%x}:A:h:h:h:h}}
RF_SEED=${RF_SEED:-$RF_REPO/build/refac/seed-r6k.bin}
export SEED_REPO=$RF_REPO SEED_BUILD=${SEED_BUILD:-$RF_REPO/build/refac}
source $RF_REPO/scripts/seed/lib.sh
rf_compile() {
  local src=${1:A} out=${2:A}; shift 2
  local sp=() p
  for p in "$@"; do sp+=(--source-path ${p:A}); done
  SEED_RESOURCES_35=${RF_RES:-$RF_REPO:/private/tmp:/Users/junkawasaki/github} SEED_SECONDS=${RF_SECONDS:-900} \
    SEED_PAIRS=${SEED_PAIRS:-16777216} SEED_VECTOR_ITEMS=${SEED_VECTOR_ITEMS:-67108864} \
    seed_run $RF_SEED $(cat ${RF_SEED%.bin}.offset 2>/dev/null || echo 0) compile $src $sp --unpinned --target aarch64-macos --output $out.kseed > $out.compile.log 2>&1 \
    || { tail -5 $out.compile.log >&2; return 1; }
  SEED_RESOURCES_35=${RF_RES:-$RF_REPO:/private/tmp:/Users/junkawasaki/github} SEED_VECTOR_ITEMS=${SEED_VECTOR_ITEMS:-67108864} \
    seed_run $RF_SEED $(cat ${RF_SEED%.bin}.offset 2>/dev/null || echo 0) extract-native $out.kseed --symbol main --output $out.bin > $out.extract.log 2>&1 \
    || { tail -3 $out.extract.log >&2; return 1; }
  sed -n 's/.*:offset \([0-9]*\).*/\1/p' $out.extract.log > $out.offset
  [ -s $out.offset ]
}
rf_run() {
  local out=${1:A}; shift
  local l; l=$(seed_loader) || return 2
  KEXE_COMMAND=1 KEXE_CAP_RESOURCES_35=${RF_RUNRES:-/private/tmp:/tmp:/Users/junkawasaki} KEXE_CAP_RESOURCES_34=${RF_RUNRES:-/private/tmp:/tmp:/Users/junkawasaki} KEXE_STRING_POOL=1073741824 KEXE_PAIRS=67108864 \
    KEXE_VECTORS=67108864 KEXE_VECTOR_ITEMS=134217728 KEXE_CPU_SECONDS=${RF_RUN_SECONDS:-600} KEXE_WALL_SECONDS=${RF_RUN_SECONDS:-600} \
    $l $out.bin $(cat $out.offset) 0 aarch64 ${RF_GRANT:-34,35,37,38,39} -- "$@"
}
# rf_compile_sep <entry.kotoba> <out-prefix> <source-path>...   -> the same outputs as rf_compile, in separate mode: every
# module of the entry's closure (closure.py, dependency first) `compile --emit-module` into <out>.o, then `link` the entry
# object and `extract-native`. For an entry whose in-process compile stops at E5001 (the in-process project route holds
# the program's source text in OUT: amu's refactor modules carry both readings since 2026-10-10, measured in
# docs/selfhost-selfbuild-20261004.md section 8).
rf_compile_sep() {
  local src=${1:A} out=${2:A}; shift 2
  local roots=() p ns f e o
  for p in "$@"; do roots+=(${p:A}); done
  o=$out.o; rm -rf $o; mkdir -p $o
  python3 $RF_REPO/scripts/seed/refactor/closure.py $src $roots > $out.order || return 1
  local res=${RF_RES:-$RF_REPO:/private/tmp:/Users/junkawasaki/github} off=$(cat ${RF_SEED%.bin}.offset 2>/dev/null || echo 0)
  while read -r ns f; do
    e=(); [ $f = $src ] && e=(--entry)
    SEED_RESOURCES_35=$res SEED_SECONDS=${RF_SECONDS:-900} SEED_PAIRS=${SEED_PAIRS:-16777216} \
      SEED_VECTOR_ITEMS=${SEED_VECTOR_ITEMS:-67108864} \
      seed_run $RF_SEED $off compile $f --emit-module $e --object-dir $o --output $o/$ns.kso > $o/$ns.log 2>&1 \
      && grep -q ':ok true' $o/$ns.log || { echo "rf_compile_sep: $ns: $(tail -c 300 $o/$ns.log)" >&2; return 1; }
  done < $out.order
  ns=$(tail -1 $out.order | cut -d' ' -f1)
  SEED_RESOURCES_35=$res SEED_VECTOR_ITEMS=${SEED_VECTOR_ITEMS:-67108864} \
    seed_run $RF_SEED $off link $o/$ns.kso --object-dir $o --output $out.kseed > $out.compile.log 2>&1 \
    || { tail -5 $out.compile.log >&2; return 1; }
  SEED_RESOURCES_35=$res SEED_VECTOR_ITEMS=${SEED_VECTOR_ITEMS:-67108864} \
    seed_run $RF_SEED $off extract-native $out.kseed --symbol main --output $out.bin > $out.extract.log 2>&1 \
    || { tail -3 $out.extract.log >&2; return 1; }
  sed -n 's/.*:offset \([0-9]*\).*/\1/p' $out.extract.log > $out.offset
  [ -s $out.offset ]
}
