#!/bin/zsh
# Differential run: the frontend's host type-model helpers vs their :kotoba branches on the KIR interpreter.
# Env: WALL_CP (classpath file), WALL_AMU_SRC, WALL_K (kotoba-lang checkout), FRONTEND (frontend.cljk path).
# Generates the guest module (tm-gen.py: reader conditionals expanded, definitions picked by name) then runs tm-diff.cljs.
AMU=${WALL_AMU_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}
HERE="$(cd "$(dirname "$0")" && pwd)"
K=${WALL_K:?set WALL_K}
CP=$(cat ${WALL_CP:?set WALL_CP})
export TM_GUEST=${TM_GUEST:-/tmp/tm_guest.cljk}
python3 "$HERE/tm-gen.py" "${FRONTEND:?set FRONTEND to kotoba-sema/src/kotoba/compiler/frontend.cljk}" "$TM_GUEST" || exit 1
export KROOTS="$(echo "$CP" | tr ':' '\n' | grep '/src$' | tr '\n' ':')${WALL_AMU_SRC:-$AMU/src}:$K/lang/compat"
cd ${WALL_NBB_DIR:-$AMU}
ulimit -s ${WALL_ULIMIT_S:-65520} 2>/dev/null
. "$HERE/golden-wrap.sh"
golden_begin tm-run "$FRONTEND" "$HERE/tm-diff.cljs"
node --stack-size=${WALL_STACK_SIZE:-56000} ${WALL_NBB:-node_modules/nbb/cli.js} --classpath "$CP" "$HERE/tm-diff.cljs" "$@"
golden_end $?
