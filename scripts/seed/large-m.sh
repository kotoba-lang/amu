#!/bin/zsh
# scripts/seed/large-m.sh [--rung rN] [--prev seed.bin] [--check] [work-dir] -- build the LARGE-M seed profile (agent ARENA,
# 2026-10-04; seed/profiles/README.md). BOOTSTRAP-TOOL (zsh, git, python3). After the loader is built only seeds run.
#
#   tree   := `git archive` of seed/ scripts/seed tools at the rung record's unity_commit (default rung r6d)
#   map    := scripts/seed/large_m.py rewrites tree/seed/MEMORY-MAP (M 16 Mi words, the region table there), then gen-ns
#   seed-1 := the recorded rung's seed (--prev, default build/seed-boot/<rung>/seed-1.bin, which bootstrap.sh reproduces
#             and checks) compiles the large-M unity; seed-2 := seed-1 compiles it (build.sh lineage). Exit 0 iff seed-1 == seed-2.
#   --check: also require sha256(seed-1) == the `seed1_sha256` of seed/profiles/large-m-<rung>.record.
# The profile is an OPTION beside the lineage (not a rung of seed/rungs/: bootstrap.sh never builds from it); its seed is a
# compiler with the same language as the rung and larger fixed tables (TOK 655,360, NODE/SIR 458,752, CODE 1 Mi, OUT 3 Mi words, EXP 8,192).
# Output: <work>/b/seed-1.bin (+ .offset), <work>/large-m.info. Default work dir build/seed-large-m-<rung>.
emulate -L zsh; setopt pipefail
R=$(cd "$(dirname "$0")/../.." && pwd)
rung=r6d; prev=""; check=0; W=""
while [ $# -gt 0 ]; do
  case $1 in
    --rung) rung=$2; shift 2 ;; --prev) prev=$2; shift 2 ;; --check) check=1; shift ;;
    -*) echo "usage: large-m.sh [--rung rN] [--prev seed.bin] [--check] [work-dir]" >&2; exit 2 ;;
    *) W=$1; shift ;;
  esac
done
W=${W:-$R/build/seed-large-m-$rung}; mkdir -p $W; W=${W:A}
die() { echo "large-m: FAIL: $*" >&2; exit 1; }
sha() { shasum -a 256 $1 | cut -c1-64; }
REC=$R/seed/rungs/$rung.record; [ -f $REC ] || die "no $REC"
C=$(sed -n 's/^unity_commit //p' $REC | head -1); [ -n "$C" ] || die "no unity_commit in $REC"
want_prev=$(sed -n 's/^seed1_sha256 //p' $REC | head -1)
prev=${prev:-$R/build/seed-boot/$rung/seed-1.bin}
[ -f $prev ] || die "no rung seed $prev (run scripts/seed/bootstrap.sh --no-head --upto $rung first)"
[ "$(sha $prev)" = "$want_prev" ] || die "$prev is not rung $rung's seed ($want_prev)"

T=$W/tree; rm -rf $T; mkdir -p $T
git -C $R archive $C seed scripts/seed tools | tar -x -C $T || die "git archive $C"
python3 $R/scripts/seed/large_m.py $T/seed/MEMORY-MAP > $W/large_m.log || die "large_m.py"
zsh $T/scripts/seed/gen-ns.sh > $W/gen-ns.log 2>&1 || die "gen-ns (see $W/gen-ns.log)"
echo "large-m: rung $rung unity_commit $C, previous seed $(sha $prev | cut -c1-8) (load $(sysctl -n vm.loadavg | awk '{print $2}'))"
( export SEED_REPO=$T SEED_BUILD=$W/b SEED_RESOURCES_35=$W SEED_PREV=$prev SEED_VECTOR_ITEMS=67108864 SEED_SECONDS=${SEED_SECONDS:-900}
  nice zsh $T/scripts/seed/build.sh lineage ) > $W/build.log 2>&1 || { tail -5 $W/build.log; die "build.sh lineage"; }
grep -q 'FIXED POINT' $W/build.log || die "not a fixed point (see $W/build.log)"
s1=$(sha $W/b/seed-1.bin); s2=$(sha $W/b/seed-2.bin)
[ "$s1" = "$s2" ] || die "seed-1 $s1 != seed-2 $s2"
# cross check: the large-M seed compiles the rung's own (default-map) unity to exactly the rung's seed -- a compiler's output
# does not depend on its own table sizes
U=$W/rung-unity.kotoba; : > $U
for p in $(git -C $R show ${C}:seed/MANIFEST | grep -v '^[[:space:]]*#' | grep -v '^[[:space:]]*$' | sed 's/[[:space:]].*//'); do
  git -C $R show ${C}:${p} >> $U || die "missing $p at $C"; printf '\n' >> $U
done
( export SEED_REPO=$T SEED_BUILD=$W/b SEED_RESOURCES_35=$W SEED_VECTOR_ITEMS=67108864 SEED_SECONDS=${SEED_SECONDS:-900}
  source $T/scripts/seed/lib.sh
  seed_run $W/b/seed-1.bin $(cat $W/b/seed-1.offset) compile $U --target aarch64-macos --output $W/rung-unity.kseed > $W/cross.log 2>&1 &&
  seed_run $W/b/seed-1.bin $(cat $W/b/seed-1.offset) extract-native $W/rung-unity.kseed --symbol main --output $W/rung-unity.bin >> $W/cross.log 2>&1 ) \
  || die "cross compile (see $W/cross.log)"
[ "$(sha $W/rung-unity.bin)" = "$want_prev" ] || die "the large-M seed compiles rung $rung's unity to $(sha $W/rung-unity.bin), not $want_prev"
{ echo "profile large-m"
  echo "rung $rung"
  echo "unity_commit $C"
  echo "unity_sha256 $(sha $W/b/seed-unity.kotoba)"
  echo "memory_map_sha256 $(sha $T/seed/MEMORY-MAP)"
  echo "prev_seed_sha256 $(sha $prev)"
  echo "fixed_point yes"
  echo "cross_rung_unity_sha256 $(sha $W/rung-unity.bin) (= rung $rung seed1_sha256)"
  echo "seed1_bytes $(wc -c < $W/b/seed-1.bin | tr -d ' ')"
  echo "seed1_sha256 $s1"
  echo "seed2_sha256 $s2"
  sed 's/^large_m: /layout /' $W/large_m.log; } > $W/large-m.info
cat $W/large-m.info
if [ $check -eq 1 ]; then
  P=$R/seed/profiles/large-m-$rung.record; [ -f $P ] || die "no $P"
  want=$(sed -n 's/^seed1_sha256 //p' $P | head -1)
  [ "$s1" = "$want" ] || die "seed-1 $s1 != recorded $want"
  echo "large-m: CHECK PASS (seed-1 = recorded $want)"
fi
echo "large-m: FIXED POINT $s1"
