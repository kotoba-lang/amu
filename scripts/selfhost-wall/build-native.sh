#!/bin/zsh
# BOOTSTRAP-REFERENCE: build the JVM-compiled amu CLI as a GraalVM native image from the
# selfhost-wall classpath (worktrees named in WALL_CP), for check-native.sh.
# JVM + GraalVM are bootstrap tools here (docs/selfhost-priority.md rules 2 and 4); nothing
# this script produces is a product artifact. One build at a time (peak RSS ~4-5 GB).
#
#   WALL_CP=/tmp/cp.txt [GRAALVM_HOME=...] [OUT=<dir>] [OPT=2] scripts/selfhost-wall/build-native.sh [probe.cljk ...]
#
# Steps: (1) stage .cljk as .cljc and AOT-compile kotoba.compiler.cli on the JVM;
# (2) run the JVM `check` under the native-image tracing agent over a few probe sources
# (a native image has no reflection unless it is told about it -- the project loader and the
# file readers use some); (3) native-image with that metadata.
set -e
AMU=$(cd "$(dirname "$0")/../.." && pwd)
CP=${WALL_CP:?set WALL_CP}
K=${WALL_K:?set WALL_K (kotoba-lang checkout: lang/compat, lang/selfhost-compiler-grant.edn)}
GH=${GRAALVM_HOME:-$HOME/tools/graalvm/graalvm-jdk-25.0.4+7.1/Contents/Home}
OUT=${OUT:-$AMU/build/native-image}
OPT=${OPT:-2}
mkdir -p $OUT
cd $AMU
python3 scripts/build-native-image.py --graal-home $GH --work-dir $OUT/work --output $OUT/amu-native \
  --opt $OPT --no-native --classpath-file $CP --first-source ${WALL_AMU_SRC:-$AMU/src}
JCP=$OUT/work/classes:$(cat $OUT/work/classpath.txt)
SPA=(${(f)"$(echo "$(cat $CP)" | tr ':' '\n' | grep '/src$' | sed 's/^/--source-path\n/')"} --source-path ${WALL_AMU_SRC:-$AMU/src} --source-path $K/lang/compat --policy $K/lang/selfhost-compiler-grant.edn)
rm -rf $OUT/agent-cfg; mkdir -p $OUT/agent-cfg
probe=$OUT/probe.cljk
echo '(ns probe {:kotoba/export [f]}) (defn f [x :i64] :i64 x)' > $probe
first=1
for f in $probe "$@"; do
  mode=config-merge-dir; [ $first = 1 ] && { mode=config-output-dir; first=0; }
  $GH/bin/java -Xss512m -agentlib:native-image-agent=$mode=$OUT/agent-cfg -cp "$JCP" kotoba.compiler.cli check $f $SPA --json >/dev/null 2>&1 || true
done
# clojure.core.server__init has a root-binding side effect at class-init time; it must not be
# initialised at image build time.
python3 - $OUT/agent-cfg/reachability-metadata.json <<'P'
import json,sys
p=sys.argv[1]; d=json.load(open(p))
d['reflection']=[e for e in d.get('reflection',[]) if 'clojure.core.server' not in str(e.get('type'))]
json.dump(d,open(p,'w'))
P
python3 scripts/build-native-image.py --graal-home $GH --work-dir $OUT/work --output $OUT/amu-native \
  --opt $OPT --native-arg=-H:ConfigurationFileDirectories=$OUT/agent-cfg --classpath-file $CP --first-source ${WALL_AMU_SRC:-$AMU/src}
echo "built $OUT/amu-native"
