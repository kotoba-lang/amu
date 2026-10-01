#!/bin/zsh
# bootstrap-tooling: runs wall-cache-conformance.cljs (needs nbb; WALL_CP, WALL_K as for the other differentials).
AMU=${WALL_AMU_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}; HERE="$(cd "$(dirname "$0")" && pwd)"
K=${WALL_K:?set WALL_K}; CP=$(cat ${WALL_CP:?set WALL_CP})
export KROOTS="${WALL_AMU_SRC:-$AMU/src}:$(echo "$CP" | tr ':' '\n' | grep '/src$' | tr '\n' ':')$K/lang/compat"
cd ${WALL_NBB_DIR:-$AMU}; [ -d node_modules/nbb ] || cd /Users/junkawasaki/github/kotoba-lang/amu-measure
exec node --stack-size=${WALL_STACK_SIZE:-30000} node_modules/nbb/cli.js --classpath "${WALL_AMU_SRC:-$AMU/src}:$CP" "$HERE/wall-cache-conformance.cljs"
