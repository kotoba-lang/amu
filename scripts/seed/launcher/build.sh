#!/bin/zsh
# scripts/seed/launcher/build.sh [--front DIR] [--worktree] [--builder AMU] [work-dir] -- the NATIVE `amu` launcher: one Mach-O that is the
# product command (agent CMD, 2026-10-04; design seed/amu-main/LAUNCHER.md). BOOTSTRAP-TOOL (zsh, python3, cc).
#
# The launcher is not a second program in front of the compiler: it is the C loader tools/kexe_loader.c with the
# seed-built code of amu.main embedded (KEXE_EMBEDDED). amu.main does bin/amu's routing itself (usage text, --jvm-free,
# the host --target default, check / compile / refactor / link / modules / extract-native, named stubs for the rest), so
# `amu <args>` runs as ONE process (plus the loader's supervisor fork) with no node, nbb, JVM or shell.
#
#   1. tree: git HEAD's seed/ (archived; --worktree takes seed/amu-main from the worktree instead; LAUNCHER_OVERLAY="a b"
#      takes only those seed/amu-main paths from the worktree), its split
#      (seed/split/gen-split.py) + seed/amu-main/patch-split.py (no-op once seed.main exports drv-compile-file).
#   2. objects (KSEEDO1, separate mode): the frontend closure + kotoba.amu-front.check are taken from --front DIR (default
#      build/frontsrc/two/o: objects compiled FROM SOURCE by scripts/seed/frontsrc/build-one-src.sh, no kir-dump); the seed
#      split, the amu.* modules amu.main reaches (src/, l/compile = the launcher's compile, k/check) and amu.main (--entry)
#      are compiled here by the seed (rung r6m's recorded seed, checked against seed/rungs/r6m.record; LAUNCHER_RUNG /
#      LAUNCHER_SEED), or with --builder AMU by that packaged image (the self-rebuild); LAUNCHER_REFACTOR adds the refactor
#      route (see below).
#   3. link, extract-native main (the seed, or the builder), package (KEXE_EMBEDDED; wires 3,35,37,38,39, never 20; amu-one's budgets)
#      -> <work>/amu (+ amu.info).
# Default work dir build/launcher. Then: zsh seed/amu-main/usage-parity.sh <work>/amu, seed/amu-main/parity.sh.
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h:h}
FRONT=$R/build/frontsrc/two/o; WT=""; W=""; builder=""
while [ $# -gt 0 ]; do
  case $1 in --front) FRONT=${2:A}; shift 2 ;; --worktree) WT=1; shift ;; --builder) builder=${2:A}; shift 2 ;;
    -*) echo "usage: build.sh [--front DIR] [--worktree] [--builder AMU] [work-dir]" >&2; exit 2 ;; *) W=$1; shift ;; esac
done
W=${W:-$R/build/launcher}; mkdir -p $W; W=${W:A}
SCOPE=${LAUNCHER_SCOPE:-$R:/Users/junkawasaki/github/kotoba-lang/amu-embench:/private/tmp:/tmp}
export SEED_PAIRS=${SEED_PAIRS:-16777216}
sha() { shasum -a 256 $1 | cut -c1-64; }
die() { echo "launcher: FAIL: $*" >&2; exit 1; }
step() { echo "launcher: $* (load $(sysctl -n vm.loadavg | awk '{print $2}'))"; }

