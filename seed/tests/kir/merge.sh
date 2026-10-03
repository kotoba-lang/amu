#!/bin/zsh
# seed/tests/kir/merge.sh <guest.cljk> <input-file> [label] -- the merge test (agent KIR3; BOOTSTRAP-TOOL, zsh + python3).
#
# One piece of the BIG compiler, wrapped by a guest whose arity-0 `main` reads the file named by argument 0
# (:cli/args "0", :fs/app-data) and writes its answer (:io/write), is
#   1. compiled by STAGE-0 (bootstrap-reference, build/native-image/amu-native, `compile --unpinned --target aarch64-macos`
#      with the wall classpath as source paths) to a kexe/v1 -> its KIR (:program) is cut out (scripts/seed/kir_extract.py);
#   2. the KIR is compiled by the SEED backend (`compile-kir`, under the C loader only);
#   3. both natives (stage-0's extract-native of `main`, the seed's extract-native of `main`) run under the C loader on the
#      same input; stdout bytes are compared.
# One tsv line on stdout:
#   label  kir-bytes  s0-compile-ms  s0-compile-rss-mb  seed-compile-ms  seed-compile-rss-mb  s0-code  seed-code
#   s0-run-ms  seed-run-ms  s0-run-rss-mb  seed-run-rss-mb  out-bytes  verdict(EQUAL|DIFF|SEED-REFUSED: ..|S0-REFUSED: ..)
#   s0-run-cpu-ms  seed-run-cpu-ms  load1
# (run ms = wall clock of the loader process, median of MERGE_RUNS; cpu ms = user + sys of the loader and its children
#  (/usr/bin/time -l; its "instructions retired" covers only the parent, not the forked runner, so it is not used);
#  rss = maximum resident set size; load1 = the 1-minute load average at the end)
# Env: SEED_BUILD (seed-1.bin of that dir is the compiler), WALL_CP (default /private/tmp/wall-cp-11.txt), WALL_K
#      (kotoba-lang checkout), MERGE_W (work dir, default $SEED_BUILD/merge), MERGE_RUNS (runs per side, default 3; the
#      median is reported), MERGE_GRANT (default 35,37,38,39).
emulate -L zsh
setopt pipefail
export SEED_BUILD=${SEED_BUILD:-$(cd "$(dirname "$0")/../../.." && pwd)/build/seed-kir3}
source "$(dirname "$0")/../../../scripts/seed/lib.sh"
R=$SEED_REPO
g=${1:A}; inp=${2:A}; lab=${3:-${1:t:r}}
W=${MERGE_W:-$SEED_BUILD/merge}; mkdir -p $W
L=$(seed_loader) || exit 2
K=${WALL_K:-/Users/junkawasaki/github/kotoba-lang/kotoba-lang}
CP=$(cat ${WALL_CP:-/private/tmp/wall-cp-11.txt})
SP=(); for d in ${(f)"$(echo "$CP" | tr ':' '\n' | grep '^/.*/src$')"} $R/src $K/lang/compat; do SP+=(--source-path $d); done
pol=$W/policy.edn; echo '{:allow #{[:cap/call 35] [:cap/call 37] [:cap/call 38] [:cap/call 39]}}' > $pol
grant=${MERGE_GRANT:-35,37,38,39}
runs=${MERGE_RUNS:-3}

# /usr/bin/time -l output -> "ms rss-mb"
tm() { awk '/ real /{ms=$1*1000} /maximum resident/{rss=$1/1048576} / real /{cpu=($3+$5)*1000} END{printf "%d %.1f %d", ms, rss, cpu}' $1; }
med() { print -l $@ | sort -n | awk '{a[NR]=$1} END{print a[int((NR+1)/2)]}'; }
line() { local IFS=$'\t'; print -r -- "$*"; }

