#!/bin/zsh
# scripts/seed/build.sh <step> -- the seed bootstrap chain (design section 3.1). BOOTSTRAP-TOOL (zsh).
#
#   build.sh unity        concatenate seed/MANIFEST (each file + "\n") -> build/seed/seed-unity.kotoba (+ .sha256)
#   build.sh 0            unity, then STAGE-0 (bootstrap-reference, JVM-built native image) compiles it:
#                         build/seed/seed-0.{kexe,bin,offset,info}. Labelled BOOTSTRAP in seed-0.info.
#   build.sh N   (N>=1)   seed-(N-1) compiles the unity source under the C loader only (no node/JVM/nbb):
#                           seed-(N-1) compile seed-unity.kotoba --target aarch64-macos --output seed-N.kseed
#                           seed-(N-1) extract-native seed-N.kseed --symbol main --output seed-N.bin  (stdout :offset N)
#                         -> build/seed/seed-N.{kseed,bin,offset,info}
#   build.sh fixed-point  0, 1, 2, then `cmp seed-1.bin seed-2.bin` (gate G4, first half). Exit 0 iff identical.
#
# Env: see lib.sh (SEED_STAGE0, SEED_BUILD, SEED_RESOURCES_35 = wire-35 scope, default the repo).
#      SEED_HEX_STDOUT=1: the seed writes its container as hex on stdout instead of through wire 35 (the T3
#      fallback); build.sh decodes it with `xxd -r -p`.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
B=$SEED_BUILD; U=$B/seed-unity.kotoba
step=${1:?usage: build.sh unity|0|N|fixed-point}

sha() { shasum -a 256 $1 | cut -c1-64; }

unity() {
  local p missing=0
  for p in $(seed_manifest); do [ -f $SEED_REPO/$p ] || { echo "build: missing $p" >&2; missing=1; }; done
  [ $missing -eq 0 ] || return 2
  : > $U.tmp
  for p in $(seed_manifest); do cat $SEED_REPO/$p >> $U.tmp; printf '\n' >> $U.tmp; done
  mv $U.tmp $U; sha $U > $U.sha256
  echo "build: unity $(wc -l < $U | tr -d ' ') lines, sha256 $(cat $U.sha256)"
}

stage0() {
  unity || return $?
  rm -f $B/seed-0.*(N)
  if ! seed_stage0_build $U $B/seed-0; then
    echo "build: stage-0 refused the unity source:"; grep -o ':message "[^"]*"' $B/seed-0.log | head -3; return 1
  fi
  { echo "label BOOTSTRAP (seed-0 built by stage-0, JVM-built native image; not a selfhost artifact)"
    echo "unity-sha256 $(cat $U.sha256)"; echo "stage0 $SEED_STAGE0"; echo "stage0-sha256 $(sha $SEED_STAGE0)"
    echo "bin-sha256 $(sha $B/seed-0.bin)"; echo "offset $(cat $B/seed-0.offset)"; } > $B/seed-0.info
  echo "build: seed-0.bin $(wc -c < $B/seed-0.bin | tr -d ' ') bytes, main at $(cat $B/seed-0.offset) (BOOTSTRAP)"
}

stageN() {
  local n=$1 p=$(( $1 - 1 )) out
  [ -f $B/seed-$p.bin ] && [ -f $B/seed-$p.offset ] || { echo "build: seed-$p missing (run build.sh $p)" >&2; return 2; }
  [ -f $U ] || unity || return $?
  rm -f $B/seed-$n.*(N)
  if [ -n "$SEED_HEX_STDOUT" ]; then
    seed_run $B/seed-$p.bin $(cat $B/seed-$p.offset) compile $U --target aarch64-macos --output - > $B/seed-$n.hex 2> $B/seed-$n.log \
      || { echo "build: seed-$p compile failed:"; head -5 $B/seed-$n.log; return 1; }
    xxd -r -p $B/seed-$n.hex > $B/seed-$n.kseed
  else
    seed_run $B/seed-$p.bin $(cat $B/seed-$p.offset) compile $U --target aarch64-macos --output $B/seed-$n.kseed > $B/seed-$n.log 2>&1 \
      || { echo "build: seed-$p compile failed:"; head -5 $B/seed-$n.log; return 1; }
  fi
  out=$(seed_run $B/seed-$p.bin $(cat $B/seed-$p.offset) extract-native $B/seed-$n.kseed --symbol main --output $B/seed-$n.bin 2>>$B/seed-$n.log) \
    || { echo "build: seed-$p extract-native failed: $out"; return 1; }
  echo "$out" | sed -n 's/.*:offset \([0-9]*\).*/\1/p' > $B/seed-$n.offset
  [ -s $B/seed-$n.offset ] && [ -s $B/seed-$n.bin ] || { echo "build: no offset/bin from extract-native: $out"; return 1; }
  { echo "label seed-$n built by seed-$p under tools/kexe_loader.c"
    echo "unity-sha256 $(cat $U.sha256)"; echo "compiler-sha256 $(sha $B/seed-$p.bin)"
    echo "bin-sha256 $(sha $B/seed-$n.bin)"; echo "offset $(cat $B/seed-$n.offset)"; } > $B/seed-$n.info
  echo "build: seed-$n.bin $(wc -c < $B/seed-$n.bin | tr -d ' ') bytes, main at $(cat $B/seed-$n.offset)"
}

case $step in
  unity) unity ;;
  0) stage0 ;;
  fixed-point)
    stage0 && stageN 1 && stageN 2 || exit 1
    if cmp -s $B/seed-1.bin $B/seed-2.bin && cmp -s $B/seed-1.offset $B/seed-2.offset; then
      echo "build: FIXED POINT seed-1.bin == seed-2.bin sha256 $(sha $B/seed-1.bin)"
    else
      echo "build: NOT a fixed point: seed-1.bin != seed-2.bin"; cmp $B/seed-1.bin $B/seed-2.bin | head -1; exit 1
    fi ;;
  <->) stageN $step ;;
  *) echo "usage: build.sh unity|0|N|fixed-point" >&2; exit 2 ;;
esac
