#!/bin/zsh
# seed/tests/text/check-text.sh [seed.bin] -- the kotoba.lang.text differential (agent TEXT, 2026-10-04). BOOTSTRAP-TOOL.
# One driver (gen.py: 5,422 cases of the 14 exports of the guest twin kotoba.lang.text over multi-byte / astral / whitespace /
# empty inputs, folded into 136 arity-0 group exports) is answered four ways, and every group must agree:
#   HOST     kotoba-lang/text's src/kotoba/lang/text.cljk under kbb/nbb (host.cljk), folded by gen.py (the oracle)
#   SEED     the seed compiles the driver and the twins from source (--source-path <kotoba-lang>/lang/compat), native run
#   S0-NEW   stage-0 (BOOTSTRAP-REFERENCE) compiles the same driver against the same twins, native run
#   S0-OLD   stage-0 against the twins as they were before agent TEXT's rewrite (kotoba-lang $TEXT_OLD_REV, which used the
#            builtins string-contains? / string-replace-all / string-index-of-from), native run: informational, it shows
#            which groups the rewrite changed (the empty-separator split fix) and that every other group is unchanged
# Every native run: the C loader, no capability, the r6-diff budgets. Output: $W/text-diff.tsv (group, host, seed, s0-new,
# s0-old, verdict AGREE = HOST SEED S0-NEW equal, plus OLD-SAME / OLD-DIFF), a summary line; exit 0 iff every group AGREEs.
# Env: SEED_BUILD (default build/text), TEXT_K (kotoba-lang checkout, default /private/tmp/wt-K-kotoba-lang), TEXT_HOST_SRC
# (the host text library's src, default /private/tmp/wt-F-text/src), TEXT_OLD_REV (default 919232d).
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/../../../scripts/seed/lib.sh"
R=$SEED_REPO; B=${SEED_BUILD:A}; W=$B/text-diff; T=$R/seed/tests/text
K=${TEXT_K:-/private/tmp/wt-K-kotoba-lang}; HS=${TEXT_HOST_SRC:-/private/tmp/wt-F-text/src}; OLD=${TEXT_OLD_REV:-919232d}
bin=${1:-$R/build/seed-r6d/seed-1.bin}; bin=${bin:A}; off=$(cat ${bin%.bin}.offset)
L=$(seed_loader) || exit 2; L=${L:A}
rm -rf $W; mkdir -p $W/old
python3 $T/gen.py gen $W 40 || exit 2
kbb --backend sci --classpath $HS $T/host.cljk $W/cases.json > $W/host.json || { echo "check-text: host run failed" >&2; exit 2; }
python3 $T/gen.py fold $W $W/host.json > $W/host.fold || exit 2
git -C $K archive $OLD lang/compat | tar -x -C $W/old || exit 2
export SEED_RESOURCES_35=$R:$W:$K/lang/compat
seed_run $bin $off compile $W/main.kotoba --source-path $K/lang/compat --unpinned --output $W/seed.kseed > $W/seed.log 2>&1
[ -s $W/seed.kseed ] || { echo "check-text: SEED refused the driver: $(grep -m1 'seed:' $W/seed.log)"; exit 1; }
echo '{:allow #{}}' > $W/pol.edn
for v in new old; do
  root=$K/lang/compat; [ $v = old ] && root=$W/old/lang/compat
  seed_slot_take
  ( ulimit -s 65500; cd $W; nice $SEED_STAGE0 compile $W/main.kotoba --source-path $root --unpinned --target aarch64-macos \
      --jvm-free --policy $W/pol.edn --output $W/s0-$v.kexe > $W/s0-$v.log 2>&1 )
  seed_slot_give
  grep -q ':ok true' $W/s0-$v.log || { echo "check-text: stage-0 ($v twins) refused the driver: $(head -c 300 $W/s0-$v.log)"; exit 1; }
  python3 $R/scripts/seed/r6_diff.py offsets kexe $W/s0-$v.kexe $W/s0-$v.bin > $W/s0-$v.off
done
python3 $R/scripts/seed/r6_diff.py offsets kseed $W/seed.kseed $W/seed.bin > $W/seed.off
run1() {
  local v
  v=$(cd $W; KEXE_STRING_POOL=268435456 KEXE_PAIRS=4194304 KEXE_VECTORS=65536 KEXE_VECTOR_ITEMS=16777216 \
      KEXE_CPU_SECONDS=20 KEXE_WALL_SECONDS=20 $L $1 $2 0 aarch64 3 2>/dev/null | tail -1)
  [ $? -eq 0 ] && [ -n "$v" ] && echo $v || echo trap
}
load0=$(uptime | sed 's/.*averages: //')
print -r -- "# check-text $(date '+%F %T') seed $(shasum -a 256 $bin | cut -c1-16) stage-0 $(shasum -a 256 $SEED_STAGE0 | cut -c1-16) kotoba-lang $(git -C $K rev-parse --short HEAD)$(git -C $K diff --quiet -- lang/compat || echo +dirty) old $OLD load $load0" > $W/text-diff.tsv
ok=0; n=0; same=0
while read -r g want; do
  a=$(run1 $W/seed.bin $(awk -v s=$g '$1==s {print $2}' $W/seed.off))
  b=$(run1 $W/s0-new.bin $(awk -v s=$g '$1==s {print $2}' $W/s0-new.off))
  c=$(run1 $W/s0-old.bin $(awk -v s=$g '$1==s {print $2}' $W/s0-old.off))
  n=$((n+1)); vd=DIFF; od=OLD-DIFF
  [ "$a" = "$want" ] && [ "$b" = "$want" ] && { vd=AGREE; ok=$((ok+1)); }
  [ "$c" = "$want" ] && { od=OLD-SAME; same=$((same+1)); }
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' $g $want $a $b $c $vd $od >> $W/text-diff.tsv
done < $W/host.fold
print -r -- "# load at end $(uptime | sed 's/.*averages: //')" >> $W/text-diff.tsv
cases=$(python3 -c "import json; print(len(json.load(open('$W/cases.json'))))")
echo "check-text: $ok/$n groups agree (HOST = SEED = S0-NEW), $cases cases; the pre-rewrite twins (S0-OLD) answer the host's value on $same/$n; table $W/text-diff.tsv"
[ $ok -eq $n ]