k=$W/$lab.kexe
seed_slot_take
( ulimit -s 65500 2>/dev/null; cd ${g:h}; /usr/bin/time -l nice $SEED_STAGE0 compile $g --unpinned --target aarch64-macos --jvm-free --policy $pol ${=SP} --output $k ) > $W/$lab.s0.log 2> $W/$lab.s0.time
seed_slot_give
grep -q ':ok true' $W/$lab.s0.log || { line $lab - - - - - - - - - - - - "S0-REFUSED: $(grep -o ':message "[^"]*' $W/$lab.s0.log | head -1 | cut -c11-150)"; exit 1; }
s0c=($(tm $W/$lab.s0.time)); s0c=($s0c[1,2])
python3 $R/scripts/seed/kir_extract.py $k $W/$lab.kir || exit 2
kb=$(wc -c < $W/$lab.kir | tr -d ' ')
( /usr/bin/time -l zsh -c "source $R/scripts/seed/lib.sh; SEED_SECONDS=300 seed_run $SEED_BUILD/seed-1.bin 0 compile-kir $W/$lab.kir --output $W/$lab.kseed" ) > $W/$lab.sd.log 2> $W/$lab.sd.time
sdc=($(tm $W/$lab.sd.time)); sdc=($sdc[1,2])
if ! grep -q ':ok true' $W/$lab.sd.log; then
  line $lab $kb $s0c $sdc - - - - - - - "SEED-REFUSED: $(cat $W/$lab.sd.log $W/$lab.sd.time | grep -m1 -E 'seed:|KEXE|error' | cut -c1-160)"; exit 1
fi
o0=$( ulimit -s 65500 2>/dev/null; nice $SEED_STAGE0 extract-native $k --symbol main --output $W/$lab.s0.bin 2>&1 | sed -n 's/.*:offset \([0-9]*\).*/\1/p' )
o1=$( seed_run $SEED_BUILD/seed-1.bin 0 extract-native $W/$lab.kseed --symbol main --output $W/$lab.sd.bin | sed -n 's/.*:offset \([0-9]*\).*/\1/p' )
[ -n "$o0" ] && [ -n "$o1" ] || { line $lab $kb $s0c $sdc - - - - - - - "EXTRACT-FAILED"; exit 1; }
run() {  # <bin> <off> <out> <time>
  ( cd ${inp:h}; /usr/bin/time -l env KEXE_COMMAND=1 KEXE_CAP_RESOURCES_35=${inp:h} KEXE_STRING_POOL=1073741824 KEXE_PAIRS=33554432 \
      KEXE_VECTORS=4194304 KEXE_VECTOR_ITEMS=134217728 KEXE_CPU_SECONDS=600 KEXE_WALL_SECONDS=600 \
      $L $1 $2 0 aarch64 $grant -- $inp ) > $3 2> $4
}
t0=(); t1=(); r0=(); r1=(); i0=(); i1=()
for i in $(seq 1 $runs); do
  run $W/$lab.s0.bin $o0 $W/$lab.s0.out $W/$lab.s0.rt; x=($(tm $W/$lab.s0.rt)); t0+=$x[1]; r0+=$x[2]; i0+=$x[3]
  run $W/$lab.sd.bin $o1 $W/$lab.sd.out $W/$lab.sd.rt; x=($(tm $W/$lab.sd.rt)); t1+=$x[1]; r1+=$x[2]; i1+=$x[3]
done
v=EQUAL; cmp -s $W/$lab.s0.out $W/$lab.sd.out || v="DIFF($(cmp $W/$lab.s0.out $W/$lab.sd.out 2>&1 | head -1 | cut -c1-80))"
grep -q KEXE_TRAP $W/$lab.s0.rt $W/$lab.sd.rt && v="$v TRAP($(grep -h -o 'KEXE_TRAP.*' $W/$lab.s0.rt $W/$lab.sd.rt | head -1 | cut -c1-60))"
line $lab $kb $s0c $sdc $(wc -c < $W/$lab.s0.bin | tr -d ' ') $(wc -c < $W/$lab.sd.bin | tr -d ' ') $(med $t0) $(med $t1) $(med $r0) $(med $r1) \
  "$(wc -c < $W/$lab.s0.out | tr -d ' ')" "$v" $(med $i0) $(med $i1) "$(sysctl -n vm.loadavg | awk '{print $2}')"
