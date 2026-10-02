#!/bin/zsh
# scripts/seed/kir-stats.sh <seed.bin> <offset> <unity.kotoba> (kir|src):<file> ... -- memory census of the seed's compile
# pipeline (seed/tests/kir/kir-stats_t.kotoba). BOOTSTRAP-TOOL (zsh). The unity source minus its last file (99-entry)
# plus the stats program is compiled by <seed.bin>; each input is then compiled by that program under the C loader and
# one line of region fills is printed (see the stats program's header). Inputs must lie under $SEED_BUILD.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
bin=$1 off=$2 uni=$3; shift 3
W=$SEED_BUILD/kir-stats; mkdir -p $W
n=$(( $(wc -l < $SEED_REPO/seed/99-entry.kotoba) + 1 ))
t=$(wc -l < $uni)
awk -v k=$((t - n)) 'NR <= k' $uni > $W/stats.kotoba
cat $SEED_REPO/seed/tests/kir/kir-stats_t.kotoba >> $W/stats.kotoba
SEED_RESOURCES_35=$SEED_BUILD seed_run $bin $off compile ${W:A}/stats.kotoba --output ${W:A}/stats.kseed > $W/stats.log 2>&1 || { cat $W/stats.log; exit 1; }
SEED_RESOURCES_35=$SEED_BUILD seed_run $bin $off extract-native ${W:A}/stats.kseed --symbol main --output ${W:A}/stats.bin > $W/stats.x || exit 1
so=$(sed -n 's/.*:offset \([0-9]*\).*/\1/p' $W/stats.x)
for a in "$@"; do
  m=${a%%:*} f=${a#*:}
  printf "%s %s" $m ${f:t}
  SEED_RESOURCES_35=$SEED_BUILD seed_run $W/stats.bin $so $m ${f:A}
done
