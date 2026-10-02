#!/bin/zsh
# scripts/seed/seed-cc.sh -- run a seed compiler (raw code + offset of `main`) under the C loader. BOOTSTRAP-TOOL (zsh).
#
#   seed-cc.sh compile <seed.bin> <seed-offset> <src.kotoba> <out.kseed>
#       the seed compiles <src> (hex container on stdout, the stable stage-0 output path), `xxd -r -p` -> <out.kseed>
#   seed-cc.sh extract <out.kseed> <symbol> <out.bin>
#       writes the code slice of the kseed/v1 container and prints "{:ok true :symbol S :offset N :arity A}".
#       Done here (head/tail) until the seed can read a binary container itself (02-io has no byte reader yet).
# Only the loader, the seed guest, xxd, head, tail, wc and sed run: no node/JVM/nbb.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
case $1 in
  compile)
    local bin=$2 off=$3 src=${4:A} out=$5
    SEED_RESOURCES_35=${SEED_RESOURCES_35:-${src:h}} seed_run $bin $off compile $src - > $out.hex || { rm -f $out.hex; exit 1; }
    xxd -r -p $out.hex > $out && rm -f $out.hex ;;
  extract)
    local k=$2 sym=$3 out=$4 len n hl line
    read -r magic len n < $k
    [ "$magic" = KSEED1 ] || { echo "{:ok false :message \"not a kseed/v1 container\"}"; exit 1; }
    line=$(head -n $((n + 1)) $k | tail -n $n | awk -v s="$sym" '$1 == s {print $2, $3}')
    [ -n "$line" ] || { echo "{:ok false :message \"symbol '$sym' not exported by the container\"}"; exit 1; }
    hl=$(head -n $((n + 2)) $k | wc -c | tr -d ' ')
    tail -c +$((hl + 1)) $k | head -c $len > $out
    echo "{:ok true :symbol $sym :offset ${line% *} :arity ${line#* } :length $len}" ;;
  *) echo "usage: seed-cc.sh compile <seed.bin> <off> <src> <out.kseed> | extract <kseed> <symbol> <out.bin>" >&2; exit 2 ;;
esac
