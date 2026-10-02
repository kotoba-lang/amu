#!/bin/zsh
# scripts/seed/lw-corpus-oracle.sh -- STAGE-0 results of seed/tests/corpus/*.kotoba for the 30-lower gate.
# BOOTSTRAP-TOOL (owner 30-lower). For every corpus program: stage-0 (bootstrap-reference) compiles it, extracts its
# exported test-* function and runs it under the C loader (tools/kexe_loader.c, arity 0). Writes
# seed/tests/unit/30-lower-corpus.oracle, one line per program: `<stem> <result>` | `<stem> trap` | `<stem> refused`.
# lw-gate.sh corpus compares the SIR interpreter's result with this line (trap = any non-zero interpreter status).
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
R=$SEED_REPO; W=$SEED_BUILD/lw-oracle; mkdir -p $W
echo '{:allow #{}}' > $W/pol.edn
L=$(seed_loader) || exit 2
out=$R/seed/tests/unit/30-lower-corpus.oracle
: > $out.tmp
for p in $R/seed/tests/corpus/*.kotoba; do
  stem=${p:t:r}
  sym=$(sed -n 's/.*(:export \[\([^] ]*\).*/\1/p' $p | head -1)
  seed_slot_take
  r=$( ulimit -s 65500; nice $SEED_STAGE0 compile $p --target aarch64-macos --jvm-free --policy $W/pol.edn --output $W/$stem.kexe 2>&1 )
  if echo "$r" | grep -q ':ok true'; then
    r=$( nice $SEED_STAGE0 extract-native $W/$stem.kexe --symbol $sym --output $W/$stem.bin 2>&1 )
  fi
  seed_slot_give
  if ! echo "$r" | grep -q ':ok true'; then echo "$stem refused" >> $out.tmp; echo "$stem refused $(echo $r | grep -o ':message "[^"]*"')"; continue; fi
  off=$(echo "$r" | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  v=$($L $W/$stem.bin $off 0 aarch64 - 2>/dev/null); rc=$?
  if [ $rc -eq 0 ]; then echo "$stem $v" >> $out.tmp; else echo "$stem trap" >> $out.tmp; fi
done
mv $out.tmp $out
echo "lw-corpus-oracle: $(wc -l < $out | tr -d ' ') programs, $(grep -c refused $out) refused, $(grep -c trap $out) trap"
