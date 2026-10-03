#!/bin/zsh
# scripts/seed/frontsrc/build-one-src.sh [--builder AMU] [work-dir] -- ONE amu image whose frontend is compiled FROM SOURCE
# by the seed (agent FRONTSRC, 2026-10-04). Same image shape as scripts/seed/emit/build-one.sh (amu-one), with the one
# difference that `kotoba.amu-front.check` and its whole require closure (kotoba.form, kotoba.compiler.frontend.analyze and
# the frontend below it) are compiled from their Kotoba source in separate mode (--emit-module), not from JVM kir-dump KIR.
# No java, node or nbb at any step; stage-0 is not used. BOOTSTRAP-TOOL (zsh, python3 for the farm/closure, cc + the C
# loader tools/kexe_loader.c for packaging).
#
#   1. tree: git HEAD's seed/ scripts/seed tools (archived), its split (seed/split/gen-split.py).
#   2. module list: scripts/seed/reach-twins.py over FS_REACH / FS_CP (default build/walls/reach-walls.txt and
#      build/walls/cp-walls.txt: the INTEGRATE inputs, kotoba-sema agent/walls-arena-f64 at /private/tmp/wt-WALLS-sema),
#      farmed into one root (scripts/seed/r6_scan.py farm); the closure of seed/amu-front/check.cljk's requires.
#   3. objects (KSEEDO1, separate mode), all written by ONE compiler C:
#        the frontend closure (dependency-first), kotoba.amu-front.check (seed/amu-front/check.cljk), the seed split
#        (`modules` order), amu.cli, amu.refactor, amu.compile (s/), amu.check (k/), amu.main (--entry; the entry is
#        seed/frontsrc/amu/main.kotoba = seed/amu-main's dispatcher + link/modules/extract-native routed to the seed driver).
#      C = the seed binary (default: rung r6l's recorded seed, checked against seed/rungs/r6l.record; FS_RUNG), or, with
#      --builder AMU, a packaged amu image (its `compile` command = the seed compiler linked into it): the self-rebuild.
#   4. link, extract-native (the seed binary; with --builder, the builder image's own link/extract-native), package with
#      tools/kexe_loader.c (KEXE_EMBEDDED, wires 3,35,37,38,39, never 20) -> <work>/amu-one-src (+ .info).
# Budgets: the frontend's desugar needs a pair arena of 16 Mi in the compiler (SEED_PAIRS=16777216, default here).
# Env: FS_SEED (compiler seed binary), FS_REACH, FS_CP, FS_K (kotoba-lang checkout for lang/compat).
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h:h}
builder=""; W=""
while [ $# -gt 0 ]; do
  case $1 in --builder) builder=${2:A}; shift 2 ;; -*) echo "usage: build-one-src.sh [--builder AMU] [work-dir]" >&2; exit 2 ;; *) W=$1; shift ;; esac
done
W=${W:-$R/build/frontsrc/one}; mkdir -p $W; W=${W:A}
SCOPE=${FS_SCOPE:-$R:/Users/junkawasaki/github/kotoba-lang/amu-embench:/private/tmp:/tmp}
export SEED_PAIRS=${SEED_PAIRS:-16777216}
sha() { shasum -a 256 $1 | cut -c1-64; }
die() { echo "build-one-src: FAIL: $*" >&2; exit 1; }
step() { echo "build-one-src: $* (load $(sysctl -n vm.loadavg | awk '{print $2}'))"; }

# ---- 1. tree + seed ----
# the compiler seed: rung $FS_RUNG's recorded seed (default r6l; REBUILD 2026-10-04, was r6j), its sha256 checked against
# seed/rungs/$FS_RUNG.record; first of build/seed-boot/<rung>/seed-1.bin (bootstrap.sh) and build/rebuild/seed-<rung>.bin.
# FS_SEED overrides (no record check).
RUNG=${FS_RUNG:-r6l}
SB=${FS_SEED:-$R/build/seed-boot/$RUNG/seed-1.bin}; [ -n "$FS_SEED" ] || [ -s $SB ] || SB=$R/build/rebuild/seed-$RUNG.bin
[ -n "$FS_SEED" ] || [ "$(sha $SB)" = "$(sed -n 's/^seed1_sha256 //p' $R/seed/rungs/$RUNG.record)" ] || die "$SB is not rung $RUNG's seed"
T=$W/tree; rm -rf $T; mkdir -p $T
git -C $R archive HEAD seed scripts/seed tools | tar -x -C $T || die "git archive"
python3 $T/seed/split/gen-split.py > $W/gen-split.log || die "gen-split"
A=$T/seed/amu-main   # the committed amu-main and amu-front (HEAD), not the worktree's in-flight edits
export SEED_REPO=$R SEED_BUILD=$W/sb; mkdir -p $SEED_BUILD; source $R/scripts/seed/lib.sh
run() { SEED_RESOURCES_35=$R:$W SEED_VECTOR_ITEMS=134217728 SEED_SECONDS=1800 seed_run "$@"; }
# compile <file> <ns> [flags..]: with the seed, or with the builder image (its `compile` routes to seed.main in-process)
comp() {
  local f=$1 nm=$2; shift 2
  if [ -n "$builder" ]; then
    KEXE_CAP_RESOURCES_35=$R:$W $builder compile $f --target aarch64-macos --emit-module "$@" --object-dir $O --output $O/$nm.kso
  else
    run $SB 0 compile $f --emit-module "$@" --object-dir $O --output $O/$nm.kso
  fi
}
# tool <cmd> args..: the seed driver's link / modules / extract-native, by the seed or by the builder image (amu.main routes
# them to the seed driver linked into it: seed/frontsrc/amu/main.kotoba)
tool() { if [ -n "$builder" ]; then $builder "$@"; else run $SB 0 "$@"; fi; }

