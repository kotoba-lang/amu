#!/bin/zsh
# Desugar differential: host `desugar-expr` vs its Kotoba-route port (ds-gen.sh generates the guest) on the forms of the
# programs embedded in kotoba-sema's tests. Env: WALL_CP, WALL_K, WALL_AMU_SRC, FRONTEND (frontend.cljk), DS_TESTS (test dir).
AMU=${WALL_AMU_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}
HERE="$(cd "$(dirname "$0")" && pwd)"
K=${WALL_K:?set WALL_K}
CP=$(cat ${WALL_CP:?set WALL_CP})
export DS_GUEST=${DS_GUEST:-/tmp/ds_guest.cljk}
[ -n "$DS_NOGEN" ] || "$HERE/ds-gen.sh" || exit 1
export DS_TESTS=${DS_TESTS:?set DS_TESTS to kotoba-sema/test}
export KROOTS="$(echo "$CP" | tr ':' '\n' | grep '/src$' | tr '\n' ':')${WALL_AMU_SRC:-$AMU/src}:$K/lang/compat"
cd ${WALL_NBB_DIR:-$AMU}
ulimit -s ${WALL_ULIMIT_S:-65520} 2>/dev/null
exec node --stack-size=${WALL_STACK_SIZE:-56000} ${WALL_NBB:-node_modules/nbb/cli.js} --classpath "$CP" "$HERE/ds-diff.cljs" "$@"
