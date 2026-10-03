#!/bin/zsh
# scripts/seed/bootstrap.sh [options] -- reproduce the WHOLE seed lineage from the committed R0 seed binary.
# BOOTSTRAP-TOOL (zsh + git + shasum). Owner HOUSE. After the loader is built (cc, tools/kexe_loader.c) only the loader and
# the seeds run: no node, JVM, nbb or stage-0 (except with --stage0-r0, which is the one optional check that needs it).
#
# The chain (docs/selfhost-seed-bootstrap-20261002.md):
#   seed/bootstrap/seed-r0.bin     the R0 fixed point, committed (sha256 in seed/bootstrap/SHA256SUMS and seed/rungs/r0.record)
#   for each seed/rungs/<rung>.record, in LINEAGE order (r0 r1 r2 r3 r4 r5a r4b ...: seed_rung_records of lib.sh = by the history
#   position of the record's unity commit; extension rungs rNx included):
#       unity(N) = the seed/MANIFEST files of the record's `unity_commit`, each followed by "\n" (read from git, not from
#                  the working tree)
#       [bridge_commit B: the previous rung's seed (or, with `bridge_compiler_rung K`, rung K's seed) compiles unity(B) -> the bridge
#        seed, sha256 = `bridge_sha256`]
#       seed-N-1 := (bridge | previous seed) compiles unity(N);  seed-N-2 := seed-N-1 compiles unity(N)
#       gate: seed-N-1 == seed-N-2 (fixed point) and sha256(seed-N-1) == the record's `seed1_sha256`
#   finally the working tree (or --commit C): seed-A compiles the unity -> seed-B -> seed-C; fixed point iff A == B == C.
# Exit 0 iff every recorded hash is reproduced and the head is a fixed point. Every stage prints its sha256 and seconds.
#
# Options:
#   --upto rN       stop after rung rN (no head step)           --no-head   verify the recorded rungs only
#   --commit C      head unity from commit C instead of the working tree
#   --stage0-r0     additionally rebuild R0 from its unity with STAGE-0 (bootstrap-reference, JVM-built) -> seed-0 -> seed-1 and
#                   check seed-1 == the committed R0 seed (the original, non-selfhost provenance of the lineage)
#   --keep          keep intermediate seeds (default: kept anyway in $SEED_BOOT)
# Env: SEED_BOOT (work dir, default <repo>/build/seed-boot; must lie inside SEED_RESOURCES_35, default the repo), SEED_SECONDS
#      (per compile wall/cpu limit, default 600), see lib.sh.
emulate -L zsh
setopt pipefail
export SEED_BUILD=${SEED_BOOT:-$(cd "$(dirname "$0")/../.." && pwd)/build/seed-boot}
export SEED_SECONDS=${SEED_SECONDS:-600}
source "$(dirname "$0")/lib.sh"
R=$SEED_REPO; W=${SEED_BUILD:A}; mkdir -p $W
upto=""; head_step=1; commit=""; stage0=0
while [ $# -gt 0 ]; do
  case $1 in
    --upto) upto=$2; shift 2 ;; --no-head) head_step=0; shift ;; --commit) commit=$2; shift 2 ;;
    --stage0-r0) stage0=1; shift ;; --keep) shift ;;
    *) echo "usage: bootstrap.sh [--upto rN] [--no-head] [--commit C] [--stage0-r0]" >&2; exit 2 ;;
  esac
done
sha() { shasum -a 256 $1 | cut -c1-64; }
now() { perl -MTime::HiRes=time -e 'printf "%.1f", time'; }
die() { echo "bootstrap: FAIL: $*" >&2; exit 1; }
rec() { sed -n "s/^$2 //p" $1 | head -1; }       # rec <record> <key>

# unity_at <commit|WORKTREE> <out>: concatenation of the MANIFEST files, each + "\n" (as scripts/seed/build.sh does)
unity_at() {
  local c=$1 out=$2 p list
  if [ $c = WORKTREE ]; then list=$(seed_manifest); else
    list=$(git -C $R show ${c}:seed/MANIFEST | grep -v '^[[:space:]]*#' | grep -v '^[[:space:]]*$' | sed 's/[[:space:]].*//') || die "no seed/MANIFEST at $c"
  fi
  : > $out.tmp
  for p in ${(f)list}; do
    if [ $c = WORKTREE ]; then cat $R/$p >> $out.tmp || die "missing $p"; else git -C $R show ${c}:${p} >> $out.tmp || die "missing $p at $c"; fi
    printf '\n' >> $out.tmp
  done
  mv $out.tmp $out
}

