#!/bin/zsh
# seed/tests/kir/writesep/run.sh [seed.bin] -- KIR5: the seed writes containers and code slices whose bytes hold the loader's
# own wire-35 tokens (02-io io-write-bytes in pieces). For each ws*.kotoba (string literals spelling the WRITE and APPEND
# tokens, alone, repeated, adjacent, at the start/end of a literal): compile --output <file> must succeed and equal the hex
# route (--output -, xxd -r -p); extract-native main must succeed; the extracted main runs under the loader. PASS/FAIL per
# program, exit 1 on any FAIL. Before KIR5 the file route trapped (SIGILL) on all four.
emulate -L zsh
H=${0:A:h}; R=${H:h:h:h:h}
export SEED_BUILD=${SEED_BUILD:-$R/build/seed}
source $R/scripts/seed/lib.sh
S=${1:-$SEED_BUILD/seed-1.bin}; S=${S:A}; off=$(cat ${S%.bin}.offset)
W=$SEED_BUILD/writesep; mkdir -p $W; W=${W:A}
export SEED_RESOURCES_35=$W
fail=0
for f in $H/ws*.kotoba; do
  b=${f:t:r}; cp $f $W/$b.kotoba
  r1=$(seed_run $S $off compile $W/$b.kotoba --output $W/$b.kseed 2>&1 | head -1)
  seed_run $S $off compile $W/$b.kotoba --output - 2>/dev/null | xxd -r -p > $W/$b.hex.kseed
  r2=$(seed_run $S $off extract-native $W/$b.kseed --symbol main --output $W/$b.bin 2>&1 | head -1)
  o=$(echo "$r2" | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  v=FAIL
  if [[ $r1 == *":ok true"* ]] && cmp -s $W/$b.kseed $W/$b.hex.kseed && [ -n "$o" ]; then
    seed_run $W/$b.bin $o > $W/$b.out 2>&1; rc=$?
    v="PASS exit=$rc"
  fi
  [[ $v == PASS* ]] || fail=1
  echo "$b $v ${r1[1,60]}"
done
exit $fail
