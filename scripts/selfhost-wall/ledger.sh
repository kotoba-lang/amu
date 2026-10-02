#!/bin/zsh
# Selfhost LEDGER: definitions with a real Kotoba body, per module of the minimal self-build reach set.
# The progress metric (docs/selfhost-minimal-reach-20261002.md). Files OK is a diagnostic only.
#
#   WALL_CP=<classpath file> WALL_K=<kotoba-lang checkout> scripts/selfhost-wall/ledger.sh [list.txt]
#
# With no list, the minimal reach set is computed (reach-minimal.py, Kotoba view). Env:
#   LEDGER_ROWS=<file>   one row per definition (module, name, host-lines, kotoba-body, diff-cases, disagreements)
#   LEDGER_SCAN=<tsv>    a wall-scan TSV, adds the native-checker status per module (default: newest
#                        /private/tmp/wall-scan-native*.tsv when present)
#   LEDGER_DIFF=<tsv>    `module<TAB>name<TAB>cases<TAB>disagreements` from the differential recordings
# Classification (real / nil / refusal / stub) is described in ledger.py. Pure text analysis: no JVM, no node.
here=${0:A:h}
amu=${WALL_AMU_ROOT:-${here:h:h}}
list=$1
if [ -z "$list" ]; then
  list=$(mktemp)
  python3 $here/reach-minimal.py $amu ${WALL_CP:?set WALL_CP} ${WALL_K:?set WALL_K} > $list 2>/dev/null
fi
scan=${LEDGER_SCAN:-$(ls -t /private/tmp/wall-scan-native*.tsv 2>/dev/null | head -1)}
args=($list)
[ -n "$LEDGER_ROWS" ] && args+=(--rows $LEDGER_ROWS)
[ -n "$scan" ] && args+=(--scan $scan)
[ -n "$LEDGER_DIFF" ] && args+=(--diff $LEDGER_DIFF)
exec python3 $here/ledger.py $args
