#!/bin/sh
# The measured pipeline on a scratch copy of a source file; the real tree is never written.
#   pipeline.sh <frontend.cljk> <workdir> [test-dir-for-observable-names]
# 1. rules a,b,d,e,f -> <workdir>/s1/kotoba/compiler/frontend.cljk       (dual-style output: the host text is intact)
# 2. rule c (target host-env, in place, host-valid) on step 1's output -> <workdir>/s2/...
# 3. diff-suite.sh on s1 and on s2: kotoba-sema's suite per-test outcomes against the original.
# 4. rule c (target dual) report on step 1's output (the Kotoba-route shape; not run, listed).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC=${1:?frontend.cljk}; W=${2:?workdir}; TESTS=${3:-/Users/junkawasaki/github/kotoba-lang/kotoba-sema/test}
mkdir -p "$W/s1/kotoba/compiler" "$W/s2/kotoba/compiler"
echo "== 1. a,b,d,e,f"; "$HERE/codemod.sh" "$SRC" --rules a,b,d,e,f --out "$W/s1/kotoba/compiler/frontend.cljk" --report "$W/s1.rep" > "$W/s1.out"
echo "== 2. c (host-env)"; "$HERE/codemod.sh" "$W/s1/kotoba/compiler/frontend.cljk" --rules c --target host-env --observable-from "$TESTS" --out "$W/s2/kotoba/compiler/frontend.cljk" --report "$W/s2.rep" > "$W/s2.out"
echo "== 3a. suite on s1"; "$HERE/diff-suite.sh" "$W/s1" "$W/suite-s1"
echo "== 3b. suite on s2"; "$HERE/diff-suite.sh" "$W/s2" "$W/suite-s2"
echo "== 4. c (dual) report"; "$HERE/codemod.sh" "$W/s1/kotoba/compiler/frontend.cljk" --rules c --target dual --observable-from "$TESTS" --dry-run --report "$W/dual.rep" > "$W/dual.out"
