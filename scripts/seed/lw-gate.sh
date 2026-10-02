#!/bin/zsh
# scripts/seed/lw-gate.sh [unit|ports|corpus|all] -- the 30-lower early correctness gate. BOOTSTRAP-TOOL (zsh).
# Owner: 30-lower.
#
# Builds ONE test binary with stage-0 (bootstrap-reference) from
#     seed/00-ns + seed/10-lex + seed/11-read + seed/20-names + seed/21-check + seed/30-lower
#     + seed/tests/unit/30-lower_t.kotoba
# (LW_CHECK=0: without 21-check, using the stand-in checker seed/tests/unit/30-lower-stubck.kotoba)
# (01-mem/02-io are not needed by these modules; the test carries its own heap init), then runs it under the C
# loader, one process per program (M cannot be reset cheaply):
#   unit    seed/tests/unit/30-lower-in.kotoba, stdout compared with seed/tests/unit/30-lower.expected
#           (SIR dump golden + interpreter results); `unit --update` rewrites the golden
#   ports   bench/embench/ports/*.kotoba (19): every arity-0 export (test-*) must give 1 with status 0
#   corpus  seed/tests/corpus/*.kotoba: the result must equal stage-0's (30-lower-corpus.oracle)
# The gate is the SIR INTERPRETER (lw-interp in 30-lower): no backend is involved.
#
# LW_NOANDOR=1 (default while the stable stage-0 is used): every part is passed through scripts/seed/lw_noandor.py
# first, because the stable stage-0 answers 'internal compiler error' on any and/or/not (CONTRACT-REQUESTS.md).
# Set LW_NOANDOR=0 once stage-0 is rebuilt.
# LW_FRONT=ref (default until 10-lex/11-read build under stage-0; LW_FRONT=real uses them): no 10-lex/11-read; the token/node/literal tables come from the Python reference lexer/reader
# (scripts/seed/lw_tables.py over scripts/seed/lexread_ref.py) via seed/tests/unit/30-lower-refload.kotoba.
# LW_PUT=1 (default): the frontend modules' `vector-assoc!` go through one trivially linear `lwg-put` (the stable
# stage-0's whole-module linearity proof otherwise refuses them; seed/CONTRACT-REQUESTS.md, 30-lower line).
# Both rewrites change only how the TEST binary is built, never the seed sources.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
R=$SEED_REPO
what=${1:-all}; update=0; [ "$2" = "--update" ] && update=1
W=$SEED_BUILD/lw-gate; mkdir -p $W/scratch
front=${LW_FRONT:-ref}
if [ $front = ref ]; then mods=(00-ns 20-names); else mods=(00-ns 10-lex 11-read 20-names); fi
[ "${LW_CHECK:-1}" = 1 ] && mods+=(21-check)
mods+=(30-lower)
: > $W/unit.kotoba
for m in $mods; do
  f=$R/seed/$m.kotoba
  [ -f $f ] || { echo "lw-gate: missing $f" >&2; exit 2; }
  put=""; case $m in 10-lex|11-read|20-names|21-check) [ "${LW_PUT:-1}" = 1 ] && put=--put;; esac
  if [ "${LW_NOANDOR:-1}" = 1 ]; then python3 $R/scripts/seed/lw_noandor.py $f $put >> $W/unit.kotoba || exit 2
  else cat $f >> $W/unit.kotoba; fi
  printf '\n' >> $W/unit.kotoba
  [ $m = 00-ns ] && [ "${LW_PUT:-1}" = 1 ] && echo '(defn- lwg-put [V :vector-i64 i :i64 x :i64] :vector-i64 (vector-assoc! V i x))' >> $W/unit.kotoba
done
T=$R/seed/tests/unit/30-lower_t.kotoba
if [ "${LW_CHECK:-1}" != 1 ]; then  # stand-in checker instead of 21-check
  sed 's/(ck-run M3 S)/(t-ck M3 1)/' $T > $W/test.kotoba; cat $R/seed/tests/unit/30-lower-stubck.kotoba >> $W/test.kotoba
else cp $T $W/test.kotoba; fi
if [ $front = ref ]; then  # reference lexer/reader tables instead of 10-lex/11-read
  sed -i '' 's/(lx-run M0 S)/(t-rl-load M0 S)/; s/(rd-run M1 S)/(t-rl-root M1 S)/' $W/test.kotoba
  cat $R/seed/tests/unit/30-lower-refload.kotoba >> $W/test.kotoba
