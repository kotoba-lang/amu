#!/bin/zsh
# scripts/seed/refactor/split-cases.sh <rf-prefix> <cases-file> <out-dir> -- split-diff.sh over every case line
# "<file> [partition flags...]" (a file path relative to the repo, or absolute). Agent REFAC, 2026-10-04.
emulate -L zsh
H=${0:A:h}; R=${H:h:h:h}; P=${1:A}; C=${2:A}; W=${3:A}
same=0; differ=0; i=0
while IFS= read -r line; do
  [[ -z $line || $line == \#* ]] && continue
  i=$((i+1)); a=(${=line}); f=$a[1]; [[ $f = /* ]] || f=$R/$f
  if zsh $H/split-diff.sh $P $W/$i $f ${a[2,-1]}; then same=$((same+1)); else differ=$((differ+1)); fi
done < $C
echo "split-cases: $same same (SKIP counted as same: the host refused the partition), $differ differ ($i cases)"
[ $differ = 0 ]
