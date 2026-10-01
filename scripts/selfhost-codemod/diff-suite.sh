#!/bin/sh
# Differential check of a rewrite on the host route: run kotoba-sema's suite (run-tests.cljk on nbb) twice -- once with the
# original frontend.cljk, once with the rewritten copy first on the classpath -- and compare per-test outcomes.
#   diff-suite.sh <rewritten-src-root> [workdir]
# <rewritten-src-root> holds kotoba/compiler/frontend.cljk (a copy; the real tree is never touched).
# Env: WALL_CP (classpath file), K_SEMA (kotoba-sema checkout), NBB_DIR, AMU_SRC.
set -e
NEW=${1:?rewritten src root}
W=${2:-/tmp/codemod-diff}
mkdir -p "$W"
K_SEMA=${K_SEMA:-/Users/junkawasaki/github/kotoba-lang/kotoba-sema}
NBB_DIR=${NBB_DIR:-/Users/junkawasaki/github/kotoba-lang/amu-measure}
AMU_SRC=${AMU_SRC:-/private/tmp/wt-A-amu-measure/src}
CP_FILE=${WALL_CP:-/private/tmp/wall-cp-5.txt}
run() { # <first-src> <out>
  ( cd "$NBB_DIR"; ulimit -s 65520 2>/dev/null || true
    node --stack-size=${STACK:-56000} node_modules/nbb/cli.js \
      --classpath "$1:$AMU_SRC:$(cat "$CP_FILE"):$K_SEMA/test:$K_SEMA/resources" "$K_SEMA/run-tests.cljk" > "$2" 2>&1 || true )
}
norm() { # test outcomes without file paths, line numbers or stack frames
  grep -E '^(FAIL in|ERROR in|  expected:|nbb: )' "$1" | sed -E 's/:line [0-9]+/:line N/g; s/\(([^)]*_test\.cljk):[0-9]+\)/(\1)/'
  grep -E '^  actual:' "$1" | sed -E 's/.*(:message "[^"]*").*/actual \1/' | sed -E 's/^(.{0,200}).*/\1/'
}
[ -s "$W/base.txt" ] && [ -z "$REBASE" ] || run "$K_SEMA/src" "$W/base.txt"
run "$NEW" "$W/new.txt"
norm "$W/base.txt" | sort > "$W/base.norm"
norm "$W/new.txt" | sort > "$W/new.norm"
echo "baseline: $(grep '^nbb:' "$W/base.txt")"
echo "rewrite : $(grep '^nbb:' "$W/new.txt")"
if diff "$W/base.norm" "$W/new.norm" > "$W/outcome.diff"; then echo "IDENTICAL per-test outcomes ($(wc -l < "$W/base.norm") normalized lines)"; else echo "DIFFERENT:"; head -20 "$W/outcome.diff"; exit 1; fi
