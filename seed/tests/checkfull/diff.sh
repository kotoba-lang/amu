#!/bin/zsh
# seed/tests/checkfull/diff.sh <amu> <work-dir> [cases-file] -- `amu check` differential against stage-0 (agent CHECKFULL,
# 2026-10-04). BOOTSTRAP-TOOL (zsh, python3). Stage-0 = build/native-image/amu-native, BOOTSTRAP-REFERENCE: the oracle,
# never in the amu image's process tree. Every case runs in seed/tests/checkfull/fx on both sides; the default cases are
# cases-args.txt plus every fixture policy p*.edn against io / pure / two / abort.kotoba.
# Classes: SAME (exit status, stdout, stderr byte-identical), SAME-NORM (equal once each printed set's members are
# sorted -- a host set prints in hash order -- and the `:line:col` after the file name of a refusal line is dropped; the
# frontend's refusal carries no span), STUB (amu answers exit 69 :not-available), DECLARED (declared.txt), DIFF.
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h:h}
A=${1:?usage: diff.sh <amu> <work-dir> [cases]}; A=${A:A}; W=${2:?}; mkdir -p $W; W=${W:A}
S0=$R/build/native-image/amu-native
C=$W/cases.txt; grep -v '^#' ${3:-$H/cases-args.txt} | grep -v '^$' > $C
if [ -z "$3" ]; then for p in $H/fx/p*.edn; do for f in io pure two abort; do echo "check $f.kotoba --policy ${p:t}" >> $C; done; done; fi
: > $W/result.tsv; n=0
while IFS= read -r line; do
  n=$((n + 1)); d=$W/c$n; mkdir -p $d
  args=(${(z)line})
  ( cd $H/fx; nice $S0 ${args} > $d/s0.out 2> $d/s0.err; echo $? > $d/s0.rc )
  ( cd $H/fx; $A ${args} > $d/a.out 2> $d/a.err; echo $? > $d/a.rc )
  python3 - $d "$line" $H/declared.txt >> $W/result.tsv <<'P'
import sys, re
d, line, dec = sys.argv[1:4]
declared = {l.split('\t')[0] for l in open(dec) if l.strip() and not l.startswith('#')}
rd = lambda p: open(d + '/' + p, 'rb').read().decode('utf-8', 'replace')
s0 = (rd('s0.rc').strip(), rd('s0.out'), rd('s0.err')); am = (rd('a.rc').strip(), rd('a.out'), rd('a.err'))
def sets(t): return re.sub(r'#\{([^{}]*)\}', lambda m: '#{' + ' '.join(sorted(re.findall(r'\[[^\]]*\]|\S+', m[1]))) + '}', t)
def norm(t): return sets(re.sub(r'^(error: \S+ at .*?)(:\d+)+: ', r'\1: ', t, flags=re.M))
if s0 == am: cls = 'SAME'
elif am[0] == '69' and ':not-available' in am[2]: cls = 'STUB'
elif (s0[0], norm(s0[1]), norm(s0[2])) == (am[0], norm(am[1]), norm(am[2])): cls = 'SAME-NORM'
elif line in declared: cls = 'DECLARED'
else: cls = 'DIFF'
first = lambda t: (t[1] + t[2]).strip().split('\n')[0][:160]
print('\t'.join([cls, line, s0[0], am[0], first(s0), first(am)]))
P
done < $C
cut -f1 $W/result.tsv | sort | uniq -c
grep -v '^SAME' $W/result.tsv | cut -f1-4
! grep -q '^DIFF' $W/result.tsv
