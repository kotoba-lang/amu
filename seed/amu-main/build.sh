#!/bin/zsh
# seed/amu-main/build.sh [--route s|k|both] [work-dir] -- build the `amu` command as ONE Kotoba entry (agent MAINS, 2026-10-04;
# seed/amu-main/README.md). BOOTSTRAP-TOOL (zsh; python3 and java only in route k's KIR step).
#
# Route s (SOURCE, selfhost-built, no stage-0 / JVM / node at any step): the seed (default: rung r6j's seed 4b2498ec, its
#   own fixed point (CMD 2026-10-04; was r6f da6d0a98); AM_SEED=<seed.bin> with .offset beside it overrides) compiles seed/amu-main/src/amu/main.kotoba in the
#   project route with --source-path src, s, seed/split (the seed's own source split into namespaces: amu.compile links
#   the whole seed compiler in-process; the split copy gets seed/amu-main/patch-split.py, a no-op once seed.main defines
#   drv-compile-file) -> kseed; extract-native main; package with tools/kexe_loader.c (KEXE_EMBEDDED, scripts/seed/package.sh,
#   wires 3,35,37,38,39 (3 = :hash/sha256 for the kexe/v1 seal), never 20) -> <work>/amu-s.
# Route k (KIR, BOOTSTRAP-labelled at build time): the same dispatcher with k/amu/check.kotoba (calls the frontend's
#   analyze through seed/amu-front/check.cljk) -> KIR by scripts/selfhost-wall/kir-dump.clj on the JVM-built classes
#   (BOOTSTRAP-REFERENCE, build time only) -> seed compile-kir with the large-M seed profile (AM_SEED_K) -> <work>/amu-k.
#   See seed/amu-main/build-k.sh.
# Output: <work>/amu-s (+ amu-s.info), default work dir build/mains.
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h}
route=s; W=""
while [ $# -gt 0 ]; do
  case $1 in --route) route=$2; shift 2 ;; -*) echo "usage: build.sh [--route s|k|both] [work-dir]" >&2; exit 2 ;; *) W=$1; shift ;; esac
done
W=${W:-$R/build/mains}; mkdir -p $W; W=${W:A}
sha() { shasum -a 256 $1 | cut -c1-64; }
if [ $route = k ] || [ $route = both ]; then zsh $H/build-k.sh $W || exit 1; [ $route = k ] && exit 0; fi

want=$(sed -n 's/^seed1_sha256 //p' $R/seed/rungs/r6j.record)
SB=${AM_SEED:-}
if [ -z "$SB" ]; then
  for c in $W/seed-1.bin $R/build/float/seed-1.bin $R/build/let/b/seed-1.bin $R/build/seed-boot/r6j/seed-1.bin; do
    [ -s $c ] && [ "$(sha $c)" = "$want" ] && { SB=$c; break; }; done
  [ -n "$SB" ] || { echo "amu-main: no r6j seed ($want); run scripts/seed/bootstrap.sh or set AM_SEED" >&2; exit 1; }
