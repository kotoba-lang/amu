#!/bin/zsh
# scripts/seed/r6-diff.sh [seed.bin] [ns ..] -- the per-module R6 differential (design 1.4 row R6; agent R6C, 2026-10-03).
# BOOTSTRAP-TOOL (zsh + scripts/seed/r6_diff.py). Run after scripts/seed/r6-scan.sh (same SEED_BUILD): for every module the
# SEED compiled from source in the scan, a generated driver project (r6_diff.py gen: one arity-0 export per case, each calling
# one export of the module on fixed arguments and folding the result into an i64) is compiled
#   (a) by the seed:    seed compile main.kotoba --source-path <scan farm> --unpinned --output d.kseed   (the project route:
#                       the module and its requires compiled from source, linked into one image)
#   (b) by STAGE-0:     amu-native compile main.kotoba --source-path <scan farm> --unpinned --target aarch64-macos (BOOTSTRAP-
#                       REFERENCE, at most 2 machine-wide, nice), code read with r6_diff.py offsets (kexe_code.py's reading)
# and every case runs under the C loader (no capability granted, 20 s CPU) on both images. A case AGREES when both answer the
# same value or both trap (same loader budgets, wire 3 granted to both). Per module: AGREE n/n, DIFF (cases differ), S0-REFUSED (stage-0 does not compile the driver
# natively: its message), SEED-REFUSED (the seed refuses the driver: a driver/interface defect), NOCASE (no export has a
# signature the driver can call). Output: $SEED_BUILD/r6diff/r6-diff.tsv (ns, verdict, agree, cases, skipped, detail),
# per-case values in $SEED_BUILD/r6diff/<ns>/values.tsv, the load average at start and end.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
R=$SEED_REPO; B=${SEED_BUILD:A}; S=$B/r6; W=${R6DIFF_DIR:-$B/r6diff}   # R6DIFF_DIR: another output directory (a partial run)
bin=${1:-$B/seed-1.bin}; [ -f "$bin" ] && shift || bin=$B/seed-1.bin
bin=${bin:A}; off=$(cat ${bin%.bin}.offset 2>/dev/null || echo 0)
[ -f $S/r6-scan.tsv ] || { echo "r6-diff: run scripts/seed/r6-scan.sh first ($S/r6-scan.tsv)" >&2; exit 2; }
L=$(seed_loader) || exit 2; L=${L:A}
rm -rf $W; mkdir -p $W
cp $bin $W/compiler.bin; bin=$W/compiler.bin   # a private copy: a rebuild of seed-1 during the run must not change the compiler
python3 $R/scripts/seed/r6_diff.py gen $S $W "$@" > $W/gen.txt || { echo "r6-diff: gen failed" >&2; exit 2; }
# stage-0's compile-time policy admits the capabilities the scanned modules name; at run time only wire 3 is granted to both
echo '{:allow #{[:cap/call :hash/sha256] [:cap/call :fs/app-data] [:cap/call :fs/browse] [:cap/call :process/spawn]}}' > $W/pol.edn
export SEED_RESOURCES_35=$R:$S:$W
load0=$(uptime | sed 's/.*averages: //')
print -r -- "# r6-diff $(date '+%F %T') seed $(shasum -a 256 $bin | cut -c1-16) stage-0 $(shasum -a 256 $SEED_STAGE0 | cut -c1-16) load $load0" > $W/r6-diff.tsv
# run <code.bin> <offset> -> value, or "trap"
# Both images run with the same loader budgets (seed_run's: the defaults are small and stage-0's code allocates more vectors)
# and the same grant: wire 3 (:hash/sha256), the only capability a scanned module calls without an argument from the driver.
run1() {
  local v
  v=$(cd $W; KEXE_STRING_POOL=268435456 KEXE_PAIRS=4194304 KEXE_VECTORS=65536 KEXE_VECTOR_ITEMS=16777216 \
      KEXE_CPU_SECONDS=20 KEXE_WALL_SECONDS=20 $L $1 $2 0 aarch64 3 2>/dev/null | tail -1)
  [ $? -eq 0 ] && [ -n "$v" ] && echo $v || echo trap
}
while read -r ns ncase nskip; do
  d=$W/$ns
  if [ $ncase -eq 0 ]; then printf '%s\tNOCASE\t0\t0\t%s\t-\n' $ns $nskip >> $W/r6-diff.tsv; continue; fi
  r=$(seed_run $bin $off compile $d/main.kotoba --source-path $S/src --unpinned --output $d/seed.kseed 2>&1)
  if [ ! -s $d/seed.kseed ]; then
    printf '%s\tSEED-REFUSED\t0\t%s\t%s\t%s\n' $ns $ncase $nskip "$(print -r -- "$r" | grep -m1 'seed:' | cut -c1-200)" >> $W/r6-diff.tsv; continue
  fi
  seed_slot_take
  r=$( ulimit -s 65500; cd $d; nice $SEED_STAGE0 compile $d/main.kotoba --source-path $S/src --unpinned --target aarch64-macos --jvm-free --policy $W/pol.edn --output $d/s0.kexe 2>&1 )
  seed_slot_give
  if ! print -r -- "$r" | grep -q ':ok true'; then
    printf '%s\tS0-REFUSED\t0\t%s\t%s\t%s\n' $ns $ncase $nskip "$(print -r -- "$r" | grep -o ':message "\([^"\\]\|\\.\)*"' | head -1 | cut -c11-210)" >> $W/r6-diff.tsv; continue
  fi
  python3 $R/scripts/seed/r6_diff.py offsets kseed $d/seed.kseed $d/seed.bin > $d/seed.off
  python3 $R/scripts/seed/r6_diff.py offsets kexe $d/s0.kexe $d/s0.bin > $d/s0.off
  agree=0; n=0; first=""
  : > $d/values.tsv
  for k in $(seq 0 $((ncase - 1))); do
    o1=$(awk -v s=c$k '$1==s {print $2}' $d/seed.off); o2=$(awk -v s=c$k '$1==s {print $2}' $d/s0.off)
    v1=$([ -n "$o1" ] && run1 $d/seed.bin $o1 || echo noexport); v2=$([ -n "$o2" ] && run1 $d/s0.bin $o2 || echo noexport)
    n=$((n+1)); printf 'c%s\t%s\t%s\t%s\n' $k $v1 $v2 "$(awk -F'\t' -v s=c$k '$1==s {print $3}' $d/cases.tsv)" >> $d/values.tsv
    if [ "$v1" = "$v2" ] && [ "$v1" != noexport ]; then agree=$((agree+1)); else [ -n "$first" ] || first="c$k seed $v1 stage-0 $v2: $(awk -F'\t' -v s=c$k '$1==s {print $3}' $d/cases.tsv | cut -c1-120)"; fi
  done
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' $ns $([ $agree -eq $n ] && echo AGREE || echo DIFF) $agree $n $nskip "${first:--}" >> $W/r6-diff.tsv
done < $W/gen.txt
print -r -- "# load at end $(uptime | sed 's/.*averages: //')" >> $W/r6-diff.tsv
awk -F'\t' '!/^#/ {v[$2]++; if ($2=="AGREE"||$2=="DIFF") {a+=$3; c+=$4}} END {printf "r6-diff: modules"; for (k in v) printf " %s %d", k, v[k]; printf "; cases %d/%d agree\n", a, c}' $W/r6-diff.tsv
