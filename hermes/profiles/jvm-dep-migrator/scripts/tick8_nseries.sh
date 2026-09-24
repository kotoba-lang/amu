#!/bin/bash
# re-check n-series passes with correct parse (tick8)
cd /tmp/amu-tick8 || exit 1
for f in n1 n2 n5; do
  out=$(bin/amu check --jvm-free /tmp/q9probe2/$f.kotoba 2>&1 | head -1)
  case "$out" in
    "{:ok true"*) echo "PASS $f" ;;
    *) echo "FAIL $f: $(echo "$out" | grep -o 'kotoba.error/[a-z-]*' | head -1)" ;;
  esac
done
