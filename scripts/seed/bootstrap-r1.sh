#!/bin/zsh
# scripts/seed/bootstrap-r1.sh [r0-seed.bin] -- the rung-1 bootstrap chain. BOOTSTRAP-TOOL (zsh), owner R1.
#
# From R1 on the seed source is written in the R1 language (case, ->, when, records ...) and the stable stage-0 refuses
# the unity source ("EDN value contains too many nodes"), so the chain starts from the R0 seed binary, not stage-0:
#
#   a  R0 seed (fe2c20ae..., packaged R0 fixed point; arg 1, default build/seed-r1/base/seed-r0.bin)
#        compiles the unity source of commit R1_BRIDGE (69b32c614: R1 features + 12-kirread, all written in the R0
#        language)                                                   -> $B/bridge/seed-1.bin (expected 0f6497a3...)
#   b  that bridge seed compiles the CURRENT unity (seed/MANIFEST, R1 language)
#                                                                    -> $B/seed-1.bin
#   c  seed-1 compiles the current unity -> seed-2, seed-2 -> seed-3; FIXED POINT iff seed-1 == seed-2 == seed-3.
#
# $B (SEED_BUILD, default <repo>/build/seed-r1) then holds seed-0.bin (= the bridge seed, the previous-language compiler of
# this rung), seed-1.bin, seed-2.bin, so the gates run on it unchanged:
#   SEED_BUILD=<abs $B> zsh scripts/seed/gates.sh --rung r1 --no-build
# Only the C loader and the seed run here (no stage-0, node, JVM or nbb).
emulate -L zsh
setopt pipefail
export SEED_BUILD=${SEED_BUILD:-$(cd "$(dirname "$0")/../.." && pwd)/build/seed-r1}
source "$(dirname "$0")/lib.sh"
R=$SEED_REPO; B=${SEED_BUILD:A}; S=$R/scripts/seed
R1_BRIDGE=${R1_BRIDGE:-69b32c614}
r0=${1:-$R/build/seed-r1/base/seed-r0.bin}
sha() { shasum -a 256 $1 | cut -c1-64; }
[ -s $r0 ] && [ -s ${r0%.bin}.offset ] || { echo "bootstrap-r1: no R0 seed at $r0 (+ .offset)" >&2; exit 2; }
echo "bootstrap-r1: R0 seed $r0 sha256 $(sha $r0)"

# a: bridge
BB=$B/bridge; mkdir -p $BB
cp $r0 $BB/seed-0.bin; cp ${r0%.bin}.offset $BB/seed-0.offset
: > $BB/seed-unity.kotoba
for p in $(seed_manifest); do git -C $R show $R1_BRIDGE:$p >> $BB/seed-unity.kotoba || exit 1; printf '\n' >> $BB/seed-unity.kotoba; done
sha $BB/seed-unity.kotoba > $BB/seed-unity.kotoba.sha256
SEED_BUILD=$BB zsh $S/build.sh 1 || exit 1
echo "bootstrap-r1: bridge (unity of $R1_BRIDGE, $(wc -l < $BB/seed-unity.kotoba | tr -d ' ') lines) sha256 $(sha $BB/seed-1.bin)"

# b, c: current unity
cp $BB/seed-1.bin $B/seed-0.bin; cp $BB/seed-1.offset $B/seed-0.offset
SEED_BUILD=$B zsh $S/build.sh unity || exit 1
for n in 1 2 3; do SEED_BUILD=$B zsh $S/build.sh $n || exit 1; done
if cmp -s $B/seed-1.bin $B/seed-2.bin && cmp -s $B/seed-2.bin $B/seed-3.bin && cmp -s $B/seed-1.offset $B/seed-2.offset; then
  echo "bootstrap-r1: FIXED POINT seed-1 == seed-2 == seed-3 sha256 $(sha $B/seed-1.bin) ($(wc -c < $B/seed-1.bin | tr -d ' ') bytes)"
else
  echo "bootstrap-r1: NOT a fixed point"; cmp $B/seed-1.bin $B/seed-2.bin | head -1; cmp $B/seed-2.bin $B/seed-3.bin | head -1; exit 1
fi
