#!/bin/zsh
# seed/amu-front/build.sh [work-dir] -- build `amu-front`, the native `check` command made from the big frontend
# (agent COMPOSE, 2026-10-03; seed/amu-front/README.md). BOOTSTRAP-TOOL (zsh, python3, java for step 2 only).
#
#   1. seed M: a PRIVATE copy of the seed at tag seed-r6c-kir (be8898af lineage) whose MEMORY-MAP has M = 16 Mi words
#      (TOK 524,288, NODE 458,752, SIR 458,752, CODE 1 Mi, OUT 3 Mi, FN 16,384 ..., FRONT's table), built by the
#      recorded rung seed (SEED_PREV, build.sh lineage) and checked to be its own fixed point. The whole linked frontend
#      is 435k KIR tokens; the committed seed's TOK region holds 262,144 (CONTRACT-REQUESTS 2026-10-03 FRONT/COMPOSE).
#   2. KIR: scripts/selfhost-wall/kir-dump.clj on the JVM-built compiler classes (build/native-image/work,
#      BOOTSTRAP-REFERENCE, the pre-ADR-0363 lineage) over seed/amu-front/check.cljk + kotoba-sema at AF_KSEMA_REV
#      (default bd40e37, the last frontend revision written for that lineage; the ADR-0363 port 15e45a3 is not accepted by
#      it). The stable native stage-0 has no KIR emission and refuses the linked frontend at its aarch64 admission
#      (measured, see the doc), so this is the same route FRONT used for analyze. RAISE=1 (whole-frontend link).
#   3. slice main's call closure (seed/tests/kir/slice.py); the reader twin's one `decimal-f64-parse` (float literals) is
#      replaced by none (no seed lowering for it: a float literal is then refused by the frontend, a listed gap);
#      `seed compile-kir` + `extract-native` under the C loader only.
#   4. package: tools/kexe_loader.c in its KEXE_EMBEDDED form (as scripts/seed/package.sh), budgets from MEM2
#      (docs/selfhost-analyze-memory-20261003.md: 64 Mi vector handles, 64 Mi pairs, hash-consing 2^16 on by default
#      through a constructor in the generated header, which a caller's KEXE_HASHCONS overrides), wire allow list
#      3,35,37,38,39 (hash/sha, fs, stdout, argv, stderr), never 20 (spawn). Wire 3 is needed: the frontend names every
#      record schema and closure type by a sha256 identity (:schema-identities, __kotoba_invoke_t_<hash>); without it the
#      guest's first such call is a denied capability = SIGILL (measured: 28 corpus programs trapped before this).
#   5. no host processes: the packaged command runs under build/seed/noproc/noproc.dylib (scripts/seed/no-host-processes.sh)
#      with an empty PATH on two inputs; PASS = no exec/spawn/system/popen logged, one supervisor fork per run.
# Env (ARENA 2026-10-04): AF_SEED=<seed.bin> (its .offset beside it) skips step 1 and uses that seed, e.g. the recorded
#      large-M profile (scripts/seed/large-m.sh, seed/profiles/large-m-r6d.record); AF_F64=1 keeps the reader twin's
#      decimal-f64-parse (F64 2026-10-04: compile-kir lowers it from rung r6g on, 12-kirread's dec group; the R6D/R6E
#      seeds refuse it E2101 on the KIR route and the r6c-kir lineage too, so the default still replaces it by none).
# Env: AF_SCOPE (wire-35 directories, colon separated; default the repo, amu-embench, /private/tmp, /tmp),
#      AF_KSEMA (kotoba-sema checkout), AF_KSEMA_REV, WALL_CP, WALL_K, AF_FORCE=1 (redo every step).
# Output: <work>/amu-front (the command), <work>/amu-front.info.
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h}
W=${1:-$R/build/compose}; mkdir -p $W; W=${W:A}
KSEMA=${AF_KSEMA:-/Users/junkawasaki/github/kotoba-lang/kotoba-sema}; KREV=${AF_KSEMA_REV:-bd40e37}
K=${WALL_K:-/private/tmp/wt-K-kotoba-lang}; CP=$(cat ${WALL_CP:-/private/tmp/wall-cp-16.txt})
SCOPE=${AF_SCOPE:-$R:/Users/junkawasaki/github/kotoba-lang/amu-embench:/private/tmp:/tmp}
sha() { shasum -a 256 $1 | cut -c1-64; }
step() { echo "amu-front: $* (load $(sysctl -n vm.loadavg | awk '{print $2}'))"; }

# ---- 1. the seed with the larger M ----
X=$W/seedx
if [ -n "$AF_SEED" ]; then
  [ -s $AF_SEED ] && [ -s ${AF_SEED%.bin}.offset ] || { echo "amu-front: AF_SEED $AF_SEED (+ .offset) missing"; exit 1; }
