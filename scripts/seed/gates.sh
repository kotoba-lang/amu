#!/bin/zsh
# scripts/seed/gates.sh [--rung rN] [--no-build] [--only G1,G3,...] [--skip G5,...] -- run the seed gates G1-G5 (and the
# rung conformance gate GR from r1 on), print a table with timing, and exit 0 only when every gate that ran passed
# ("rung-ready"). BOOTSTRAP-TOOL (zsh), owner GATES. Rows:
#   BUILD  scripts/seed/build.sh fixed-point : unity -> seed-0 (stage-0, BOOTSTRAP) -> seed-1 -> seed-2 (skipped by --no-build,
#          which then only requires build/seed/seed-{0,1,2}.bin to exist)
#   G4     fixed point seed-1.bin == seed-2.bin (sha256 printed), and seed-0 / seed-1 give byte-identical containers on
#          every G1 port and G2 corpus program (checked after G1 and G2 have run with both compilers)
#   G1     19 Embench ports compiled by seed-0 and by seed-1, test-* = 1 under the C loader and kexe-benchmark (fuel 16M)
#   G2     seed/tests/corpus (63 programs) equal to stage-0's oracle, seed-0 and seed-1
#   G3     refusal texts, scripts/seed/g3.sh --rung rN
#   G5     no program started by the packaged seed (scripts/seed/no-host-processes.sh; packages seed-1 first)
#   GR     rung conformance (scripts/seed/gr.sh rN), r1 and later only
#   ERR    scripts/seed/errors-check.py: seed/HEADS :errors == the text tables of 90-drv, module-local codes registered
#   FUEL   with --with-fuel: seed fuel <= stage-0 fuel per port and probe (scripts/seed/fuel.sh)
# Output: build/seed/gates/<rung>/<gate>.log, build/seed/gates/<rung>/summary.tsv (gate, status, seconds, detail), and
# the table on stdout. Statuses: PASS, FAIL, SKIP (not requested or not applicable at the rung).
# Env: see lib.sh. The stage-0 compile inside BUILD respects the machine-wide two-slot lock.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
rung=r0; nobuild=0; only=""; skip=""; withfuel=0
while [ $# -gt 0 ]; do
  case $1 in --rung) rung=$2; shift 2 ;; --no-build) nobuild=1; shift ;; --with-fuel) withfuel=1; shift ;; --only) only=$2; shift 2 ;; --skip) skip=$2; shift 2 ;; *) echo "usage: gates.sh [--rung rN] [--no-build] [--with-fuel] [--only G1,..] [--skip G5,..]" >&2; exit 2 ;; esac
