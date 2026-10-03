#!/bin/zsh
# scripts/seed/frontsrc/test.sh <amu-one-src> [work] -- tests of an amu image whose frontend is compiled from source
# (agent FRONTSRC, 2026-10-04). BOOTSTRAP-TOOL (zsh; cc only to build the exec interposer of no-host-processes.sh).
#   T1 check ok          examples/aiueos-probe.kotoba            -> "ok profile=default effects=#{} exports=[main]", 0
#   T2 check refuse      seed/tests/r1/feat/46-doseq-trap.kotoba and seed/tests/corpus/060-truthiness.kotoba are refused
#                        with stage-0's line (subset-reject, "if test is :i64"), exit 65
#   T3 check usage       `check` without a file -> 64; unknown command -> 64
#   T4 compile           the crc32 Embench port -> kseed byte-identical to the r6j seed's (FS_SEED), and its test export
#                        runs to rc=0 through the C loader
#   T5 build commands    `modules`, `compile --emit-module`, `link`, `extract-native` of a 2-module project answer 0
#                        and the linked entry runs (exit = its main)
#   T6 no host process   T1, T4 and T5's link under the exec interposer (build/seed/noproc/noproc.dylib, empty PATH):
#                        every process loaded it, 0 exec/spawn/system/popen, forks = commands (the loader's supervisor)
# Exit 0 when all pass.
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h:h}
A=${1:?usage: test.sh <amu-one-src> [work]}; A=${A:A}
W=${2:-$R/build/frontsrc/test}; rm -rf $W; mkdir -p $W; W=${W:A}
pass=0; fail=0
ok() { pass=$((pass + 1)); echo "PASS $*"; }
no() { fail=$((fail + 1)); echo "FAIL $*"; }
# T1
o=$($A check $R/examples/aiueos-probe.kotoba 2>&1); s=$?
[ $s -eq 0 ] && [ "$o" = "ok profile=default effects=#{} exports=[main]" ] && ok "T1 check ok" || no "T1 check ok ($s: $o)"
# T2
for f in seed/tests/r1/feat/46-doseq-trap.kotoba seed/tests/corpus/060-truthiness.kotoba; do
  o=$($A check $R/$f 2>&1); s=$?
  [ $s -eq 65 ] && [[ "$o" == "error: subset-reject at $R/$f"*"if test is :i64"* ]] && ok "T2 check refuse ${f:t}" || no "T2 check refuse ${f:t} ($s: $o)"
done
# T3
$A check > /dev/null 2>&1; s1=$?; $A frobnicate > /dev/null 2>&1; s2=$?
[ $s1 -eq 64 ] && [ $s2 -eq 64 ] && ok "T3 usage 64/64" || no "T3 usage ($s1 $s2)"
# T4
E=/Users/junkawasaki/github/kotoba-lang/amu-embench/bench/embench/ports
export SEED_REPO=$R SEED_BUILD=$W; source $R/scripts/seed/lib.sh; L=$(seed_loader)
SB=${FS_SEED:-$R/build/float/seed-1.bin}
SEED_RESOURCES_35=$R:$E:$W seed_run $SB 0 compile $E/crc32.kotoba --target aarch64-macos --output $W/crc32-seed.kseed > /dev/null 2>&1
$A compile $E/crc32.kotoba --target aarch64-macos --output $W/crc32.kseed > $W/t4.out 2>&1 \
  && off=$($A extract-native $W/crc32.kseed --symbol test-crc32 --output $W/crc32.bin | sed -n 's/.*:offset \([0-9]*\).*/\1/p') \
  && v=$($L $W/crc32.bin $off 0 aarch64 35 2>&1; echo "rc=$?")
same=no; cmp -s $W/crc32.kseed $W/crc32-seed.kseed && same=yes
[[ "$v" == *"rc=0" ]] && [ $same = yes ] && ok "T4 compile crc32 (== seed's kseed) + run test-crc32 ($(echo $v | tr '\n' ' '))" || no "T4 compile (same=$same $(cat $W/t4.out) $v)"
# T5
mkdir -p $W/p/pa $W/o
printf '(ns pa.lib\n  {:kotoba/export [seven]})\n\n(defn seven [] :i64 7)\n' > $W/p/pa/lib.kotoba
printf '(ns pa.main\n  {:kotoba/export [main]}\n  (:require [pa.lib :as l]))\n\n(defn main [] :i64 (+ (l/seven) 35))\n' > $W/p/pa/main.kotoba
m=$($A modules $W/p/pa/main.kotoba --source-path $W/p 2>&1)
$A compile $W/p/pa/lib.kotoba --target aarch64-macos --emit-module --object-dir $W/o --output $W/o/pa.lib.kso > $W/t5.out 2>&1 \
  && $A compile $W/p/pa/main.kotoba --target aarch64-macos --emit-module --entry --object-dir $W/o --output $W/o/pa.main.kso >> $W/t5.out 2>&1 \
  && $A link $W/o/pa.main.kso --object-dir $W/o --output $W/pa.kseed >> $W/t5.out 2>&1 \
  && off=$($A extract-native $W/pa.kseed --symbol main --output $W/pa.bin | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
KEXE_COMMAND=1 $L $W/pa.bin ${off:-0} 0 aarch64 35 -- > /dev/null 2>&1; s=$?
[ $s -eq 42 ] && [[ "$m" == *"pa.lib"* ]] && ok "T5 modules/emit-module/link/extract-native, entry exits 42" || no "T5 ($s; $m; $(tail -2 $W/t5.out))"
# T6
N=$R/build/seed/noproc
if [ -f $N/noproc.dylib ]; then
  LG=$W/noproc.log; rm -f $LG; mkdir -p $W/empty-path; n=0; nf=0
  nr() { n=$((n + 1)); env -i PATH=$W/empty-path HOME=$HOME TMPDIR=/tmp NOPROC_LOG=$LG DYLD_INSERT_LIBRARIES=$N/noproc.dylib $A "$@" > $W/nr.$n 2>&1 || nf=$((nf + 1)); }
  nr check $R/examples/aiueos-probe.kotoba
  nr compile $E/crc32.kotoba --target aarch64-macos --output $W/crc32b.kseed
  nr link $W/o/pa.main.kso --object-dir $W/o --output $W/pa2.kseed
  loaded=$(awk '$2 == "loaded"' $LG | wc -l | tr -d ' '); calls=$(awk '$2 != "loaded" && $2 != "fork"' $LG | wc -l | tr -d ' ')
  forks=$(awk '$2 == "fork"' $LG | wc -l | tr -d ' ')
  [ $nf -eq 0 ] && [ $loaded -eq $n ] && [ $calls -eq 0 ] && [ $forks -eq $n ] \
    && ok "T6 no host process: $n runs, $loaded interposer loads, $calls exec/spawn/system/popen, $forks supervisor forks" \
    || no "T6 ($nf failed, loaded $loaded/$n, calls $calls, forks $forks)"
else
  no "T6 no interposer at $N/noproc.dylib (run scripts/seed/no-host-processes.sh once)"
fi
echo "frontsrc test: $pass passed, $fail failed ($A $(shasum -a 256 $A | cut -c1-16))"
[ $fail -eq 0 ]
