#!/bin/zsh
# BOOTSTRAP-REFERENCE differential for the Kotoba-route absence and abort passes of kotoba-sema's frontend/infer.cljk
# (resolve-absence-if, infer-absent-results, infer-absent-parameter-types, infer-abort-error-types, elaborate-aborts):
# the HOST passes (recorded while sema/analyze runs the programs embedded in kotoba-sema's tests, on nbb) vs the Kotoba
# readings (guests/abort.cljk, linked with the whole frontend and run on the KIR interpreter on the JVM-built compiler).
#
#   WALL_CP=<cp> WALL_K=<kotoba-lang> WALL_AMU_SRC=<src> DS_TESTS=<kotoba-sema>/test [DS_EXTRA=<dir>:<dir>] [WALL_NBB_DIR=..] \
#     scripts/selfhost-wall/abort-diff.sh [cases.txt]
#
# Without CASES the host side is recorded first (abort-record.cljs). Each case line is
# [:abort|:elab|:results|:params ctx functions ... expected] or [:absence ctx form locals signatures statement? expected]; the guest
# answers OK or DIFF per line. The EDN a case is written in carries neither spans nor the `:kotoba.diag/source-head` metadata, so a
# parameter-use-conflict message differs in `[x at L:C]` and in the head the author wrote (`string-length` for `string-byte-length`):
# those are the only expected DIFFs. Env: ABORT_OUT (work dir, default /tmp/abort-diff), ABORT_JOBS (parallel guests, default 3),
# GRAALVM_HOME, WALL_JVM_WORK (default <repo>/build/native-image/work: the AOT classes build-native.sh leaves behind).
HERE="$(cd "$(dirname "$0")" && pwd)"
AMU=${WALL_AMU_ROOT:-$(cd "$HERE/../.." && pwd)}
K=${WALL_K:?set WALL_K}
CP=$(cat ${WALL_CP:?set WALL_CP})
OUT=${ABORT_OUT:-/tmp/abort-diff}; mkdir -p $OUT
JOBS=${ABORT_JOBS:-3}
W=${WALL_JVM_WORK:-$AMU/build/native-image/work}
J=${GRAALVM_HOME:-$HOME/tools/graalvm/graalvm-jdk-25.0.4+7.1/Contents/Home}/bin/java
SRC=(${(f)"$(echo "$CP" | tr ':' '\n' | grep '/src$')"} ${WALL_AMU_SRC:-$AMU/src} $K/lang/compat)
export KROOTS="${(j/:/)SRC}"
cases=$1
if [ -z "$cases" ]; then
  cases=$OUT/cases.txt
  ( cd ${WALL_NBB_DIR:-$AMU}; ulimit -s 65500
    DS_TESTS=${DS_TESTS:?set DS_TESTS} DS_EXTRA=$DS_EXTRA OUT=$cases \
      node --stack-size=56000 node_modules/nbb/cli.js --classpath "$CP:${WALL_AMU_SRC:-$AMU/src}" $HERE/abort-record.cljs ) || exit 1
fi
find $OUT -name "ans.*" -delete
for k in {0..$((JOBS-1))}; do awk -v k=$k -v n=$JOBS 'NR%n==k' $cases > $OUT/chunk.$k; done
for k in {0..$((JOBS-1))}; do
  ( export GUEST=$HERE/guests/abort.cljk ENTRY=ab-run ABORT_CACHE=$OUT; ulimit -s 65500
    $J -Xss1g -Xmx6g -cp "$W/classes:$(cat $W/classpath.txt)" clojure.main $HERE/abort-run-jvm.clj < $OUT/chunk.$k > $OUT/ans.$k 2> $OUT/err.$k ) &
done
wait
cat $OUT/ans.* | sed 's/ ||.*//' | sort | uniq -c | sort -rn | head -20
echo "cases: $(wc -l < $cases)  answers: $(cat $OUT/ans.* | wc -l)  (DIFF lines are in $OUT/ans.*)"
