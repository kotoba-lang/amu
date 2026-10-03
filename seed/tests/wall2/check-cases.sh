#!/bin/zsh
# seed/tests/wall2/check-cases.sh GRAPH-FIXTURES > cases.txt -- WALL2's case list for check-run.sh / check-host.cljk:
# `check <file>` for the 391 programs of seed/amu-main/parity.sh's corpus (same dirs), `check <entry> --source-path
# <root>...` for every graph-host.cljk tree, and the corpus' first 20 programs again with parity.sh's policy.
emulate -L zsh
R=${0:A:h:h:h:h}; G=${1:?graph fixtures}; G=${G:A}
E=/Users/junkawasaki/github/kotoba-lang/amu-embench/bench/embench/ports
dirs=($E $R/seed/tests/r1/feat $R/seed/tests/r1/conf $R/seed/tests/corpus $R/resources/kotoba/lang-conformance/values
      $R/resources/kotoba/lang-conformance/control $R/resources/kotoba/lang-conformance/native $R/seed/tests/conformance/*(/)
      $R/examples $R/test/dual-backend $R/test/nbb/fixtures $R/test/nbb/fixtures/state $R/bench/runtime-comparison)
files=(); for d in $dirs; do files+=($d/*.kotoba(N)); done
for f in $files; do echo "check $f"; done
for d in $G/*/(N); do
  a=("${(@f)$(cat $d/args)}"); line="check ${a[1]}"; for r in ${a[2,-1]}; do line="$line --source-path $r"; done; echo $line
done
pol=$R/build/wall2/check-policy.edn; mkdir -p ${pol:h}
echo '{:allow #{[:cap/call 35] [:cap/call 37] [:cap/call 38] [:cap/call 39]}}' > $pol
for f in ${files[1,20]}; do echo "check $f --policy $pol"; done
