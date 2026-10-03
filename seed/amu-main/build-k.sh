#!/bin/zsh
# seed/amu-main/build-k.sh [work-dir] -- route k of seed/amu-main/build.sh: the amu entry with a REAL `check` (agent MAINS,
# 2026-10-04). BOOTSTRAP-TOOL (zsh, python3; java in step 2 only, labelled BOOTSTRAP-REFERENCE: build time, never run time).
#
#   1. roots: <work>/k/roots-<variant> = seed/amu-main/src (amu.main, amu.cli, amu.refactor) + amu.check from k/ (calls
#      kotoba.amu-front.check, the committed seed/amu-front/check.cljk at HEAD) + amu.compile:
#        variant k2: s/amu/compile.kotoba + the seed's split source at HEAD (the seed compiler linked in: compile REAL)
#        variant k1: k/amu/compile.kotoba (declared stub)
#      AM_VARIANT=k2 (default: k2, then k1 when k2 does not build) or k1.
#   2. KIR: scripts/selfhost-wall/kir-dump.clj (RAISE=1) on build/native-image/work's JVM classes over kotoba-sema at
#      AM_KSEMA_REV (default 2d7d05d, agent/f64-front: the revision of amu-front's 391/391 build) + the image roots.
#   3. slice main's closure (seed/tests/kir/slice.py), seed compile-kir with the large-M profile seed of rung r6g
#      (AM_SEED_K, default the recorded c13e22c0 seed, seed/profiles/large-m-r6g.record; decimal-f64-parse lowered), extract.
#   4. package as seed/amu-front/build.sh does (KEXE_EMBEDDED, MEM2 budgets, hash-consing 2^16, wires 3,35,37,38,39, never 20).
# Output: <work>/amu-k, <work>/amu-k.info, <work>/k/<variant>.log (each variant's outcome, refusals verbatim).
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h}
W=${1:-$R/build/mains}; mkdir -p $W/k; W=${W:A}; K=$W/k
KSEMA=${AM_KSEMA:-/Users/junkawasaki/github/kotoba-lang/kotoba-sema}; KREV=${AM_KSEMA_REV:-2d7d05d}
KL=${WALL_K:-/private/tmp/wt-K-kotoba-lang}; CP=$(cat ${WALL_CP:-/private/tmp/wall-cp-16.txt})
SCOPE=${AM_SCOPE:-$R:/Users/junkawasaki/github/kotoba-lang/amu-embench:/private/tmp:/tmp}
sha() { shasum -a 256 $1 | cut -c1-64; }
step() { echo "amu-main k: $* (load $(sysctl -n vm.loadavg | awk '{print $2}'))"; }
want=$(sed -n 's/^seed1_sha256 //p' $R/seed/profiles/large-m-r6g.record)
SB=${AM_SEED_K:-}
if [ -z "$SB" ]; then
  for c in $R/build/f64/lm1/b/seed-1.bin $R/build/seed-large-m-r6g/b/seed-1.bin; do [ -s $c ] && [ "$(sha $c)" = "$want" ] && { SB=$c; break; }; done
  [ -n "$SB" ] || { echo "amu-main k: no large-M r6g seed ($want): scripts/seed/large-m.sh --rung r6g, or AM_SEED_K" >&2; exit 1; }
fi
SB=${SB:A}; SOFF=$(cat ${SB%.bin}.offset)
export SEED_REPO=$R SEED_BUILD=$K/sb; mkdir -p $SEED_BUILD; source $R/scripts/seed/lib.sh

KS=$K/ksema-$KREV
if [ ! -d $KS/src ]; then mkdir -p $KS; git -C $KSEMA archive $KREV src resources | tar -x -C $KS || exit 1; fi
T=$K/tree; rm -rf $T; mkdir -p $T; git -C $R archive HEAD seed/split seed/MANIFEST seed/amu-front/check.cljk | tar -x -C $T || exit 1

