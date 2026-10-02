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
[ -n "$SKIP_TRACE" ] && [ -d $OUT/agent-cfg ] || { rm -rf $OUT/agent-cfg; mkdir -p $OUT/agent-cfg; DO_TRACE=1; }
probe=$OUT/probe.cljk
echo '(ns probe {:kotoba/export [f]}) (defn f [x :i64] :i64 x)' > $probe
# A literal wider than 64 bits is read by the Clojure reader through
# BigInteger(String) (reflection); without that entry the native checker answers
# a different refusal on every source holding one (11 files of the reach list
# regressed silently on a from-scratch build). The probe forces the reader down
# that path -- decimal, hex and an N-suffixed literal -- so the tracing agent
# records the constructor; the checker refuses it ("host literal bigint"), which
# is the expected answer and is what check-native then reports.
probe_wide=$OUT/probe-wide.cljk
cat > $probe_wide <<'W'
(ns probe-wide {:kotoba/export [f]})
(defn f [x :i64] :i64
  (if (= x 0) 18446744073709551615 (if (= x 1) 0xFFFFFFFFFFFFFFFFF 9223372036854775808N)))
W
first=1
agent() { [ -n "$DO_TRACE" ] || return 0; _agent "$@"; }
_agent() { # agent <java main args...> : one traced JVM run; refusals are fine, they walk the same code
  mode=config-merge-dir; [ $first = 1 ] && { mode=config-output-dir; first=0; }
  $GH/bin/java -Xss512m -agentlib:native-image-agent=$mode=$OUT/agent-cfg -cp "$JCP" kotoba.compiler.cli "$@" >/dev/null 2>&1 || true
}
for f in $probe $probe_wide "$@"; do agent check $f $SPA --json; done
# The compile path (kotoba.native.* lowering, hex/bytes helpers, the KEXE packager, extract-native) reaches
# reflection that `check` never does: a native image traced over `check` alone answered "internal compiler
# error" on 12 of the 19 Embench ports in `compile` mode. So trace compile (+ extract-native) too, over the
# 19 ports, a :bytes capability-call program (wire 35 over :bytes, seed/02-io-bytes), a program holding a
# literal wider than 64 bits, and the seed's own unity pieces when they exist.
POL=$OUT/trace-policy.edn
echo '{:allow #{[:cap/call 35] [:cap/call 37] [:cap/call 38] [:cap/call 39]}}' > $POL
TR=$OUT/trace-out; rm -rf $TR; mkdir -p $TR
n=0
for f in $AMU/seed/tests/t3/*.kotoba $AMU/build/seed/seed-unity.kotoba $AMU/build/seed/io-bytes/unity.kotoba $probe $probe_wide; do
  [ -f $f ] || continue
  n=$((n+1)); o=$TR/$n.kexe
  agent check $f --jvm-free --json
  agent compile $f --target aarch64-macos --jvm-free --policy $POL --output $o
  [ -f $o ] && agent extract-native $o --symbol main --output $TR/$n.bin
done
# ports export test-*, not main: extract those symbols too (the qualification script does)
for f in $AMU/bench/embench/ports/*.kotoba; do
  b=$(basename $f .kotoba); sym=$(sed -n '1s/.*:export \[\([^]]*\)\].*/\1/p' $f | tr ' ' '\n' | grep '^test-' | head -1)
  agent compile $f --target aarch64-macos --jvm-free --output $TR/$b.kexe
  [ -n "$sym" ] && [ -f $TR/$b.kexe ] && agent extract-native $TR/$b.kexe --symbol $sym --output $TR/$b.bin
done
# clojure.core.server__init has a root-binding side effect at class-init time; it must not be
# initialised at image build time.
python3 - $OUT/agent-cfg <<'P'
import json,sys,os
d=sys.argv[1]
# GraalVM 25 writes reachability-metadata.json; GraalVM 21 writes reflect-config.json (a list of {name:..}).
p=os.path.join(d,'reachability-metadata.json')
if os.path.exists(p):
    m=json.load(open(p)); m['reflection']=[e for e in m.get('reflection',[]) if 'clojure.core.server' not in str(e.get('type'))]
    json.dump(m,open(p,'w'))
p=os.path.join(d,'reflect-config.json')
if os.path.exists(p):
    m=[e for e in json.load(open(p)) if 'clojure.core.server' not in str(e.get('name'))]
    json.dump(m,open(p,'w'))
P
# Fail the build here, not three files later, if the wide-literal entry is missing.
grep -q 'java.math.BigInteger' $OUT/agent-cfg/*.json \
  || { echo "build-native: tracing agent did not record java.math.BigInteger (probe-wide)" >&2; exit 3; }
python3 scripts/build-native-image.py --graal-home $GH --work-dir $OUT/work --output $OUT/amu-native \
  --opt $OPT --native-arg=-H:ConfigurationFileDirectories=$OUT/agent-cfg --classpath-file $CP --first-source ${WALL_AMU_SRC:-$AMU/src}
echo "built $OUT/amu-native"
