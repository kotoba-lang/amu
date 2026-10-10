#!/bin/zsh
# seed/tests/kgraph-capacity/check.sh [work-dir] [reference-loader] -- the kgraph budget of tools/kexe_loader.c:
#   - the default stays 4096 (the artifact ABI's :kgraph-capacity): budget.kotoba asserting 4096 datoms answers, 4097
#     traps `:budget/cells :arena :kgraph`;
#   - KEXE_KGRAPH raises it for one run (4097 and 1,000,000 datoms answer under KEXE_KGRAPH=1048576), up to
#     KEXE_KGRAPH_MAX (16 Mi): 0, garbage and 16777217 are refused by name with exit 2, 16777216 is admitted;
#   - kgraph_get answers through the (entity, attribute) index exactly what the scan answered: every answer is checked
#     against the closed form, and against REFERENCE-LOADER (a loader built from an earlier tools/kexe_loader.c, which
#     scans) for every N it can hold.
# The guest is compiled by bin/amu (BOOTSTRAP-REFERENCE: the loader is under test, not the compiler).
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h:h}
W=${1:-$R/build/kgraph-capacity}; mkdir -p $W; W=${W:A}; REF=${2:+${2:A}}
L=$W/kexe-loader; cc -std=c11 -O2 $R/tools/kexe_loader.c -o $L || exit 2
echo '{:allow #{}}' > $W/policy.edn
(cd $R && bin/amu compile $H/budget.kotoba --target aarch64-macos --policy $W/policy.edn --output $W/budget.kexe > $W/compile.log 2>&1) || { cat $W/compile.log; exit 2; }
off=$(cd $R && bin/amu extract-native $W/budget.kexe --symbol entry --output $W/budget.bin | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
[ -n "$off" ] || { echo "extract-native failed" >&2; exit 2; }
fails=0
expect() { # n -> N + sum over e of the last i < n with i mod 7 = e
  python3 -c "import sys; n=int(sys.argv[1]); print(n + sum(max(i for i in range(e, n, 7)) for e in range(7) if e < n))" $1; }
check() { # label expected-status expected-stdout-or-pattern env... -- n
  local label=$1 st=$2 want=$3; shift 3; local envs=(); while [ "$1" != "--" ]; do envs+=($1); shift; done; shift
  local out err rc; out=$(env $envs KEXE_CPU_SECONDS=60 KEXE_WALL_SECONDS=60 $L $W/budget.bin $off 1 aarch64 - $1 2>$W/err); rc=$?; err=$(cat $W/err)
  if [ $rc -eq $st ] && { [[ "$out" == "$want" ]] || [[ "$err" == *"$want"* ]]; }; then echo "PASS $label"
  else echo "FAIL $label: exit $rc (want $st) stdout [$out] stderr [${err//$'\n'/ }] want [$want]"; fails=$((fails+1)); fi
}
check "default, 4096 datoms" 0 "$(expect 4096)" -- 4096
check "default, 4097 datoms traps" 120 ":budget/cells :arena :kgraph" -- 4097
check "KEXE_KGRAPH=4097, 4097 datoms" 0 "$(expect 4097)" KEXE_KGRAPH=4097 -- 4097
check "KEXE_KGRAPH=4097, 4098 datoms traps" 120 ":budget/cells :arena :kgraph" KEXE_KGRAPH=4097 -- 4098
check "KEXE_KGRAPH=1048576, 1000000 datoms" 0 "$(expect 1000000)" KEXE_KGRAPH=1048576 -- 1000000
check "KEXE_KGRAPH=16777216 admitted" 0 "$(expect 10)" KEXE_KGRAPH=16777216 -- 10
check "KEXE_KGRAPH=16777217 refused" 2 "KEXE_KGRAPH exceeds the 16777216-datom ceiling" KEXE_KGRAPH=16777217 -- 10
check "KEXE_KGRAPH=0 refused" 2 "KEXE_KGRAPH must be a positive decimal integer" KEXE_KGRAPH=0 -- 10
check "KEXE_KGRAPH=1x refused" 2 "KEXE_KGRAPH must be a positive decimal integer" KEXE_KGRAPH=1x -- 10
check "KEXE_KGRAPH= (empty) is the default" 120 ":budget/cells :arena :kgraph" KEXE_KGRAPH= -- 4097
if [ -n "$REF" ]; then
  for n in 0 1 6 7 8 100 4095 4096 4097; do
    a=$(KEXE_CPU_SECONDS=60 KEXE_WALL_SECONDS=60 $L $W/budget.bin $off 1 aarch64 - $n 2>&1; echo "exit $?")
    b=$(KEXE_CPU_SECONDS=60 KEXE_WALL_SECONDS=60 $REF $W/budget.bin $off 1 aarch64 - $n 2>&1; echo "exit $?")
    if [ "$a" = "$b" ]; then echo "PASS same as the reference loader, N=$n"; else echo "FAIL N=$n: [$a] vs reference [$b]"; fails=$((fails+1)); fi
  done
fi
echo "kgraph-capacity check: $fails failed"; [ $fails -eq 0 ]
