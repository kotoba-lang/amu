#!/bin/sh
# End-to-end check of `amu refactor` through the launcher (bin/amu -> nbb), on a scratch copy of a fixture.
# The unit tests (test/kotoba/compiler/refactor*_test.cljk) run in run-tests.cljk; this proves the routing,
# the path resolution of the launcher, the exit codes and that the source tree is never touched by plan / --check.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"
AMU="$HERE/bin/amu"
W="$(mktemp -d)"; trap 'rm -rf "$W"' EXIT
cp "$HERE/test/fixtures/refactor/equiv.cljk" "$W/equiv.cljk"
fail=0
check() { # <label> <expected-exit> <command...>
  label=$1; want=$2; shift 2
  out=$("$@" 2>"$W/err"); got=$?
  if [ "$got" = "$want" ]; then echo "ok   $label"; else echo "FAIL $label: exit $got, wanted $want"; head -c 400 "$W/err"; fail=1; fi
  printf '%s' "$out" > "$W/out"
}
has() { grep -q -- "$1" "$W/out" && echo "ok   $2" || { echo "FAIL $2"; fail=1; }; }
cd "$W"
check "list-rules" 0 "$AMU" refactor list-rules;                      has ":format :kotoba.refactor/v1" "format tag"
before=$(cksum < equiv.cljk)
check "plan (relative path)" 0 "$AMU" refactor plan all equiv.cljk;   has ":changed true" "plan sees changes"
[ "$before" = "$(cksum < equiv.cljk)" ] && echo "ok   plan wrote nothing" || { echo "FAIL plan wrote"; fail=1; }
check "apply --check (pending)" 1 "$AMU" refactor apply all equiv.cljk --check; has ":ok false" "check is red while pending"
check "apply" 0 "$AMU" refactor apply all equiv.cljk;                 has ":written 1" "one file written"
check "apply --check (clean)" 0 "$AMU" refactor apply all equiv.cljk --check; has ":ok true" "check is green after apply"
check "graph --summary" 0 "$AMU" refactor graph equiv.cljk --summary; has ":source-forms" "graph"
check "unknown rule" 64 "$AMU" refactor plan zz equiv.cljk;           grep -q ":refactor/unknown-rule" "$W/err" && echo "ok   stable code" || { echo "FAIL code"; fail=1; }
check "missing file" 65 "$AMU" refactor plan a nope.cljk
exit $fail
