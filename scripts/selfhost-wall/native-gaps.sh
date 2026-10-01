#!/bin/zsh
# native-gaps.sh <guest.cljk>... : per guest, the native backend's refusals aggregated by detail (count, example functions),
# and the operations the wasm emitter does not mention. Bootstrap scaffolding (runs the scanner on nbb); the answer is
# data for docs/selfhost-native-gaps-20261001.md. Env as guest-run.sh, plus WASM_SRC (default /private/tmp/wt-D-kotoba-wasm/src/kotoba/wasm).
HERE="$(cd "$(dirname "$0")" && pwd)"
AMU=${WALL_AMU_ROOT:-$(cd "$HERE/../.." && pwd)}
K=${WALL_K:?set WALL_K}; CP=$(cat ${WALL_CP:?set WALL_CP})
SRCDIRS=(${(f)"$(echo "$CP" | tr ':' '\n' | grep '/src$')"} ${WALL_AMU_SRC:-$AMU/src} $K/lang/compat)
export KROOTS="${(j/:/)SRCDIRS}" WASM_SRC=${WASM_SRC:-/private/tmp/wt-D-kotoba-wasm/src/kotoba/wasm}
args=(); for g in "$@"; do args+=("$(cd "$(dirname $g)" && pwd)/$(basename $g)"); done
cd ${WALL_NBB_DIR:-$AMU}; ulimit -s 65520 2>/dev/null
for g in $args; do
  echo "=== $g"
  GUEST=$g nice node --stack-size=56000 node_modules/nbb/cli.js --classpath "$CP:${WALL_AMU_SRC:-$AMU/src}" "$HERE/native-gaps.cljs" 2>&1 \
    | awk -F'\t' '/^#/ {print; next} NF<3 {print "ERROR " $0; next} {k=$2 "\t" $3; n[k]++; if (n[k]<=3) ex[k]=ex[k] " " $1} END {for (k in n) print n[k] "\t" k "\t" ex[k]}' | sort -rn
done
