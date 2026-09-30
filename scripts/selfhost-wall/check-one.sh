#!/bin/zsh
# Selfhost wall harness, one source: prints "<file>\tOK" or the first `amu check` refusal.
# Env: WALL_CP (classpath file, see make-classpath.py), WALL_AMU_SRC (this repo's src),
#      WALL_K (kotoba-lang checkout holding lang/compat and the grant policy).
f=$1
AMU=${WALL_AMU_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}
K=${WALL_K:?set WALL_K to the kotoba-lang checkout}
CP=$(cat ${WALL_CP:?set WALL_CP})
SP="$(echo "$CP" | tr ':' '\n' | grep '/src$' | sed 's/^/--source-path /' | tr '\n' ' ') --source-path ${WALL_AMU_SRC:-$AMU/src} --source-path $K/lang/compat"
cd $AMU
r=$(node --stack-size=4096 node_modules/nbb/cli.js --classpath "$CP" src/kotoba/compiler/nbb/wasm_cli.cljk check $f --policy $K/lang/selfhost-compiler-grant.edn ${=SP} 2>&1)
if echo "$r" | grep -q ':ok true\|:format :kotoba.check/v1'; then m="OK"; else m=$(echo "$r" | grep -o ':message "[^"]*' | head -1 | cut -c11-170); fi
printf "%s\t%s\n" "$f" "$m"
