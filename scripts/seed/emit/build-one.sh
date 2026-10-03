#!/bin/zsh
# scripts/seed/emit/build-one.sh [work-dir] -- ONE amu image with a real `check` (the big frontend on the KIR route) AND a
# real `compile` (the seed compiler linked in from source), joined by `seed link` (agent EMIT, 2026-10-04).
# BOOTSTRAP-TOOL (zsh, python3; java in step 2 only, labelled BOOTSTRAP-REFERENCE: build time, never run time).
#
#   1. seeds: the seed of THIS tree (git HEAD's seed/ + the worktree's seed/90-drv.kotoba and seed/50-out.kotoba, i.e. the
#      EMIT block) built by the lineage route from rung r6h's recorded seed (EMIT_PREV, default build/link/b/seed-1.bin,
#      checked against seed/rungs/r6h.record), its own fixed point; and its LARGE-M profile (scripts/seed/large_m.py, the
#      ARENA profile: TOK 655,360 ..), also its own fixed point, for the 2.4 MB frontend KIR. The split of the same tree
#      (seed/split/gen-split.py) is the compiler that amu.compile links in.
#   2. KIR of seed/amu-front/check.cljk (namespace kotoba.amu-front.check) by scripts/selfhost-wall/kir-dump.clj on the
#      JVM-built classes over kotoba-sema EMIT_KSEMA_REV (default 2d7d05d, amu-k's revision): BOOTSTRAP-REFERENCE, build time.
#      Sliced to main's closure (seed/tests/kir/slice.py); decimal-f64-parse kept (lowered by 12-kirread since r6g).
#   3. objects (60-proj separate mode, KSEEDO1), every one written by a seed of step 1:
#        kotoba.amu-front.check  <- large-M seed: compile-kir check.main.kir --emit-module --ns kotoba.amu-front.check
#        seed.* (the split, in `seed modules` order), amu.cli, amu.refactor, amu.compile (s/), amu.check (k/: requires
#        kotoba.amu-front.check and calls its main), amu.main (--entry)  <- seed: compile <f> --emit-module
#   4. seed link amu.main.kso -> amu.kseed; extract-native main; package with tools/kexe_loader.c (KEXE_EMBEDDED, the budgets
#      and hash-consing of amu-k, wires 3,35,37,38,39, never 20) -> <work>/amu-one (+ amu-one.info).
# Env: EMIT_PREV, EMIT_KSEMA (kotoba-sema checkout), EMIT_KSEMA_REV, WALL_CP, WALL_K, EMIT_FORCE=1 (redo the KIR step).
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h:h}
W=${1:-$R/build/emit}; mkdir -p $W; W=${W:A}
A=$R/seed/amu-main
KSEMA=${EMIT_KSEMA:-/Users/junkawasaki/github/kotoba-lang/kotoba-sema}; KREV=${EMIT_KSEMA_REV:-2d7d05d}
KL=${WALL_K:-/private/tmp/wt-K-kotoba-lang}; CP=$(cat ${WALL_CP:-/private/tmp/wall-cp-16.txt})
SCOPE=${EMIT_SCOPE:-$R:/Users/junkawasaki/github/kotoba-lang/amu-embench:/private/tmp:/tmp}
sha() { shasum -a 256 $1 | cut -c1-64; }
die() { echo "build-one: FAIL: $*" >&2; exit 1; }
step() { echo "build-one: $* (load $(sysctl -n vm.loadavg | awk '{print $2}'))"; }

# ---- 1. seeds ----
PREV=${EMIT_PREV:-$R/build/link/b/seed-1.bin}
[ "$(sha $PREV)" = "$(sed -n 's/^seed1_sha256 //p' $R/seed/rungs/r6h.record)" ] || die "$PREV is not rung r6h's seed"
T=$W/tree; rm -rf $T; mkdir -p $T
git -C $R archive HEAD seed scripts/seed tools | tar -x -C $T || die "git archive"
cp $R/seed/90-drv.kotoba $R/seed/50-out.kotoba $T/seed/
python3 $T/seed/split/gen-split.py > $W/gen-split.log || die "gen-split"
step "seed (lineage from r6h)"
( export SEED_REPO=$T SEED_BUILD=$W/b SEED_RESOURCES_35=$W SEED_PREV=$PREV SEED_VECTOR_ITEMS=67108864 SEED_SECONDS=900
  nice zsh $T/scripts/seed/build.sh lineage ) > $W/build.log 2>&1 || { tail -5 $W/build.log; die "build.sh lineage"; }
