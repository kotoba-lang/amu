#!/bin/zsh
# seed/amu-front/corpus.sh <work-dir> [amu-front] -- verdict differential of the native `amu-front check` against stage-0
# `amu check` (agent COMPOSE, 2026-10-03; seed/amu-front/README.md). BOOTSTRAP-TOOL (zsh + python3; stage-0 is
# the JVM-built native image build/native-image/amu-native, labelled BOOTSTRAP-REFERENCE; it is the oracle, never in the
# product process tree).
#
# Corpus: the program directories of scripts/selfhost-wall/kir-backend-diff.sh (391 programs; stage-0 compiles 315 of them
# for aarch64-macos, docs/selfhost-seed-merge-20261003.md section 2). Both sides get the same command line
# `check <file>` (no --source-path, no policy). One process per file on both sides.
# Output: <work>/verdicts.tsv: id file bytes s0-rc s0-line af-rc af-line af-real-s af-maxrss-B class load1 vectors pairs heap-B
#   (the last three: the loader's KEXE_ARENA_USE high-water marks of the native run)
# class: SAME-OK (both ok, same profile/effects-as-set/exports), SAME-REFUSE (both refuse, same message text),
#        OK-DIFF (both ok, report differs), REFUSE-DIFF (both refuse, other text), AF-REFUSES (stage-0 ok, native refuses),
#        AF-ACCEPTS (stage-0 refuses, native ok), AF-TRAP (native crashed / budget trap / no line).
# Env: AF_S0 (stage-0 binary), AF_FILES (file with a path list instead of the default corpus), AF_SKIP_S0=1 (reuse s0 lines),
#      AF_ONLY_S0=1 (only the stage-0 side).
emulate -L zsh; setopt pipefail nullglob
H=${0:A:h}; R=${H:h:h}
W=${1:?usage: corpus.sh <work-dir> [amu-front]}; mkdir -p $W/run; W=${W:A}
AF=${2:-$R/build/compose/amu-front}; AF=${AF:A}
S0=${AF_S0:-$R/build/native-image/amu-native}
E=/Users/junkawasaki/github/kotoba-lang/amu-embench/bench/embench/ports
if [ -n "$AF_FILES" ]; then files=(${(f)"$(cat $AF_FILES)"})
else
  dirs=($E $R/seed/tests/r1/feat $R/seed/tests/r1/conf $R/seed/tests/corpus $R/resources/kotoba/lang-conformance/values
        $R/resources/kotoba/lang-conformance/control $R/resources/kotoba/lang-conformance/native $R/seed/tests/conformance/*(/)
        $R/examples $R/test/dual-backend $R/test/nbb/fixtures $R/test/nbb/fixtures/state $R/bench/runtime-comparison)
  files=(); for d in $dirs; do files+=($d/*.kotoba); done
fi
grp() { local d=$1; d=${d#$R/}; d=${d#/Users/junkawasaki/github/kotoba-lang/amu-embench/bench/}; d=${d%.kotoba}; echo ${d//\//.}; }
ulimit -s 65500 2>/dev/null
out=$W/verdicts.tsv; : > $out
for f in $files; do
  id=$(grp $f); r=$W/run/$id; mkdir -p $r
  if [ -z "$AF_SKIP_S0" ] || [ ! -s $r/s0.rc ]; then
    nice $S0 check $f > $r/s0.out 2> $r/s0.err; echo $? > $r/s0.rc
  fi
  [ -n "$AF_ONLY_S0" ] && continue
  load=$(sysctl -n vm.loadavg | awk '{print $2}')
  KEXE_ARENA_USE=1 /usr/bin/time -l $AF check $f > $r/af.out 2> $r/af.err; echo $? > $r/af.rc
  python3 - $f $id $r $load >> $out <<'P'
import sys, re, os
f, id, r, load = sys.argv[1:5]
def rd(p):
    try: return open(p, encoding='utf-8', errors='replace').read()
    except OSError: return ''
def line(out, err):
    for l in (out + '\n' + err).split('\n'):
        if l.startswith('ok ') or l.startswith('error: '): return l.strip()
    return ''
s0 = line(rd(r + '/s0.out'), rd(r + '/s0.err')); s0rc = rd(r + '/s0.rc').strip()
aerr = rd(r + '/af.err'); af = line(rd(r + '/af.out'), aerr); afrc = rd(r + '/af.rc').strip()
real = (re.search(r'([0-9.]+) real', aerr) or [None, ''])[1]
rss = (re.search(r'(\d+)\s+maximum resident', aerr) or [None, ''])[1]
ar = lambda k: (re.search(r'KEXE_ARENA_USE \{.*?:%s (\d+)' % k, aerr) or [None, ''])[1]
def okparts(l):
    m = re.match(r'ok profile=(\S+) effects=#\{(.*?)\} exports=\[(.*?)\]', l)
    return None if not m else (m[1], tuple(sorted(m[2].split())), m[3].split())
def sets(t):  # a printed host set's member order is hash order: compare members sorted
    return re.sub(r'#\{([^{}]*)\}', lambda m: '#{' + ' '.join(sorted(re.findall(r'\[[^\]]*\]|\S+', m[1]))) + '}', t)
def msg(l):
    m = re.match(r'error: \S+ at .*?: (.*)$', l) or re.match(r'error: \S+: (.*)$', l)
    return sets(m[1] if m else l)
if not af: cls = 'AF-TRAP'
elif s0.startswith('ok') and af.startswith('ok'): cls = 'SAME-OK' if okparts(s0) == okparts(af) else 'OK-DIFF'
elif s0.startswith('error') and af.startswith('error'):
    a, b = msg(s0), msg(af)
    cls = 'SAME-REFUSE' if a == b else 'REFUSE-DIFF'
elif s0.startswith('ok'): cls = 'AF-REFUSES'
else: cls = 'AF-ACCEPTS'
if not af:
    t = [l for l in aerr.split('\n') if 'KEXE' in l or 'trap' in l.lower()]
    af = ('TRAP ' + (t[-1] if t else 'rc=' + afrc))[:300]
cl = lambda s: s.replace('\t', ' ')[:400]
print('\t'.join([id, f, str(os.path.getsize(f)), s0rc, cl(s0), afrc, cl(af), real, rss, cls, load, ar('vectors'), ar('pairs'), ar('heap-bytes')]))
P
  tail -1 $out | awk -F'\t' '{printf "%-50s %-12s %ss\n", $1, $10, $8}'
done
echo; awk -F'\t' '{print $10}' $out | sort | uniq -c
