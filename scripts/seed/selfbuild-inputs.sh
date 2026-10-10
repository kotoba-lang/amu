#!/bin/zsh
# scripts/seed/selfbuild-inputs.sh <out-dir> -- durable inputs of scripts/seed/selfbuild.sh (agent claude, 2026-10-10).
# BOOTSTRAP-TOOL (zsh + git). It only chooses and copies input files; every verdict is the seed's.
#
# selfbuild.sh used to read three /private/tmp paths (the classpath file, a kotoba-lang worktree, the reach list) that
# are gone. This writes the same three inputs into <out-dir> from durable sources:
#
#   <out>/reach.txt     the module list: the paths of a recorded scan order (SB_ORDER, `ns path deps..` per line).
#                       reach-twins.py re-resolves every entry by namespace, so the listed path only names the module.
#   <out>/cp/src        the classpath snapshot: every file of the recorded farm (SB_FARM) that came from neither amu
#                       (path present in SB_AMU_SNAP:src) nor kotoba-lang lang/compat (path present in SB_KL_REV), then
#                       the SB_OVERLAY files (repo rev path, written at their src-relative path).
#   <out>/cp.txt        the classpath file naming <out>/cp/src (reach-twins takes the `/src` entries).
#   <out>/kotoba-lang   `lang/compat` and `lang/selfhost-compiler-grant.edn` of kotoba-lang SB_KL_REV (git archive).
#   <out>/inputs.txt    provenance: every rev resolved to a full commit, sha256 of the order and of each overlay.
#
# amu's own src is NOT copied: selfbuild.sh passes the live worktree (<amu-root>/src) as the amu root, so the roots are
# the loader's: classpath, amu src, kotoba-lang lang/compat (project_files.cljk resolve-module-file; a single `.kotoba`
# across roots stands in for the `.cljk` twins). No module is special-cased.
#
# Defaults (env): the seed17 snapshot of AGENT-ENV (wt/amu-seed17/build/seed17/inputs/scan: order.txt + src, from amu
# a93ee4068 with classpath roots osaho 660a544, kotoba-native 752cdf2, kotoba-sema c2e1343, ...), kotoba-lang
# 965c5f5 (lang/compat: the project and kotoba-reader twins; the refactor library is amu's own src since the fold), and the
# OVERLAY below.
emulate -L zsh
setopt pipefail
R=$(cd "$(dirname "$0")/../.." && pwd)
O=${1:?usage: selfbuild-inputs.sh <out-dir>}
GH=${GH:-/Users/junkawasaki/github}
SNAP=${SB_SNAP:-$GH/wt/amu-seed17/build/seed17/inputs/scan}
ORDER=${SB_ORDER:-$SNAP/order.txt}; FARM=${SB_FARM:-$SNAP/src}
AMU_SNAP=${SB_AMU_SNAP:-a93ee4068}
KL_REPO=${SB_KL_REPO:-$GH/kotoba-lang/kotoba-lang}; KL_REV=${SB_KL_REV:-965c5f5b2f574f6be8f0b9572ca6cd6bac28ce97}
# 2026-10-10 (final round): the dual-runtime-port-D commits the image needs, pinned by full commit (the repos' local
# branch refs may lag their remotes; a commit is what makes the farm reproducible): osaho 3d29ca9 (kir.admission takes
# Form policies: more than 32 grants no longer trap, a vector :allow is refused as on the host; interp/target as
# d2cc281), kotoba-mir e2cf973 (keyword lookups without a key Form), kotoba-native ca8bb09 (vt-put in place).
OVERLAY=${SB_OVERLAY:-"$GH/kotoba-lang/osaho 3d29ca9e56320837567d65120fc53b09bd88c83f src/kotoba/kir/interp.cljk
$GH/kotoba-lang/osaho 3d29ca9e56320837567d65120fc53b09bd88c83f src/kotoba/kir/target.cljk
$GH/kotoba-lang/osaho 3d29ca9e56320837567d65120fc53b09bd88c83f src/kotoba/kir/admission.cljk
$GH/kotoba-lang/kotoba-mir e2cf973cdda3c88d84f34b0a6e84d6ded93ed763 src/kotoba/mir.cljk
$GH/kotoba-lang/kotoba-native ca8bb098e349226d623c48c7eb267f44de52d711 src/kotoba/native/machine_ir.cljk"}
die() { echo "selfbuild-inputs: FAIL: $*" >&2; exit 1; }
for p in $ORDER $FARM; do [ -e $p ] || die "missing $p"; done
amu_c=$(git -C $R rev-parse --verify -q "$AMU_SNAP^{commit}") || die "amu snapshot commit $AMU_SNAP not in $R"
kl_c=$(git -C $KL_REPO rev-parse --verify -q "$KL_REV^{commit}") || die "kotoba-lang $KL_REV not in $KL_REPO"
mkdir -p $O; O=${O:A}; rm -rf $O/cp $O/kotoba-lang; mkdir -p $O/cp/src $O/kotoba-lang
# kotoba-lang
git -C $KL_REPO archive $kl_c lang/compat lang/selfhost-compiler-grant.edn | tar -x -C $O/kotoba-lang || die "archive $kl_c"
# classpath snapshot
typeset -A in_amu in_kl
for f in $(git -C $R ls-tree -r --name-only $amu_c src); do in_amu[${f#src/}]=1; done
for f in $(git -C $KL_REPO ls-tree -r --name-only $kl_c lang/compat); do in_kl[${f#lang/compat/}]=1; done
na=0; nk=0; nc=0
for f in $(cd $FARM && find . -type f | sed 's#^\./##' | sort); do
  if [ -n "${in_amu[$f]}" ]; then na=$((na+1))
  elif [ -n "${in_kl[$f]}" ]; then nk=$((nk+1))
  else mkdir -p $O/cp/src/${f:h}; cp $FARM/$f $O/cp/src/$f; nc=$((nc+1)); fi
done
{ echo "selfbuild-inputs $(date '+%F %T')"
  echo "order $ORDER sha256 $(shasum -a 256 $ORDER | cut -c1-64) modules $(grep -c . $ORDER)"
  echo "farm $FARM: $nc classpath files kept, $na amu files dropped (amu $amu_c), $nk kotoba-lang files dropped"
  echo "kotoba-lang $KL_REPO $KL_REV $kl_c"
} > $O/inputs.txt
print -r -- "$OVERLAY" | while read -r repo rev fpath; do
  [ -n "$repo" ] || continue
  c=$(git -C $repo rev-parse --verify -q "$rev^{commit}") || die "overlay rev $rev not in $repo"
  rel=${fpath#src/}; [ -f $O/cp/src/$rel ] || die "overlay $fpath replaces no classpath file"
  git -C $repo show $c:$fpath > $O/cp/src/$rel || die "overlay $repo $rev $fpath"
  echo "overlay ${repo:t} $c $fpath sha256 $(shasum -a 256 $O/cp/src/$rel | cut -c1-64)" >> $O/inputs.txt
done || exit 1
print -r -- "$O/cp/src" > $O/cp.txt
awk '{print $2}' $ORDER > $O/reach.txt
cat $O/inputs.txt
