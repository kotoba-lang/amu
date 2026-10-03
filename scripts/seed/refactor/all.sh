#!/bin/zsh
# scripts/seed/refactor/all.sh <rf-prefix> <out-dir> [kotoba-lang] -- every REFAC differential over seed/tests/refactor
# (agent REFAC, 2026-10-04). One summary line per suite; exit 0 when every suite has 0 DIFFER.
emulate -L zsh
H=${0:A:h}; R=${H:h:h:h}; P=${1:A}; W=${2:A}; K=${3:-/private/tmp/wt-K-port-kotoba-lang}; mkdir -p $W
T=$R/seed/tests/refactor; rc=0
for c in args graph plan partition dynvars graph-src plan-src; do
  zsh $H/diff.sh $P $T/cases-$c.txt $W/$c > $W/$c.log 2>&1 || rc=1; echo "$c: $(tail -1 $W/$c.log)"
done
zsh $H/apply-cases.sh $P $T/cases-apply.txt $W/apply > $W/apply.log 2>&1 || rc=1; echo "apply: $(tail -1 $W/apply.log)"
zsh $H/split-cases.sh $P $T/cases-split.txt $W/split > $W/split.log 2>&1 || rc=1; echo "split: $(tail -1 $W/split.log)"
zsh $H/verify-diff.sh $K $W/verify > $W/verify.log 2>&1 || rc=1; echo "verify: $(tail -1 $W/verify.log)"
exit $rc
