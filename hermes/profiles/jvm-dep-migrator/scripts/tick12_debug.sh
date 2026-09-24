#!/bin/bash
# tick12 debug: dump raw check output for known-pass probes
cd ~/github/com-junkawasaki/orgs/kotoba-lang/amu || exit 1
out=/tmp/q9debug.txt
: > "$out"
for f in p06-string-lit p13-reduce-bounded p16-typed-map p17-string-compare p18-fold-case p01-cond p02-cond-macro c2-bitor c5-bitor-const; do
  echo "=== $f ===" >> "$out"
  bin/amu check --jvm-free "/tmp/q9probe3/$f.kotoba" 2>&1 | tail -3 >> "$out"
  echo "exit=$?" >> "$out"
done
echo DONE >> "$out"
