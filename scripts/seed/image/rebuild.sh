#!/bin/zsh
# BOOTSTRAP-TOOL. Rebuild r6m's unified image for three generations from a
# content-pinned selfbuild scan and compat snapshot. No stage-0 in these builds.
# Usage: rebuild.sh INPUTS OUT
# INPUTS: scan/{src,order.txt,o}, kotoba-lang/lang/compat.
# Run inside a worktree whose build/seed-boot/r6m/seed-1.bin matches r6m.record.
emulate -L zsh
setopt pipefail nullglob
R=${0:A:h:h:h:h}
I=${1:?usage: rebuild.sh INPUTS OUT}; I=${I:A}
W=${2:?output}; mkdir -p $W; W=${W:A}
[[ $W != $I && $W != $R && $W != "$I"/* && $I != "$W"/* ]] \
  || { echo 'input and output directories must be disjoint' >&2; exit 2; }
S=$R/build/seed-boot/r6m/seed-1.bin
want=$(sed -n 's/^seed1_sha256 //p' $R/seed/rungs/r6m.record)
got=$(shasum -a 256 $S | awk '{print $1}')
[[ -n $want && $got = $want ]] || { echo 'missing/mismatched recorded r6m seed' >&2; exit 2; }
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
for g in 1 2 3; do
  previous=$((g - 1)); builder=""; args=()
  if [ $g -gt 1 ]; then builder=$W/g$previous/amu; args=(--builder $builder); fi
  FRONT_BUILDER=$builder zsh $R/scripts/seed/image/front.sh $S $W/inputs/scan/o \
    $K/lang/compat/kotoba/compiler $W/front$g > $W/front$g.out 2>&1 || exit 1
  LAUNCHER_REFACTOR=$K zsh $R/scripts/seed/launcher/build.sh $args --front $W/front$g \
    $W/g$g > $W/g$g.out 2>&1 || exit 1
done
for f in amu amu.bin amu.kseed; do
  cmp -s $W/g1/$f $W/g2/$f && cmp -s $W/g2/$f $W/g3/$f || { echo "FAIL generations differ: $f"; exit 1; }
done
for g in 1 2 3; do
  (cd $W/g$g/o && for f in *.kso; do shasum -a 256 $f; done) > $W/objects$g.sha || exit 1
done
cmp -s $W/objects1.sha $W/objects2.sha && cmp -s $W/objects2.sha $W/objects3.sha || { echo 'FAIL object content differs'; exit 1; }
(cd $R && shasum -a 256 -c $W/inputs.sha256 > $W/input-check.log) || exit 1
echo "PASS 3 generations (objects, container, native code, command); $(shasum -a 256 $W/g3/amu)"
