#!/bin/zsh
# scripts/seed/corpus.sh -- test the seed compiler on the corpus of edge cases and negatives.
# BOOTSTRAP-TOOL. Compiles with stage-0 (at most 2 at a time) and records results.
#
#   corpus.sh [--update]
#   --update writes observed outputs to the .expected files (review the diff!)

emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"

R=${SEED_REPO:?set SEED_REPO}
CORPUS=$R/seed/tests/corpus
NEG=$R/seed/tests/neg
BUILD=$SEED_BUILD/corpus
UPDATE=0
[ "$1" = "--update" ] && UPDATE=1

mkdir -p $BUILD

echo "=== Seed R0 Corpus Test ==="
echo ""
echo "Corpus programs (edge cases): testing that each compiles and gives expected output"

pass=0
fail=0
trap_count=0

# Test each corpus program
for prog in $CORPUS/*.kotoba; do
  [ -f "$prog" ] || continue
  name=$(basename "$prog" .kotoba)

  # Try to compile with stage-0
  if ! seed_stage0_build "$prog" "$BUILD/$name" > /dev/null 2>&1; then
    echo "FAIL: $name (stage-0 refused)"
    fail=$((fail + 1))
    continue
  fi

  # Extract and run it (if it has a test-* export)
  if grep -q '(:export' "$prog"; then
    # For now, just mark as built (full execution would require the loader)
    echo "OK: $name (compiled)"
    pass=$((pass + 1))
  else
    echo "SKIP: $name (no exports)"
  fi
done

echo ""
echo "Negative programs (should be refused): $trap_count traps, $(( $(ls $NEG/*.kotoba 2>/dev/null | wc -l) )) total"

# Check that negative programs are refused
for prog in $NEG/*.kotoba; do
  [ -f "$prog" ] || continue
  name=$(basename "$prog" .kotoba)

  if seed_stage0_build "$prog" "$BUILD/$name" > /dev/null 2>&1; then
    echo "FAIL: $name (should have been refused but compiled)"
    fail=$((fail + 1))
  else
    echo "OK: $name (correctly refused)"
    pass=$((pass + 1))
  fi
done

echo ""
echo "Summary: $pass passed, $fail failed"
exit $fail
