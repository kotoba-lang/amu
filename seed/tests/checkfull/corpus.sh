#!/bin/zsh
# seed/tests/checkfull/corpus.sh <amu> <work-dir> [policy.edn] -- `amu check [--policy P]` over the 391 corpus programs of
# seed/amu-main/parity.sh against stage-0 (agent CHECKFULL, 2026-10-04). BOOTSTRAP-TOOL (zsh, python3); stage-0 is the
# BOOTSTRAP-REFERENCE oracle (build/native-image/amu-native), cached per (program, policy) sha in build/checkfull/s0cache.
# Classes as parity.sh's check column: SAME-OK SAME-REFUSE (+ -RC when only the exit status differs) OK-DIFF REFUSE-DIFF
# AMU-REFUSES AMU-ACCEPTS AMU-TRAP STUB. Both sides run in the program's directory with the program's absolute path.
# Since 2026-10-10 prove-100 G2/G3/CHECK_FULL no longer call this script: the image's `check` is nbb.check-cli's
# Kotoba run and is judged against bin/amu (seed/tests/check-cli/image.sh, args.sh). Kept for stage-0 history.
emulate -L zsh; setopt pipefail nullglob
H=${0:A:h}; R=${H:h:h:h}
A=${1:?usage: corpus.sh <amu> <work-dir> [policy]}; A=${A:A}; W=${2:?}; mkdir -p $W; W=${W:A}
P=${3:-}; [ -n "$P" ] && P=${P:A}
S0=$R/build/native-image/amu-native; KC=$R/build/checkfull/s0cache; mkdir -p $KC
E=/Users/junkawasaki/github/kotoba-lang/amu-embench/bench/embench/ports
dirs=($E $R/seed/tests/r1/feat $R/seed/tests/r1/conf $R/seed/tests/corpus $R/resources/kotoba/lang-conformance/values
      $R/resources/kotoba/lang-conformance/control $R/resources/kotoba/lang-conformance/native $R/seed/tests/conformance/*(/)
      $R/examples $R/test/dual-backend $R/test/nbb/fixtures $R/test/nbb/fixtures/state $R/bench/runtime-comparison)
files=(); for d in $dirs; do files+=($d/*.kotoba); done
pa=(); [ -n "$P" ] && pa=(--policy $P)
ph=none; [ -n "$P" ] && ph=$(shasum -a 256 $P | cut -c1-12)
: > $W/check.tsv
for f in $files; do
  k=$KC/$(shasum -a 256 $f | cut -c1-16)-$ph
  if [ ! -f $k.rc ]; then ( cd ${f:h}; nice $S0 check $f $pa > $k.out 2> $k.err; echo $? > $k.rc ); fi
  d=$W/run/$(echo ${f#$R/} | tr '/' '.'); mkdir -p $d
  ( cd ${f:h}; $A check $f $pa > $d/a.out 2> $d/a.err; echo $? > $d/a.rc )
  python3 - $f $k $d >> $W/check.tsv <<'P'
import sys, re
f, k, d = sys.argv[1:4]
rd = lambda p: open(p, 'rb').read().decode('utf-8', 'replace')
def line(o, e):
    for l in (o + '\n' + e).split('\n'):
        if l.startswith('ok ') or l.startswith('error: ') or l.startswith('{:format'): return l.strip()
    return ''
c0, c1 = rd(k + '.rc').strip(), rd(d + '/a.rc').strip()
s0 = line(rd(k + '.out'), rd(k + '.err')); am = line(rd(d + '/a.out'), rd(d + '/a.err'))
def okparts(l):
    m = re.match(r'ok profile=(\S+) effects=#\{(.*?)\} exports=\[(.*?)\]', l)
    return None if not m else (m[1], tuple(sorted(re.findall(r'\[[^\]]*\]|\S+', m[2]))), m[3].split())
def sets(t): return re.sub(r'#\{([^{}]*)\}', lambda m: '#{' + ' '.join(sorted(re.findall(r'\[[^\]]*\]|\S+', m[1]))) + '}', t)
def msg(l):
    m = re.match(r'error: \S+ at .*?: (.*)$', l) or re.match(r'error: \S+: (.*)$', l)
    return sets(m[1] if m else l)
if c1 == '69': cls = 'STUB'
elif not am: cls = 'AMU-TRAP'
elif s0.startswith('ok') and am.startswith('ok'): cls = 'SAME-OK' if okparts(s0) == okparts(am) else 'OK-DIFF'
elif not s0.startswith('ok') and not am.startswith('ok'): cls = 'SAME-REFUSE' if msg(s0) == msg(am) else 'REFUSE-DIFF'
elif s0.startswith('ok'): cls = 'AMU-REFUSES'
else: cls = 'AMU-ACCEPTS'
if cls in ('SAME-OK', 'SAME-REFUSE') and c0 != c1: cls += '-RC'
print('\t'.join([f, c0, s0[:200], c1, am[:200], cls]))
P
done
{ echo "corpus $(date '+%F %T') load $(sysctl -n vm.loadavg | awk '{print $2}') amu $(shasum -a 256 $A | cut -c1-16) policy ${P:-none} files ${#files}"
  cut -f6 $W/check.tsv | sort | uniq -c; } > $W/summary.txt
cat $W/summary.txt
