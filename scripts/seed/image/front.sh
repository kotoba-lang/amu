#!/bin/zsh
# scripts/seed/image/front.sh SEED SCAN-OBJDIR TWINDIR OUT -- the --front object dir of the unified amu image (agent IMAGE,
# 2026-10-05). BOOTSTRAP-TOOL (zsh). Only the seed runs (no stage-0, JVM, node or nbb).
#   SEED         the compiler seed binary (offset 0), e.g. rung r6m's 8d3338e1
#   SCAN-OBJDIR  the objects of a selfbuild scan by the same seed (scripts/seed/selfbuild.sh --seed SEED --no-link: <w>/r6/o),
#                i.e. the frontend, kotoba.sema and kotoba-lang's compat twins compiled FROM SOURCE in separate mode
#   TWINDIR      kotoba-lang lang/compat/kotoba/compiler holding project.kotoba / project_files.kotoba (the project route's
#                guest twins); they are recompiled here so a twin newer than the scan's is what the image links
#   OUT          the object dir written (scan objects, the product entries included; project twins from TWINDIR, + kotoba.amu-front.check)
# FRONT_BUILDER=<amu image> (the self-rebuild): every object is compiled again here by that image's `compile --emit-module`
# (its internal module compiler: the seed compiler linked into it; the product `compile` is nbb.cli's) from the scan's farm sources (SCAN-OBJDIR/../src, in SCAN-OBJDIR/../order.txt order), not copied.
emulate -L zsh; setopt pipefail; renice -n 10 $$ > /dev/null
S=${1:?seed}; O0=${2:?scan objdir}; TW=${3:?twindir}; O=${4:?out}; H=${0:A:h}; R=${H:h:h:h}
S=${S:A}; O0=${O0:A}; TW=${TW:A}; mkdir -p $O; O=${O:A}
export SEED_REPO=$R SEED_BUILD=$O.sb SEED_PAIRS=${SEED_PAIRS:-16777216} SEED_RESOURCES_35=$R:$O:$O.sb:$TW:${O0:h}/src SEED_SECONDS=1800 SEED_VECTOR_ITEMS=134217728
mkdir -p $SEED_BUILD; source $R/scripts/seed/lib.sh
die() { echo "front: FAIL: $*" >&2; exit 1; }
rm -f $O/*.kso(N)
B=${FRONT_BUILDER:+${FRONT_BUILDER:A}}
c() {
  if [ -n "$B" ]; then
    KEXE_CAP_RESOURCES_35=$SEED_RESOURCES_35 $B compile $1 --target aarch64-macos --emit-module --object-dir $O --output $O/$2.kso > $O.sb/$2.log 2>&1
  else seed_run $S 0 compile $1 --emit-module --object-dir $O --output $O/$2.kso > $O.sb/$2.log 2>&1; fi || die "$2: $(grep -m1 -E 'seed: E|error' $O.sb/$2.log)"
}
# 2026-10-10 (product entries): nbb.check-cli and nbb.check-driver are no longer skipped: the image's `check` is
# check-cli's Kotoba `run` and its `compile` aarch64-cli's (seed/amu-main k/amu/check, l/amu/compile).
skip() { case $1 in amu.*|seed.*) return 0 ;; esac; return 1; }
# 2026-10-10 (fixed point on the integration sources): the scan now holds nbb.cli's Kotoba twin, whose closure needs
# kotoba.compiler.effect-row (via native-artifact) and the project twins (via nbb.cli). So the effect modules are no longer
# skipped, and the project twins are compiled from TWINDIR at their place in the scan order instead of after the loop.
src() { case $1 in kotoba.compiler.project) echo $TW/project.kotoba ;; kotoba.compiler.project-files) echo $TW/project_files.kotoba ;; *) echo $2 ;; esac; }
# Recompile initial-generation inputs too: the scan objects select the closure,
# but are never used as an unverified cache of its code.
while read nm p rest; do
  skip $nm || { [ -s $O0/$nm.kso ] && c $(src $nm $p) $nm < /dev/null; }
done < $O0/../order.txt
[ -s $O/kotoba.compiler.project.kso ] || c $TW/project.kotoba kotoba.compiler.project
[ -s $O/kotoba.compiler.project-files.kso ] || c $TW/project_files.kotoba kotoba.compiler.project-files
c $R/seed/amu-front/check.cljk kotoba.amu-front.check
echo "front: ${B:+builder $B $(shasum -a 256 $B | cut -c1-16), }$(ls $O/*.kso | wc -l | tr -d ' ') objects, seed $(shasum -a 256 $S | cut -c1-16), project twins $(shasum -a 256 $TW/project.kotoba $TW/project_files.kotoba | cut -c1-64 | tr '\n' ' '), scan $O0"
