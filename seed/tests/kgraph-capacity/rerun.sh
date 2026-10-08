#!/bin/zsh
# seed/tests/kgraph-capacity/rerun.sh <compile-twin-work> <loader> <out-dir> <list> -- re-runs the compile-twin guest
# (<work>/spike.bin, built by seed/tests/compile-twin/run.sh) on each program of <list> under <loader> (a variant from
# loader-variant.sh) with the same budgets as run.sh plus KEXE_KGRAPH_REPORT, and classifies against the host kexe that
# run.sh left in <work>/h. Writes <out>/result.tsv: class, program, the KGRAPH census line, the first trap/refusal line.
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h:h}
W=${1:A}; L=${2:A}; O=${3}; mkdir -p $O/g; O=${O:A}
off=$(sed -n 's/.*:offset \([0-9]*\).*/\1/p' $W/extract.log 2>/dev/null)
[ -n "$off" ] || off=${KG_OFFSET:?set KG_OFFSET to the extract-native offset of spike.bin}
: > $O/result.tsv
for f in ${(f)"$(cat $4)"}; do
  f=${f:A}; k=${${f#$R/}//\//.}
  [ -f $W/h/$k.log ] || { echo "no host result for $k in $W/h" >&2; continue; }
  hs=0; [ -f $W/h/$k.kexe ] || hs=1
  KEXE_KGRAPH_REPORT=1 KEXE_COMMAND=1 KEXE_CAP_RESOURCES_35=$R:$W:$O KEXE_STRING_POOL=1073741824 KEXE_PAIRS=67108864 \
    KEXE_VECTORS=67108864 KEXE_VECTOR_ITEMS=134217728 KEXE_HASHCONS=16 KEXE_CPU_SECONDS=300 KEXE_WALL_SECONDS=300 \
    $L $W/spike.bin $off 0 aarch64 3,35,37,38,39 -- $f $O/g/$k.edn --policy $W/policy.edn > $O/g/$k.log 2>&1; gs=$?
  if [ $hs -eq 0 ] && [ $gs -eq 0 ]; then cls=$(python3 $R/seed/tests/compile-twin/compare.py $W/h/$k.kexe $O/g/$k.edn)
  elif [ $hs -ne 0 ] && [ $gs -ne 0 ]; then cls=BOTH-REFUSE
  elif [ $hs -eq 0 ]; then cls=GUEST-FAILS
  else cls=GUEST-ONLY; fi
  printf '%s\t%s\t%s\t%s\n' $cls ${f#$R/} "$(grep -h '^KGRAPH {' $O/g/$k.log)" "$(grep -v '^KGRAPH' $O/g/$k.log | head -c 160 | tr '\n\t' '  ')" >> $O/result.tsv
done
cut -f1 $O/result.tsv | sort | uniq -c
