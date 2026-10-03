#!/bin/zsh
# scripts/seed/refactor/verify-diff.sh <kotoba-lang> <out-dir> -- differential of the verify twin (kotoba-lang
# lang/compat/kotoba/compiler/refactor/verify.kotoba, compiled by the seed into seed/tests/refactor/verify/probe.kotoba)
# against the host verify.cljk under nbb (BOOTSTRAP oracle), over the runner-output pairs in seed/tests/refactor/verify.
# Agent REFAC, 2026-10-04.
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h:h}; K=${1:A}; W=${2:A}; mkdir -p $W
source $H/lib.sh
T=$R/seed/tests/refactor/verify
rf_compile $T/probe.kotoba $W/p $K/lang/compat || exit 2
same=0; differ=0
for pair in "a b" "b a" "a a" "a c" "c c"; do
  set -- ${=pair}
  (cd $R && node_modules/.bin/nbb --classpath src $T/host.cljs $T/$1.txt $T/$2.txt) > $W/h.out 2>&1
  rf_run $W/p $T/$1.txt $T/$2.txt > $W/n.out 2>&1
  if cmp -s $W/h.out $W/n.out; then same=$((same+1)); echo "SAME $pair"; else differ=$((differ+1)); echo "DIFFER $pair"; fi
done
echo "verify-diff: $same same, $differ differ"
[ $differ = 0 ]
