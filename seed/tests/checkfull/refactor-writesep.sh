#!/bin/zsh
# seed/tests/checkfull/refactor-writesep.sh <rf-prefix> <work-dir> -- `amu refactor apply` of files whose CONTENT holds
# the loader's wire-35 tokens WRITE_SEP / APPEND_SEP (agent CHECKFULL, 2026-10-04). Before CHECKFULL the Kotoba route
# trapped (SIGILL, the provider's single-occurrence rule); amu.refactor-io/write-file now writes the content in pieces.
# Each variant is src/kotoba/compiler/refactor/rules/destructure.cljk (rule a rewrites it) with the tokens placed as
# below; scripts/seed/refactor/apply-diff.sh compares bin/amu (nbb, oracle) and the Kotoba route: answer, status, file.
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h:h}
P=${1:?usage: refactor-writesep.sh <rf-prefix> <work>}; W=${2:?}; mkdir -p $W/v; W=${W:A}
B=$R/src/kotoba/compiler/refactor/rules/destructure.cljk
t() { echo -n "$1_SEP"; }
WS=$(t WRITE); AS=$(t APPEND)
{ echo ";; $WS at the start"; cat $B; } > $W/v/start.cljk
{ cat $B; echo ";; tail $WS"; } > $W/v/end.cljk
{ cat $B; echo ";; $WS$WS twice, adjacent"; } > $W/v/twice.cljk
{ cat $B; echo ";; $AS alone"; } > $W/v/append.cljk
{ cat $B; echo ";; x$WS$AS${WS}y mixed, then é and 日本 after"; } > $W/v/mixed.cljk
{ cat $B; printf '%s' ";; ends with the token $WS"; } > $W/v/last.cljk
same=0; differ=0
for f in $W/v/*.cljk; do
  if zsh $R/scripts/seed/refactor/apply-diff.sh $P $W/${f:t:r} a $f; then same=$((same+1)); else differ=$((differ+1)); fi
done
echo "refactor-writesep: $same same, $differ differ"
[ $differ = 0 ]
