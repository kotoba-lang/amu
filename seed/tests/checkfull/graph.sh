#!/bin/zsh
# seed/tests/checkfull/graph.sh <amu> <work-dir> <graph-fixtures>... -- `amu check <entry> --source-path <root>..` against
# stage-0 (BOOTSTRAP-REFERENCE) on project trees (agent CHECKFULL, 2026-10-04). A fixture dir holds `args` (the entry,
# then the roots, one per line, absolute) as seed/tests/wall2/graph-host.cljk writes them, and is run in its t/ dir; a
# variant per tree adds --policy <fx>/corpus-policy-all.edn. Classes as diff.sh (SAME, SAME-NORM, STUB, DIFF).
emulate -L zsh; setopt pipefail nullglob extendedglob
H=${0:A:h}; R=${H:h:h:h}
A=${1:?usage}; A=${A:A}; W=${2:?}; mkdir -p $W; W=${W:A}; shift 2
S0=$R/build/native-image/amu-native
: > $W/result.tsv; n=0
for G in "$@"; do for d in ${G:A}/*/; do
  a0=("${(@f)$(cat $d/args)}"); a=(); for x in $a0; do if [[ $x == /* ]]; then a+=($x); else a+=(${d}t/$x); fi; done
  for pol in "" $H/fx/corpus-policy-all.edn; do
    n=$((n + 1)); c=$W/c$n; mkdir -p $c
    line=(check ${a[1]}); for r in ${a[2,-1]}; do line+=(--source-path $r); done
    [ -n "$pol" ] && line+=(--policy $pol)
    ( cd $d/t; nice $S0 $line > $c/s0.out 2> $c/s0.err; echo $? > $c/s0.rc; $A $line > $c/a.out 2> $c/a.err; echo $? > $c/a.rc )
    python3 - $c "${d:h:t}/${d:t} ${pol:+policy}" >> $W/result.tsv <<'P'
import sys, re
d, name = sys.argv[1:3]
rd = lambda p: open(d + '/' + p, 'rb').read().decode('utf-8', 'replace')
s0 = (rd('s0.rc').strip(), rd('s0.out'), rd('s0.err')); am = (rd('a.rc').strip(), rd('a.out'), rd('a.err'))
def sets(t): return re.sub(r'#\{([^{}]*)\}', lambda m: '#{' + ' '.join(sorted(re.findall(r'\[[^\]]*\]|\S+', m[1]))) + '}', t)
def norm(t): return sets(re.sub(r'^(error: \S+ at .*?)(:\d+)+: ', r'\1: ', t, flags=re.M))
if s0 == am: cls = 'SAME'
elif am[0] == '69' and ':not-available' in am[2]: cls = 'STUB'
elif (s0[0], norm(s0[1]), norm(s0[2])) == (am[0], norm(am[1]), norm(am[2])): cls = 'SAME-NORM'
else: cls = 'DIFF'
first = lambda t: (t[1] + t[2]).strip().split('\n')[0][:200]
print('\t'.join([cls, name, s0[0], am[0], first(s0), first(am)]))
P
  done
done; done
cut -f1 $W/result.tsv | sort | uniq -c
grep -v '^SAME' $W/result.tsv
