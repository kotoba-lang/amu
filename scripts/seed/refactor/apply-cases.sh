#!/bin/zsh
# scripts/seed/refactor/apply-cases.sh <rf-prefix> <cases-file> <out-dir> -- apply-diff.sh over every case line
# "<rules> <repo-relative file> [flags...]" (@O@ = an --out file in the case's work dir). Agent REFAC, 2026-10-04.
emulate -L zsh
H=${0:A:h}; R=${H:h:h:h}; P=${1:A}; C=${2:A}; W=${3:A}
same=0; differ=0; i=0
while IFS= read -r line; do
  [[ -z $line || $line == \#* ]] && continue
  i=$((i+1)); a=(${=line})
  if zsh $H/apply-diff.sh $P $W/$i $a[1] $R/$a[2] ${a[3,-1]}; then same=$((same+1)); else differ=$((differ+1)); fi
done < $C
echo "apply-cases: $same same, $differ differ ($i cases)"
[ $differ = 0 ]