# rung $LAUNCHER_RUNG's recorded seed (default r6m; IMAGE 2026-10-05, was r6l), checked against its record; first of
# build/seed-boot/<rung>/seed-1.bin, build/image/seed-<rung>.bin and build/rebuild/seed-<rung>.bin. LAUNCHER_SEED
# overrides (no record check).
RUNG=${LAUNCHER_RUNG:-r6m}
SB=${LAUNCHER_SEED:-$R/build/seed-boot/$RUNG/seed-1.bin}
[ -n "$LAUNCHER_SEED" ] || [ -s $SB ] || SB=$R/build/image/seed-$RUNG.bin
[ -n "$LAUNCHER_SEED" ] || [ -s $SB ] || SB=$R/build/rebuild/seed-$RUNG.bin
[ -n "$LAUNCHER_SEED" ] || [ "$(sha $SB)" = "$(sed -n 's/^seed1_sha256 //p' $R/seed/rungs/$RUNG.record)" ] || die "$SB is not rung $RUNG's seed"
[ -s $FRONT/kotoba.amu-front.check.kso ] || die "no frontend objects in $FRONT (run scripts/seed/frontsrc/build-one-src.sh)"
T=$W/tree; rm -rf $T; mkdir -p $T
git -C $R archive HEAD seed | tar -x -C $T || die "git archive"
if [ -n "$WT" ]; then rm -rf $T/seed/amu-main; cp -R $R/seed/amu-main $T/seed/amu-main; fi
for f in ${=LAUNCHER_OVERLAY:-}; do cp $R/seed/amu-main/$f $T/seed/amu-main/$f || die "overlay $f"; done
python3 $T/seed/split/gen-split.py > $W/gen-split.log || die "gen-split"
PATCH=$(python3 $T/seed/amu-main/patch-split.py $T/seed/split) || die "patch-split: $PATCH"
export SEED_REPO=$R SEED_BUILD=$W/sb; mkdir -p $SEED_BUILD; source $R/scripts/seed/lib.sh
run() { SEED_RESOURCES_35=$R:$W${RK:+:$RK} SEED_VECTOR_ITEMS=134217728 SEED_SECONDS=1800 seed_run "$@"; }
O=$W/o; rm -rf $O; mkdir -p $O; : > $W/emit.log
# --builder AMU (REBUILD): every compile, modules, link and extract-native is done by a packaged amu image (its `compile`
# = the seed compiler linked into it, `modules` / `link` / `extract-native` = its seed driver): the launcher rebuilds itself
comp() {
  local f=$1 nm=$2; shift 2
  if [ -n "$builder" ]; then
    KEXE_CAP_RESOURCES_35=$R:$W${RK:+:$RK} $builder compile $f --target aarch64-macos --emit-module "$@" --object-dir $O --output $O/$nm.kso
  else run $SB 0 compile $f --emit-module "$@" --object-dir $O --output $O/$nm.kso; fi
}
tool() { if [ -n "$builder" ]; then KEXE_CAP_RESOURCES_35=$R:$W${RK:+:$RK} $builder "$@"; else run $SB 0 "$@"; fi; }

