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
#   GR     rung conformance (scripts/seed/gr.sh), r1 and later only: the rung's own seed/tests/<rung> AND every earlier rK with an
#          oracle (a later rung keeps every earlier rung's programs passing; r4 = r1 + r3 + r4)
#   UNIT   with --with-unit: every module unit test (scripts/seed/unit-all.sh) built by the CURRENT seed-1
#   Honesty (HOUSE2, 2026-10-03): the rung name must resolve to test directories and a refusal golden (seed_rung_tests /
#          seed_rung_golden in lib.sh, aliases in seed/tests/ALIASES) or the run fails at once; --no-build refuses seed binaries whose
#          recorded unity sha256 differs from the CURRENT seed/MANIFEST sources (a stale or hand-copied build is not a result);
#          BUILD is build.sh auto: stage-0 fixed point, or, where stage-0 refuses the unity (R3+ language), the lineage route
#          (seed-0 = the newest recorded rung seed reproduced by bootstrap.sh --no-head); G3 includes the negatives of every rung K<=N.
#   ERR    scripts/seed/errors-check.py: seed/HEADS :errors == the text tables of 90-drv, module-local codes registered
#   FUEL   with --with-fuel: seed fuel <= stage-0 fuel per port and probe (scripts/seed/fuel.sh)
# Output: build/seed/gates/<rung>/<gate>.log, build/seed/gates/<rung>/summary.tsv (gate, status, seconds, detail), and
# the table on stdout. Statuses: PASS, FAIL, SKIP (not requested or not applicable at the rung).
# Env: see lib.sh. The stage-0 compile inside BUILD respects the machine-wide two-slot lock.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
rung=r0; nobuild=0; only=""; skip=""; withfuel=0; withunit=0
while [ $# -gt 0 ]; do
  case $1 in --rung) rung=$2; shift 2 ;; --no-build) nobuild=1; shift ;; --with-fuel) withfuel=1; shift ;; --with-unit) withunit=1; shift ;; --only) only=$2; shift 2 ;; --skip) skip=$2; shift 2 ;; *) echo "usage: gates.sh [--rung rN] [--no-build] [--with-fuel] [--with-unit] [--only G1,..] [--skip G5,..]" >&2; exit 2 ;; esac
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

# ---- rung must resolve (no silent reuse of another rung's tests)
gr_dirs=""
if [ "$rung" != r0 ]; then
  gr_dirs=$(seed_rung_gr_dirs $rung) && [ -n "$gr_dirs" ] && seed_rung_golden $rung > /dev/null \
    || { echo "gates: rung $rung has no test directory with an oracle or no refusal golden (seed/tests/<rung>, seed/tests/ALIASES, seed/tests/golden/refusal-<rung>.txt)" >&2; exit 2; }
fi
# unity sha256 of the CURRENT sources (the same concatenation build.sh makes)
cur_unity=$( { for p in $(seed_manifest); do cat $R/$p; printf '\n'; done } | shasum -a 256 | cut -c1-64 )

# ---- BUILD
if want BUILD; then
  if [ $nobuild -eq 1 ]; then
    built=$(sed -n 's/^unity-sha256 //p' $B/seed-1.info 2>/dev/null)
    run BUILD sh -c "for k in 0 1 2; do [ -s $B/seed-\$k.bin ] || { echo missing seed-\$k.bin; exit 1; }; done; [ '$built' = '$cur_unity' ] || { echo 'STALE: seed-1 was built from unity '\"$built\"', the current sources are '$cur_unity' (rebuild without --no-build)'; exit 1; }; echo 'reused '$B'/seed-{0,1,2}.bin (--no-build), built from the current sources: unity sha256 '$cur_unity'; '\$(head -1 $B/seed-0.info | cut -c1-90)"
  else
    run BUILD zsh $S/build.sh auto
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
    if grep -q '^label LINEAGE' $B/seed-0.info 2>/dev/null; then
      # lineage build: seed-0 is the previous recorded rung seed, whose containers differ legitimately when the code generator changed
      echo "G4: (lineage build: seed-0 vs seed-1 container difference is informational, the fixed point above is the gate)"; return 0
    fi
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
  else
    grall() {   # every directory runs; the last log line joins the per-directory result lines
      local d rc=0 out="" l
      for d in ${=gr_dirs}; do l=$(zsh $S/gr.sh $d $B/seed-1.bin 2>&1); [ $? -eq 0 ] || rc=1; echo "$l"; out="$out${out:+ | }$(echo "$l" | grep '^GR \[' | cut -c1-150)"; done
      echo "$out"; return $rc
    }
    run GR grall
  fi
fi

# ---- UNIT (with --with-unit)
if [ $withunit -eq 1 ] && want UNIT; then run UNIT zsh $S/unit-all.sh $B/seed-1.bin; fi

# ---- table
order=(BUILD ERR G1 G2 G3 G4 G5 GR UNIT FUEL)
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
