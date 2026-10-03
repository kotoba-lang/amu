#!/bin/zsh
# analyze-memory.sh -- the analyze guest's memory per source byte on compiler-size inputs (H-M3/H-M4, agent MEM2, 2026-10-03;
# docs/selfhost-analyze-memory-20261003.md). One loader process per input file, arena marks per process.
#
#   analyze-memory.sh <work-dir> [file.kotoba ...]      (no files: the 19 Embench ports + the seed MANIFEST prefixes)
#
# The guest is the whole linked frontend (`an/analyze`) compiled by the seed backend: front-native.sh's e2e guest
# (AM_GUEST, default build/front/e2e.sd.bin, entry offset AM_OFFSET, default 2182856). Each input becomes one case line
# [:hir "<source>" nil]; with the expected answer nil the guest prints "DIFF guest <HIR>" when the analysis ran to the end,
# "DIFF guest refused: .." when the frontend refused, so the outcome column is HIR / REFUSED / TRAP.
# Env: AM_HC (KEXE_HASHCONS log2, default 16; 0 = off), AM_VECTORS (default 67108864 = the ADR 0364 ceiling), AM_PAIRS
# (default 67108864), AM_CENSUS=1 (KEXE_ARENA_CENSUS: print the census line too). Output: <work>/ladder.tsv
# bytes, file, outcome, vectors, pairs, vector-items, heap-bytes, rss-bytes, real-s, load1.
emulate -L zsh; setopt pipefail
HERE=${0:A:h}; R=${HERE:h:h}
W=${1:?usage: analyze-memory.sh <work-dir> [file ...]}; shift; mkdir -p $W; W=${W:A}
G=${AM_GUEST:-$R/build/front/e2e.sd.bin}; OFF=${AM_OFFSET:-2182856}
[ -s $G ] || { echo "analyze-memory: no guest $G (build it with front-native.sh <dir> e2e)" >&2; exit 2; }
L=$W/kexe-loader
if [ ! -x $L ] || [ $R/tools/kexe_loader.c -nt $L ]; then cc $R/tools/kexe_loader.c -std=c11 -O2 -o $L || exit 2; fi
if [ $# -eq 0 ]; then
  python3 $HERE/analyze-memory-inputs.py $R $W/in || exit 2
  set -- ${AM_PORTS:-/Users/junkawasaki/github/kotoba-lang/amu-embench/bench/embench/ports}/*.kotoba $W/in/pfx*.kotoba
fi
hc=(); [ "${AM_HC:-16}" != 0 ] && hc=(KEXE_HASHCONS=${AM_HC:-16})
cen=(); [ -n "$AM_CENSUS" ] && cen=(KEXE_ARENA_CENSUS=1)
printf 'bytes\tfile\toutcome\tvectors\tpairs\tvector-items\theap-bytes\trss-bytes\treal-s\tload1\n' > $W/ladder.tsv
for f in "$@"; do
  python3 -c "
import sys; s=open(sys.argv[1],encoding='utf-8').read()
print('[:hir \"%s\" nil]' % s.replace('\\\\','\\\\\\\\').replace('\"','\\\\\"').replace('\n','\\\\n').replace('\t','\\\\t').replace('\r','\\\\r'))" $f > $W/one.case
  load=$(sysctl -n vm.loadavg | awk '{print $2}')
  env KEXE_COMMAND=1 KEXE_ARENA_USE=1 KEXE_STRING_POOL=1073741824 KEXE_PAIRS=${AM_PAIRS:-67108864} \
      KEXE_VECTORS=${AM_VECTORS:-67108864} KEXE_VECTOR_ITEMS=134217728 KEXE_CPU_SECONDS=1800 KEXE_WALL_SECONDS=1800 $hc $cen \
      /usr/bin/time -l $L $G $OFF 0 aarch64 3,37,41 < $W/one.case > $W/one.out 2> $W/one.err
  o=$(head -c 24 $W/one.out)
  case $o in "DIFF guest refused"*) oc=REFUSED;; "DIFF guest {"*|OK*) oc=HIR;; *) oc=TRAP;; esac
  grep -q KEXE_TRAP $W/one.err && oc="TRAP$({ grep -o 'KEXE_TRAP.*:reason.*' $W/one.err || grep -o 'KEXE_TRAP.*' $W/one.err; } | head -1 | grep -o ':reason [^ }]*\|:arena [^ }]*\|:signal [^ }]*' | awk '{printf "%s", $2}')"
  m() { grep -o ":$1 [0-9]*" $W/one.err | head -1 | awk '{print $2}'; }
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' $(wc -c < $f | tr -d ' ') ${f:t} $oc $(m vectors) $(m pairs) $(m vector-items) \
    $(m heap-bytes) $(grep 'maximum resident' $W/one.err | awk '{print $1}') $(grep ' real' $W/one.err | awk '{print $1}') $load \
    | tee -a $W/ladder.tsv
  [ -n "$AM_CENSUS" ] && grep KEXE_ARENA_CENSUS $W/one.err
done
