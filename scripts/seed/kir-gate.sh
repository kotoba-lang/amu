#!/bin/zsh
# scripts/seed/kir-gate.sh [seed.bin [offset]] -- the KIR-consumer gate (design section 5.2; seed/12-kirread.kotoba).
# BOOTSTRAP-TOOL (zsh). For every Embench port:
#   1. STAGE-0 (bootstrap-reference) compiles the port: `amu-native compile <port> --target aarch64-macos --output p.kexe`;
#      the KIR text is the kexe's :program (stage-0 has no --emit-kir flag), cut out by scripts/seed/kir_extract.py -> p.kir.
#      KIR_KEXE_DIR=<dir> reuses <dir>/<port>/<port>.kexe instead (no stage-0 run).
#   2. the seed compiles the KIR: `seed compile-kir p.kir --output p.kir.kseed`, extracts test-* (seed extract-native),
#      and the code must return 1 under the C loader AND kexe-benchmark (fuel 16M), as in G1.
#   3. the seed also compiles the whole kexe (`compile-kir p.kexe`): the container must be byte-identical to step 2's.
#   4. the seed compiles the port SOURCE (the G1 path): fuel (kexe-benchmark contextFuelConsumed) and code bytes of the
#      KIR route are printed next to the source route's; the differences are explained in
#      docs/selfhost-seed-kirread-20261002.md.
#   5. seed/tests/kir/pos/*.kir (export t must return 1) and seed/tests/kir/neg/*.kir (refused): the observed lines must
#      equal seed/tests/kir/expected (KIR_UPDATE=1 rewrites it; review the diff).
# KIR_PORTS=0 skips steps 1-4.
# Default compiler: build/seed/seed-1.bin (it must have compile-kir, i.e. be built from a unity with 12-kirread).
# Exit 0 iff every port passes steps 2 and 3.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
bin=${1:-$SEED_BUILD/seed-1.bin}; off=${2:-$(cat ${bin%.bin}.offset)}
P=${SEED_PORTS:-/Users/junkawasaki/github/kotoba-lang/amu-embench/bench/embench/ports}
W=$SEED_BUILD/kir-gate-${bin:t:r}; rm -rf $W; mkdir -p $W
L=$(seed_loader) || exit 2
KB=$SEED_BUILD/kexe-benchmark
if [ ! -x $KB ] || [ $SEED_REPO/bench/runtime-comparison/kexe-benchmark.c -nt $KB ]; then
  cc -O2 -std=c11 $SEED_REPO/bench/runtime-comparison/kexe-benchmark.c -o $KB || exit 2
fi
pol=$W/stage0-policy.edn; echo '{:allow #{}}' > $pol

stage0_kexe() {  # <src> <out.kexe>
  if [ -n "$KIR_KEXE_DIR" ]; then cp $KIR_KEXE_DIR/${1:t:r}/${1:t:r}.kexe $2; return $?; fi
  seed_slot_take
  local r=$( ulimit -s 65500 2>/dev/null; nice $SEED_STAGE0 compile $1 --target aarch64-macos --jvm-free --policy $pol --output $2 2>&1 )
  seed_slot_give
  echo "$r" | grep -q ':ok true'
}
# run <bin> <offset> -> "loader-result bench-result fuel"
runit() {
  local r j rb fu
  r=$(cd $W; KEXE_PAIRS=2097152 KEXE_VECTORS=4096 KEXE_VECTOR_ITEMS=65536 KEXE_FUEL=16777216 KEXE_CPU_SECONDS=60 KEXE_WALL_SECONDS=60 $L $1 $2 0 aarch64 - 2>/dev/null | tail -1)
  j=$($KB raw $1 $2 aarch64 0 1 0 16777216 2>/dev/null)
  rb=$(echo "$j" | sed -n 's/.*"result":\(-*[0-9]*\).*/\1/p'); fu=$(echo "$j" | sed -n 's/.*"contextFuelConsumed":\([0-9]*\).*/\1/p')
  echo "${r:-?} ${rb:-?} ${fu:-?}"
}
# seed <args..>: the seed under test, wire-35 scope = W
seed() { SEED_RESOURCES_35=$W seed_run $bin $off "$@"; }
xoff() { sed -n 's/.*:offset \([0-9]*\).*/\1/p'; }

