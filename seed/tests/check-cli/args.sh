#!/bin/zsh
# seed/tests/check-cli/args.sh AMU work-dir [cases-file] -- the argument and refusal differential of the image's PRODUCT
# `check` against `bin/amu check` (BOOTSTRAP-REFERENCE: the nbb route of the same entry, nbb.check-cli; agent claude,
# 2026-10-10). It replaces seed/tests/checkfull/diff.sh's stage-0 oracle for prove-100 G3 / CHECK_FULL: since
# 2026-10-10 the image's `check` IS nbb.check-cli's Kotoba run and prints bin/amu's :kotoba.check/v1 answer map, so
# stage-0's human `ok ...` / `error: ...` line is no longer the contract. The cases are diff.sh's: cases-args.txt plus
# every fixture policy p*.edn against io / pure / two / abort.kotoba, each run in seed/tests/checkfull/fx by both sides
# with the same argv (bin/amu makes caller paths absolute; that directory is cut from its texts before comparing).
# judge.py classes each case (SAME SAME-DATA NAMED STUB DIFF); a named row is scoped `fx:<case line>` or `*`.
# result.tsv: class, case, host exit, image exit, detail, host first line, image first line.
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h:h}; X=$R/seed/tests/checkfull
A=${1:?usage: args.sh AMU work-dir [cases]}; A=${A:A}; W=${2:?}; mkdir -p $W; W=${W:A}
C=$W/cases.txt; grep -v '^#' ${3:-$X/cases-args.txt} | grep -v '^$' > $C
if [ -z "$3" ]; then for p in $X/fx/p*.edn; do for f in io pure two abort; do echo "check $f.kotoba --policy ${p:t}" >> $C; done; done; fi
: > $W/result.tsv; n=0
while IFS= read -r line; do
  n=$((n + 1)); d=$W/c$n; rm -rf $d; mkdir -p $d
  args=(${(z)line})
  ( cd $X/fx; KOTOBA_VERDICT_CACHE=off $R/bin/amu ${args} > $d/h.out 2> $d/h.err; echo $? > $d/h.rc ) < /dev/null
  ( cd $X/fx; $A ${args} > $d/g.out 2> $d/g.err; echo $? > $d/g.rc ) < /dev/null
  IFS=$'\t' read -r cls det < <(python3 $H/judge.py $d "fx:$line" $X/fx $H/named.tsv)
  first() { (cat $d/$1.out $d/$1.err) | sed "s|$X/fx/||g" | head -1 | cut -c1-160 | tr '\t' ' '; }
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' $cls "$line" $(cat $d/h.rc) $(cat $d/g.rc) "$det" "$(first h)" "$(first g)" >> $W/result.tsv
done < $C
echo "check-cli args $(shasum -a 256 $A | cut -c1-16): cases $(wc -l < $W/result.tsv | tr -d ' ')"
cut -f1 $W/result.tsv | sort | uniq -c
grep -v '^SAME' $W/result.tsv | cut -f1-5
! grep -q '^DIFF' $W/result.tsv
