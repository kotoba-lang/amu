#!/bin/zsh
# seed/amu-main/parity.sh <work-dir> [--check AMU] [--compile AMU] -- behaviour parity of the native amu entries against
# stage-0 on the corpus (agent MAINS, 2026-10-04; seed/amu-main/README.md). BOOTSTRAP-TOOL (zsh + python3). Stage-0 is
# build/native-image/amu-native, BOOTSTRAP-REFERENCE: the oracle, never in an amu image's process tree.
#
# Corpus: the 391 programs of seed/amu-front/corpus.sh (= the dirs of scripts/selfhost-wall/kir-backend-diff.sh).
#   check   both sides `check <file>`; classes as seed/amu-front/corpus.sh: SAME-OK SAME-REFUSE OK-DIFF REFUSE-DIFF
#           AMU-REFUSES AMU-ACCEPTS AMU-TRAP, plus STUB (the image answers the declared not-available, exit 69).
#   compile both sides `compile <file> --target aarch64-macos --output <x>`; stage-0's kexe comes from the shared cache
#           build/seed-kir/census/kexe/<sha256/16 of the source>.kexe (a miss is compiled under lib.sh's 2 slots, nice).
#           Verdict classes: BOTH-OK, BOTH-REFUSE, AMU-REFUSES (stage-0 ok), AMU-ACCEPTS (stage-0 refuses), STUB, AMU-TRAP.
#           BOTH-OK: every export of stage-0's KIR (scripts/selfhost-wall/kbd_exports.py list) whose parameters the loader
#           can supply runs from both codes under the C loader (fuel 16M, arity 0 once, arity > 0 per representative
#           argument vector): result by content (KEXE_RESULT_TYPE), exit status and trap line compared -> SAME / DIFF /
#           TIMEOUT (loader time limit: not a behaviour) / MISSING (exported by stage-0, absent in the amu container).
#           The program is BEHAVIOUR-SAME when every run export is SAME.
#   The report format of compile is NOT compared here (seed/amu-main/usage-parity.sh compares the argument layer byte for
#   byte). Since CMD (2026-10-04) amu writes :kotoba.kexe/v1 (column 12: its seal, kexe_check.py) and gets the same --policy.
# Env: AM_FILES (path list instead of the corpus), AM_SEED (seed.bin used for extract-native of amu's kseed; default the
#      r6f seed build/mains/seed-1.bin), AM_SECONDS (loader limit per run, default 60), AM_FUEL (16777216).
# Output: <work>/check.tsv, <work>/compile.tsv, <work>/exports.tsv, <work>/summary.txt
emulate -L zsh; setopt pipefail nullglob
H=${0:A:h}; R=${H:h:h}
W=${1:?usage: parity.sh <work-dir> [--check AMU] [--compile AMU]}; shift; mkdir -p $W/run; W=${W:A}
AC=""; AP=""
while [ $# -gt 0 ]; do case $1 in --check) AC=${2:A}; shift 2 ;; --compile) AP=${2:A}; shift 2 ;; *) echo "bad arg $1" >&2; exit 2 ;; esac; done
export SEED_BUILD=$W/sb SEED_RESOURCES_35=$R; mkdir -p $SEED_BUILD; source $R/scripts/seed/lib.sh
S0=$SEED_STAGE0
SB=${AM_SEED:-$R/build/mains/seed-1.bin}; SB=${SB:A}
L=$(seed_loader) || exit 2
FUEL=${AM_FUEL:-16777216}; SECS=${AM_SECONDS:-60}
KC=$R/build/seed-kir/census/kexe; mkdir -p $KC
pol=$W/policy.edn; echo '{:allow #{[:cap/call 35] [:cap/call 37] [:cap/call 38] [:cap/call 39]}}' > $pol
E=/Users/junkawasaki/github/kotoba-lang/amu-embench/bench/embench/ports
if [ -n "$AM_FILES" ]; then files=(${(f)"$(cat $AM_FILES)"})
else
  dirs=($E $R/seed/tests/r1/feat $R/seed/tests/r1/conf $R/seed/tests/corpus $R/resources/kotoba/lang-conformance/values
        $R/resources/kotoba/lang-conformance/control $R/resources/kotoba/lang-conformance/native $R/seed/tests/conformance/*(/)
        $R/examples $R/test/dual-backend $R/test/nbb/fixtures $R/test/nbb/fixtures/state $R/bench/runtime-comparison)
  files=(); for d in $dirs; do files+=($d/*.kotoba); done
fi
grp() { local d=$1; d=${d#$R/}; d=${d#/Users/junkawasaki/github/kotoba-lang/amu-embench/bench/}; d=${d%.kotoba}; echo ${d//\//.}; }
xoff() { sed -n 's/.*:offset \([0-9]*\).*/\1/p'; }
ulimit -s 65500 2>/dev/null
# runx <bin> <off> <prefix> <rtype> <arity> [args]: as kir-backend-diff.sh's runx (loader only, fuel on)
runx() {
  local b=$1 o=$2 p=$3 rt=$4 ar=$5; shift 5
  ( cd $D; KEXE_PAIRS=2097152 KEXE_VECTORS=65536 KEXE_VECTOR_ITEMS=1048576 KEXE_FUEL=$FUEL KEXE_CPU_SECONDS=$SECS KEXE_WALL_SECONDS=$SECS \
      KEXE_CAP_RESOURCES_35=$D nice $L $b $o $ar aarch64 $SEED_GRANT "$@" > $p.out 2> $p.err; echo "rc=$? $(grep -v '^ *$' $p.err | tail -1 | tr '\t' ' ' | cut -c1-100)" > $p.st
    if [ "$rt" = opaque ]; then mv $p.out $p.raw; : > $p.out
    elif [ "$rt" != i64 ]; then
      mv $p.out $p.raw
      KEXE_STRUCTURED_REPORT=1 KEXE_RESULT_TYPE=$rt KEXE_PAIRS=2097152 KEXE_VECTORS=65536 KEXE_VECTOR_ITEMS=1048576 KEXE_FUEL=$FUEL \
        KEXE_CPU_SECONDS=$SECS KEXE_WALL_SECONDS=$SECS KEXE_CAP_RESOURCES_35=$D nice $L $b $o $ar aarch64 $SEED_GRANT "$@" 2>/dev/null \
        | grep '^{:status' | sed -e 's/ :result -\{0,1\}[0-9][0-9]*//' -e 's/ :fuel {.*//' > $p.out
    fi )
}
line() { python3 -c '
import sys
for l in (open(sys.argv[1], errors="replace").read() + "\n" + open(sys.argv[2], errors="replace").read()).split("\n"):
    if l.startswith("ok ") or l.startswith("error: "): print(l.strip()[:400]); break' $1 $2; }

: > $W/check.tsv; : > $W/compile.tsv; : > $W/exports.tsv
for f in $files; do
  id=$(grp $f); D=$W/run/$id; rm -rf $D; mkdir -p $D
  # ---- check ----
  if [ -n "$AC" ]; then
    nice $S0 check $f > $D/s0c.out 2> $D/s0c.err; c0=$?
    $AC check $f > $D/ac.out 2> $D/ac.err; c1=$?
    python3 - $id $D $c0 $c1 >> $W/check.tsv <<'P'
import sys, re
id, D, c0, c1 = sys.argv[1:5]
rd = lambda p: open(p, errors='replace').read()
def line(o, e):
    for l in (o + '\n' + e).split('\n'):
        if l.startswith('ok ') or l.startswith('error: '): return l.strip()
    return ''
s0 = line(rd(D + '/s0c.out'), rd(D + '/s0c.err')); am = line(rd(D + '/ac.out'), rd(D + '/ac.err'))
def okparts(l):
    m = re.match(r'ok profile=(\S+) effects=#\{(.*?)\} exports=\[(.*?)\]', l)
    return None if not m else (m[1], tuple(sorted(m[2].split())), m[3].split())
def sets(t): return re.sub(r'#\{([^{}]*)\}', lambda m: '#{' + ' '.join(sorted(re.findall(r'\[[^\]]*\]|\S+', m[1]))) + '}', t)
def msg(l):
    m = re.match(r'error: \S+ at .*?: (.*)$', l) or re.match(r'error: \S+: (.*)$', l)
    return sets(m[1] if m else l)
if c1 == '69': cls = 'STUB'
elif not am: cls = 'AMU-TRAP'
elif s0.startswith('ok') and am.startswith('ok'): cls = 'SAME-OK' if okparts(s0) == okparts(am) else 'OK-DIFF'
elif s0.startswith('error') and am.startswith('error'): cls = 'SAME-REFUSE' if msg(s0) == msg(am) else 'REFUSE-DIFF'
elif s0.startswith('ok'): cls = 'AMU-REFUSES'
else: cls = 'AMU-ACCEPTS'
if cls in ('SAME-OK', 'SAME-REFUSE') and c0 != c1: cls += '-RC'
print('\t'.join([id, c0, s0.replace('\t', ' ')[:200], c1, am.replace('\t', ' ')[:200], cls]))
P
  fi
  # ---- compile ----
  if [ -n "$AP" ]; then
    h=$(shasum -a 256 $f | cut -c1-16); k=$KC/$h.kexe
    if [ ! -f $k ] && [ ! -f $k.fail ]; then
      seed_slot_take
      r=$( cd ${f:h}; nice $S0 compile $f --target aarch64-macos --jvm-free --policy $pol --output $k.tmp.$$ 2>&1 )
      seed_slot_give
      if echo "$r" | grep -q ':ok true'; then mv $k.tmp.$$ $k; else echo "$r" | head -3 > $k.fail; rm -f $k.tmp.$$*; fi
    fi
    # CMD (2026-10-04): amu writes stage-0's :kotoba.kexe/v1 (AM_KSEED=1: the older kseed/v1 images) and gets the same
    # --policy as stage-0 (was: stage-0 only, so a policy refusal counted as AMU-ACCEPTS)
    if [ -n "$AM_KSEED" ]; then ao=$D/a.kseed; ( cd ${f:h}; $AP compile $f --target aarch64-macos --output $ao ) > $D/ap.out 2> $D/ap.err; c1=$?
    else ao=$D/a.kexe; ( cd ${f:h}; $AP compile $f --target aarch64-macos --policy $pol --output $ao ) > $D/ap.out 2> $D/ap.err; c1=$?; fi
    s0v=ok; [ -f $k ] || s0v=refuse
    if [ $c1 = 69 ]; then cls=STUB; elif [ $c1 = 0 ] && grep -q ':ok true' $D/ap.out && [ -s $ao ]; then a=ok; else a=refuse; fi
    sealv=-; if [ -z "$AM_KSEED" ] && [ -s $ao ]; then sealv=$(python3 $H/kexe_check.py seal $ao | cut -d' ' -f2); fi
    if [ $c1 != 69 ]; then
      if [ $c1 != 0 ] && [ $c1 != 65 ] && [ $c1 != 64 ]; then cls=AMU-TRAP
      elif [ $s0v = ok ] && [ $a = ok ]; then cls=BOTH-OK
      elif [ $s0v = refuse ] && [ $a = refuse ]; then cls=BOTH-REFUSE
      elif [ $s0v = ok ]; then cls=AMU-REFUSES; else cls=AMU-ACCEPTS; fi
    fi
    nx=0 ns=0 nd=0 nt=0 nm=0 nn=0
    if [ $cls = BOTH-OK ]; then
      python3 $R/scripts/seed/kir_extract.py $k $D/p.kir > /dev/null 2>&1
      local -a ex exl av; ex=("${(@f)$(python3 $R/scripts/selfhost-wall/kbd_exports.py list $D/p.kir 2>/dev/null)}")
      for ln in $ex; do
        [ -n "$ln" ] || continue
        exl=("${(@ps:\t:)ln}"); s=$exl[1] ar=$exl[2] as=$exl[6] rt=$exl[7]
        [[ $exl[5] = user ]] || continue
        o0=$(python3 $R/scripts/selfhost-wall/kbd_exports.py s0code $k $s $D/0.bin | xoff)
        if [ -n "$AM_KSEED" ]; then o1=$(SEED_RESOURCES_35=$W SEED_VECTOR_ITEMS=67108864 seed_run $SB 0 extract-native $ao --symbol $s --output $D/1.bin 2>/dev/null | xoff)
        else o1=$(python3 $H/kexe_check.py code $ao $s $D/1.bin 2>/dev/null | xoff); fi
        if [ -n "$o0" ] && [ -z "$o1" ]; then nm=$((nm+1)); print -r -- "$id	$s	MISSING" >> $W/exports.tsv; continue; fi
        [ -n "$o0" ] || continue
        if [ "$as" = - ]; then nn=$((nn+1)); print -r -- "$id	$s	NOT-RUN" >> $W/exports.tsv; continue; fi
        [ "$as" = . ] && av=("") || av=("${(@s:;:)as}")
        for ai in {1..$#av}; do
          nx=$((nx+1)); runx $D/0.bin $o0 $D/0.$s.$ai $rt $ar ${(s:|:)av[ai]}; runx $D/1.bin $o1 $D/1.$s.$ai $rt $ar ${(s:|:)av[ai]}
          st0=$(cat $D/0.$s.$ai.st); st1=$(cat $D/1.$s.$ai.st)
          if [[ "$st0 $st1" == *SIGALRM* || "$st0 $st1" == *SIGXCPU* ]]; then v=TIMEOUT; nt=$((nt+1))
          elif cmp -s $D/0.$s.$ai.out $D/1.$s.$ai.out && [ "${st0%% *}" = "${st1%% *}" ]; then v=SAME; ns=$((ns+1))
          else v=DIFF; nd=$((nd+1)); fi
          print -r -- "$id	$s.$ai	$v	$st0	$st1" >> $W/exports.tsv
        done
        rm -f $D/0.bin $D/1.bin
      done
      if [ $nd -gt 0 ] || [ $nm -gt 0 ]; then cls=BOTH-OK-DIFF; elif [ $nx -gt 0 ]; then cls=BEHAVIOUR-SAME; else cls=BOTH-OK-NORUN; fi
    fi
    am=$(grep -v '^ *$' $D/ap.err | head -1 | tr '\t' ' ' | cut -c1-160)
    print -r -- "$id	$s0v	$c1	$cls	$nx	$ns	$nd	$nt	$nm	$nn	$am	$sealv" >> $W/compile.tsv
  fi
  print -r -- "$id $([ -n "$AC" ] && tail -1 $W/check.tsv | cut -f6) $([ -n "$AP" ] && tail -1 $W/compile.tsv | cut -f4)"
done
{ echo "parity $(date '+%F %T') load $(sysctl -n vm.loadavg | awk '{print $2}') stage-0 $(shasum -a 256 $S0 | cut -c1-16) (BOOTSTRAP-REFERENCE)"
  [ -n "$AC" ] && { echo "check: $AC $(shasum -a 256 $AC | cut -c1-16) files $(wc -l < $W/check.tsv | tr -d ' ')"; cut -f6 $W/check.tsv | sort | uniq -c; }
  [ -n "$AP" ] && { echo "compile: $AP $(shasum -a 256 $AP | cut -c1-16) files $(wc -l < $W/compile.tsv | tr -d ' ')"; cut -f4 $W/compile.tsv | sort | uniq -c
    echo "kexe/v1 seals (column 12): $(cut -f12 $W/compile.tsv | sort | uniq -c | tr -s ' ' | tr '\n' ' ')"
    echo "export runs: $(awk -F'\t' '{s+=$5} END {print s}' $W/compile.tsv) (SAME $(awk -F'\t' '{s+=$6} END {print s}' $W/compile.tsv), DIFF $(awk -F'\t' '{s+=$7} END {print s}' $W/compile.tsv), TIMEOUT $(awk -F'\t' '{s+=$8} END {print s}' $W/compile.tsv), MISSING $(awk -F'\t' '{s+=$9} END {print s}' $W/compile.tsv), NOT-RUN $(awk -F'\t' '{s+=$10} END {print s}' $W/compile.tsv))"; }
} > $W/summary.txt
cat $W/summary.txt
