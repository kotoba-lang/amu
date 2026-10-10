#!/bin/zsh
# seed/tests/check-cli/image.sh AMU [work-dir] [policy.edn] -- the native amu image's PRODUCT `check` (seed/amu-main
# k/amu/check = nbb.check-cli's Kotoba run) against `bin/amu check` (BOOTSTRAP-REFERENCE: the nbb route of the same
# code; agent claude, 2026-10-10) on the compile-cli corpus (seed/tests/compile-cli/run.sh's directories) plus the 19
# Embench ports when the amu-embench checkout is present (prove-100 G2 needs all 391), with the same command line
# (`check <abs file> [--policy P]`). Judged by judge.py (exit status; both accept -> the answer maps as data; both
# refuse -> the report maps as data; every difference must be a row of named.tsv, matched by program, key and both
# values). result.tsv: class (SAME SAME-DATA NAMED STUB DIFF), host exit, image exit, detail (named row ids or the
# unnamed keys), program, the image's stderr head. CC_JOBS (default 6) programs at a time.
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h:h}
if [ "$1" = --job ]; then
  W=$2; f=${3:A}; A=$(cat $W/image); k=${${f#$R/}//\//.}; pol=($(cat $W/policy-args))
  D=$W/c/$k; rm -rf $D; mkdir -p $D
  (cd $R && KOTOBA_VERDICT_CACHE=off bin/amu check $f $pol > $D/h.out 2> $D/h.err); hs=$?
  KEXE_CAP_RESOURCES_35=$R:$W $A check $f $pol > $D/g.out 2> $D/g.err; gs=$?
  echo $hs > $D/h.rc; echo $gs > $D/g.rc
  IFS=$'\t' read -r cls det < <(python3 $H/judge.py $D ${f#$R/} - $H/named.tsv)
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' $cls $hs $gs "$det" ${f#$R/} "$(head -c 160 $D/g.err | tr '\n\t' '  ')" > $W/rows/$k.tsv
  exit 0
fi
A=${1:?usage: image.sh AMU [work-dir] [policy.edn]}; A=${A:A}
W=${2:-$R/build/check-cli-image}; mkdir -p $W; W=${W:A}
echo $A > $W/image; if [ -n "$3" ]; then echo "--policy ${3:A}" > $W/policy-args; else : > $W/policy-args; fi
cd $R
E=/Users/junkawasaki/github/kotoba-lang/amu-embench/bench/embench/ports
files=(); for d in $E seed/tests/r1/feat seed/tests/r1/conf seed/tests/corpus resources/kotoba/lang-conformance/{values,control,native} \
                  $R/seed/tests/conformance/*(/N) examples test/dual-backend test/nbb/fixtures test/nbb/fixtures/state bench/runtime-comparison; do
  files+=(${${d:A}/#$PWD/$R}/*.kotoba(N)); done
rm -rf $W/rows $W/c; mkdir -p $W/rows
print -l ${files:A} | xargs -P ${CC_JOBS:-6} -I{} zsh $H/image.sh --job $W {}
cat $W/rows/*.tsv | sort -t$'\t' -k5 > $W/result.tsv
echo "check-cli image $(shasum -a 256 $A | cut -c1-16) policy ${3:-none}: programs $(wc -l < $W/result.tsv | tr -d ' ')"
cut -f1 $W/result.tsv | sort | uniq -c
