#!/bin/zsh
# seed/tests/r6c/check-r6c.sh [seed.bin] -- the R6C feature cases (agent R6C, 2026-10-03). BOOTSTRAP-TOOL (zsh).
# Every seed/tests/r6c/feat/*.kotoba carries a line ";; want: V": V an integer = what main answers (hand-derived), or an
# error code Ennnn = the seed refuses it with that code. A positive is compiled twice: the single-module route
# (`compile f`) and the project route of the R6 scan (`compile f --emit-module --entry` + `link`); both images must be
# byte-identical (cmp) and main must answer V under the C loader. Exit 0 iff every case passes.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/../../../scripts/seed/lib.sh"
R=$SEED_REPO; D=$R/seed/tests/r6c/feat; B=${SEED_BUILD:A}; W=$B/check-r6c; rm -rf $W; mkdir -p $W
bin=${${1:-$B/seed-1.bin}:A}; off=$(cat ${bin%.bin}.offset 2>/dev/null || echo 0)
L=$(seed_loader) || exit 2; L=${L:A}
export SEED_RESOURCES_35=$R:$W
pass=0 fail=0
for f in $D/*.kotoba; do
  lab=${f:t:r}; d=$W/$lab; mkdir -p $d/o; d=${d:A}
  want=$(sed -n 's/^;; want: *\([^ ]*\).*/\1/p' $f | head -1)
  grant=$(sed -n 's/^;; grant: *\([^ ]*\).*/\1/p' $f | head -1); grant=${grant:--}
  [ -n "$want" ] || { fail=$((fail+1)); echo "FAIL $lab: no ';; want:' line"; continue; }
  r1=$(seed_run $bin $off compile $f --output $d/in.kseed 2>&1)
  if [[ $want == E* ]]; then
    c1=$(print -r -- "$r1" | sed -n 's/^seed: \(E[0-9]*\).*/\1/p' | head -1)
    if [ ! -s $d/in.kseed ] && [ "$c1" = $want ]; then pass=$((pass+1)); echo "PASS $lab refused: $(print -r -- "$r1" | grep '^seed:' | head -1)"
    else fail=$((fail+1)); echo "FAIL $lab: want $want, got '$c1' $(print -r -- "$r1" | head -1)"; fi
    continue
  fi
  [ -s $d/in.kseed ] || { fail=$((fail+1)); echo "FAIL $lab: $(print -r -- "$r1" | grep seed: | head -1)"; continue; }
  ns=$(sed -n 's/^(ns \([^ )]*\).*/\1/p' $f | head -1)
  r2=$(seed_run $bin $off compile $f --emit-module --entry --object-dir $d/o --output $d/o/$ns.kso 2>&1) \
    && r2=$(seed_run $bin $off link $d/o/$ns.kso --object-dir $d/o --output $d/sep.kseed 2>&1)
  [ -s $d/sep.kseed ] || { fail=$((fail+1)); echo "FAIL $lab project route: $(print -r -- "$r2" | grep seed: | head -1)"; continue; }
  cmp -s $d/in.kseed $d/sep.kseed || { fail=$((fail+1)); echo "FAIL $lab: single-module and project-route images differ"; continue; }
  x=$(seed_run $bin $off extract-native $d/in.kseed --symbol main --output $d/in.bin 2>&1); o=$(print -r -- "$x" | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  v=$(cd $d; KEXE_CPU_SECONDS=20 KEXE_WALL_SECONDS=20 $L $d/in.bin $o 0 aarch64 $grant 2>/dev/null | tail -1)
  x2=$(seed_run $bin $off extract-native $d/sep.kseed --symbol main --output $d/sep.bin 2>&1); o2=$(print -r -- "$x2" | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  v2=$(cd $d; KEXE_CPU_SECONDS=20 KEXE_WALL_SECONDS=20 $L $d/sep.bin $o2 0 aarch64 $grant 2>/dev/null | tail -1)
  if [ "$v" = "$want" ] && [ "$v2" = "$want" ]; then pass=$((pass+1)); echo "PASS $lab $v ($(wc -c < $d/in.kseed | tr -d ' ') bytes)"
  else fail=$((fail+1)); echo "FAIL $lab: got '$v' (project route '$v2') want $want"; fi
done
echo "check-r6c: PASS $pass FAIL $fail (compiler $(shasum -a 256 $bin | cut -c1-16), load $(uptime | sed 's/.*averages: //'))"
[ $fail -eq 0 ]
