#!/bin/zsh
# seed/tests/kgraph-capacity/census.sh <spike.bin> <offset> <loader> <out.tsv> <list> -- guest only: runs the compile-twin
# spike on each program of <list> under a loader-variant.sh build with KEXE_KGRAPH_REPORT and writes
# program, guest exit status, kgraph datoms used, registered keywords, first refusal/trap line. No host comparison.
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h:h}
B=${1:A}; off=$2; L=${3:A}; T=${4:A}; tmp=${T:h}/census-tmp; mkdir -p $tmp; : > $T
one() {
  local f=$1 k=${${1#$R/}//\//.} gs
  KEXE_KGRAPH_REPORT=1 KEXE_COMMAND=1 KEXE_CAP_RESOURCES_35=$R:${T:h} KEXE_STRING_POOL=1073741824 KEXE_PAIRS=67108864 \
    KEXE_VECTORS=67108864 KEXE_VECTOR_ITEMS=134217728 KEXE_HASHCONS=16 KEXE_CPU_SECONDS=300 KEXE_WALL_SECONDS=300 \
    $L $B $off 0 aarch64 3,35,37,38,39 -- $f $tmp/$k.edn > $tmp/$k.log 2>&1; gs=$?
  local used=$(sed -n 's/^KGRAPH {:used \([0-9]*\) .*:kw-entities \([0-9]*\) .*/\1\t\2/p' $tmp/$k.log)
  printf '%s\t%s\t%s\t%s\n' ${f#$R/} $gs "$used" "$(grep -v '^KGRAPH' $tmp/$k.log | head -c 120 | tr '\n\t' '  ')"
}
for f in ${(f)"$(cat $5)"}; do one ${f:A} >> $T; done