# ---- frontend objects (FRONTSRC, from source) ----
nf=0
for k in $FRONT/*.kso; do case ${k:t} in seed.*|amu.*) ;; *) cp $k $O/; nf=$((nf + 1)) ;; esac; done
step "frontend: $nf objects from $FRONT"
# ---- seed split ----
SPLIT=$T/seed/split
tool modules $SPLIT/seed/main.kotoba --source-path $SPLIT > $W/modules.txt 2> $W/modules.log || die "seed modules"
step "seed split: $(wc -l < $W/modules.txt | tr -d ' ') modules ($PATCH)"
while read nm p; do comp $p $nm < /dev/null >> $W/emit.log 2>&1 || { tail -2 $W/emit.log; die "split $nm"; }; done < $W/modules.txt
# ---- amu modules (dependency-first by retry, as build-one-src.sh) ----
A=$T/seed/amu-main; S=$W/roots; rm -rf $S; mkdir -p $S/amu
cp $A/src/amu/*.kotoba $S/amu/; cp $A/k/amu/check.kotoba $S/amu/; cp $A/l/amu/compile.kotoba $S/amu/
# LAUNCHER_REFACTOR=<kotoba-lang checkout> (REBUILD, opt-in): the unified image's refactor route: src/amu/refactor.kotoba
# is replaced by the one-line delegate to amu.refactor-cli (as scripts/seed/refactor/build-image.sh), the refactor library
# closure of <root>/lang/compat (seed `modules` of refactor_cli.kotoba) is compiled to objects here, and wire 34
# (:fs/browse, scoped as 35) is added to the baked wire list. Still never 20.
RK=${LAUNCHER_REFACTOR:+${LAUNCHER_REFACTOR:A}}
if [ -n "$RK" ]; then
  [ -d $RK/lang/compat/kotoba/compiler/refactor ] || die "LAUNCHER_REFACTOR: no lang/compat refactor library in $RK"
  printf '(ns amu.refactor\n  {:kotoba/export [run]}\n  (:require [amu.refactor-cli :as rc]))\n\n;; `amu refactor`: the Kotoba-route dispatcher amu.refactor-cli (scripts/seed/launcher/build.sh LAUNCHER_REFACTOR)\n(defn run [] :i64 (rc/run))\n' > $S/amu/refactor.kotoba
  tool modules $S/amu/refactor_cli.kotoba --source-path $S --source-path $RK/lang/compat > $W/refactor-modules.txt 2> $W/refactor-modules.log \
    || { cat $W/refactor-modules.log; die "refactor modules"; }
  nk=0
  while read nm p; do
    case $p in $RK/*) comp $p $nm < /dev/null >> $W/emit.log 2>&1 || { tail -2 $W/emit.log; die "refactor library $nm"; }; nk=$((nk + 1)) ;; esac
  done < $W/refactor-modules.txt
  step "refactor library: $nk modules from $RK/lang/compat ($(git -C $RK rev-parse --short HEAD 2>/dev/null))"
fi
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
step "amu: ${#todo} modules + amu.main"
while [ ${#todo} -gt 0 ]; do
  left=()
  for f in $todo; do
    nm=amu.${${f:t:r}//_/-}
    comp $f $nm < /dev/null > $W/amu-try.log 2>&1 && cat $W/amu-try.log >> $W/emit.log || left+=($f)
  done
  [ ${#left} -eq ${#todo} ] && { cat $W/amu-try.log; die "amu modules: ${left}"; }
  todo=($left)
done
comp $S/amu/main.kotoba amu.main --entry < /dev/null >> $W/emit.log 2>&1 || { tail -2 $W/emit.log; die "amu.main"; }
( cd $O && shasum -a 256 *.kso ) > $W/objects.sha
# ---- link, extract, package ----
step "link${builder:+ by the builder}"
tool link $O/amu.main.kso --object-dir $O --output $W/amu.kseed > $W/link.log 2>&1 || { cat $W/link.log; die "link"; }
off=$(tool extract-native $W/amu.kseed --symbol main --output $W/amu.bin | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
[ -n "$off" ] || die "extract-native"
D=$W/package; mkdir -p $D
len=$(wc -c < $W/amu.bin | tr -d ' ')
POOL=1073741824; PAIRS=67108864; VECS=67108864; ITEMS=134217728; CPU=1800; WALL=1800; HC=16; ALLOW=3,35,37,38,39; SCOPE34=""; KGRAPH=1048576  # kgraph datoms: the frontend keeps run-time keyword texts there (docs/selfhost-kgraph-capacity-20261008.md)
RDESC="seed/amu-main/src/amu/refactor.kotoba"
[ -n "$RK" ] && { ALLOW=3,34,35,37,38,39; SCOPE34=$SCOPE; RDESC="Kotoba route amu.refactor-cli + $RK/lang/compat $(git -C $RK rev-parse --short HEAD 2>/dev/null)"; }
{ echo "/* generated by scripts/seed/launcher/build.sh from amu.bin -- do not edit */"
  echo "#include <stdlib.h>"
  echo "#define KEXE_EMBEDDED 1"
  echo "#define KEXE_EMBEDDED_OFFSET ${off}u"
  echo "#define KEXE_EMBEDDED_ARITY 0u"
  echo "#define KEXE_EMBEDDED_ISA \"aarch64\""
  echo "#define KEXE_EMBEDDED_ALLOW \"$ALLOW\""
  echo "#define KEXE_EMBEDDED_SCOPE35 \"$SCOPE\""
  echo "#define KEXE_EMBEDDED_SCOPE34 \"$SCOPE34\""
  echo "#define KEXE_EMBEDDED_SPAWN_PROGRAMS \"\""
  echo "#define KEXE_EMBEDDED_SPAWN_ENV \"\""
  echo "#define KEXE_EMBEDDED_SPAWN_PATH_LOOKUP 0"
  echo "#define KEXE_EMBEDDED_STRING_POOL ${POOL}u"
  echo "#define KEXE_EMBEDDED_FUEL 0u"
  echo "#define KEXE_EMBEDDED_PAIRS ${PAIRS}u"
  echo "#define KEXE_EMBEDDED_VECTORS ${VECS}u"
  echo "#define KEXE_EMBEDDED_VECTOR_ITEMS ${ITEMS}u"
  echo "#define KEXE_EMBEDDED_KGRAPH ${KGRAPH}u"
  echo "#define KEXE_EMBEDDED_CPU_SECONDS ${CPU}u"
  echo "#define KEXE_EMBEDDED_WALL_SECONDS ${WALL}u"
  echo "__attribute__((constructor)) static void amu_launcher_hashcons(void) { setenv(\"KEXE_HASHCONS\", \"$HC\", 0); }"
  echo "static const unsigned char kexe_embedded_code[$len] = {"
  xxd -i < $W/amu.bin
  echo "};"; } > $D/kexe_embedded.h