elif [ -n "$AF_FORCE" ] || [ ! -s $X/b/seed-1.bin ]; then
  step "seed M=16Mi words"
  rm -rf $X; mkdir -p $X
  git -C $R archive seed-r6c-kir seed scripts/seed tools | tar -x -C $X || exit 1
  python3 - $X/seed/MEMORY-MAP <<'P' || exit 1
import re, sys
p = sys.argv[1]; s = open(p).read()
caps = [('TOK', 524288), ('NODE', 458752), ('SYM', 65536), ('HASH', 131072), ('FN', 16384), ('SCOPE', 65536),
        ('SIR', 458752), ('LABEL', 262144), ('CODE', 1048576), ('FIX', 131072), ('LIT', 32768), ('LITB', 524288),
        ('EXP', 1024), ('OUT', 3145728)]
s = s.replace('[:c MM-WORDS 8388608', '[:c MM-WORDS 16777216', 1)
base = 256
for name, cap in caps:
    m = re.search(r'\[:c MM-%s-BASE (\d+)\] \[:c MM-%s-W (\d+)\] \[:c MM-%s-CAP (\d+)\]' % (name, name, name), s)
    w = int(m.group(2))
    s = s[:m.start()] + '[:c MM-%s-BASE %d] [:c MM-%s-W %d] [:c MM-%s-CAP %d]' % (name, base, name, w, name, cap) + s[m.end():]
    base += w * cap
assert base < 16777216
s = re.sub(r'\[:c MM-HEAP-BASE \d+\] \[:c MM-HEAP-END \d+\]', '[:c MM-HEAP-BASE %d] [:c MM-HEAP-END 16777216]' % base, s)
open(p, 'w').write(s)
P
  zsh $X/scripts/seed/gen-ns.sh > /dev/null || exit 1
  ( export SEED_REPO=$X SEED_BUILD=$X/b SEED_PREV=$(ls $R/build/seedfix-g/seed-1.bin) SEED_VECTOR_ITEMS=67108864 SEED_SECONDS=900
    nice zsh $X/scripts/seed/build.sh lineage ) > $W/seedx.log 2>&1 || { tail -5 $W/seedx.log; exit 1; }
fi
if [ -n "$AF_SEED" ]; then
  SB=${AF_SEED:A}; SOFF=$(cat ${SB%.bin}.offset)
  export SEED_REPO=$R SEED_BUILD=$W/sb; mkdir -p $W/sb; source $R/scripts/seed/lib.sh
else
  grep -q 'FIXED POINT' $W/seedx.log || { echo "amu-front: the private seed is not its own fixed point"; exit 1; }
  SB=$X/b/seed-1.bin; SOFF=$(cat $X/b/seed-1.offset)
  export SEED_REPO=$X SEED_BUILD=$X/b; source $X/scripts/seed/lib.sh
fi

# ---- 2. KIR of the driver + the linked frontend ----
KS=$W/ksema-$KREV
if [ ! -d $KS/src ]; then mkdir -p $KS; git -C $KSEMA archive $KREV src resources | tar -x -C $KS || exit 1; fi
KR="$(echo "$CP" | tr ':' '\n' | grep '/src$' | grep -v '/kotoba-sema/src$' | tr '\n' ':')$KS/src:$R/src:$K/lang/compat"
JW=$R/build/native-image/work
if [ -n "$AF_FORCE" ] || [ ! -s $W/check.kir ] || [ $H/check.cljk -nt $W/check.kir ]; then
  step "kir-dump (JVM, bootstrap-reference)"
  ( ulimit -s 65500; RAISE=1 GUEST=$H/check.cljk OUT=$W/check.kir KROOTS=$KR nice java -Xss1g -Xmx6g \
      -cp "$JW/classes:$(cat $JW/classpath.txt)" clojure.main $R/scripts/selfhost-wall/kir-dump.clj ) > $W/kir-dump.log 2>&1 \
    || { tail -5 $W/kir-dump.log; exit 1; }
fi

# ---- 3. slice, compile-kir, extract ----
step "slice + seed compile-kir"
python3 $R/seed/tests/kir/slice.py slice $W/check.kir $W/check.main.kir main || exit 1
[ -n "$AF_F64" ] || python3 -c "
import sys; p=sys.argv[1]; s=open(p).read(); n=s.count('(decimal-f64-parse tok)')
s=s.replace('(decimal-f64-parse tok)','(option-none-of [:option :f64])'); open(p,'w').write(s); print('decimal-f64-parse replaced:', n)" $W/check.main.kir
SEED_RESOURCES_35=$W SEED_VECTOR_ITEMS=67108864 SEED_SECONDS=900 KEXE_ARENA_USE=1 \
  seed_run $SB $SOFF compile-kir $W/check.main.kir --output $W/check.kseed > $W/compile-kir.log 2>&1 \
  || { tail -3 $W/compile-kir.log; exit 1; }