pass=0; fail=0; kb=0; ks=0; fk=0; fs=0
# ---- 5. small positive and negative KIR programs ----
T=$W/t; mkdir -p $T; cp -r $SEED_REPO/seed/tests/kir/pos $SEED_REPO/seed/tests/kir/neg $T/
for f in $T/pos/*.kir; do
  if seed compile-kir $f --output $f.kseed > /dev/null 2> $f.err; then
    o=$(seed extract-native $f.kseed --symbol t --output $f.bin | xoff)
    echo "pos/${f:t} -> $(KEXE_FUEL=1000000 $L $f.bin $o 0 aarch64 - 2>&1 | tail -1)"
  else echo "pos/${f:t} -> COMPILE-FAIL $(head -1 $f.err)"; fi
done > $W/tests.out
for f in $T/neg/*.kir; do e=$(seed compile-kir $f - 2>&1 > /dev/null); echo "neg/${f:t} rc=$? $e"; done >> $W/tests.out
if [ -n "$KIR_UPDATE" ]; then cp $W/tests.out $SEED_REPO/seed/tests/kir/expected; echo "KIR tests: UPDATED seed/tests/kir/expected"
elif diff -u $SEED_REPO/seed/tests/kir/expected $W/tests.out > $W/tests.diff; then echo "KIR tests: $(wc -l < $W/tests.out | tr -d ' ') pass"
else echo "KIR tests: FAIL"; cat $W/tests.diff; fail=$((fail+1)); fi
[ "${KIR_PORTS:-1}" = 0 ] && { [ $fail -eq 0 ]; exit $?; }
printf "port\tverdict\tKIR-route loader/bench\tfuel kir/src\tcode bytes kir/src\tcode kir vs src\tkir bytes\tkexe-input\n"; ident=0
for f in $P/*.kotoba; do
  p=${f:t:r}
  sym=$(sed -n '1s/.*:export \[[^]]*\(test-[a-z0-9-]*\).*/\1/p' $f)
  cp $f $W/$p.kotoba
  if ! stage0_kexe $W/$p.kotoba $W/$p.kexe; then echo "$p\tSTAGE0-FAIL"; fail=$((fail+1)); continue; fi
  python3 $SEED_REPO/scripts/seed/kir_extract.py $W/$p.kexe $W/$p.kir || { echo "$p\tNO-PROGRAM"; fail=$((fail+1)); continue; }
  if ! seed compile-kir $W/$p.kir --output $W/$p.kir.kseed > $W/$p.kir.log 2>&1; then
    echo "$p\tKIR-COMPILE-FAIL\t$(head -1 $W/$p.kir.log)"; fail=$((fail+1)); continue; fi
  o=$(seed extract-native $W/$p.kir.kseed --symbol $sym --output $W/$p.kir.bin | xoff)
  rk=($(runit $W/$p.kir.bin $o))
  seed compile-kir $W/$p.kexe --output $W/$p.kexe.kseed > $W/$p.kexe.log 2>&1
  if cmp -s $W/$p.kir.kseed $W/$p.kexe.kseed; then same=same; else same=DIFFERS; fi
  seed compile $W/$p.kotoba --output $W/$p.src.kseed > $W/$p.src.log 2>&1
  os=$(seed extract-native $W/$p.src.kseed --symbol $sym --output $W/$p.src.bin | xoff)
  rs=($(runit $W/$p.src.bin $os))
  if [ "$rk[1]" = 1 ] && [ "$rk[2]" = 1 ] && [ $same = same ]; then v=PASS; pass=$((pass+1)); else v=FAIL; fail=$((fail+1)); fi
  bk=$(wc -c < $W/$p.kir.bin | tr -d ' '); bs=$(wc -c < $W/$p.src.bin | tr -d ' ')
  kb=$((kb+bk)); ks=$((ks+bs)); fk=$((fk+${rk[3]:-0})); fs=$((fs+${rs[3]:-0}))
  if cmp -s $W/$p.kir.bin $W/$p.src.bin; then bi=identical; ident=$((ident+1)); else bi=differs; fi
  printf "%s\t%s\t%s/%s\t%s/%s\t%s/%s\t%s\t%s\t%s\n" $p $v $rk[1] $rk[2] $rk[3] $rs[3] $bk $bs $bi $(wc -c < $W/$p.kir | tr -d ' ') $same
done
echo "KIR gate: $pass pass, $fail fail; code bytes kir/src $kb/$ks ($ident byte-identical); fuel kir/src $fk/$fs (compiler $bin, sha256 $(shasum -a 256 $bin | cut -c1-16))"
[ $fail -eq 0 ]
