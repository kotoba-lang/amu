#!/bin/zsh
# scripts/seed/g4.sh -- gate G4: fixed point (build.sh fixed-point: seed-1.bin == seed-2.bin) and seed-0 / seed-1 give
# byte-identical containers on every G1 port and G2 corpus program (g1.sh and g2.sh run with each compiler, each must
# pass by itself too). BOOTSTRAP-TOOL (zsh); after build.sh step 0 only the C loader, the seed, xxd and coreutils run.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
S=$SEED_REPO/scripts/seed; B=$SEED_BUILD; rc=0
zsh $S/build.sh fixed-point || exit 1
for c in seed-0 seed-1; do
  zsh $S/g1.sh $B/$c.bin | tail -1 || rc=1
  zsh $S/g2.sh $B/$c.bin | tail -1 || rc=1
done
s=0; d=0
for k in $B/g1-seed-0/*.kseed(N) $B/g2-seed-0/*.kseed(N); do
  o=${k/\/g1-seed-0\//\/g1-seed-1\/}; o=${o/\/g2-seed-0\//\/g2-seed-1\/}
  if cmp -s $k $o; then s=$((s+1)); else d=$((d+1)); echo "G4: DIFF ${k:t}"; fi
done
echo "G4: seed-0 vs seed-1 containers: $s identical, $d different; fixed point sha256 $(shasum -a 256 $B/seed-1.bin | cut -c1-64)"
[ $d -eq 0 ] && [ $rc -eq 0 ]