# ---- 2. module list, farm, closure ----
REACH=${FS_REACH:-$R/build/walls/reach-walls.txt}; CP=${FS_CP:-$R/build/walls/cp-walls.txt}; K=${FS_K:-/private/tmp/wt-K-kotoba-lang}
( cd $R && python3 scripts/seed/reach-twins.py $REACH $CP $R $K ) > $W/list.txt 2> $W/list.err || die "reach-twins"
F=$W/farm; rm -rf $F; mkdir -p $F
python3 $R/scripts/seed/r6_scan.py farm $W/list.txt $F > $W/order.txt 2> $W/farm.err || die "farm"
for d in $(sed 's#/src/.*#/src#; s#/lang/compat/.*#/lang/compat#' $W/list.txt | sort -u); do
  echo "root $d $(git -C $d rev-parse --short HEAD 2>/dev/null) $(git -C $d status --short 2>/dev/null | grep -c .) dirty"; done > $W/roots.txt
python3 - $W/order.txt $R/seed/amu-front/check.cljk > $W/front-order.txt <<'EOF' || die "closure"
import re, sys
order = [l.split() for l in open(sys.argv[1]) if l.strip()]
deps = {o[0]: [d for d in o[2:] if d != '-'] for o in order}
src = open(sys.argv[2]).read()
req = re.findall(r'\[([a-z][\w.\-]*) :as', src[:src.index('(:schemas')])
need, todo = set(), list(req)
while todo:
    x = todo.pop()
    if x in need: continue
    if x not in deps: sys.exit('missing module ' + x)
    need.add(x); todo += deps[x]
for o in order:
    if o[0] in need: print(o[0], o[1])
EOF

# ---- 3. objects ----
O=$W/o; rm -rf $O; mkdir -p $O; : > $W/emit.log
step "frontend closure from source: $(wc -l < $W/front-order.txt | tr -d ' ') modules ($( awk '{print $2}' $W/front-order.txt | xargs cat | wc -l | tr -d ' ') lines)${builder:+ by $builder}"
while read nm p; do
  echo "== $nm" >> $W/emit.log
  comp $p $nm < /dev/null >> $W/emit.log 2>&1 || { tail -2 $W/emit.log; die "frontend module $nm"; }