done
R=$SEED_REPO; B=$SEED_BUILD; S=$R/scripts/seed; D=$B/gates/$rung; mkdir -p $D
: > $D/summary.tsv
now() { perl -MTime::HiRes=time -e 'printf "%.3f", time'; }
want() { [ -n "$only" ] && [[ ",$only," != *",$1,"* ]] && return 1; [[ ",$skip," == *",$1,"* ]] && return 1; return 0; }
row() { printf '%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" >> $D/summary.tsv; }
# run <gate> <logname> <cmd...> : times the command, records PASS/FAIL, detail = last non-empty line of the log
run() {
  local g=$1; shift
  local t0=$(now) rc
  "$@" > $D/$g.log 2>&1; rc=$?
  local t1=$(now)
  row $g $([ $rc -eq 0 ] && echo PASS || echo FAIL) $(printf '%.1f' $((t1-t0))) "$(grep -v '^[[:space:]]*$' $D/$g.log | tail -1 | cut -c1-230)"
  return $rc
}
skiprow() { row $1 SKIP 0 "$2"; }

# ---- BUILD
if want BUILD; then
  if [ $nobuild -eq 1 ]; then
    run BUILD sh -c "for k in 0 1 2; do [ -s $B/seed-\$k.bin ] || { echo missing seed-\$k.bin; exit 1; }; done; echo 'reused build/seed/seed-{0,1,2}.bin (--no-build): unity sha256 '\$(cat $B/seed-unity.kotoba.sha256 2>/dev/null)"
  else
    run BUILD zsh $S/build.sh fixed-point
  fi
else skiprow BUILD "not requested"; fi

# ---- ERR: the error-code table (pure text, no compiler)
if want ERR; then run ERR python3 $S/errors-check.py; else skiprow ERR "not requested"; fi

# ---- G1 / G2 with both compilers (seed-0 = stage-0 built, BOOTSTRAP; seed-1 = self-built)
for c in seed-0 seed-1; do
  if [ -s $B/$c.bin ]; then
    want G1 && { run G1.$c zsh $S/g1.sh $B/$c.bin; }
    want G2 && { run G2.$c zsh $S/g2.sh $B/$c.bin; }
  fi
done
# fold the two compilers into one G1 and one G2 row
fold() {   # fold <gate>: replace the per-compiler rows with one row
  local g=$1 st=PASS secs=0 det="" l
  grep -q "^$g\.seed-" $D/summary.tsv || return 0
  while IFS=$'\t' read -r a b c d; do
    [[ $a == $g.seed-* ]] || continue
    [ "$b" = PASS ] || st=FAIL
    secs=$((secs + c)); det="$det${det:+ | }${a#$g.}: $d"
  done < $D/summary.tsv
  grep -v "^$g\.seed-" $D/summary.tsv > $D/summary.tmp; mv $D/summary.tmp $D/summary.tsv
  row $g $st $(printf '%.1f' $secs) "$det"
}
fold G1; fold G2

# ---- G4: fixed point + container identity between seed-0 and seed-1 on the G1+G2 outputs
if want G4; then
  g4() {
    [ -s $B/seed-1.bin ] && [ -s $B/seed-2.bin ] || { echo "no seed-1/seed-2"; return 1; }
    cmp -s $B/seed-1.bin $B/seed-2.bin || { echo "G4: seed-1.bin != seed-2.bin"; return 1; }
    local s=0 d=0 k o
    for k in $B/g1-seed-0/*.kseed(N) $B/g2-seed-0/*.kseed(N); do
      o=${k/\/g1-seed-0\//\/g1-seed-1\/}; o=${o/\/g2-seed-0\//\/g2-seed-1\/}
      if cmp -s $k $o; then s=$((s+1)); else d=$((d+1)); echo "G4: DIFF ${k:t}"; fi
    done
    echo "G4: seed-1.bin == seed-2.bin ($(wc -c < $B/seed-1.bin | tr -d ' ') bytes, sha256 $(shasum -a 256 $B/seed-1.bin | cut -c1-64)); seed-0 vs seed-1 containers: $s identical, $d different"
    [ $d -eq 0 ] && [ $s -gt 0 ]
  }
  run G4 g4
else skiprow G4 "not requested"; fi

# ---- G3
if want G3; then run G3 zsh $S/g3.sh --rung $rung; else skiprow G3 "not requested"; fi

# ---- G5
if want G5; then
  run G5 sh -c "zsh $S/package.sh 1 > $D/G5.package.log 2>&1 && zsh $S/no-host-processes.sh"
else skiprow G5 "not requested"; fi

# ---- FUEL (only with --with-fuel: T5 fuel accounting, scripts/seed/fuel.sh; fails while the FF-FUEL over-charge of
# docs/selfhost-seed-fuel-20261002.md is open)
if [ $withfuel -eq 1 ] && want FUEL; then run FUEL zsh $S/fuel.sh $B/seed-1.bin; fi

# ---- GR
if want GR; then
  if [ "$rung" = r0 ]; then skiprow GR "rung r0: G2 is the rung conformance"
  else run GR zsh $S/gr.sh $rung; fi
fi

# ---- table
order=(BUILD G1 G2 G3 G4 G5 GR FUEL)
echo
printf '%-6s %-5s %8s  %s\n' GATE STATUS SECONDS DETAIL
fails=0; ran=0
for g in $order; do
  l=$(awk -F'\t' -v g=$g '$1==g' $D/summary.tsv)
  [ -n "$l" ] || continue
  st=$(echo "$l" | cut -f2); sec=$(echo "$l" | cut -f3); det=$(echo "$l" | cut -f4)
  printf '%-6s %-5s %8s  %s\n' $g $st $sec "$det"
  [ $st = FAIL ] && fails=$((fails+1)); [ $st = PASS ] && ran=$((ran+1))
done
tot=$(awk -F'\t' '{s+=$3} END {printf "%.1f", s}' $D/summary.tsv)
echo
if [ $fails -eq 0 ] && [ $ran -gt 0 ]; then echo "rung $rung: READY ($ran gates passed, ${tot}s, load $(sysctl -n vm.loadavg | awk '{print $2}'))"; exit 0
else echo "rung $rung: NOT READY ($fails failed, $ran passed, ${tot}s); logs in $D"; exit 1; fi
