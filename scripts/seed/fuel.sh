#!/bin/zsh
# scripts/seed/fuel.sh [seed.bin [offset]] -- fuel accounting check (design T5): for each of the 19 Embench ports the fuel
# CONSUMED by the stage-0 build and by the seed build, measured by kexe-benchmark (`raw <bin> <off> aarch64 0 1 0 <fuel>`,
# contextFuelConsumed), and the MINIMAL PASSING FUEL of each (the run with fuel = consumed must return 1, the run with
# consumed-1 must not). Prints a table and the ratio seed/stage-0; writes build/seed/fuel.tsv. BOOTSTRAP-TOOL (zsh), owner GATES.
# Exit 0 iff for every port seed minimal fuel <= stage-0 minimal fuel (T5: "the seed's minimal fuel no greater"); the
# per-port table also reports when the seed charges MORE than stage-0 (over-charge), which is the FF-FUEL question.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
bin=${1:-$SEED_BUILD/seed-1.bin}; off=${2:-$(cat ${bin%.bin}.offset)}
R=$SEED_REPO; W=$SEED_BUILD/fuel; mkdir -p $W
P=${SEED_PORTS:-$R/bench/embench/ports}
KB=$SEED_BUILD/kexe-benchmark
[ -x $KB ] || cc -O2 -std=c11 $R/bench/runtime-comparison/kexe-benchmark.c -o $KB -ldl || exit 2
echo '{:allow #{}}' > $W/pol.edn
export SEED_RESOURCES_35=$R:$W
bench() { $KB raw $1 $2 aarch64 0 1 0 $3 2>/dev/null | sed -n 's/.*"result":\(-*[0-9]*\).*"contextFuelConsumed":\([0-9]*\).*/\1 \2/p'; }
: > $W/fuel.tsv; bad=0; over=0; tot0=0; tot1=0
printf '%-16s %12s %12s %8s  %s\n' port stage-0 seed ratio minimal-fuel-check
for f in $P/*.kotoba; do
  p=${f:t:r}; sym=$(sed -n '1s/.*:export \[[^]]*\(test-[a-z0-9-]*\).*/\1/p' $f)
  seed_slot_take
  ( ulimit -s 65500; nice $SEED_STAGE0 compile $f --target aarch64-macos --jvm-free --policy $W/pol.edn --output $W/$p.s0.kexe > $W/$p.s0.log 2>&1 )
  x=$(nice $SEED_STAGE0 extract-native $W/$p.s0.kexe --symbol $sym --output $W/$p.s0.bin 2>&1)
  seed_slot_give
  o0=$(echo "$x" | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  seed_run $bin $off compile $f $W/$p.sd.kseed > /dev/null 2> $W/$p.sd.err || { echo "$p: seed refused"; bad=1; continue; }
  x=$(zsh $R/scripts/seed/seed-cc.sh extract $W/$p.sd.kseed $sym $W/$p.sd.bin); o1=$(echo "$x" | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  r0=($(bench $W/$p.s0.bin $o0 16777216)); r1=($(bench $W/$p.sd.bin $o1 16777216))
  f0=${r0[2]}; f1=${r1[2]}
  # minimal passing fuel: consumed passes, consumed-1 fails (exact for a straight-line fuel counter)
  m0=ok; m1=ok
  [ "$(bench $W/$p.s0.bin $o0 $f0 | cut -d' ' -f1)" = 1 ] || m0=consumed-fails
  [ "$(bench $W/$p.s0.bin $o0 $((f0-1)) | cut -d' ' -f1)" = 1 ] && m0="$m0,minus1-passes"
  [ "$(bench $W/$p.sd.bin $o1 $f1 | cut -d' ' -f1)" = 1 ] || m1=consumed-fails
  [ "$(bench $W/$p.sd.bin $o1 $((f1-1)) | cut -d' ' -f1)" = 1 ] && m1="$m1,minus1-passes"
  [ "${r0[1]}" = 1 ] && [ "${r1[1]}" = 1 ] || { echo "$p: wrong result s0=${r0[1]} seed=${r1[1]}"; bad=1; }
  [ $f1 -le $f0 ] || over=$((over+1))
  tot0=$((tot0+f0)); tot1=$((tot1+f1))
  printf '%-16s %12d %12d %8.4f  stage-0:%s seed:%s%s\n' $p $f0 $f1 $((f1*1.0/f0)) $m0 $m1 "$([ $f1 -gt $f0 ] && echo '  OVER-CHARGE')"
  printf '%s\t%d\t%d\n' $p $f0 $f1 >> $W/fuel.tsv
done
cp $W/fuel.tsv $SEED_BUILD/fuel.tsv
# ---- probes: seed/tests/fuel/*.kotoba, one charging situation each (entry of a leaf / a wrapper / a recursive function,
# recur back-edges, nested loops, string and vector literals, runtime calls, vector-at over a constant table)
echo; printf '%-12s %10s %10s %6s\n' probe stage-0 seed delta
pover=0
for f in $R/seed/tests/fuel/*.kotoba; do
  p=${f:t:r}
  seed_slot_take
  ( ulimit -s 65500; nice $SEED_STAGE0 compile $f --target aarch64-macos --jvm-free --policy $W/pol.edn --output $W/pr-$p.s0.kexe > /dev/null 2>&1 )
  x=$(nice $SEED_STAGE0 extract-native $W/pr-$p.s0.kexe --symbol test --output $W/pr-$p.s0.bin 2>&1)
  seed_slot_give
  o0=$(echo "$x" | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  SEED_RESOURCES_35=$R:$W seed_run $bin $off compile $f $W/pr-$p.sd.kseed > /dev/null 2>&1 || { echo "$p: seed refused"; bad=1; continue; }
  x=$(zsh $R/scripts/seed/seed-cc.sh extract $W/pr-$p.sd.kseed test $W/pr-$p.sd.bin); o1=$(echo "$x" | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  r0=($(bench $W/pr-$p.s0.bin $o0 16777216)); r1=($(bench $W/pr-$p.sd.bin $o1 16777216))
  [ "${r0[1]}" = "${r1[1]}" ] || { echo "$p: results differ s0=${r0[1]} seed=${r1[1]}"; bad=1; }
  d=$((r1[2]-r0[2])); [ $d -gt 0 ] && pover=$((pover+1))
  printf '%-12s %10d %10d %+6d%s\n' $p ${r0[2]} ${r1[2]} $d "$([ $d -gt 0 ] && echo '  OVER-CHARGE')"
  printf 'probe/%s\t%d\t%d\n' $p ${r0[2]} ${r1[2]} >> $SEED_BUILD/fuel.tsv
done
over=$((over+pover))
printf '%-16s %12d %12d %8.4f\n' TOTAL $tot0 $tot1 $((tot1*1.0/tot0))
echo "fuel: seed charges more than stage-0 on $over ports/probes; seed total / stage-0 total = $(printf '%.4f' $((tot1*1.0/tot0)))"
[ $bad -eq 0 ] && [ $over -eq 0 ]
