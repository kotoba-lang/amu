#!/bin/zsh
# scripts/seed/ck-gate.sh [--ref-front] [--update] [label-substring ...] -- admission gate of seed modules 20-names
# and 21-check. BOOTSTRAP-TOOL (owner 20-names/21-check). Builds 00-ns + 10-lex + 11-read + 20-names + 21-check +
# seed/tests/check/ck-common.kotoba + ck-dump.kotoba with STAGE-0 (scripts/seed/lib.sh) and runs it natively on:
#   port/<n>   the 19 Embench ports (bench/embench/ports)                       must be admitted ("ok ...")
#   corpus/<n> seed/tests/corpus/*.kotoba                                        must be admitted
#   self/unity the seed's own unity source (seed/MANIFEST, existing files)       must be admitted
#   case/<n>   seed/tests/check/cases/ok-*.kotoba must be admitted, err-*.kotoba refused
#   neg/<n>    seed/tests/neg/*.kotoba                                           must be refused ("E<code> ...")
#   conf/<d>/<n> the kotoba-lang conformance programs ($CK_CONFORMANCE)          refused, except the ones listed
#              in CK_CONF_ACCEPT (inside Seed-0)
#   spell      seed/tests/check/spellings.kotoba in mode "s" (symbol -> head code table)
# Every result line is compared with seed/tests/check/golden.txt (`<label> <line>`); --update rewrites it. Every line
# is also compared with the independent Python model scripts/seed/ck_ref.py.
# --ref-front: no 10-lex/11-read: the TOK/NODE tables come from the Python reference reader (ck_ref.py --tables,
# loaded by seed/tests/check/ck-load.kotoba); files with a lexical/reader error are skipped; only the reference
# model comparison applies (not the golden). Exit 0 = every expectation holds and every comparison agrees.
# STATUS 2026-10-03 (HOUSE2, measured with the R4 seed): the unit builds with the seed (seed_modbuild) and admits the 19 ports and the
# corpus, but the golden seed/tests/check/golden.txt was never recorded and the reference ck_ref.py is the R0 checker: it DIFFs on the
# R1+ language cases (err-2102-true, err-2114-kw-value, err-2118-*). Not part of gates.sh; G1/G2/G3/GR are the live admission gates.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
R=$SEED_REPO; W=$SEED_BUILD/check; mkdir -p $W
CK_CONFORMANCE=${CK_CONFORMANCE:-/private/tmp/wt-K-kotoba-lang/lang/conformance}
CK_CONF_ACCEPT=${CK_CONF_ACCEPT:-""}   # conf/entry_extensions/main has no ns form and untyped params: refused (E2004)
front=real; [ "$1" = "--ref-front" ] && { front=ref; shift; }
update=0; [ "$1" = "--update" ] && { update=1; shift; }
G=$R/seed/tests/check/golden.txt

if [ $front = ref ]; then B=ck-ref; parts=(seed/00-ns.kotoba seed/01-mem.kotoba seed/02-io.kotoba seed/20-names.kotoba seed/21-check.kotoba seed/tests/check/ck-common.kotoba seed/tests/check/ck-load.kotoba)
else B=ck; parts=(seed/00-ns.kotoba seed/01-mem.kotoba seed/02-io.kotoba seed/10-lex.kotoba seed/11-read.kotoba seed/20-names.kotoba seed/21-check.kotoba seed/tests/check/ck-common.kotoba seed/tests/check/ck-dump.kotoba); fi
: > $W/$B.new
for p in $parts; do cat $R/$p >> $W/$B.new; printf '\n' >> $W/$B.new; done
cmp -s $W/$B.new $W/$B.kotoba || mv $W/$B.new $W/$B.kotoba
if ! { [ -f $W/$B.bin ] && [ $W/$B.bin -nt $W/$B.kotoba ] && [ -s $W/$B.offset ]; }; then
  seed_modbuild $W/$B.kotoba $W/$B || { echo "ck-gate: stage-0 refused the build"; grep -o ':message "[^"]*"' $W/$B.log | head -3; head -c 800 $W/$B.log; exit 1; }
fi
# the self source: the MANIFEST files that exist today
: > $W/self.kotoba
for p in $(seed_manifest); do [ -f $R/$p ] && { cat $R/$p >> $W/self.kotoba; printf '\n' >> $W/self.kotoba; }; done

export SEED_RESOURCES_35="$R:$W:$CK_CONFORMANCE"
list() {
  for f in $R/bench/embench/ports/*.kotoba; do echo "port/${f:t:r} ok $f"; done
  for f in $R/seed/tests/corpus/*.kotoba; do echo "corpus/${f:t:r} ok $f"; done
  echo "self/unity ok $W/self.kotoba"
  for f in $R/seed/tests/check/cases/ok-*.kotoba(N); do echo "case/${f:t:r} ok $f"; done
  for f in $R/seed/tests/check/cases/err-*.kotoba(N); do echo "case/${f:t:r} E $f"; done
  for f in $R/seed/tests/neg/*.kotoba; do echo "neg/${f:t:r} E $f"; done
  for f in $CK_CONFORMANCE/*/*.kotoba(N); do
    l="conf/${${f:h}:t}/${f:t:r}"
    if (( ${${(s: :)CK_CONF_ACCEPT}[(Ie)$l]} )); then echo "$l ok $f"; else echo "$l E $f"; fi
  done
}
: > $W/out.txt
fail=0; n=0; nok=0; nE=0
for line in ${(f)"$(list)"}; do
  lab=${line%% *}; rest=${line#* }; want=${rest%% *}; f=${rest#* }
  if [ $# -gt 0 ]; then hit=0; for s in $@; do [[ $lab == *$s* ]] && hit=1; done; [ $hit -eq 1 ] || continue; fi
  if [ $front = ref ]; then
    python3 $R/scripts/seed/ck_ref.py --tables $f $W/tables.txt
    [ "$(head -1 $W/tables.txt)" = "0 0" ] && continue
    res=$( cd $W; seed_run $W/$B.bin $(cat $W/$B.offset) r $f $W/tables.txt 2> $W/err.txt | head -1 )
  else
    res=$( cd $W; seed_run $W/$B.bin $(cat $W/$B.offset) r $f 2> $W/err.txt | head -1 )
  fi
  [ -n "$res" ] || res="CRASH $(head -c 200 $W/err.txt | tr '\n' ' ')"
  echo "$lab $res" >> $W/out.txt
  n=$((n+1))
  case $res in ok*) nok=$((nok+1)); [ $want = ok ] || { echo "UNEXPECTED ACCEPT $lab"; fail=1; } ;;
               E*) nE=$((nE+1)); [ $want = E ] || { echo "UNEXPECTED REFUSAL $lab: $res"; fail=1; } ;;
               *) echo "BROKEN $lab: $res"; fail=1 ;; esac
