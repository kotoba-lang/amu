#!/bin/zsh
# scripts/seed/refactor/split-diff.sh <rf-prefix> <out-dir> <src-file> [partition flags...] -- differential of
# `amu refactor split` (agent REFAC, 2026-10-04): bin/amu (nbb, oracle) writes the partition (partition --out), then splits
# into <out-dir>/split; the tree is kept and the Kotoba-route dispatcher splits into the same path. SAME when stdout,
# stderr, exit status and every written file are byte-equal.
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h:h}; P=${1:A}; W=${2:A}; F=${3:A}; shift 3
source $H/lib.sh
mkdir -p $W; rm -rf $W/split $W/h $W/n
(cd $R && bin/amu refactor partition $F --out $W/p.edn "$@" > $W/p.out 2>&1) || { echo "SKIP	split ${F:t}	(host partition refused: $(head -c 120 $W/p.out))"; exit 0; }
(cd $R && bin/amu refactor split $F --partition $W/p.edn --out $W/split > $W/h.out 2> $W/h.err); hs=$?
[ -d $W/split ] && mv $W/split $W/h
rf_run $P refactor split $F --partition $W/p.edn --out $W/split > $W/n.out 2> $W/n.err; ns=$?
[ -d $W/split ] && mv $W/split $W/n
ok=1; [ $hs = $ns ] || ok=0
for x in out err; do cmp -s $W/h.$x $W/n.$x || ok=0; done
if [ -d $W/h ] || [ -d $W/n ]; then diff -r $W/h $W/n > $W/tree.diff 2>&1 || ok=0; fi
nf=$( [ -d $W/h ] && find $W/h -type f | wc -l | tr -d ' ' || echo 0)
if [ $ok = 1 ]; then printf "SAME\tsplit %s %s\t%s files\n" ${F:t} "$*" $nf; else printf "DIFFER\tsplit %s %s\thost %s native %s\n" ${F:t} "$*" $hs $ns; fi
[ $ok = 1 ]
