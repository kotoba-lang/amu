#!/bin/zsh
# Differential caching: the HOST side of a differential (the golden outputs) is stored once per
# (function CID, case-set CID); a rerun compares the Kotoba side only.
#
#   golden-cache.sh key <name> <module[:module...]> <case-input|@literal>...   print the golden key
#   golden-cache.sh get <key> <dest>      copy the stored golden output to <dest>; exit 0 on a valid hit, 1 on a miss
#   golden-cache.sh put <key> <src>       store <src> as the golden output of <key>
#
# function CID  = wall_cache's key of the host function's module(s): their bytes, their transitive require
#                 closure and the checker/classpath identity (see wall_cache.cljk, `G` lines).
# case-set CID  = sha256 of the bytes of every case-input file (directories recurse) and of the @literal
#                 parameters (e.g. @DS_MAX=300), so editing a test program or a limit is a new case set.
# The key, the record digest and the validation are the pure Kotoba module's; this script reads and writes files.
# Same env as scan-cached.sh (WALL_CP, WALL_K, WALL_AMU_SRC, WALL_PLAN); WALL_GOLDEN_DIR (default
# $HOME/.cache/kotoba-wall-cache/golden).
export LC_ALL=C
here=$(cd "$(dirname "$0")" && pwd)
AMU=${WALL_AMU_ROOT:-$(cd "$here/../.." && pwd)}
K=${WALL_K:?set WALL_K}; CPF=${WALL_CP:?set WALL_CP}; CP=$(cat $CPF)
AMU_SRC=${WALL_AMU_SRC:-$AMU/src}
CHECK=${WALL_CHECK:-$here/check-one.sh}
GOLD=${WALL_GOLDEN_DIR:-$HOME/.cache/kotoba-wall-cache/golden}
umask 077; mkdir -p $GOLD; chmod 700 $GOLD 2>/dev/null
work=$(mktemp -d ${TMPDIR:-/tmp}/wall-golden.XXXXXX); trap 'rm -rf $work' EXIT
. $here/wall-cache-lib.sh
cmd=$1; shift
case $cmd in
key)
  name=$1; mods=$2; shift 2
  echo "${(j:\n:)${(s.:.)mods}}" > $work/mods.txt
  wc_graph $work/mods.txt
  for c in "$@"; do
    case $c in @*) echo "literal ${c#@}" | sha | sed "s/^/literal\t/";;
      *) if [ -d $c ]; then find $c -type f ! -name '.*' | sort | xargs shasum -a 256 2>/dev/null; else shasum -a 256 $c; fi | awk '{print $2 "\t" $1}';; esac
  done | sort | sha > $work/case.cid
  { printf 'H\t%s\t%s\n' $cpid $chk; cat $work/nodes.plan
    printf 'G\t%s\t%s\t%s\n' $name "${(j:;:)${(s.:.)mods}}" $(cat $work/case.cid); } | plan | awk -F'\t' '$1=="Q"{print $3}'
  ;;
get)
  key=$1; dest=$2; rec=$GOLD/$key
  [ -f $rec ] && [ -f $rec.out ] && [ ! -L $rec ] && [ ! -L $rec.out ] || exit 1
  IFS=$'\t' read -r fmt rk psha dg < $rec
  [ "$fmt" = kotoba.wall-golden/v1 ] && [ "$rk" = "$key" ] && [ "$(sha < $rec.out)" = "$psha" ] || { echo "golden-cache: rejected $key" >&2; rm -f $rec $rec.out; exit 1; }
  r=$(printf 'R\t%s\t%s\t%s\n' $key $psha $dg | plan | awk -F'\t' '$1=="V"{print $3}')
  [ "$r" = ok ] || { echo "golden-cache: rejected $key (digest)" >&2; rm -f $rec $rec.out; exit 1; }
  cp $rec.out $dest
  ;;
put)
  key=$1; src=$2; psha=$(sha < $src)
  dg=$(printf 'S\t%s\t%s\n' $key $psha | plan | awk -F'\t' '$1=="D"{print $3}')
  [ -n "$dg" ] || exit 2
  cp $src $work/out.tmp && mv $work/out.tmp $GOLD/$key.out
  printf 'kotoba.wall-golden/v1\t%s\t%s\t%s\n' $key $psha $dg > $work/rec.tmp && mv $work/rec.tmp $GOLD/$key
  ;;
*) echo "usage: golden-cache.sh key|get|put ..." >&2; exit 64;;
esac
