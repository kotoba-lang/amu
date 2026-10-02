#!/bin/zsh
# BOOTSTRAP-REFERENCE: the LINKED end-to-end differential of the frontend facade (kotoba-sema), host vs the Kotoba route.
# e2e-record.cljs (nbb) records, for every program embedded in kotoba-sema's tests, the HOST's `kotoba.sema/analyze` answer (the HIR, or the
# refusal message); guests/e2e.cljk is linked with the whole Kotoba reading of the frontend (kotoba.compiler.frontend.analyze and every module
# below it), lowered once, and run on the KIR interpreter (abort-run-jvm.clj, ceilings raised) on the same programs; it answers per line
#   OK | DIFF guest <hir> || host <hir> | DIFF guest refused: <msg> || host ... | TRAP
# so the figures are: programs analysed to the same HIR / the same refusal on the Kotoba route, and the first disagreements.
#
#   WALL_CP=<cp> WALL_K=<kotoba-lang> WALL_AMU_SRC=<src> DS_TESTS=<kotoba-sema>/test [E2E_MAX=n] scripts/selfhost-wall/e2e-diff.sh [cases.txt]
HERE="$(cd "$(dirname "$0")" && pwd)"
AMU=${WALL_AMU_ROOT:-$(cd "$HERE/../.." && pwd)}
K=${WALL_K:?set WALL_K}
CP=$(cat ${WALL_CP:?set WALL_CP})
OUT=${E2E_OUT:-/tmp/e2e-diff}; mkdir -p $OUT
JOBS=${E2E_JOBS:-3}
W=${WALL_JVM_WORK:-$AMU/build/native-image/work}
J=${GRAALVM_HOME:-$HOME/tools/graalvm/graalvm-jdk-25.0.4+7.1/Contents/Home}/bin/java
SRC=(${(f)"$(echo "$CP" | tr ':' '\n' | grep '/src$')"} ${WALL_AMU_SRC:-$AMU/src} $K/lang/compat)
export KROOTS="${(j/:/)SRC}"
cases=$1
if [ -z "$cases" ]; then
  cases=$OUT/cases.txt
  ( cd ${WALL_NBB_DIR:-$AMU}; ulimit -s 65500
    DS_TESTS=${DS_TESTS:?set DS_TESTS} DS_EXTRA=$DS_EXTRA OUT=$cases \
      node --stack-size=56000 node_modules/nbb/cli.js --classpath "$CP:${WALL_AMU_SRC:-$AMU/src}" $HERE/e2e-record.cljs ) || exit 1
fi
find $OUT -name "ans.*" -delete
for k in {0..$((JOBS-1))}; do awk -v k=$k -v n=$JOBS 'NR%n==k' $cases > $OUT/chunk.$k; done
for k in {0..$((JOBS-1))}; do
  ( export GUEST=${GUEST_FILE:-$HERE/guests/e2e.cljk} ENTRY=${ENTRY_FN:-e2e-run} ABORT_CACHE=$OUT; ulimit -s 65500
    $J -Xss1g -Xmx6g -cp "$W/classes:$(cat $W/classpath.txt)" clojure.main $HERE/abort-run-jvm.clj < $OUT/chunk.$k > $OUT/ans.$k 2> $OUT/err.$k ) &
done
wait
cat $OUT/ans.* | sed 's/ ||.*//' | sort | uniq -c | sort -rn | head -40
echo "cases: $(wc -l < $cases)  answers: $(cat $OUT/ans.* | wc -l)  (DIFF lines are in $OUT/ans.*)"
