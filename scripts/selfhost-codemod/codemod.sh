#!/bin/sh
# usage: scripts/selfhost-codemod/codemod.sh <file.cljk> --rules a,b,c,d [--target dual|host-env] [--out f] [--report f] [--dry-run]
# NBB_DIR: a checkout with node_modules/nbb (default: the amu-measure checkout next to the kotoba-lang sources)
HERE="$(cd "$(dirname "$0")" && pwd)"
NBB_DIR=${NBB_DIR:-/Users/junkawasaki/github/kotoba-lang/amu-measure}
exec node --stack-size=${STACK_SIZE:-4096} "$NBB_DIR/node_modules/nbb/cli.js" --classpath "$HERE/src" "$HERE/run.cljs" "$@"