done
if [ $# -eq 0 ]; then
  if [ $front = ref ]; then python3 $R/scripts/seed/ck_ref.py --tables $R/seed/tests/check/spellings.kotoba $W/tables.txt
    res=$( cd $W; seed_run $W/$B.bin $(cat $W/$B.offset) s $R/seed/tests/check/spellings.kotoba $W/tables.txt 2> $W/err.txt )
  else res=$( cd $W; seed_run $W/$B.bin $(cat $W/$B.offset) s $R/seed/tests/check/spellings.kotoba 2> $W/err.txt ); fi
  echo "$res" | sed 's/^/spell /' >> $W/out.txt
  python3 - $R/seed/HEADS $W/out.txt <<'PY' || fail=1
import re, sys
heads = open(sys.argv[1]).read()
sp = re.findall(r'"([^"]*)"', heads[heads.index(':spellings'):heads.index(':spellings') + 2000].split(']')[0])
kw = dict((m[1], int(m[0])) for m in re.findall(r'\[:c KW-[A-Z0-9-]+ (\d+) "([^"]+)"\]', heads))
want = {s: i for i, s in enumerate(sp) if i not in (0, 2, 36, 37)}
want.update(kw)
got = {}
for l in open(sys.argv[2]):
    m = re.match(r'spell sym (\S+) head=(-?\d+)', l)
    if m: got[m[1]] = int(m[2])
bad = [(s, want.get(s, 0), got[s]) for s in got if want.get(s, 0) != got[s]]
missing = [s for s in want if s not in got]
print("ck-gate: spellings %d checked, %d wrong %s, %d missing %s" % (len(got), len(bad), bad[:5], len(missing), missing[:5]))
sys.exit(1 if bad or missing else 0)
PY
fi
echo "ck-gate: $n programs, $nok admitted, $nE refused"
# independent cross-check: the Python reference model (scripts/seed/ck_ref.py) must print the same line per label
CK_SELF=$W/self.kotoba CK_CONFORMANCE=$CK_CONFORMANCE python3 $R/scripts/seed/ck_ref.py --gate > $W/ref.txt
grep -v '^spell ' $W/out.txt | python3 -c '
import sys
ref = dict(l.rstrip("\n").split(" ", 1) for l in open(sys.argv[1]))
got = sys.stdin.readlines()
bad = [l for l in got if ref.get(l.split(" ", 1)[0]) != l.rstrip("\n").split(" ", 1)[1]]
print("ck-gate: reference model (ck_ref.py) agrees on %d of %d lines" % (len(got) - len(bad), len(got)))
for l in bad[:10]: print("  DIFF", l.rstrip(), "| ref:", ref.get(l.split(" ", 1)[0]))
sys.exit(1 if bad else 0)' $W/ref.txt || fail=1
if [ $front = ref ]; then [ $fail -eq 0 ] && echo "ck-gate (ref front): PASS" || echo "ck-gate (ref front): FAIL"; exit $fail; fi
if [ $update -eq 1 ]; then
  if [ $# -eq 0 ]; then cp $W/out.txt $G; else
    python3 - $G $W/out.txt <<'PY'
import sys
g = {}; order = []
for l in open(sys.argv[1]) if __import__('os').path.exists(sys.argv[1]) else []:
    k = l.split(' ', 1)[0]; g.setdefault(k, []).append(l); order.append(k) if k not in order else None
new = {}
for l in open(sys.argv[2]):
    k = l.split(' ', 1)[0]; new.setdefault(k, []).append(l)
for k in new:
    if k not in order: order.append(k)
g.update(new)
open(sys.argv[1], 'w').write(''.join(''.join(g[k]) for k in order))
PY
  fi
  echo "ck-gate: UPDATED $G"; exit $fail
fi
if [ -f $G ]; then
  if [ $# -eq 0 ]; then diff $G $W/out.txt > $W/diff.txt || { echo "ck-gate: golden differs:"; head -20 $W/diff.txt; fail=1; }
  else grep -F -x -v -f $G $W/out.txt > $W/diff.txt && { echo "ck-gate: lines not in golden:"; head -20 $W/diff.txt; fail=1; }; fi
else echo "ck-gate: no golden yet ($G); run with --update"; fail=1; fi
[ $fail -eq 0 ] && echo "ck-gate: PASS" || echo "ck-gate: FAIL"
exit $fail
