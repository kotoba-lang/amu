#!/bin/zsh
# seed/tests/r4b/check-caps.sh [--stage0] [seed.bin [offset]] -- the R4B capability programs (owner R4B). BOOTSTRAP-TOOL (zsh).
# Each caps/cNN program is compiled (by the seed, or with --stage0 by stage-0 = the oracle) and run under the C loader with
# the grants of the table below, KEXE_CAP_RESOURCES_34/35 = caps/res, SEED_R4B_DIR / SEED_R4B_FILE pointing into it and
# "hello\n" on standard input. Expected values: caps/caps.oracle (written by --stage0 --record). Exit 0 iff all equal.
emulate -L zsh
setopt pipefail
source "${0:A:h}/../../../scripts/seed/lib.sh"
D=${0:A:h}; W=$SEED_BUILD/r4b-caps; mkdir -p $W
s0=0; rec=0
[ "$1" = --stage0 ] && { s0=1; shift; }
[ "$1" = --record ] && { rec=1; shift; }
bin=${1:-$SEED_BUILD/seed-1.bin}; off=${2:-$(cat ${bin%.bin}.offset 2>/dev/null || echo 0)}
L=$(seed_loader) || exit 2
typeset -A grant
grant=(c01-sha256 3 c02-env-read 33 c03-fs-browse 33,34 c04-io-read 41 c05-app-data-bytes 33,35 c06-app-data-bytes-spelling 33,35)
res=${D}/caps/res
ok=0; bad=0; out=""
for f in $D/caps/c*.kotoba; do
  stem=${f:t:r}; g=${grant[$stem]}; rm -f $W/$stem.*(N)
  if [ $s0 = 1 ]; then
    caps=""; for c in ${(s:,:)g}; do caps="$caps [:cap/call $c]"; done; echo "{:allow #{$caps}}" > $W/pol.edn
    seed_slot_take
    r=$( ulimit -s 65500; nice $SEED_STAGE0 compile $f --target aarch64-macos --jvm-free --policy $W/pol.edn --output $W/$stem.kexe 2>&1 )
    echo "$r" | grep -q ':ok true' && r=$( nice $SEED_STAGE0 extract-native $W/$stem.kexe --symbol test --output $W/$stem.bin 2>&1 )
    seed_slot_give
  else
    seed_run $bin $off compile $f $W/$stem.kseed > $W/cc.out 2> $W/cc.err && r=$(zsh $SEED_REPO/scripts/seed/seed-cc.sh extract $W/$stem.kseed test $W/$stem.bin) \
      || r="refused $(head -1 $W/cc.err)"
  fi
  if echo "$r" | grep -q ':ok true'; then
    o=$(echo "$r" | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
    v=$(cd $W; printf 'hello\n' | SEED_R4B_DIR=$res/d SEED_R4B_FILE=$res/bytes.bin KEXE_CAP_RESOURCES_34=$res KEXE_CAP_RESOURCES_35=$res \
          KEXE_CPU_SECONDS=20 KEXE_WALL_SECONDS=20 $L $W/$stem.bin $o 0 aarch64 $g 2>$W/$stem.err | tail -1)
    [ -n "$v" ] || v=trap
  else v="refused"; fi
  out="$out$stem	$v
"
  want=$(awk -F'\t' -v s=$stem '$1==s {print $2}' $D/caps/caps.oracle 2>/dev/null)
  if [ $rec = 1 ]; then ok=$((ok+1)); elif [ "$v" = "$want" ]; then ok=$((ok+1)); else bad=$((bad+1)); echo "BAD $stem: want=$want got=$v"; fi
done
[ $rec = 1 ] && { printf '%s' "$out" > $D/caps/caps.oracle; cat $D/caps/caps.oracle; }
echo "R4B caps$([ $s0 = 1 ] && echo ' (stage-0)'): $ok equal, $bad different"
[ $bad -eq 0 ]
