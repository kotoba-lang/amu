#!/bin/zsh
# Differential run: host validate-expr vs the Kotoba-route module on the sema-test corpus.
# Env: WALL_CP (classpath file), WALL_AMU_SRC, WALL_K (kotoba-lang checkout), KTEST (kotoba-sema/test dir).
# Extra args go to vx-diff.cljs (--nested, --limit N, --show K).
HERE="$(cd "$(dirname "$0")" && pwd)"
AMU=${WALL_AMU_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}
K=${WALL_K:?set WALL_K}
CP=$(cat ${WALL_CP:?set WALL_CP})
export KTEST=${KTEST:?set KTEST to kotoba-sema/test}
export KROOTS="$(echo "$CP" | tr ':' '\n' | grep '/src$' | tr '\n' ':')${WALL_AMU_SRC:-$AMU/src}:$K/lang/compat"
export SELFHOST_WALL_DIR="$(cd "$(dirname "$0")" && pwd)"
cd ${WALL_NBB_DIR:-$AMU}
VXM=${VX_MODULE:-$(echo "$CP" | tr ':' '\n' | grep 'kotoba-sema/src$' | head -1)/kotoba/compiler/validate_expr.cljk}
. "$HERE/golden-wrap.sh"
golden_begin vx-run "$VXM" $KTEST "$HERE/vx-diff.cljs" @ARGS="$*"
# the guest recurses once per source nesting level through the KIR interpreter, so it needs a deep host stack
ulimit -s ${WALL_ULIMIT_S:-65520} 2>/dev/null
node --stack-size=${WALL_STACK_SIZE:-56000} ${WALL_NBB:-node_modules/nbb/cli.js} --classpath "$CP" "$HERE/vx-diff.cljs" "$@"
golden_end $?
