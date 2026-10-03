#!/bin/zsh
# scripts/seed/unit-all.sh [seed.bin] [mod ...] -- run the unit test of every seed module (seed/tests/unit/<mod>_t.kotoba) with the unit
# built by the GIVEN seed (default build/seed/seed-1.bin: the CURRENT rung's self-built compiler, via SEED_UNIT_SEED of unit.sh) and
# print one row per module (PASS/FAIL, seconds). BOOTSTRAP-TOOL (zsh), owner HOUSE2. After the loader is built only the seed runs.
# Exit 0 iff every module passed. Logs: $SEED_BUILD/unit/<mod>/ (unit.sh) and $SEED_BUILD/unit-all.log.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
sb=${1:-$SEED_BUILD/seed-1.bin}; [ $# -gt 0 ] && shift
[ -s $sb ] && [ -s ${sb%.bin}.offset ] || { echo "unit-all: no seed at $sb" >&2; exit 2; }
mods=($@)
if [ ${#mods} -eq 0 ]; then for p in $(seed_manifest); do m=${${p:t}%.kotoba}; [ -f $SEED_REPO/seed/tests/unit/${m}_t.kotoba ] && mods+=($m); done; fi
export SEED_UNIT_SEED=${sb:A}
: > $SEED_BUILD/unit-all.log; pass=0; fail=0
now() { perl -MTime::HiRes=time -e 'printf "%.1f", time'; }
for m in $mods; do
  t0=$(now); out=$(zsh $SEED_REPO/scripts/seed/unit.sh $m 2>&1); rc=$?; t1=$(now)
  echo "$out" >> $SEED_BUILD/unit-all.log
  if [ $rc -eq 0 ]; then pass=$((pass+1)); st=PASS; else fail=$((fail+1)); st=FAIL; fi
  printf '%-12s %s %6.1fs  %s\n' $m $st $((t1-t0)) "$(echo "$out" | head -1 | cut -c1-140)"
done
echo "unit-all: $pass passed, $fail failed of ${#mods} modules (seed ${sb:t} sha256 $(shasum -a 256 $sb | cut -c1-16), load $(sysctl -n vm.loadavg | awk '{print $2}'))"
[ $fail -eq 0 ]