fi
if [ "${LW_NOANDOR:-1}" = 1 ]; then python3 $R/scripts/seed/lw_noandor.py $W/test.kotoba >> $W/unit.kotoba
else cat $W/test.kotoba >> $W/unit.kotoba; fi

if [ ! -f $W/unit.bin ] || ! cmp -s $W/unit.kotoba $W/unit.built.kotoba; then
  t0=$(date +%s)
  if ! seed_stage0_build $W/unit.kotoba $W/unit; then
    echo "lw-gate: FAIL (stage-0 refused the test build)"; grep -o ':message "[^"]*"' $W/unit.log | head -3; exit 1
  fi
  cp $W/unit.kotoba $W/unit.built.kotoba
  echo "lw-gate: stage-0 build $(( $(date +%s) - t0 )) s, $(wc -l < $W/unit.kotoba | tr -d ' ') lines"
fi
OFF=$(cat $W/unit.offset)

# run1 <repo-relative program> [dump] -> stdout in $W/out/<stem>.out, returns the guest status
run1() {
  local stem=$(basename $1 .kotoba)
  mkdir -p $W/out
  mkdir -p $W/tables; python3 $R/scripts/seed/lw_tables.py $R/$1 $W/tables/$stem.txt
  ( cd $W; seed_run $W/unit.bin $OFF $R $W/scratch $1 ${2:--} $W/tables/$stem.txt > $W/out/$stem.out 2> $W/out/$stem.err; echo "exit=$?" >> $W/out/$stem.out )
}

fail=0
if [ $what = unit ] || [ $what = all ]; then
  run1 seed/tests/unit/30-lower-in.kotoba dump
  exp=$R/seed/tests/unit/30-lower.expected
  if [ $update = 1 ]; then cp $W/out/30-lower-in.out $exp; echo "lw-gate unit: UPDATED $exp"
  elif diff -u $exp $W/out/30-lower-in.out > $W/unit.diff; then echo "lw-gate unit: PASS ($(wc -l < $exp | tr -d ' ') lines)"
  else echo "lw-gate unit: FAIL"; head -30 $W/unit.diff; fail=1; fi
fi
gate() {  # gate <label> <files...>
  local label=$1; shift
  local n=0 ok=0 p rel line
  for p in $@; do
    n=$((n+1)); rel=${p#$R/}
    local t0=$(date +%s)
    run1 $rel
    local dt=$(( $(date +%s) - t0 ))
    if grep -q '^not-1 0$' $W/out/$(basename $p .kotoba).out && grep -q '^exit=0$' $W/out/$(basename $p .kotoba).out; then
      ok=$((ok+1)); line="ok  "
    else line="BAD "; fail=1; fi
    echo "$line $rel ${dt}s $(grep ' = ' $W/out/$(basename $p .kotoba).out | grep -v '^run ' | tr '\n' ';' | cut -c1-160) $(grep -h 'error' $W/out/$(basename $p .kotoba).out | head -1)"
  done
  echo "lw-gate $label: $ok/$n"
}
if [ $what = ports ] || [ $what = all ]; then gate ports $R/bench/embench/ports/*.kotoba; fi
# corpus: the interpreter's result must equal stage-0's (seed/tests/unit/30-lower-corpus.oracle, made by
# scripts/seed/lw-corpus-oracle.sh); a front-end refusal is counted separately (21-check's business, not lowering's)
corpus() {
  local O=$R/seed/tests/unit/30-lower-corpus.oracle n=0 ok=0 fe=0 p stem want got
  for p in $R/seed/tests/corpus/*.kotoba; do
    n=$((n+1)); stem=${p:t:r}
    run1 ${p#$R/}
    want=$(grep "^$stem " $O | cut -d' ' -f2)
    if grep -q 'error E' $W/out/$stem.out; then fe=$((fe+1)); echo "front $stem stage-0=$want seed: $(grep -h 'error E' $W/out/$stem.out)"; continue; fi
    got=$(grep ' = ' $W/out/$stem.out | head -1 | awk '{print ($5 == "0") ? $3 : "trap"}')
    if [ "$got" = "$want" ]; then ok=$((ok+1)); else fail=1; echo "BAD   $stem stage-0=$want interp=$got"; fi
  done
  echo "lw-gate corpus: $ok/$n equal to stage-0, $fe refused by the front end"
}
if [ $what = corpus ] || [ $what = all ]; then corpus; fi
exit $fail