cc -O2 -std=c11 -I $D -include $D/kexe_embedded.h $R/tools/kexe_loader.c -o $W/amu.tmp 2> $D/cc.log || die "cc"
mv $W/amu.tmp $W/amu
deps=$(otool -L $W/amu | tail -n +2 | awk '{print $1}')
echo "$deps" | grep -vq '^/usr/lib/' && die "unexpected library dependency"
{ echo "label amu native launcher (amu.main: bin/amu's launcher layer + check REAL (frontend objects from $FRONT, compiled from source by the seed) + compile REAL (seed compiler from source, :kotoba.kexe/v1) + refactor ($RDESC); no node, nbb, JVM or shell at run time)"
  echo "compiler ${builder:+builder $builder $(sha $builder) }seed ${LAUNCHER_SEED:+(LAUNCHER_SEED)}${LAUNCHER_SEED:-rung $RUNG} $(sha $SB) bytes $(wc -c < $SB | tr -d ' ')"
  echo "tree HEAD $(git -C $R rev-parse --short HEAD)${WT:+ + worktree seed/amu-main}${LAUNCHER_OVERLAY:+ + worktree $LAUNCHER_OVERLAY} ($PATCH)"
  for f in $S/amu/*.kotoba; do echo "source amu/${f:t} $(sha $f | cut -c1-16)"; done
  echo "front $FRONT $nf objects $(cat $FRONT/*.kso | shasum -a 256 | cut -c1-16)"
  echo "objects $(ls $O/*.kso | wc -l | tr -d ' ') bytes $(cat $O/*.kso | wc -c | tr -d ' ')"
  echo "kseed $(sha $W/amu.kseed) bytes $(wc -c < $W/amu.kseed | tr -d ' ')"
  echo "code $(sha $W/amu.bin) bytes $len offset $off"
  echo "command $W/amu sha256 $(sha $W/amu) bytes $(wc -c < $W/amu | tr -d ' ')"
  echo "loader-source sha256 $(sha $R/tools/kexe_loader.c)"
  echo "allow $ALLOW scope35 $SCOPE${SCOPE34:+ scope34 $SCOPE34}"
  echo "budgets string-pool $POOL pairs $PAIRS vectors $VECS vector-items $ITEMS cpu $CPU wall $WALL hashcons $HC kgraph $KGRAPH"
  echo "libraries $(echo $deps | tr '\n' ' ')"; } > $W/amu.info
cat $W/amu.info