grep -q 'FIXED POINT' $W/build.log || die "seed not a fixed point"
SB=$W/b/seed-1.bin
TL=$W/treeLM; rm -rf $TL; cp -R $T $TL
python3 $R/scripts/seed/large_m.py $TL/seed/MEMORY-MAP > $W/large_m.log || die "large_m.py"
zsh $TL/scripts/seed/gen-ns.sh > $W/gen-ns.log 2>&1 || die "gen-ns"
step "large-M seed"
( export SEED_REPO=$TL SEED_BUILD=$W/lm SEED_RESOURCES_35=$W SEED_PREV=$SB SEED_VECTOR_ITEMS=67108864 SEED_SECONDS=900
  nice zsh $TL/scripts/seed/build.sh lineage ) > $W/lm.log 2>&1 || { tail -5 $W/lm.log; die "large-M lineage"; }
grep -q 'FIXED POINT' $W/lm.log || die "large-M seed not a fixed point"
SL=$W/lm/seed-1.bin
export SEED_REPO=$R SEED_BUILD=$W/sb; mkdir -p $SEED_BUILD; source $R/scripts/seed/lib.sh
run() { SEED_RESOURCES_35=$R SEED_VECTOR_ITEMS=134217728 SEED_SECONDS=1800 seed_run "$@"; }

# ---- 2. KIR ----
K=$W/kir; mkdir -p $K
KS=$K/ksema-$KREV
if [ ! -d $KS/src ]; then mkdir -p $KS; git -C $KSEMA archive $KREV src resources | tar -x -C $KS || die "ksema archive"; fi
if [ -n "$EMIT_FORCE" ] || [ ! -s $K/check.kir ] || [ $R/seed/amu-front/check.cljk -nt $K/check.kir ]; then
  step "kir-dump (JVM, BOOTSTRAP-REFERENCE, build time)"
  KR="$(echo "$CP" | tr ':' '\n' | grep '/src$' | grep -v '/kotoba-sema/src$' | tr '\n' ':')$KS/src:$R/src:$KL/lang/compat"
  JW=$R/build/native-image/work
  ( ulimit -s 65500; RAISE=1 GUEST=$R/seed/amu-front/check.cljk OUT=$K/check.kir KROOTS=$KR nice java -Xss1g -Xmx6g \
      -cp "$JW/classes:$(cat $JW/classpath.txt)" clojure.main $R/scripts/selfhost-wall/kir-dump.clj ) > $K/kir-dump.log 2>&1 \
    || { tail -5 $K/kir-dump.log; die "kir-dump"; }
fi
python3 $R/seed/tests/kir/slice.py slice $K/check.kir $K/check.main.kir main > $K/slice.log 2>&1 || die "slice"

# ---- 3. objects ----
O=$W/o; rm -rf $O; mkdir -p $O
FO=$K/kotoba.amu-front.check.kso
key="$(sha $SL) $(sha $K/check.main.kir)"
if [ -n "$EMIT_FORCE" ] || [ ! -s $FO ] || [ "$(cat $FO.key 2>/dev/null)" != "$key" ]; then
  step "compile-kir --emit-module kotoba.amu-front.check (large-M seed)"
  KEXE_ARENA_USE=1 run $SL 0 compile-kir $K/check.main.kir --emit-module --ns kotoba.amu-front.check --object-dir $O \
      --output $FO > $W/emit-front.log 2>&1 || { cat $W/emit-front.log; die "compile-kir --emit-module"; }
  echo "$key" > $FO.key
fi
cp $FO $O/
S=$W/roots; rm -rf $S; mkdir -p $S/amu
cp $A/src/amu/*.kotoba $S/amu/; cp $A/k/amu/check.kotoba $S/amu/; cp $A/s/amu/compile.kotoba $S/amu/
SPLIT=$T/seed/split
run $SB 0 modules $SPLIT/seed/main.kotoba --source-path $SPLIT > $W/modules.txt 2> $W/modules.log || die "seed modules"
emit() {  # <file> [--entry]
  local f=$1 nm; nm=$(sed -n '1s/^(ns \([^ )]*\).*/\1/p' $f)
  run $SB 0 compile $f --emit-module $2 --object-dir $O --output $O/$nm.kso < /dev/null >> $W/emit.log 2>&1 || { tail -2 $W/emit.log; die "emit $f"; }
}
: > $W/emit.log
step "compile --emit-module: $(wc -l < $W/modules.txt | tr -d ' ') seed modules + 5 amu modules"
while read nm p; do emit $p; done < $W/modules.txt
for m in cli refactor compile check; do emit $S/amu/$m.kotoba; done
emit $S/amu/main.kotoba --entry