roots() {  # <variant> -> prints the roots dir
  local v=$1 D=$K/roots-$1; rm -rf $D; mkdir -p $D/amu $D/kotoba/amu_front
  cp $H/src/amu/*.kotoba $D/amu/; cp $H/k/amu/check.kotoba $D/amu/
  cp $T/seed/amu-front/check.cljk $D/kotoba/amu_front/check.cljk
  if [ $v = k2 ]; then cp $H/s/amu/compile.kotoba $D/amu/; mkdir -p $D/seed; cp $T/seed/split/seed/*.kotoba $D/seed/
  else cp $H/k/amu/compile.kotoba $D/amu/; fi
  echo $D
}
build() {  # <variant> -> 0 when $K/<variant>.bin and .offset exist
  local v=$1 D KR JW=$R/build/native-image/work
  D=$(roots $v)
  KR="$D:$(echo "$CP" | tr ':' '\n' | grep '/src$' | grep -v '/kotoba-sema/src$' | tr '\n' ':')$KS/src:$R/src:$KL/lang/compat"
  step "$v: kir-dump (JVM, BOOTSTRAP-REFERENCE, build time)"
  ( ulimit -s 65500; RAISE=1 GUEST=$D/amu/main.kotoba OUT=$K/$v.kir KROOTS=$KR nice java -Xss1g -Xmx6g \
      -cp "$JW/classes:$(cat $JW/classpath.txt)" clojure.main $R/scripts/selfhost-wall/kir-dump.clj ) > $K/$v.kir-dump.log 2>&1 \
    || { echo "$v: kir-dump failed: $(grep -v '^\s*at ' $K/$v.kir-dump.log | tail -3 | tr '\n' ' ' | cut -c1-400)" >> $K/$v.log; return 1; }
  python3 $R/seed/tests/kir/slice.py slice $K/$v.kir $K/$v.main.kir main > $K/$v.slice.log 2>&1 || { echo "$v: slice failed" >> $K/$v.log; return 1; }
  echo "$v: KIR $(wc -c < $K/$v.main.kir | tr -d ' ') B after slicing" >> $K/$v.log
  step "$v: seed compile-kir (large-M r6g)"
  SEED_RESOURCES_35=$K SEED_VECTOR_ITEMS=67108864 SEED_SECONDS=1800 KEXE_ARENA_USE=1 \
    seed_run $SB $SOFF compile-kir $K/$v.main.kir --output $K/$v.kseed > $K/$v.compile-kir.log 2>&1 \
    || { echo "$v: compile-kir refused: $(grep -v '^ *$' $K/$v.compile-kir.log | head -2 | tr '\n' ' ' | cut -c1-300)" >> $K/$v.log; return 1; }
  local off=$(SEED_RESOURCES_35=$K SEED_VECTOR_ITEMS=67108864 seed_run $SB $SOFF extract-native $K/$v.kseed --symbol main --output $K/$v.bin \
      | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  [ -n "$off" ] || { echo "$v: extract-native failed" >> $K/$v.log; return 1; }
  echo $off > $K/$v.offset; echo "$v: built, code $(wc -c < $K/$v.bin | tr -d ' ') B" >> $K/$v.log
}
V=""
for v in ${=AM_VARIANT:-k2 k1}; do
  rm -f $K/$v.log; if build $v; then V=$v; break; fi; cat $K/$v.log
done
[ -n "$V" ] || { echo "amu-main k: no variant built"; exit 1; }

step "package $V"
D=$K/package; mkdir -p $D
off=$(cat $K/$V.offset); len=$(wc -c < $K/$V.bin | tr -d ' ')
POOL=1073741824; PAIRS=67108864; VECS=67108864; ITEMS=134217728; CPU=1800; WALL=1800; HC=16; ALLOW=3,35,37,38,39
{ echo "/* generated by seed/amu-main/build-k.sh from $V.bin -- do not edit */"
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
  echo "__attribute__((constructor)) static void amu_main_hashcons(void) { setenv(\"KEXE_HASHCONS\", \"$HC\", 0); }"
  echo "static const unsigned char kexe_embedded_code[$len] = {"
  xxd -i < $K/$V.bin
  echo "};"; } > $D/kexe_embedded.h
cc -O2 -std=c11 -I $D -include $D/kexe_embedded.h $R/tools/kexe_loader.c -o $W/amu-k.tmp 2> $D/cc.log || { echo "amu-main k: cc failed"; exit 1; }
mv $W/amu-k.tmp $W/amu-k
deps=$(otool -L $W/amu-k | tail -n +2 | awk '{print $1}')
{ echo "label amu-k (amu.main, KIR route, variant $V: KIR from kir-dump on the JVM-built classes = BOOTSTRAP-REFERENCE at build time; native code by seed $(sha $SB | cut -c1-16) (large-M r6g); kotoba-sema $KREV)"
  for f in $K/roots-$V/amu/*.kotoba; do echo "source amu/${f:t} $(sha $f | cut -c1-16)"; done
  echo "kir $(sha $K/$V.main.kir) bytes $(wc -c < $K/$V.main.kir | tr -d ' ')"
  echo "code $(sha $K/$V.bin) bytes $len offset $off"
  echo "command $W/amu-k sha256 $(sha $W/amu-k) bytes $(wc -c < $W/amu-k | tr -d ' ')"
  echo "loader-source sha256 $(sha $R/tools/kexe_loader.c)"
  echo "allow $ALLOW scope35 $SCOPE"
  echo "budgets string-pool $POOL pairs $PAIRS vectors $VECS vector-items $ITEMS cpu $CPU wall $WALL hashcons $HC"
  echo "libraries $(echo $deps | tr '\n' ' ')"
  for v in k2 k1; do [ -f $K/$v.log ] && sed "s/^/variant-log /" $K/$v.log; done; } > $W/amu-k.info
echo "$deps" | grep -vq '^/usr/lib/' && { echo "amu-main k: unexpected library dependency"; exit 1; }
cat $W/amu-k.info
