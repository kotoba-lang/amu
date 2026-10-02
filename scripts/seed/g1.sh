#!/bin/zsh
# scripts/seed/g1.sh [seed.bin [offset]] -- gate G1: the seed compiles each Embench port; its test-* export must return 1
# under BOTH runners: the C loader (tools/kexe_loader.c, arity 0) and kexe-benchmark (bench/runtime-comparison, the
# qualification runner: `raw <bin> <off> aarch64 0 1 0 16777216`, i.e. fuel 16M and its fixed arena of 4096 vectors,
# 65536 vector items, 2M pairs). BOOTSTRAP-TOOL (zsh). Default compiler:
# build/seed/seed-0.bin. Ports: $SEED_PORTS (default the amu-embench checkout next to this repo's owner).
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
bin=${1:-$SEED_BUILD/seed-0.bin}; off=${2:-$(cat ${bin%.bin}.offset)}
P=${SEED_PORTS:-/Users/junkawasaki/github/kotoba-lang/amu-embench/bench/embench/ports}
W=$SEED_BUILD/g1; mkdir -p $W
L=$(seed_loader) || exit 2
KB=$SEED_BUILD/kexe-benchmark
if [ ! -x $KB ] || [ $SEED_REPO/bench/runtime-comparison/kexe-benchmark.c -nt $KB ]; then
  cc -O2 -std=c11 $SEED_REPO/bench/runtime-comparison/kexe-benchmark.c -o $KB || exit 2
fi
pass=0; fail=0
for f in $P/*.kotoba; do
  p=${f:t:r}
  sym=$(sed -n '1s/.*:export \[[^]]*\(test-[a-z0-9-]*\).*/\1/p' $f)
  t0=$(perl -MTime::HiRes=time -e 'printf "%.3f", time')
  if ! zsh $SEED_REPO/scripts/seed/seed-cc.sh compile $bin $off $f $W/$p.kseed 2> $W/$p.err; then
    echo "$p\tCOMPILE-FAIL\t$(head -1 $W/$p.err)"; fail=$((fail+1)); continue; fi
  t1=$(perl -MTime::HiRes=time -e 'printf "%.3f", time')
  x=$(zsh $SEED_REPO/scripts/seed/seed-cc.sh extract $W/$p.kseed $sym $W/$p.bin) || { echo "$p\tEXTRACT-FAIL\t$x"; fail=$((fail+1)); continue; }
  o=$(echo "$x" | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  r=$(cd $W; $L $W/$p.bin $o 0 aarch64 - 2> $W/$p.run.err | tail -1); st=$?
  t2=$(perl -MTime::HiRes=time -e 'printf "%.3f", time')
  j=$($KB raw $W/$p.bin $o aarch64 0 1 0 16777216 2> $W/$p.bench.err); echo "$j" > $W/$p.bench.json
  rb=$(echo "$j" | sed -n 's/.*"result":\(-*[0-9]*\).*/\1/p'); fu=$(echo "$j" | sed -n 's/.*"contextFuelConsumed":\([0-9]*\).*/\1/p')
  if [ "$r" = 1 ] && [ "$rb" = 1 ]; then v=PASS; pass=$((pass+1)); else v=FAIL; fail=$((fail+1)); fi
  printf "%s\t%s\tloader=%s bench=%s fuel=%s\tcompile %.3fs run %.3fs code %d bytes\t%s\n" $p $v "$r" "$rb" "$fu" $((t1-t0)) $((t2-t1)) $(wc -c < $W/$p.bin) "$(cat $W/$p.run.err $W/$p.bench.err | head -c 120 | tr '\n' ' ')"
done
echo "G1: $pass pass, $fail fail (compiler $bin, sha256 $(shasum -a 256 $bin | cut -c1-16))"
[ $fail -eq 0 ]
