#!/bin/zsh
# seed/tests/kir/census.sh [seed.bin [offset]] -- KIR coverage census (agent KIR; BOOTSTRAP-TOOL, zsh + python3).
#
# For every program of the corpora below:
#   1. STAGE-0 (bootstrap-reference, build/native-image/amu-native) compiles it to a kexe (cached by source sha256 in
#      $W/kexe), the KIR (:program) is cut out (scripts/seed/kir_extract.py);
#   2. census.py hist -> $W/hist.tsv: operation histogram over all KIR bodies (which shapes stage-0 emits);
#   3. the seed compiles the KIR (`compile-kir`) and the SOURCE (`compile`); for every exported arity-0 function with an
#      :i64/:bool result the three codes (stage-0's own extract-native, seed via KIR, seed via source) are run under the
#      C loader and compared. One tsv line per program in $W/programs.tsv:
#        group/name  stage0(ok|FAIL)  kir(ok|E<code>..)  src(ok|E..)  exports-run  kir-equal  src-equal  first-kir-error
#   4. summary: programs and runnable exports compiled via compile-kir with results equal to stage-0's.
# Env: SEED_BUILD (default build/seed-r1), CENSUS_DIRS (override the corpus list), CENSUS_JOBS (default 3 parallel
#      programs; stage-0 itself is bounded machine-wide by lib.sh's 2 slots).
emulate -L zsh
setopt pipefail nullglob
export SEED_BUILD=${SEED_BUILD:-$(cd "$(dirname "$0")/../../.." && pwd)/build/seed-r1}
source "$(dirname "$0")/../../../scripts/seed/lib.sh"
bin=${1:-$SEED_BUILD/seed-1.bin}; off=${2:-$(cat ${bin%.bin}.offset)}
bin=${bin:A}
R=$SEED_REPO
W=$R/build/seed-kir/census; mkdir -p $W/kexe $W/run
L=$(seed_loader) || exit 2
E=/Users/junkawasaki/github/kotoba-lang/amu-embench/bench/embench/ports
dirs=(${=CENSUS_DIRS:-$E $R/seed/tests/r1/feat $R/seed/tests/r1/conf $R/seed/tests/corpus $R/resources/kotoba/lang-conformance/values $R/resources/kotoba/lang-conformance/control $R/resources/kotoba/lang-conformance/native $R/seed/tests/conformance/*(/) $R/examples $R/test/dual-backend $R/test/nbb/fixtures $R/test/nbb/fixtures/state $R/bench/runtime-comparison})
pol=$W/policy.edn; echo '{:allow #{[:cap/call 35] [:cap/call 37] [:cap/call 38] [:cap/call 39]}}' > $pol

grp() { local d=$1; d=${d#$R/}; d=${d#/Users/junkawasaki/github/kotoba-lang/amu-embench/bench/}; echo ${d//\//.}; }
xoff() { sed -n 's/.*:offset \([0-9]*\).*/\1/p'; }
seed() { SEED_RESOURCES_35=$W SEED_SECONDS=60 seed_run $bin $off "$@"; }
runb() {  # <bin> <off> -> last line (result or error)
  ( cd $W; KEXE_PAIRS=2097152 KEXE_VECTORS=65536 KEXE_VECTOR_ITEMS=1048576 KEXE_FUEL=16777216 KEXE_CPU_SECONDS=20 KEXE_WALL_SECONDS=20 \
    $L $1 $2 0 aarch64 - 2>&1 | tail -1 | tr '\t' ' ' | cut -c1-60 )
}

one() {  # <src> <group>
  local f=$1 g=$2 p=${1:t:r} id=$2.${1:t:r} h k r ex nr=0 ke=0 se=0 kv sv kerr="" kst src sst
  local D=$W/run/$id; rm -rf $D; mkdir -p $D
  h=$(shasum -a 256 $f | cut -c1-16); k=$W/kexe/$h.kexe
  if [ ! -f $k ] && [ ! -f $k.fail ]; then
    seed_slot_take
    r=$( ulimit -s 65500 2>/dev/null; cd ${f:h}; nice $SEED_STAGE0 compile $f --target aarch64-macos --jvm-free --policy $pol --output $k.tmp 2>&1 )
    seed_slot_give
    if echo "$r" | grep -q ':ok true'; then mv $k.tmp $k; else echo "$r" | head -3 > $k.fail; rm -f $k.tmp*; fi
  fi
  if [ ! -f $k ]; then printf "%s\tFAIL\t-\t-\t0\t0\t0\t%s\n" $id "$(head -1 $k.fail | tr '\t' ' ' | cut -c1-120)" > $D/line; return; fi
  python3 $R/scripts/seed/kir_extract.py $k $D/p.kir 2>/dev/null || { printf "%s\tNOPROG\t-\t-\t0\t0\t0\t-\n" $id > $D/line; return; }
  cp $f $D/p.kotoba
  if seed compile-kir $D/p.kir --output $D/k.kseed > $D/k.log 2>&1; then kst=ok; else kst=$(grep -o 'E[0-9][0-9]*' $D/k.log | head -1); kst=${kst:-ERR}; kerr=$(head -1 $D/k.log | tr '\t' ' ' | cut -c1-140); fi
  if seed compile $D/p.kotoba --output $D/s.kseed > $D/s.log 2>&1; then sst=ok; else sst=$(grep -o 'E[0-9][0-9]*' $D/s.log | head -1); sst=${sst:-ERR}; fi
  ex=($(python3 $R/seed/tests/kir/census.py info $D/p.kir 2>/dev/null))
  local s t r0 rk rs o
  for e in $ex; do
    s=${e%%:*} t=${e#*:} r0="" rk="" rs="" o=""
    case $t in i64|bool) ;; *) continue;; esac
    o=$( ulimit -s 65500 2>/dev/null; nice $SEED_STAGE0 extract-native $k --symbol $s --output $D/0.$s.bin 2>&1 | xoff )
    [ -n "$o" ] || continue
    nr=$((nr+1)); r0=$(runb $D/0.$s.bin $o)
    if [ $kst = ok ]; then o=$(seed extract-native $D/k.kseed --symbol $s --output $D/k.$s.bin | xoff); rk=$(runb $D/k.$s.bin $o); [ "$rk" = "$r0" ] && ke=$((ke+1)); fi
    if [ $sst = ok ]; then o=$(seed extract-native $D/s.kseed --symbol $s --output $D/s.$s.bin | xoff); rs=$(runb $D/s.$s.bin $o); [ "$rs" = "$r0" ] && se=$((se+1)); fi
    echo "$s stage0=[$r0] kir=[$rk] src=[$rs]" >> $D/results
  done
  printf "%s\tok\t%s\t%s\t%d\t%d\t%d\t%s\n" $id $kst $sst $nr $ke $se "$kerr" > $D/line
}

jobs_n=${CENSUS_JOBS:-3}
for d in $dirs; do
  g=$(grp $d)
  for f in $d/*.kotoba; do
    while [ $(jobs -r | wc -l) -ge $jobs_n ]; do sleep 0.2; done
    one ${f:A} $g &
  done
done
wait
cat $W/run/*/line(N) | sort > $W/programs.tsv
python3 $R/seed/tests/kir/census.py hist $W/hist.tsv $W/run/*/p.kir(N)
awk -F'\t' '
  { n++; if ($2=="ok") { s0++; if ($3=="ok") k++; if ($4=="ok") s++; ex+=$5; ke+=$6; se+=$7;
      if ($5>0) { rp++; if ($6==$5 && $3=="ok") kp++; if ($7==$5 && $4=="ok") sp++ } } }
  END { printf "census: %d programs, stage-0 compiles %d; compile-kir accepts %d (%.1f%%), seed source route %d (%.1f%%)\n", n, s0, k, 100*k/s0, s, 100*s/s0;
        printf "census: %d programs with runnable i64/bool exports (%d exports): all equal to stage-0 via KIR %d (%.1f%%), via source %d (%.1f%%); exports equal via KIR %d, via source %d\n", rp, ex, kp, 100*kp/rp, sp, 100*sp/rp, ke, se }' $W/programs.tsv | tee $W/summary.txt
echo "compiler $bin sha256 $(shasum -a 256 $bin | cut -c1-16)" >> $W/summary.txt