off=$(SEED_RESOURCES_35=$W SEED_VECTOR_ITEMS=67108864 seed_run $SB $SOFF extract-native $W/check.kseed --symbol main --output $W/check.bin \
      | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
[ -n "$off" ] || { echo "amu-front: extract-native failed"; exit 1; }
echo $off > $W/check.offset

# ---- 4. package ----
step "package"
D=$W/package; mkdir -p $D
len=$(wc -c < $W/check.bin | tr -d ' ')
POOL=${AF_POOL:-1073741824}; PAIRS=${AF_PAIRS:-67108864}; VECS=${AF_VECTORS:-67108864}; ITEMS=${AF_VECTOR_ITEMS:-134217728}
CPU=${AF_CPU:-1800}; WALL=${AF_WALL:-1800}; HC=${AF_HC:-16}; ALLOW=3,35,37,38,39
{
  echo "/* generated by seed/amu-front/build.sh from check.bin -- do not edit */"
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
  echo "/* hash-consing (KEXE_HASHCONS, MEM2): on by default for this command; the environment may still set it (0 = off) */"
  [ "$HC" != 0 ] && echo "__attribute__((constructor)) static void amu_front_hashcons(void) { setenv(\"KEXE_HASHCONS\", \"$HC\", 0); }"
  echo "static const unsigned char kexe_embedded_code[$len] = {"
  xxd -i < $W/check.bin
  echo "};"
} > $D/kexe_embedded.h
cc -O2 -std=c11 -I $D -include $D/kexe_embedded.h $R/tools/kexe_loader.c -o $W/amu-front.tmp 2> $D/cc.log \
  || { echo "amu-front: cc failed (see $D/cc.log)"; head -5 $D/cc.log; exit 1; }
mv $W/amu-front.tmp $W/amu-front
deps=$(otool -L $W/amu-front | tail -n +2 | awk '{print $1}')
echo "$deps" | grep -vq '^/usr/lib/' && { echo "amu-front: unexpected library dependency:"; echo "$deps"; exit 1; }
{ echo "label amu-front (native check from the kotoba-sema frontend $KREV via kir-dump BOOTSTRAP-REFERENCE KIR + ${AF_SEED:+seed $AF_SEED}${AF_SEED:-private seed M=16Mi})"
  if [ -n "$AF_SEED" ]; then echo "seed $(sha $SB) bytes $(wc -c < $SB | tr -d ' ') (AF_SEED $SB) f64 ${AF_F64:-0}"
  else echo "seed $(sha $SB) bytes $(wc -c < $SB | tr -d ' ') (lineage of be8898af, MEMORY-MAP M=16Mi)"; fi
  echo "kir $(sha $W/check.main.kir) bytes $(wc -c < $W/check.main.kir | tr -d ' ')"
  echo "code check.bin sha256 $(sha $W/check.bin) bytes $len offset $off"
  echo "command $W/amu-front sha256 $(sha $W/amu-front) bytes $(wc -c < $W/amu-front | tr -d ' ')"
  echo "loader-source sha256 $(sha $R/tools/kexe_loader.c)"
  echo "allow $ALLOW scope35 $SCOPE"
  echo "budgets string-pool $POOL pairs $PAIRS vectors $VECS vector-items $ITEMS cpu $CPU wall $WALL hashcons $HC"
  echo "libraries $(echo $deps | tr '\n' ' ')"; } > $W/amu-front.info

# ---- 5. no host processes ----
NP=$R/build/seed/noproc/noproc.dylib
if [ -f $NP ]; then
  step "no-host-processes"
  L=$W/noproc.log; rm -f $L; mkdir -p $W/empty-path
  printf '(ns t.ok (:export [main]))\n(defn main [] :i64 (+ 1 2))\n' > $W/np-ok.kotoba
  printf '(ns t.bad (:export [main]))\n(defn main [] :i64 (+ 1 "x"))\n' > $W/np-bad.kotoba
  for f in np-ok np-bad; do
    env -i PATH=$W/empty-path HOME=$HOME TMPDIR=/tmp NOPROC_LOG=$L DYLD_INSERT_LIBRARIES=$NP $W/amu-front check $W/$f.kotoba
    echo "  $f exit $?"
  done
  loaded=$(awk '$2 == "loaded"' $L | wc -l | tr -d ' ')
  calls=$(awk '$2 != "loaded" && $2 != "fork"' $L | wc -l | tr -d ' ')
  forks=$(awk '$2 == "fork"' $L | wc -l | tr -d ' ')
  v=FAIL; [ $loaded -eq 2 ] && [ $calls -eq 0 ] && [ $forks -eq 2 ] && v=PASS
  echo "no-host-processes: $v (interposer loaded in $loaded of 2 runs, program starts $calls, forks $forks)" | tee -a $W/amu-front.info
else
  echo "no-host-processes: SKIPPED (no $NP; run scripts/seed/no-host-processes.sh once to build it)"
fi
echo "built $W/amu-front"; cat $W/amu-front.info