# ---- 4. link, extract, package ----
step "seed link"
run $SB 0 link $O/amu.main.kso --object-dir $O --output $W/amu.kseed > $W/link.log 2>&1 || { cat $W/link.log; die "link"; }
off=$(run $SB 0 extract-native $W/amu.kseed --symbol main --output $W/amu.bin | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
[ -n "$off" ] || die "extract-native"
D=$W/package; mkdir -p $D
len=$(wc -c < $W/amu.bin | tr -d ' ')
POOL=1073741824; PAIRS=67108864; VECS=67108864; ITEMS=134217728; CPU=1800; WALL=1800; HC=16; ALLOW=3,35,37,38,39
{ echo "/* generated by scripts/seed/emit/build-one.sh from amu.bin -- do not edit */"
  echo "#include <stdlib.h>"
  echo "#define KEXE_EMBEDDED 1"
  echo "#define KEXE_EMBEDDED_OFFSET ${off}u"
  echo "#define KEXE_EMBEDDED_ARITY 0u"
  echo "#define KEXE_EMBEDDED_ISA \"aarch64\""
  echo "#define KEXE_EMBEDDED_ALLOW \"$ALLOW\""
  echo "#define KEXE_EMBEDDED_SCOPE35 \"$SCOPE\""
  echo "#define KEXE_EMBEDDED_SCOPE34 \"\""
  echo "#define KEXE_EMBEDDED_SPAWN_PROGRAMS \"\""
  echo "#define KEXE_EMBEDDED_SPAWN_ENV \"\""
  echo "#define KEXE_EMBEDDED_SPAWN_PATH_LOOKUP 0"
  echo "#define KEXE_EMBEDDED_STRING_POOL ${POOL}u"
  echo "#define KEXE_EMBEDDED_FUEL 0u"
  echo "#define KEXE_EMBEDDED_PAIRS ${PAIRS}u"
  echo "#define KEXE_EMBEDDED_VECTORS ${VECS}u"
  echo "#define KEXE_EMBEDDED_VECTOR_ITEMS ${ITEMS}u"
  echo "#define KEXE_EMBEDDED_CPU_SECONDS ${CPU}u"
  echo "#define KEXE_EMBEDDED_WALL_SECONDS ${WALL}u"
  echo "__attribute__((constructor)) static void amu_one_hashcons(void) { setenv(\"KEXE_HASHCONS\", \"$HC\", 0); }"
  echo "static const unsigned char kexe_embedded_code[$len] = {"
  xxd -i < $W/amu.bin
  echo "};"; } > $D/kexe_embedded.h
cc -O2 -std=c11 -I $D -include $D/kexe_embedded.h $R/tools/kexe_loader.c -o $W/amu-one.tmp 2> $D/cc.log || die "cc"
mv $W/amu-one.tmp $W/amu-one
deps=$(otool -L $W/amu-one | tail -n +2 | awk '{print $1}')
echo "$deps" | grep -vq '^/usr/lib/' && die "unexpected library dependency"
{ echo "label amu-one (amu.main: check REAL via the kotoba-sema frontend $KREV on the KIR route = kir-dump on JVM-built classes, BOOTSTRAP-REFERENCE at build time; compile REAL via the seed compiler from source; every native byte by seed $(sha $SB | cut -c1-16) / large-M $(sha $SL | cut -c1-16), joined by seed link)"
  echo "seed $(sha $SB) bytes $(wc -c < $SB | tr -d ' ') (lineage from r6h $(sha $PREV | cut -c1-16), fixed point)"
  echo "seed-large-m $(sha $SL) bytes $(wc -c < $SL | tr -d ' ') (fixed point)"
  echo "tree HEAD $(git -C $R rev-parse --short HEAD) + worktree 90-drv $(sha $R/seed/90-drv.kotoba | cut -c1-16) 50-out $(sha $R/seed/50-out.kotoba | cut -c1-16)"
  for f in $S/amu/*.kotoba; do echo "source amu/${f:t} $(sha $f | cut -c1-16)"; done
  echo "kir check.main.kir $(sha $K/check.main.kir) bytes $(wc -c < $K/check.main.kir | tr -d ' ')"
  echo "objects $(ls $O/*.kso | wc -l | tr -d ' ') bytes $(cat $O/*.kso | wc -c | tr -d ' ') (front $(wc -c < $O/kotoba.amu-front.check.kso | tr -d ' '))"
  echo "kseed $(sha $W/amu.kseed) bytes $(wc -c < $W/amu.kseed | tr -d ' ')"
  echo "code $(sha $W/amu.bin) bytes $len offset $off"
  echo "command $W/amu-one sha256 $(sha $W/amu-one) bytes $(wc -c < $W/amu-one | tr -d ' ')"
  echo "loader-source sha256 $(sha $R/tools/kexe_loader.c)"
  echo "allow $ALLOW scope35 $SCOPE"
  echo "budgets string-pool $POOL pairs $PAIRS vectors $VECS vector-items $ITEMS cpu $CPU wall $WALL hashcons $HC"
  echo "libraries $(echo $deps | tr '\n' ' ')"; } > $W/amu-one.info
cat $W/amu-one.info
