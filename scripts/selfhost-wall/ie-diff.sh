#!/bin/zsh
# The infer differential: the host passes check-value-types!, elaborate-named-abilities, infer-loop-helper-results,
# check-loop-recur-argument-types!, resolve-loop-helper-param-types, infer-closure-refinements (as `analyze` calls them on the
# programs of kotoba-sema's tests) against the Kotoba-route bodies in kotoba-sema's frontend/infer.cljk.
#
#   WALL_CP=<cp> WALL_K=<kotoba-lang> WALL_AMU_SRC=<this repo>/src KSEMA=<kotoba-sema checkout> \
#   [IE_EXTRA=dir:dir] [IE_PARTS=3] [JAVA=java] [IE_WORK=/tmp/ie-diff] scripts/selfhost-wall/ie-diff.sh
#
# 1. ie-gen.py builds the guest: infer.cljk verbatim (every defn private, the module renamed) + ie-tail.cljk (the case dispatcher).
# 2. ie-host.cljs (nbb, BOOTSTRAP) analyses the programs with the six passes tapped and writes one case line per call:
#    [op ctx functions extra expected], the host's answer (or refusal message) realized and printed.
# 3. ie-interp.clj (JVM + KIR interpreter, BOOTSTRAP REFERENCE: the native and wasm backends do not admit the guest yet:
#    typed sets of keywords) links and lowers the guest once, then runs the cases in batches; the guest compares its answer with
#    the host's by form/eq (the host's :used of elaborate-named-abilities is a snapshot taken before its lazy walk is realized,
#    so the guest requires only containment there) and answers OK / OKERR (same refusal) / DIFF / ERRMSG / ERR-vs-OK / TRAP.
# 4. ie-summary.py counts per op.
HERE="$(cd "$(dirname "$0")" && pwd)"
AMU=${WALL_AMU_ROOT:-$(cd "$HERE/../.." && pwd)}
K=${WALL_K:?set WALL_K}; CPF=${WALL_CP:?set WALL_CP}; CP=$(cat $CPF)
KSEMA=${KSEMA:?set KSEMA to the kotoba-sema checkout}
WORK=${IE_WORK:-/tmp/ie-diff}; PARTS=${IE_PARTS:-3}; JAVA=${JAVA:-java}
AMU_SRC=${WALL_AMU_SRC:-$AMU/src}
mkdir -p $WORK
SRCDIRS=(${(f)"$(echo "$CP" | tr ':' '\n' | grep '/src$')"} $AMU_SRC $K/lang/compat)
export KROOTS="${(j/:/)SRCDIRS}"
python3 $HERE/ie-gen.py $KSEMA/src/kotoba/compiler/frontend/infer.cljk $HERE/ie-tail.cljk $WORK/infer_guest.cljk || exit 1
( cd $AMU; ulimit -s 65520
  KTEST=$KSEMA/test IE_EXTRA="${IE_EXTRA}" SELFHOST_WALL_DIR=$HERE node --stack-size=56000 ${WALL_NBB:-node_modules/nbb/cli.js} \
    --classpath "$CP:$AMU_SRC" $HERE/ie-host.cljs --cases $WORK/ie-cases-raw.txt ) || exit 1
awk '!s[$0]++ && length($0) <= 120000' $WORK/ie-cases-raw.txt > $WORK/ie-cases.txt
rm -f $WORK/pt*; awk -v n=$PARTS '{print > ("'$WORK'/pt" (NR%n))}' $WORK/ie-cases.txt
W=$AMU/build/native-image/work   # the JVM-built compiler classes (build-native.sh)
JCP=$W/classes:$(cat $W/classpath.txt)
for i in {0..$((PARTS-1))}; do
  ( GUEST=$WORK/infer_guest.cljk CASES=$WORK/pt$i OUT=$WORK/answers$i.txt BATCH=58000 \
      $JAVA -Xss1g -Xmx6g -cp "$JCP" clojure.main $HERE/ie-interp.clj > $WORK/interp$i.log 2>&1 ) &
done
wait
python3 $HERE/ie-summary.py $WORK/ie-cases.txt $PARTS $WORK/answers{0..$((PARTS-1))}.txt
