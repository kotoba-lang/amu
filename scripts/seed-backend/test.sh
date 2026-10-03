#!/bin/zsh
# scripts/seed-backend/test.sh [TOOLDIR] -- BOOTSTRAP-TOOL (ADR 0365): end-to-end checks of `--backend seed` on the amu nbb route.
# TOOLDIR is a scripts/seed-backend/build-wrapper.sh output (classpath.txt + packaged seed); built when missing.
#   T1 no flag: the kexe and provenance are byte-identical to bin/amu's (the lock closure, pinned verifier) for $SB_T1 files
#   T2 --backend seed on crc32: report :emitted :kotoba-seed; artifact and provenance carry the same :emitter; the extracted
#      code is byte-identical to `seed compile-kir` of the artifact's own :program; it returns 1
#   T3 fallback: f64_add (E2101 refusal) -> :fallback in the report, kexe + provenance identical to the default build
#   T4 metered fallback: typed-closure-parameters --fuel -> E1203 (documents under --metered) refused, falls back
#   T5 verify-output-set: --seed ACCEPT; no seed -> refused by name; a DIFFERENT seed program -> refused by name
#   T6 --backend llvm -> usage error; --backend seed without --seed -> usage error
#   T7 bin/amu (pinned verifier, no registry): --backend seed falls back with the reason, default bytes
emulate -L zsh
setopt pipefail
R=${0:A:h:h:h}
O=${1:-$R/build/seed-backend/tool}
[ -f $O/classpath.txt ] && [ -x $O/seed ] || zsh $R/scripts/seed-backend/build-wrapper.sh $O > /dev/null || exit 2
O=${O:A}; CP=$(cat $O/classpath.txt); W=$(mktemp -d /tmp/sb-test.XXXXXX)
P=${SB_PORTS:-/Users/junkawasaki/github/kotoba-lang/amu-embench/bench/embench/ports}
cd $R
# the last line of the command's output; its exit status is not the test (refusals exit non-zero by design)
nbb() { local e=$1; shift; { nice node --stack-size=4096 node_modules/nbb/cli.js --classpath "$CP" src/kotoba/compiler/nbb/$e "$@" 2>&1 || true; } | tail -1; }
pass=0 fail=0
ok() { if [ "$1" = 0 ]; then pass=$((pass+1)); echo "PASS $2"; else fail=$((fail+1)); echo "FAIL $2"; fi }
# T1
for f in ${(s: :)${SB_T1:-$P/crc32.kotoba $P/edn.kotoba examples/recursive-tree.kotoba}}; do
  b=${f:t:r}
  nice bin/amu compile $f --target aarch64-macos --jvm-free --output $W/$b.amu.kexe > $W/$b.amu.log 2>&1
  nbb aarch64_cli.cljk compile $f --target aarch64-macos --jvm-free --output $W/$b.def.kexe > $W/$b.def.log
  cmp -s $W/$b.amu.kexe $W/$b.def.kexe && cmp -s $W/$b.amu.kexe.provenance.edn $W/$b.def.kexe.provenance.edn \
    && ! grep -q ':backend' $W/$b.def.log; ok $? "T1 no flag = bin/amu bytes ($b)"
