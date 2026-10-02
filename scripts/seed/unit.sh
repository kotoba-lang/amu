#!/bin/zsh
# scripts/seed/unit.sh <mod> [--update] -- unit test of one seed module, compiled by STAGE-0 (bootstrap-reference),
# run by the C loader (tools/kexe_loader.c, command mode). BOOTSTRAP-TOOL.
#
#   <mod> = a MANIFEST file stem, e.g. 00-ns, 10-lex.
#   Assembles build/seed/unit/<mod>/unit.kotoba =
#       seed/00-ns.kotoba
#     + the base modules seed/01-mem.kotoba seed/02-io.kotoba that come BEFORE <mod> in MANIFEST (if they exist)
#     + the modules named on the test's first `;; deps: a b ...` line, in MANIFEST order (must precede <mod>)
#     + seed/<mod>.kotoba            (skipped for 00-ns, which is already first)
#     + seed/tests/unit/<mod>_t.kotoba   (defines `(defn- seed-main [] :i64 ...)`)
#   compiles it with stage-0 (at most 2 stage-0 compiles machine-wide), runs `main` under the loader with guest
#   argv = <repo-root> <scratch-dir> (wire 38 "0", "1"), grant 35,37,38,39, wire-35 scope = the repo, and compares
#       stdout + one final line "exit=<status>"
#   with seed/tests/unit/<mod>.expected. stderr goes to build/seed/unit/<mod>/stderr (shown on failure).
#   --update writes the observed output to the .expected file instead of comparing (review the diff!).
#
# Exit: 0 pass, 1 fail (diff or stage-0 refusal, printed), 2 setup error.
# Test-writing contract: the test prints on stdout with (typed-cap-call :io/write :string :string s); every line
# ends with "\n"; seed-main's return value is the exit status (0 = the test's own checks passed). Tests may
# include `t-` helpers; they follow the same rules as modules (seed/MEMORY-MAP :rules).
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
mod=$1; update=0; [ "$2" = "--update" ] && update=1
[ -n "$mod" ] || { echo "usage: unit.sh <mod> [--update]" >&2; exit 2; }
R=$SEED_REPO
test=$R/seed/tests/unit/${mod}_t.kotoba
exp=$R/seed/tests/unit/${mod}.expected
[ -f $test ] || { echo "unit: no test $test" >&2; exit 2; }
seed_manifest | grep -qx "seed/$mod.kotoba" || { echo "unit: $mod is not in seed/MANIFEST" >&2; exit 2; }

W=$SEED_BUILD/unit/$mod; rm -rf $W; mkdir -p $W/scratch
deps=(${=$(sed -n '1,10{s/^;; *deps: *//p;}' $test | head -1)})
parts=($R/seed/00-ns.kotoba)
seen_mod=0
for p in $(seed_manifest); do
  stem=$(basename $p .kotoba)
  if [ $stem = $mod ]; then seen_mod=1; break; fi
  [ $stem = 00-ns ] && continue
  if [ $stem = 01-mem ] || [ $stem = 02-io ] || (( ${deps[(Ie)$stem]} )); then
    if [ -f $R/$p ]; then parts+=($R/$p); else echo "unit: warning: $p does not exist yet, skipped" >&2; fi
  fi
done
for d in $deps; do
  seed_manifest | grep -qx "seed/$d.kotoba" || { echo "unit: deps names unknown module $d" >&2; exit 2; }
  (( ${parts[(I)*/seed/$d.kotoba]} )) || { echo "unit: dep $d must exist and precede $mod in MANIFEST" >&2; exit 2; }
done
[ $mod = 00-ns ] || { [ -f $R/seed/$mod.kotoba ] || { echo "unit: seed/$mod.kotoba missing" >&2; exit 2; }; parts+=($R/seed/$mod.kotoba); }
parts+=($test)
: > $W/unit.kotoba
for p in $parts; do cat $p >> $W/unit.kotoba; printf '\n' >> $W/unit.kotoba; done
print -l -- ${parts#$R/} > $W/parts.txt

t0=$(date +%s)
# ---- R1 (agent R1, 2026-10-02): SEED_UNIT_SEED=<seed.bin> builds the unit with that seed (offset from <seed>.offset)
# instead of stage-0. Needed from rung 1 on: modules written in the R1 language (41-a64gen, 30-lower) are compiled
# only by an R1 seed; stage-0 stays the default for the R0-language modules.
if [ -n "${SEED_UNIT_SEED:-}" ]; then
  sb=${SEED_UNIT_SEED:A}
  if ! { seed_run $sb $(cat ${sb%.bin}.offset) compile ${W:A}/unit.kotoba --target aarch64-macos --output ${W:A}/unit.kseed > $W/unit.log 2>&1 \
         && seed_run $sb $(cat ${sb%.bin}.offset) extract-native ${W:A}/unit.kseed --symbol main --output ${W:A}/unit.bin >> $W/unit.log 2>&1; }; then
    echo "unit $mod: FAIL (seed ${sb:t} refused the unit build)"; head -3 $W/unit.log; exit 1
  fi
  sed -n 's/.*:offset \([0-9]*\).*/\1/p' $W/unit.log | tail -1 > $W/unit.offset
elif ! seed_stage0_build $W/unit.kotoba $W/unit; then
# ---- end R1 block
  echo "unit $mod: FAIL (stage-0 refused the unit build; parts: $(tr '\n' ' ' < $W/parts.txt))"
  grep -o ':message "[^"]*"' $W/unit.log | head -3
  exit 1
fi
t1=$(date +%s)
( cd $W; seed_run $W/unit.bin $(cat $W/unit.offset) $R $W/scratch > $W/stdout 2> $W/stderr; echo "exit=$?" >> $W/stdout )
t2=$(date +%s)
if [ $update -eq 1 ]; then cp $W/stdout $exp; echo "unit $mod: UPDATED $exp ($(wc -l < $exp | tr -d ' ') lines)"; exit 0; fi
[ -f $exp ] || { echo "unit $mod: FAIL (no $exp; run with --update after checking $W/stdout)"; exit 1; }
if diff -u $exp $W/stdout > $W/diff; then
  echo "unit $mod: PASS ($(wc -l < $exp | tr -d ' ') lines; ${SEED_UNIT_SEED:+seed }${${SEED_UNIT_SEED:-stage-0}:t} $((t1-t0)) s, run $((t2-t1)) s)"
  exit 0
fi
echo "unit $mod: FAIL (diff below; stderr: $W/stderr)"
head -40 $W/diff
head -5 $W/stderr
exit 1