# compile_with <seed.bin> <unity> <out-prefix>: seed compiles the unity and extracts main -> <out-prefix>.bin/.offset
compile_with() {
  local sb=$1 u=$2 o=$3 off x
  off=$(cat ${sb%.bin}.offset)
  seed_run $sb $off compile ${u:A} --target aarch64-macos --output ${o:A}.kseed > $o.log 2>&1 || { head -3 $o.log >&2; return 1; }
  x=$(seed_run $sb $off extract-native ${o:A}.kseed --symbol main --output ${o:A}.bin 2>>$o.log) || { echo "$x" >&2; return 1; }
  echo "$x" | sed -n 's/.*:offset \([0-9]*\).*/\1/p' > $o.offset
  [ -s $o.bin ] && [ -s $o.offset ] || { echo "no output from extract-native: $x" >&2; return 1; }
}

# step <label> <seed.bin> <unity> <out-prefix>: compile_with + one line of evidence
step() {
  local t0=$(now) t1
  compile_with $2 $3 $4 || die "$1: seed ${2:t} (sha256 $(sha $2 | cut -c1-12)) could not compile ${3:t}"
  t1=$(now)
  printf 'bootstrap: %-34s %9d bytes  sha256 %s  (%.0f s)\n' "$1" $(wc -c < $4.bin) $(sha $4.bin) $((t1-t0))
}

cd $R
( cd seed/bootstrap && shasum -a 256 -c SHA256SUMS > /dev/null ) || die "seed/bootstrap/SHA256SUMS does not match the committed R0 seed"
echo "bootstrap: loader $(seed_loader | xargs shasum -a 256 | cut -c1-12) (tools/kexe_loader.c at $(git rev-parse --short HEAD)), work dir $W"
cur=$W/seed-r0.bin
cp seed/bootstrap/seed-r0.bin $cur; cp seed/bootstrap/seed-r0.offset ${cur%.bin}.offset
echo "bootstrap: R0 seed (committed)                 $(wc -c < $cur | tr -d ' ') bytes  sha256 $(sha $cur)"
last=""; lastrec=""

