#!/bin/zsh
# scripts/seed/refactor/apply-diff.sh <rf-prefix> <out-dir> <rules> <file> [flags...] -- differential of `amu refactor apply`
# (agent REFAC, 2026-10-04): the file is copied to <out-dir>/w/<basename>; bin/amu (nbb, oracle) applies to that copy,
# the answer and the resulting file are kept; the copy is restored and the Kotoba-route dispatcher applies to the same path.
# SAME when stdout, stderr, exit status and the resulting file (and an --out file) are byte-equal.
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h:h}
P=${1:A}; W=${2:A}; rules=$3; F=${4:A}; shift 4
source $H/lib.sh
mkdir -p $W/w; T=$W/w/${F:t}; O=$W/w/out.cljk
flags=("$@"); flags=(${flags//@O@/$O})
cp $F $T; rm -f $O
(cd $R && bin/amu refactor apply $rules $T $flags > $W/h.out 2> $W/h.err); hs=$?
cp $T $W/h.file; [ -e $O ] && mv $O $W/h.o || rm -f $W/h.o
cp $F $T; rm -f $O
rf_run $P refactor apply $rules $T $flags > $W/n.out 2> $W/n.err; ns=$?
cp $T $W/n.file; [ -e $O ] && mv $O $W/n.o || rm -f $W/n.o
ok=1
[ $hs = $ns ] || ok=0
for x in out err file; do cmp -s $W/h.$x $W/n.$x || ok=0; done
if [ -e $W/h.o ] || [ -e $W/n.o ]; then cmp -s $W/h.o $W/n.o || ok=0; fi
if [ $ok = 1 ]; then printf "SAME\tapply %s %s %s\t%s B\n" $rules ${F:t} "$flags" $(wc -c < $W/h.out | tr -d ' ')
else printf "DIFFER\tapply %s %s %s\thost %s native %s\n" $rules ${F:t} "$flags" $hs $ns; fi
[ $ok = 1 ]
