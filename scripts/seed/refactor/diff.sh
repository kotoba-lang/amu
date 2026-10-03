#!/bin/zsh
# scripts/seed/refactor/diff.sh <rf-prefix> <cases-file> <out-dir> -- differential of `amu refactor` on the Kotoba route
# (the seed-built dispatcher seed/tests/refactor/entry.kotoba, run through tools/kexe_loader.c) against bin/amu refactor
# (node + nbb, BOOTSTRAP-REFERENCE oracle only). Agent REFAC, 2026-10-04.
# A case is one line: the words after `refactor`, split on spaces (@R@ = the repo root, @T@ = the out dir).
# Verdict per case: SAME when stdout, stderr and the exit status are byte-equal; STUB when the native side answered
# the declared stub (exit 69, :amu-main/not-available) -- never counted as SAME; DIFFER otherwise.
# Files a case writes (--out) are compared too when the case names them as `--out @T@/<name>`.
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h:h}
P=${1:A}; C=${2:A}; W=${3:A}; mkdir -p $W
source $H/lib.sh
same=0; stub=0; differ=0; i=0
while IFS= read -r line; do
  [[ -z $line || $line == \#* ]] && continue
  i=$((i+1))
  line=${line//@R@/$R}; line=${line//@T@/$W}
  args=(${=line})
  outs=(); for ((k=1;k<${#args};k++)); do { [ "${args[k]}" = --out ] || [ "${args[k]}" = --patch-out ]; } && outs+=(${args[k+1]}); done
  for o in $outs; do rm -rf $o; done
  (cd $R && bin/amu refactor $args > $W/$i.h.out 2> $W/$i.h.err); hs=$?
  for o in $outs; do [ -e $o ] && mv $o $W/$i.h.file; done
  rf_run $P refactor $args > $W/$i.n.out 2> $W/$i.n.err; ns=$?
  for o in $outs; do [ -e $o ] && mv $o $W/$i.n.file; done
  fs=0; if [ -e $W/$i.h.file ] || [ -e $W/$i.n.file ]; then cmp -s $W/$i.h.file $W/$i.n.file || fs=1; fi
  if [ $ns = 69 ] && grep -q 'amu-main/not-available' $W/$i.n.err; then
    stub=$((stub+1)); printf "STUB\t%s\t(host %s)\n" "$line" $hs
  elif [ $hs = $ns ] && [ $fs = 0 ] && cmp -s $W/$i.h.out $W/$i.n.out && cmp -s $W/$i.h.err $W/$i.n.err; then
    same=$((same+1)); printf "SAME\t%s\t%s B\n" "$line" $(wc -c < $W/$i.h.out | tr -d ' ')
  else
    differ=$((differ+1)); printf "DIFFER\t%s\thost %s native %s %s\n" "$line" $hs $ns \
      "$(cmp $W/$i.h.out $W/$i.n.out 2>&1 | head -1; cmp $W/$i.h.err $W/$i.n.err 2>&1 | head -1; [ $fs = 1 ] && echo file-differs)"
  fi
done < $C
echo "refactor-diff: $same same, $stub stub, $differ differ ($i cases; native $(shasum -a 256 $P.bin | cut -c1-12))"
[ $differ -eq 0 ]