fi
SB=${SB:A}; SOFF=$(cat ${SB%.bin}.offset 2>/dev/null || echo 0)
label="rung r6j"; [ "$(sha $SB)" = "$want" ] || label="unrecorded seed"
# the seed's split source from git HEAD (other agents edit seed/*.kotoba in the worktree): an archived copy, checked to be
# the split of that commit's MANIFEST
T=$W/tree; rm -rf $T; mkdir -p $T; git -C $R archive HEAD seed/split seed/MANIFEST seed/*.kotoba | tar -x -C $T || exit 1
python3 $T/seed/split/gen-split.py --check || { echo "amu-main: seed/split is not the split of HEAD's seed/MANIFEST" >&2; exit 1; }
SPLIT=$T/seed/split; HEADREV=$(git -C $R rev-parse --short HEAD)
PATCH=$(python3 $H/patch-split.py $SPLIT) || { echo "amu-main: $PATCH" >&2; exit 1; }; echo "amu-main: $PATCH"

S=$W/s; rm -rf $S; mkdir -p $S
# the amu sources: the worktree's seed/amu-main/{src,s}, except the paths in AM_FROM_HEAD (space separated, relative to
# seed/amu-main, e.g. "src/amu/refactor.kotoba"), taken from git HEAD (another agent's file in progress) (CMD, 2026-10-04)
AS=$W/am; rm -rf $AS; mkdir -p $AS; cp -R $H/src $H/s $AS/
for f in ${=AM_FROM_HEAD:-}; do git -C $R show HEAD:seed/amu-main/$f > $AS/$f || exit 1; done
export SEED_BUILD=$S SEED_RESOURCES_35=$R SEED_VECTOR_ITEMS=67108864 SEED_SECONDS=900
source $R/scripts/seed/lib.sh
echo "amu-main: route s: seed $(sha $SB | cut -c1-16) ($label) compiles the entry (load $(sysctl -n vm.loadavg | awk '{print $2}'))"
nice zsh -c "source $R/scripts/seed/lib.sh; seed_run $SB $SOFF compile $AS/src/amu/main.kotoba --source-path $AS/src --source-path $AS/s \
  --source-path $SPLIT --unpinned --target aarch64-macos --output $S/amu.kseed" > $S/compile.log 2>&1 \
  || { echo "amu-main: compile failed:"; tail -3 $S/compile.log; exit 1; }
nice zsh -c "source $R/scripts/seed/lib.sh; seed_run $SB $SOFF extract-native $S/amu.kseed --symbol main --output $S/seed-1.bin" > $S/extract.log 2>&1 \
  || { echo "amu-main: extract-native failed:"; tail -3 $S/extract.log; exit 1; }
sed -n 's/.*:offset \([0-9]*\).*/\1/p' $S/extract.log > $S/seed-1.offset
[ -s $S/seed-1.offset ] || { echo "amu-main: no offset"; exit 1; }
SEED_BUILD=$S zsh $R/scripts/seed/package.sh 1 --out $W/amu-s --allow 3,35,37,38,39 \
  --scope "$R:/Users/junkawasaki/github/kotoba-lang/amu-embench:/private/tmp:/tmp" > $S/package.log 2>&1 \
  || { echo "amu-main: package failed:"; tail -3 $S/package.log; exit 1; }
deps=$(otool -L $W/amu-s | tail -n +2 | awk '{print $1}')
{ echo "label amu-s (amu.main, SOURCE route: every byte compiled by seed $(sha $SB | cut -c1-16) ($label) from source; no stage-0, JVM or node)"
  echo "seed $(sha $SB) bytes $(wc -c < $SB | tr -d ' ')"
  for f in $AS/src/amu/*.kotoba $AS/s/amu/*.kotoba; do echo "source ${f#$AS/} $(sha $f | cut -c1-16) lines $(wc -l < $f | tr -d ' ')"; done
  echo "split seed/split/seed at $HEADREV (gen-split --check OK; $PATCH) $(cat $SPLIT/seed/*.kotoba | shasum -a 256 | cut -c1-16)"
  echo "kseed $(sha $S/amu.kseed) bytes $(wc -c < $S/amu.kseed | tr -d ' ')"
  echo "code $(sha $S/seed-1.bin) bytes $(wc -c < $S/seed-1.bin | tr -d ' ') offset $(cat $S/seed-1.offset)"
  echo "command $W/amu-s sha256 $(sha $W/amu-s) bytes $(wc -c < $W/amu-s | tr -d ' ')"
  echo "loader-source sha256 $(sha $R/tools/kexe_loader.c)"
  echo "allow 3,35,37,38,39"
  echo "libraries $(echo $deps | tr '\n' ' ')"; } > $W/amu-s.info
echo "$deps" | grep -vq '^/usr/lib/' && { echo "amu-main: unexpected library dependency"; exit 1; }
cat $W/amu-s.info
