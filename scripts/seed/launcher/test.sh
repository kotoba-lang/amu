#!/bin/zsh
# scripts/seed/launcher/test.sh [AMU] [work-dir] -- the native launcher's gate (agent CMD, 2026-10-04; LAUNCHER.md).
# BOOTSTRAP-TOOL (zsh, python3; stage-0 and node only as oracles, never in AMU's process tree).
#   L1 argument layer: seed/amu-main/usage-parity.sh AMU -> PASS when no case is DIFF (SAME or DECLARED only)
#   L2 Embench: the 19 ports compiled by AMU to :kotoba.kexe/v1 (seal checked) and every correctness export run from AMU's
#      code and from stage-0's under the C loader (seed/amu-main/parity.sh --compile, AM_FILES = the ports) -> PASS when
#      19 BEHAVIOUR-SAME, 0 DIFF, 0 MISSING, 19 seals ok
#   L3 no host process: AMU --help, check, compile, compile + run, an unknown command and a stub under the exec interposer
#      (build/seed/noproc/noproc.dylib, scripts/seed/no-host-processes.sh; empty PATH, env -i): every run loads the
#      interposer, no exec / posix_spawn / system / popen at all, at most the loader's own supervisor fork per run
#   L4 static: otool -L only /usr/lib; the baked wire list has no 20 (spawn)
# Exit 0 when all PASS.
emulate -L zsh; setopt pipefail nullglob
H=${0:A:h}; R=${H:h:h:h}
A=${1:-$R/build/launcher/amu}; A=${A:A}
W=${2:-$R/build/launcher/test}; rm -rf $W; mkdir -p $W; W=${W:A}
fail=0; ok() { echo "PASS $*"; }; no() { echo "FAIL $*"; fail=1; }

# L1
zsh $R/seed/amu-main/usage-parity.sh $A $W/usage > $W/usage.out 2>&1
s=$(tail -1 $W/usage.out)
if [ "$(cut -f2 $W/usage/usage.tsv | grep -c DIFF)" = 0 ] && [ -s $W/usage/usage.tsv ]; then ok "L1 $s"; else no "L1 $s"; fi

# L2
E=/Users/junkawasaki/github/kotoba-lang/amu-embench/bench/embench/ports
ls $E/*.kotoba > $W/ports.txt
AM_FILES=$W/ports.txt zsh $R/seed/amu-main/parity.sh $W/embench --compile $A > $W/embench.out 2>&1
n=$(cut -f4 $W/embench/compile.tsv | grep -c '^BEHAVIOUR-SAME$'); sl=$(cut -f12 $W/embench/compile.tsv | grep -c '^ok$')
d=$(awk -F'\t' '{s+=$7+$9} END {print s+0}' $W/embench/compile.tsv); x=$(awk -F'\t' '{s+=$5} END {print s+0}' $W/embench/compile.tsv)
if [ $n = 19 ] && [ $sl = 19 ] && [ $d = 0 ]; then ok "L2 Embench 19/19 BEHAVIOUR-SAME, $x export runs, 0 DIFF/MISSING, 19 seals ok"
else no "L2 Embench $n/19 BEHAVIOUR-SAME, seals ok $sl, DIFF+MISSING $d"; fi

# L3
N=$R/build/seed/noproc
if [ -f $N/noproc.dylib ]; then
  LG=$W/noproc.log; rm -f $LG; mkdir -p $W/empty-path $W/nr; n=0; nf=0
  print -r -- '(ns x) (defn fact [n :i64] :i64 (if (<= n 1) 1 (* n (fact (- n 1))))) (defn main [] :i64 (fact 5))' > $W/nr/x.kotoba
  nr() { n=$((n + 1)); ( cd $W/nr; env -i PATH=$W/empty-path HOME=$HOME TMPDIR=/tmp NOPROC_LOG=$LG DYLD_INSERT_LIBRARIES=$N/noproc.dylib $A "$@" > $W/nr.$n 2>&1 ); echo "$? $*" >> $W/nr.rc; }
  : > $W/nr.rc
  nr --help; nr check x.kotoba; nr compile x.kotoba --output x.kexe; nr compile x.kotoba --target aarch64-macos --output y.kexe
  nr no-such-command; nr inspect x.kotoba
  loads=$(grep -c ' loaded' $LG 2>/dev/null); ex=$(grep -cE 'exec|spawn|system|popen' $LG 2>/dev/null)
  forks=$(grep -c ' fork' $LG 2>/dev/null)
  want="0 --help|0 check x.kotoba|0 compile x.kotoba --output x.kexe|0 compile x.kotoba --target aarch64-macos --output y.kexe|64 no-such-command|69 inspect x.kotoba"
  got=$(paste -sd'|' $W/nr.rc)
  if [ "$got" = "$want" ] && [ "$loads" -ge $n ] && [ "$ex" = 0 ] && [ "$forks" -le $n ]; then
    ok "L3 no host process: $n runs (statuses $got), $loads interposer loads, $forks supervisor forks, 0 exec/spawn/system/popen"
  else no "L3 statuses [$got] loads $loads exec $ex forks $forks (log $LG)"; fi
else no "L3 no interposer at $N/noproc.dylib (run scripts/seed/no-host-processes.sh once)"; fi

# L4
deps=$(otool -L $A | tail -n +2 | awk '{print $1}' | tr '\n' ' ')
allow=$(strings $A | grep -m1 -E '^3,35,37,38,39$|^[0-9,]+$' )
if ! echo "$deps" | tr ' ' '\n' | grep -v '^$' | grep -vq '^/usr/lib/' && [[ ",$allow," != *",20,"* ]]; then ok "L4 libraries: $deps; wires $allow"
else no "L4 libraries: $deps; wires $allow"; fi
echo "launcher test: amu $(shasum -a 256 $A | cut -c1-16) load $(sysctl -n vm.loadavg | awk '{print $2}')"
exit $fail
