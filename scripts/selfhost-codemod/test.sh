#!/bin/sh
# Unit + host-equivalence tests of the codemod library (nbb).
HERE="$(cd "$(dirname "$0")" && pwd)"
NBB_DIR=${NBB_DIR:-/Users/junkawasaki/github/kotoba-lang/amu-measure}
exec node --stack-size=${STACK_SIZE:-4096} "$NBB_DIR/node_modules/nbb/cli.js" --classpath "$HERE/src:$HERE/test" "$HERE/test/run.cljs"