done
# T2
r=$(nbb aarch64_cli.cljk compile $P/crc32.kotoba --target aarch64-macos --jvm-free --output $W/c.kexe --backend seed --seed $O/seed)
echo "$r" | grep -q ':emitted :kotoba-seed'; ok $? "T2 crc32 emitted by the seed"
e1=$(grep -o ':emitter {[^}]*}' $W/c.kexe); e2=$(grep -o ':emitter {[^}]*}' $W/c.kexe.provenance.edn)
[ -n "$e1" ] && [ "$e1" = "$e2" ] && [[ "$e1" == *"$(shasum -a 256 $O/seed | cut -c1-64)"* ]]; ok $? "T2 artifact and provenance record the seed's sha256"
x=$(nbb x86_64_cli.cljk extract-native $W/c.kexe --symbol test-crc32 --output $W/c.bin --seed $O/seed)
off=$(echo "$x" | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
python3 $R/scripts/seed/kir_extract.py $W/c.kexe $W/c.kir && $O/seed compile-kir $W/c.kir --output $W/c.kseed > /dev/null 2>&1
python3 -c "import sys; d=open('$W/c.kseed','rb').read(); sys.exit(0 if d[d.index(b'\n\n')+2:]==open('$W/c.bin','rb').read() else 1)"; ok $? "T2 artifact code = seed compile-kir of its own :program"
cc -O2 -std=c11 $R/bench/runtime-comparison/kexe-benchmark.c -o $W/kb -ldl 2>/dev/null
$W/kb raw $W/c.bin $off aarch64 0 1 0 16777216 | grep -q '"result":1,'; ok $? "T2 test-crc32 returns 1"
# T3
f=resources/kotoba/lang-conformance/native/f64_add.kotoba
nbb aarch64_cli.cljk compile $f --target aarch64-macos --jvm-free --output $W/f0.kexe > /dev/null
r=$(nbb aarch64_cli.cljk compile $f --target aarch64-macos --jvm-free --output $W/f1.kexe --backend seed --seed $O/seed)
echo "$r" | grep -q ':emitted :machine-ir.*:fallback {:kind :refused, :code "E2101"'; ok $? "T3 f64 refusal falls back with the reason"
cmp -s $W/f0.kexe $W/f1.kexe && cmp -s $W/f0.kexe.provenance.edn $W/f1.kexe.provenance.edn; ok $? "T3 fallback artifact + provenance = default"
# T4
r=$(nbb aarch64_cli.cljk compile test/nbb/fixtures/typed-closure-parameters.kotoba --target aarch64-macos --jvm-free --fuel 1000000 --output $W/d.kexe --backend seed --seed $O/seed)
echo "$r" | grep -q ':fallback {:kind :refused, :code "E1203"'; ok $? "T4 metered documents refused (E1203), fallback"
# T5
nbb output_set_cli.cljk verify-output-set $W/c.kexe --seed $O/seed | grep -q ':committed true'; ok $? "T5 verify-output-set --seed accepts"
nbb output_set_cli.cljk verify-output-set $W/c.kexe | grep -q 'recorded emitter is not available'; ok $? "T5 no seed: refused by name"
cp $O/seed $W/other-seed && printf '\0' >> $W/other-seed
nbb output_set_cli.cljk verify-output-set $W/c.kexe --seed $W/other-seed | grep -q 'recorded emitter is not available'; ok $? "T5 a different seed program: refused by name"
# T6
nbb aarch64_cli.cljk compile $P/crc32.kotoba --target aarch64-macos --output $W/u.kexe --backend llvm | grep -q 'invalid-usage'; ok $? "T6 unknown --backend is a usage error"
AMU_SEED= nbb aarch64_cli.cljk compile $P/crc32.kotoba --target aarch64-macos --output $W/u.kexe --backend seed | grep -q 'needs the packaged seed'; ok $? "T6 --backend seed without a seed is a usage error"
# T7 bin/amu (lock closure: the verifier pin predates kotoba-verifier ADR 0052) does not run the seed; it falls back, saying why
r=$({ nice bin/amu compile $P/crc32.kotoba --target aarch64-macos --jvm-free --output $W/b.kexe --backend seed --seed $O/seed 2>&1 || true; } | tail -1)
echo "$r" | grep -q ':emitted :machine-ir.*no emitter registry' && cmp -s $W/b.kexe $W/crc32.amu.kexe; ok $? "T7 bin/amu with the pinned verifier: fallback, default bytes"
echo "seed-backend test: $pass passed, $fail failed (work $W, load $(sysctl -n vm.loadavg | awk '{print $2}'))"
[ $fail = 0 ]