if [ $stage0 -eq 1 ]; then
  r0=$R/seed/rungs/r0.record; [ -f $r0 ] || die "no r0.record"
  S0=$W/stage0-r0; mkdir -p $S0
  unity_at $(rec $r0 unity_commit) $S0/seed-unity.kotoba
  t0=$(now)
  seed_stage0_build $S0/seed-unity.kotoba $S0/seed-0 || die "stage-0 refused the R0 unity: $(grep -o ':message "[^"]*"' $S0/seed-0.log | head -2)"
  echo "bootstrap: R0 seed-0 by STAGE-0 (BOOTSTRAP)    $(wc -c < $S0/seed-0.bin | tr -d ' ') bytes  sha256 $(sha $S0/seed-0.bin)  ($(printf '%.0f' $(( $(now)-t0 ))) s)"
  step "R0 seed-1 by seed-0" $S0/seed-0.bin $S0/seed-unity.kotoba $S0/seed-1
  cmp -s $S0/seed-1.bin $cur || die "stage-0 route: seed-1 ($(sha $S0/seed-1.bin)) != the committed R0 seed"
  echo "bootstrap: STAGE-0 ROUTE OK: stage-0 -> seed-0 -> seed-1 == the committed R0 seed"
fi

# ---- the recorded rungs, in order
typeset -A SEEDOF       # rung name -> its recorded fixed-point seed (for `bridge_compiler_rung`)
SEEDOF[r0]=$cur
for rf in ${(f)"$(seed_rung_records)"}; do
  rg=$(rec $rf rung); n=${rg#r}
  [ -z "$upto" ] || [ $(seed_rung_key $rg) -le $(seed_rung_key $upto) ] || break
  uc=$(rec $rf unity_commit); [ -n "$uc" ] || uc=$(rec $rf head)
  want=$(rec $rf seed1_sha256); [ -n "$want" ] || die "$rg: no seed1_sha256 in $rf"
  D=$W/$rg; mkdir -p $D
  unity_at $uc $D/seed-unity.kotoba
  [ "$(sha $D/seed-unity.kotoba)" = "$(rec $rf unity_sha256)" ] || die "$rg: unity of $uc has sha256 $(sha $D/seed-unity.kotoba), the record says $(rec $rf unity_sha256)"
  echo "bootstrap: $rg unity of ${uc:0:9}: $(wc -l < $D/seed-unity.kotoba | tr -d ' ') lines, sha256 $(sha $D/seed-unity.kotoba | cut -c1-16) (as recorded)"
  c=$cur
  bc=$(rec $rf bridge_commit)
  if [ -n "$bc" ]; then
    unity_at $bc $D/bridge-unity.kotoba
    bcr=$(rec $rf bridge_compiler_rung)        # optional: the rung whose seed compiles the bridge (an extension whose bridge predates the previous rung)
    [ -n "$bcr" ] && c=${SEEDOF[$bcr]:?"$rg: bridge_compiler_rung $bcr has no seed yet"}
    step "$rg bridge (unity of ${bc:0:9}, by ${c:h:t})" $c $D/bridge-unity.kotoba $D/bridge
    [ "$(sha $D/bridge.bin)" = "$(rec $rf bridge_sha256)" ] || die "$rg: bridge sha256 $(sha $D/bridge.bin) != recorded $(rec $rf bridge_sha256)"
    c=$D/bridge.bin
    if [ $stage0 -eq 1 ]; then
      # independent route: STAGE-0 (bootstrap-reference) compiles the bridge unity itself (a different compiler, so a
      # different bridge binary), and that bridge must still produce the recorded fixed point
      seed_stage0_build $D/bridge-unity.kotoba $D/bridge-s0 || die "$rg: stage-0 refused the bridge unity: $(grep -o ':message "[^"]*"' $D/bridge-s0.log | tail -1)"
      echo "bootstrap: $rg bridge by STAGE-0 (BOOTSTRAP)       $(wc -c < $D/bridge-s0.bin | tr -d ' ') bytes  sha256 $(sha $D/bridge-s0.bin | cut -c1-16)... (differs from the seed-built bridge: another compiler)"
      step "$rg seed-1 (by stage-0 bridge)" $D/bridge-s0.bin $D/seed-unity.kotoba $D/seed-1-s0
      [ "$(sha $D/seed-1-s0.bin)" = "$want" ] || die "$rg: stage-0 route gives $(sha $D/seed-1-s0.bin), the record says $want"
      echo "bootstrap: $rg STAGE-0 ROUTE OK: stage-0 -> bridge -> seed-1 == record"
    fi
  fi
  step "$rg seed-1 (by ${c:h:t}/${c:t:r})" $c $D/seed-unity.kotoba $D/seed-1
  step "$rg seed-2 (by seed-1)" $D/seed-1.bin $D/seed-unity.kotoba $D/seed-2
  cmp -s $D/seed-1.bin $D/seed-2.bin && cmp -s $D/seed-1.offset $D/seed-2.offset || die "$rg: not a fixed point (seed-1 != seed-2)"
  [ "$(sha $D/seed-1.bin)" = "$want" ] || die "$rg: fixed point sha256 $(sha $D/seed-1.bin) != recorded $want"
  [ "$(sha $D/seed-2.bin)" = "$(rec $rf seed2_sha256)" ] || die "$rg: seed-2 sha256 $(sha $D/seed-2.bin) != recorded $(rec $rf seed2_sha256)"
  [ "$(wc -c < $D/seed-1.bin | tr -d ' ')" = "$(rec $rf seed1_bytes)" ] || die "$rg: size differs from the record"
  echo "bootstrap: $rg FIXED POINT == record ${want:0:16}"
  cur=$D/seed-1.bin; last=$rg; lastrec=$rf; SEEDOF[$rg]=$cur
done

[ $head_step -eq 1 ] && [ -z "$upto" ] || { echo "bootstrap: OK (recorded rungs through ${last:-none})"; exit 0; }

# ---- the head: working tree (or --commit)
H=$W/head; mkdir -p $H
src=${commit:-WORKTREE}
unity_at $src $H/seed-unity.kotoba
echo "bootstrap: head unity (${commit:-working tree}): $(wc -l < $H/seed-unity.kotoba | tr -d ' ') lines, sha256 $(sha $H/seed-unity.kotoba | cut -c1-16)"
step "head seed-A (by $last)" $cur $H/seed-unity.kotoba $H/seed-A
step "head seed-B (by seed-A)" $H/seed-A.bin $H/seed-unity.kotoba $H/seed-B
step "head seed-C (by seed-B)" $H/seed-B.bin $H/seed-unity.kotoba $H/seed-C
if cmp -s $H/seed-A.bin $H/seed-B.bin && cmp -s $H/seed-B.bin $H/seed-C.bin && cmp -s $H/seed-A.offset $H/seed-C.offset; then
  hh=$(sha $H/seed-A.bin)
  echo "bootstrap: HEAD FIXED POINT seed-A == seed-B == seed-C sha256 $hh ($(wc -c < $H/seed-A.bin | tr -d ' ') bytes)"
  [ "$hh" = "$(rec $lastrec seed1_sha256)" ] && echo "bootstrap: head seed == the $last record" || echo "bootstrap: head seed differs from the $last record (expected once the sources moved on; record the next rung to pin it)"
else
  die "head is not a fixed point (A/B/C differ)"
fi
echo "bootstrap: OK"
