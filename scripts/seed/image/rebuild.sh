#!/bin/zsh
# BOOTSTRAP-TOOL. Rebuild the unified image (seed rung r6n, was r6m) for three generations from a
# content-pinned selfbuild scan and compat snapshot. No stage-0 in these builds.
# Usage: rebuild.sh INPUTS OUT
# INPUTS: scan/{src,order.txt,o}, kotoba-lang/lang/compat.
# Run inside a worktree whose build/seed-boot/r6n/seed-1.bin matches r6n.record (2026-10-10: r6n's extract-native reads
# a container over 8 MiB in windows; the image with the product entries is 10.98 MB, which r6m's seed cannot extract).
# A candidate uses REBUILD_SEED plus REBUILD_SEED_SHA256; both frontend and
# launcher compilation use that pinned seed. The default record is unchanged.
emulate -L zsh
setopt pipefail nullglob
R=${0:A:h:h:h:h}
I=${1:?usage: rebuild.sh INPUTS OUT}; I=${I:A}
W=${2:?output}; mkdir -p $W; W=${W:A}
[[ $W != $I && $W != $R && $W != "$I"/* && $I != "$W"/* ]] \
  || { echo 'input and output directories must be disjoint' >&2; exit 2; }
S=${REBUILD_SEED:-$R/build/seed-boot/r6n/seed-1.bin}
if [ -n "$REBUILD_SEED" ]; then
  want=${REBUILD_SEED_SHA256:-}
  [[ $want =~ '^[0-9a-f]{64}$' ]] || { echo 'custom seed requires its explicit SHA-256 pin' >&2; exit 2; }
else
  want=$(sed -n 's/^seed1_sha256 //p' $R/seed/rungs/r6n.record)
fi
got=$(shasum -a 256 $S | awk '{print $1}')
[[ -n $want && $got = $want ]] || { echo 'missing/mismatched pinned seed' >&2; exit 2; }
for f in $I/scan/order.txt $I/kotoba-lang/lang/compat/kotoba/compiler/project.kotoba \
         $I/kotoba-lang/lang/compat/kotoba/compiler/project_files.kotoba; do
  [ -s $f ] || { echo "missing input $f" >&2; exit 2; }
done
[ ! -e $W/inputs ] || { echo "output already has inputs: $W" >&2; exit 2; }
cp -R $I $W/inputs || exit 2
# The farm retains each source's original extension. Rebase only path metadata,
# never compiler source text. Every listed path must name a copied source file.
while read nm p deps; do
  suffix=${p#*/src/}
  [ "$suffix" != "$p" ] && [ -s $W/inputs/scan/src/$suffix ] || { echo "bad farm path $p" >&2; exit 2; }
  printf '%s %s %s\n' "$nm" "$W/inputs/scan/src/$suffix" "$deps"
done < $I/scan/order.txt > $W/inputs/scan/order.txt
find $W/inputs -type f -exec shasum -a 256 {} + | LC_ALL=C sort > $W/inputs.sha256
K=$W/inputs/kotoba-lang
# The refactor library (2026-10-10): kotoba-lang's twins when the snapshot's lang/compat carries them, else amu's own
# folded src/kotoba/compiler/refactor from the scan farm (LAUNCHER_REFACTOR_SRC).
if [ -d $K/lang/compat/kotoba/compiler/refactor ]; then refactor_env="LAUNCHER_REFACTOR=$K"
else refactor_env="LAUNCHER_REFACTOR_SRC=$W/inputs/scan/src"; fi
echo "refactor library: $refactor_env"
# Generation 0 (2026-10-10) is the bootstrap: the pinned seed compiles everything. Its image links the compiler of the
# tree's seed/ sources, which may be newer than the seed binary (since r6m: seed/41-a64gen, 42-layout, 60-proj), so g0
# can differ from g1. Generations 1-3 are each built by the previous generation's image and must be byte-identical.
for g in 0 1 2 3; do
  previous=$((g - 1)); builder=""; args=()
  if [ $g -gt 0 ]; then builder=$W/g$previous/amu; args=(--builder $builder); fi
  FRONT_BUILDER=$builder zsh $R/scripts/seed/image/front.sh $S $W/inputs/scan/o \
    $K/lang/compat/kotoba/compiler $W/front$g > $W/front$g.out 2>&1 || exit 1
  env LAUNCHER_SEED=$S $refactor_env zsh $R/scripts/seed/launcher/build.sh $args --front $W/front$g \
    $W/g$g > $W/g$g.out 2>&1 || exit 1
done
for f in amu amu.bin amu.kseed; do
  cmp -s $W/g1/$f $W/g2/$f && cmp -s $W/g2/$f $W/g3/$f || { echo "FAIL generations differ: $f"; exit 1; }
done
for g in 0 1 2 3; do
  (cd $W/g$g/o && for f in *.kso; do shasum -a 256 $f; done) > $W/objects$g.sha || exit 1
done
cmp -s $W/g0/amu $W/g1/amu && echo 'g0 (seed-built) = g1' || echo 'g0 (seed-built) differs from g1: the tree seed/ compiler differs from the pinned seed'
cmp -s $W/objects1.sha $W/objects2.sha && cmp -s $W/objects2.sha $W/objects3.sha || { echo 'FAIL object content differs'; exit 1; }
(cd $R && shasum -a 256 -c $W/inputs.sha256 > $W/input-check.log) || exit 1
echo "PASS 3 generations (objects, container, native code, command); $(shasum -a 256 $W/g3/amu)"
