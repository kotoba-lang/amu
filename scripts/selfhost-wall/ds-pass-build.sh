#!/bin/zsh
# ds-pass-build.sh: build the desugar PASS image of pass-driver.sh (guest = the desugar differential guest plus ds-pass-tail.cljk:
# passes !read !desugar !count !all, one serialized Form per line). BOOTSTRAP-REFERENCE: compiled by stage-0 (the native-image amu).
#   ds-pass-build.sh <out-dir>        writes <out-dir>/ds_pass.{main.cljk,kexe,bin,offset}
# Env: DS_BASE (the generated desugar guest, default /private/tmp/ds_guest_w.cljk = ds-gen.sh output of 2026-10-02 01:20; a freshly
#      generated guest needs ds-names.txt to name every definition the current frontend calls), WALL_K, WALL_CP (default
#      /private/tmp/wt-K-kotoba-lang, /private/tmp/wall-cp-16.txt), AMU_NATIVE.
HERE="$(cd "$(dirname "$0")" && pwd)"; AMU=${HERE:h:h}
out=${1:?usage: ds-pass-build.sh <out-dir>}; mkdir -p $out; out=${out:A}
K=${WALL_K:-/private/tmp/wt-K-kotoba-lang}; CP=$(cat ${WALL_CP:-/private/tmp/wall-cp-16.txt}); N=${AMU_NATIVE:-$AMU/build/native-image/amu-native}
base=${DS_BASE:-/private/tmp/ds_guest_w.cljk}
sed 's/{:kotoba\/export \[ds-run\]}/{:kotoba\/export [main]}/' $base > $out/ds_pass.main.cljk
cat $HERE/ds-pass-tail.cljk >> $out/ds_pass.main.cljk
printf '\n(defn main [] :i64\n  (let [text (typed-cap-call :io/read :string :string "")\n        out (ds-pass-run text)\n        n (typed-cap-call :io/write :string :string out)]\n    0))\n' >> $out/ds_pass.main.cljk
echo "{:allow #{[:cap/call 3] [:cap/call 37] [:cap/call 41]}}" > $out/policy.edn
SRCDIRS=(${(f)"$(echo "$CP" | tr ':' '\n' | grep '/src$')"} $AMU/src $K/lang/compat); SP=(); for d in $SRCDIRS; do SP+=(--source-path $d); done
export KROOTS="${(j/:/)SRCDIRS}"
( ulimit -s 65500; nice $N compile $out/ds_pass.main.cljk --target aarch64-macos --jvm-free --unpinned --policy $out/policy.edn --output $out/ds_pass.kexe $SP ) 2>&1 | tail -2
# extract-native refuses a kexe above the EDN node ceiling of the stable stage-0; kexe_code.py reads :code directly (byte-identical, scripts/seed/kexe_code.py)
python3 $AMU/scripts/seed/kexe_code.py $out/ds_pass.kexe main $out/ds_pass.bin | tee /dev/stderr | sed -n 's/.*:offset \([0-9]*\).*/\1/p' > $out/ds_pass.offset
