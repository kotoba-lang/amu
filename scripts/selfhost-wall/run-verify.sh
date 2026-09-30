#!/bin/zsh
# Runs verify-definition-identity.cljs with the stack it needs (the KIR interpreter nests host frames).
# Env: KROOTS (source roots), FILES, SYNTH, STACK (default 30000), NBB (path to nbb/cli.js).
ulimit -s 65500 2>/dev/null
here=${0:A:h}
NBB=${NBB:-${here}/../../node_modules/nbb/cli.js}
exec node --stack-size=${STACK:-30000} $NBB --classpath "${CLASSPATH_EXTRA:-}:${here}/../../src" $here/verify-definition-identity.cljs
