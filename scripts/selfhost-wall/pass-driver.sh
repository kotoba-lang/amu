#!/bin/zsh
# pass-driver.sh: run a compiler pipeline as ONE LOADER PROCESS PER PASS (hypothesis H-M3, docs/selfhost-coscientist.md).
# BOOTSTRAP-TOOL (zsh + /usr/bin/time; the passes themselves are native aarch64 code run by tools/kexe_loader.c).
#
#   pass-driver.sh [-w workdir] [-l loader] [-k] <pass.bin> <input> <pass> [<pass> ...]
#
# <pass.bin> is a native image extracted from a kexe (its offset is read from <pass.bin minus .bin>.offset, or the env PASS_OFFSET);
# <input> is the first pass's input, one serialized Form per line (EDN text); each <pass> is a name the image dispatches on: the
# driver feeds the process "!<pass>\n" followed by the previous pass's output (the compact serialized Form state, a file), and the
# process exit reclaims every arena. Lines the pass answers with ERR/UNPORTED (a refused form) are counted and not passed on.
# The loader runs with KEXE_HASHCONS on by default (pair hash-consing, tools/kexe_loader.c; KEXE_HASHCONS=0 turns it off) and
# KEXE_ARENA_USE=1; the report lists, per pass, the arena high-water marks against the loader limits, peak RSS and user CPU.
#   -k   keep the work directory (default: kept; files NN-<pass>.in/.out/.err stay for inspection)
# Env: PASS_OFFSET, KEXE_HASHCONS (default 16 = 2^16 entries, 512 KiB), DRV_POOL/DRV_PAIRS/DRV_VECTORS/DRV_VECTOR_ITEMS (loader budgets,
#      defaults 1 GiB / 64M / 4M / 128M words = the loader maxima), DRV_SECONDS (cpu+wall, default 900), DRV_GRANT (3,37,41).
# Exit: 0 all passes ran; 1 a pass trapped (the trap line is printed); 2 usage.
HERE="$(cd "$(dirname "$0")" && pwd)"; AMU=${HERE:h:h}
work=; loader=
while getopts "w:l:k" o; do case $o in w) work=$OPTARG;; l) loader=$OPTARG;; k) ;; *) exit 2;; esac; done
shift $((OPTIND-1))
bin=${1:?usage: pass-driver.sh [-w dir] [-l loader] <pass.bin> <input> <pass>...}; input=${2:?input}; shift 2
[ $# -ge 1 ] || { echo "pass-driver: no pass named" >&2; exit 2; }
off=${PASS_OFFSET:-$(cat ${bin%.bin}.offset 2>/dev/null)}; [ -n "$off" ] || { echo "pass-driver: no offset (PASS_OFFSET or ${bin%.bin}.offset)" >&2; exit 2; }
[ -n "$work" ] || work=$(mktemp -d ${TMPDIR:-/tmp}/pass-driver.XXXXXX); mkdir -p $work
if [ -z "$loader" ]; then
  loader=$work/kexe-loader; cc $AMU/tools/kexe_loader.c -std=c11 -O2 -o $loader || exit 2
fi
: ${KEXE_HASHCONS:=16}
export KEXE_HASHCONS KEXE_ARENA_USE=1 KEXE_COMMAND=1
export KEXE_STRING_POOL=${DRV_POOL:-1073741824} KEXE_PAIRS=${DRV_PAIRS:-67108864} KEXE_VECTORS=${DRV_VECTORS:-4194304}
export KEXE_VECTOR_ITEMS=${DRV_VECTOR_ITEMS:-134217728} KEXE_CPU_SECONDS=${DRV_SECONDS:-900} KEXE_WALL_SECONDS=${DRV_SECONDS:-900}
prev=$input; n=0; rc=0
printf "%-10s %10s %10s %10s %10s %9s %8s %7s %8s %6s %6s\n" pass in-bytes out-bytes pairs vectors heap-MB rss-MB user-s pair% vec% dropped
for p in "$@"; do
  n=$((n+1)); nn=$(printf %02d $n); base=$work/$nn-${p#!}
  { echo "!${p#!}"; cat $prev; } > $base.in
  /usr/bin/time -l $loader $bin $off 0 aarch64 ${DRV_GRANT:-3,37,41} < $base.in > $base.raw 2> $base.err
  st=$?
  if [ $st -ne 0 ] || grep -q KEXE_TRAP $base.err; then
    echo "pass-driver: pass '$p' trapped (exit $st): $(grep -m1 KEXE_TRAP $base.err | cut -c1-200)"; rc=1; break
  fi
  grep -v '^ERR \|^UNPORTED ' $base.raw > $base.out
  dropped=$(( $(wc -l < $base.raw) - $(wc -l < $base.out) ))
  pairs=$(sed -n 's/.*:pairs \([0-9]*\).*/\1/p' $base.err | head -1); vecs=$(sed -n 's/.*:vectors \([0-9]*\).*/\1/p' $base.err | head -1)
  heap=$(sed -n 's/.*:heap-bytes \([0-9]*\).*/\1/p' $base.err | head -1)
  rss=$(awk '/maximum resident/ {print $1}' $base.err); user=$(awk '/ user / {print $3}' $base.err)
  printf "%-10s %10d %10d %10d %10d %9.1f %8.1f %7s %7.1f%% %5.1f%% %6d\n" $p $(( $(wc -c < $base.in) )) $(wc -c < $base.out) $pairs $vecs \
    $((heap/1048576.0)) $((rss/1048576.0)) $user $((pairs*100.0/${DRV_PAIRS:-67108864})) $((vecs*100.0/${DRV_VECTORS:-4194304})) $dropped
  prev=$base.out
done
echo "pass-driver: work=$work final=$prev hashcons=$KEXE_HASHCONS load=$(uptime | sed 's/.*averages: //')"
exit $rc
