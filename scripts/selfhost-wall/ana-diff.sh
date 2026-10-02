#!/bin/zsh
# BOOTSTRAP-REFERENCE differential for the Kotoba-route readings of the frontend's remaining modules
# (kotoba-sema frontend/state_ability, row, record_projection, analyze): the HOST passes, recorded while sema/analyze runs the
# programs embedded in kotoba-sema's tests (ana-record.cljs, nbb), against the Kotoba readings (guests/ana.cljk, linked with the
# whole frontend, run on the KIR interpreter on the JVM-built compiler; abort-run-jvm.clj raises the project ceilings).
#
#   WALL_CP=<cp> WALL_K=<kotoba-lang> WALL_AMU_SRC=<src> DS_TESTS=<kotoba-sema>/test [DS_EXTRA=<dir>:<dir>] [WALL_NBB_DIR=..] \
#     [ANA_OPS=spec,thread] scripts/selfhost-wall/ana-diff.sh [cases.txt]
#
# Each case line is [:op ctx args... expected]; the guest answers OK or DIFF per line (summary: count per op and verdict).
# Env: ANA_OUT (work dir, default /tmp/ana-diff), ANA_JOBS (parallel guests, default 3), GRAALVM_HOME, WALL_JVM_WORK.
HERE="$(cd "$(dirname "$0")" && pwd)"
AMU=${WALL_AMU_ROOT:-$(cd "$HERE/../.." && pwd)}
K=${WALL_K:?set WALL_K}
CP=$(cat ${WALL_CP:?set WALL_CP})
OUT=${ANA_OUT:-/tmp/ana-diff}; mkdir -p $OUT
JOBS=${ANA_JOBS:-3}
W=${WALL_JVM_WORK:-$AMU/build/native-image/work}
J=${GRAALVM_HOME:-$HOME/tools/graalvm/graalvm-jdk-25.0.4+7.1/Contents/Home}/bin/java
SRC=(${(f)"$(echo "$CP" | tr ':' '\n' | grep '/src$')"} ${WALL_AMU_SRC:-$AMU/src} $K/lang/compat)
export KROOTS="${(j/:/)SRC}"
cases=$1
if [ -z "$cases" ]; then
  cases=$OUT/cases.txt
  ( cd ${WALL_NBB_DIR:-$AMU}; ulimit -s 65500
    DS_TESTS=${DS_TESTS:?set DS_TESTS} DS_EXTRA=$DS_EXTRA OUT=$cases \
      node --stack-size=56000 node_modules/nbb/cli.js --classpath "$CP:${WALL_AMU_SRC:-$AMU/src}" $HERE/ana-record.cljs ) || exit 1
fi
find $OUT -name "ans.*" -delete
for k in {0..$((JOBS-1))}; do awk -v k=$k -v n=$JOBS 'NR%n==k' $cases > $OUT/chunk.$k; done
for k in {0..$((JOBS-1))}; do
  ( export GUEST=$HERE/guests/ana.cljk ENTRY=ana-run ABORT_CACHE=$OUT; ulimit -s 65500
    $J -Xss1g -Xmx6g -cp "$W/classes:$(cat $W/classpath.txt)" clojure.main $HERE/abort-run-jvm.clj < $OUT/chunk.$k > $OUT/ans.$k 2> $OUT/err.$k ) &
done
wait
cat $OUT/ans.* | sed 's/ ||.*//' | sort | uniq -c | sort -rn | head -40
echo "cases: $(wc -l < $cases)  answers: $(cat $OUT/ans.* | wc -l)  (DIFF lines are in $OUT/ans.*)"