done < $W/front-order.txt
comp $T/seed/amu-front/check.cljk kotoba.amu-front.check < /dev/null >> $W/emit.log 2>&1 || { tail -2 $W/emit.log; die "check.cljk"; }
S=$W/roots; rm -rf $S; mkdir -p $S/amu
cp $A/src/amu/*.kotoba $S/amu/; cp $A/k/amu/check.kotoba $S/amu/; cp $A/s/amu/compile.kotoba $S/amu/
cp $R/seed/frontsrc/amu/main.kotoba $S/amu/main.kotoba   # + link/modules/extract-native routes (self-rebuild)
SPLIT=$T/seed/split
tool modules $SPLIT/seed/main.kotoba --source-path $SPLIT > $W/modules.txt 2> $W/modules.log || die "seed modules"
step "seed split ($(wc -l < $W/modules.txt | tr -d ' ') modules) + 5 amu modules"
while read nm p; do comp $p $nm < /dev/null >> $W/emit.log 2>&1 || die "split $nm"; done < $W/modules.txt
# the amu.* library modules (every file but main), dependency-first by retry: a pass compiles what it can (E6025 = a
# require has no object yet); stop when a pass adds nothing
# only the amu.* modules amu.main reaches through its requires (src/ also holds REFAC's Kotoba-route refactor_*.kotoba,
# which need the kotoba-lang compat root and are not reached while src/amu/refactor.kotoba is the declared stub)
python3 - $S/amu > $W/amu-reach.txt <<'EOP' || die "amu closure"
import os, re, sys
d = sys.argv[1]; seen, todo = set(), ['main']
while todo:
    m = todo.pop()
    if m in seen: continue
    seen.add(m)
    src = open(os.path.join(d, m.replace('-', '_') + '.kotoba')).read()
    todo += [x for x in re.findall(r'\[amu\.([\w-]+)', src) if os.path.exists(os.path.join(d, x.replace('-', '_') + '.kotoba'))]
for m in sorted(seen - {'main'}): print(os.path.join(d, m.replace('-', '_') + '.kotoba'))
EOP
todo=(${(f)"$(cat $W/amu-reach.txt)"})
while [ ${#todo} -gt 0 ]; do
  left=()
  for f in $todo; do
    nm=amu.${${f:t:r}//_/-}
    comp $f $nm < /dev/null > $W/amu-try.log 2>&1 && cat $W/amu-try.log >> $W/emit.log || left+=($f)
  done
  [ ${#left} -eq ${#todo} ] && { cat $W/amu-try.log; die "amu modules: ${left}"; }
  todo=($left)
done
comp $S/amu/main.kotoba amu.main --entry < /dev/null >> $W/emit.log 2>&1 || die "amu.main"
( cd $O && shasum -a 256 *.kso ) > $W/objects.sha

# ---- 4. link, extract, package (the seed binary, or the builder image's seed driver) ----
step "link${builder:+ by the builder}"
tool link $O/amu.main.kso --object-dir $O --output $W/amu.kseed > $W/link.log 2>&1 || { cat $W/link.log; die "link"; }
off=$(tool extract-native $W/amu.kseed --symbol main --output $W/amu.bin | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
[ -n "$off" ] || die "extract-native"
D=$W/package; mkdir -p $D
len=$(wc -c < $W/amu.bin | tr -d ' ')
POOL=1073741824; PAIRS=67108864; VECS=67108864; ITEMS=134217728; CPU=1800; WALL=1800; HC=16; ALLOW=3,35,37,38,39
{ echo "/* generated by scripts/seed/frontsrc/build-one-src.sh from amu.bin -- do not edit */"
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
cc -O2 -std=c11 -I $D -include $D/kexe_embedded.h $R/tools/kexe_loader.c -o $W/amu-one-src.tmp 2> $D/cc.log || die "cc"
mv $W/amu-one-src.tmp $W/amu-one-src
deps=$(otool -L $W/amu-one-src | tail -n +2 | awk '{print $1}')
echo "$deps" | grep -vq '^/usr/lib/' && die "unexpected library dependency"
{ echo "label amu-one-src (amu.main: check REAL via the kotoba-sema frontend compiled FROM SOURCE by the seed, no kir-dump; compile REAL via the seed compiler from source; entry seed/frontsrc/amu/main.kotoba (amu.main + link/modules/extract-native); objects, link and extract by ${builder:-seed $(sha $SB | cut -c1-16)})"
  echo "compiler ${builder:+builder $builder $(sha $builder)} seed ${FS_SEED:+(FS_SEED) }${FS_SEED:-rung $RUNG} $(sha $SB) bytes $(wc -c < $SB | tr -d ' ')"
  echo "tree HEAD $(git -C $R rev-parse --short HEAD) pairs $SEED_PAIRS"
  cat $W/roots.txt
  for f in $S/amu/*.kotoba $T/seed/amu-front/check.cljk; do echo "source ${f:t} $(sha $f | cut -c1-16)"; done
  echo "frontend-closure $(wc -l < $W/front-order.txt | tr -d ' ') modules"
  echo "objects $(ls $O/*.kso | wc -l | tr -d ' ') bytes $(cat $O/*.kso | wc -c | tr -d ' ') sha-of-list $(sha $W/objects.sha)"
  echo "kseed $(sha $W/amu.kseed) bytes $(wc -c < $W/amu.kseed | tr -d ' ')"
  echo "code $(sha $W/amu.bin) bytes $len offset $off"
  echo "command $W/amu-one-src sha256 $(sha $W/amu-one-src) bytes $(wc -c < $W/amu-one-src | tr -d ' ')"
  echo "loader-source sha256 $(sha $R/tools/kexe_loader.c)"
  echo "allow $ALLOW scope35 $SCOPE"
  echo "budgets string-pool $POOL pairs $PAIRS vectors $VECS vector-items $ITEMS cpu $CPU wall $WALL hashcons $HC"
  echo "libraries $(echo $deps | tr '\n' ' ')"; } > $W/amu-one-src.info
cat $W/amu-one-src.info
