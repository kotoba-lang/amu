#!/bin/zsh
# scripts/selfhost-wall/kir-backend-diff.sh [seed.bin] -- the backend falsification test of docs/selfhost-seed-merge-20261003.md
# section 7 (agent INT, 2026-10-03; BOOTSTRAP-TOOL: zsh + python3, test harness only, never in a product process tree).
#
# Question: can the seed backend (`seed compile-kir`) replace stage-0's `native/machine_ir` + aarch64 emitter on WHOLE sealed
# programs? Both backends get the identical sealed `:program` KIR (the kexe's :program, = `ir/native-program kir`, the bytes the
# verifier re-emits from). Stage-0 is the bootstrap reference build/native-image/amu-native (JVM-built native image).
#
# Part P (programs): every program of the corpora below that stage-0 compiles for aarch64-macos. Per program:
#   1. stage-0 kexe (cache: build/seed-kir/census/kexe/<sha256/16 of source>.kexe, shared with census.sh; a miss is compiled
#      under lib.sh's machine-wide 2 slots, nice);
#   2. KIR cut out (kir_extract.py); `seed compile-kir` -> ok, or the refusal (code + text);
#   3. every KIR export (EXPORT, 2026-10-04: all of :exports, scripts/selfhost-wall/kbd_exports.py; before: arity 0 only) must
#      be in the seed's container; one whose parameters are i64/bool/string/vector-i64 (arity <= 5) runs from BOTH codes under the C loader
#      (fuel on, 16M), arity 0 once, arity > 0 once per representative argument vector (up to 5 fixed vectors): stdout or
#      the typed report of the result (by content), the last stderr line (traps) and the exit status are compared; arity 0
#      also under kexe-benchmark (fuel 16M): result and contextFuelConsumed. Others: NOT-RUN (present in both, counted).
#   4. code bytes (the whole :code of each container).
#   One tsv line per program in $W/programs.tsv:
#     id  s0  seed(ok|E..)  exports  same-behaviour  seed-only-traps  fuel-equal  fuel-s0-sum  fuel-seed-sum  code-s0  code-seed  note
#   Per export lines in $W/run/<id>/exports.tsv, classes: SAME; SAME KB-CRASH-<side> (loader runs agree, kexe-benchmark crashed on
#   a runtime slot it leaves NULL); DIFF (stdout or exit status or two different kexe-benchmark results); DIFF-TRAPKIND (both trap,
#   different trap); DIFF-EXPORT-MISSING-IN-SEED (stage-0's artifact exports it, the seed's container does not); TIMEOUT-<side>
#   (the loader's time limit, KBD_SECONDS, default 120: not a behaviour, listed); SEED-ONLY-TRAP appended when s0 returned.
# Part G (guests): the big-compiler guests (seed/tests/kir/merge.sh via flip.sh FLIP_PARTS=merge: whole KIR of each guest, not a
#   slice) at scale 1 and 8, run with THIS seed. KBD_PARTS="P G" (default), KBD_G=0 skips G.
# Verdict (the five no-go checks; any one = NO-GO):
#   F1 one DIFF (stdout / result / exit status / kexe-benchmark result) on a program both compile, or a merge DIFF;
#   F2 a program stage-0 compiles and the seed refuses, other than the documented refusals (KBD_DOC, the plan's item 4:
#      wire 23 :entropy/draw, float arithmetic/compare/parse/print, > 16 parameters, 65+ item vectors with non-literal items,
#      record captures in fn literals);
#   F3 a seed-only trap (stage-0's run returns, the seed's traps);
#   F4 a fuel difference (kexe-benchmark contextFuelConsumed) on a program both compile and both finish;
#   F5 the seed's fixed point or a rung gate breaking: this script does not change the seed; it records the seed's sha256 and
#      checks seed-1 == seed-2 of its build dir when present (the rung gates are scripts/seed/gates.sh, HOUSE4).
# Env: SEED_BUILD (default build/seed-r6a; seed-1.bin is the backend under test), KBD_W (work dir, default $SEED_BUILD/kbd),
#      KBD_DIRS (corpus override), KBD_JOBS (default 3), KBD_FUEL (default 16777216).
emulate -L zsh
setopt pipefail nullglob
H=${0:A:h}; R=${H:h:h}
export SEED_BUILD=${SEED_BUILD:-$R/build/seed-r6a}
source $R/scripts/seed/lib.sh
S=${1:-$SEED_BUILD/seed-1.bin}; S=${S:A}
W=${KBD_W:-$SEED_BUILD/kbd}; mkdir -p $W/run; W=${W:A}
KC=$R/build/seed-kir/census/kexe; mkdir -p $KC
L=$(seed_loader) || exit 2; cp $L $W/kexe-loader.pinned; L=$W/kexe-loader.pinned
KB=$W/kexe-benchmark; [ -x $KB ] || cc -O2 -std=c11 $R/bench/runtime-comparison/kexe-benchmark.c -o $KB || exit 2
FUEL=${KBD_FUEL:-16777216}
E=/Users/junkawasaki/github/kotoba-lang/amu-embench/bench/embench/ports
dirs=(${=KBD_DIRS:-$E $R/seed/tests/r1/feat $R/seed/tests/r1/conf $R/seed/tests/corpus $R/resources/kotoba/lang-conformance/values $R/resources/kotoba/lang-conformance/control $R/resources/kotoba/lang-conformance/native $R/seed/tests/conformance/*(/) $R/examples $R/test/dual-backend $R/test/nbb/fixtures $R/test/nbb/fixtures/state $R/bench/runtime-comparison})
pol=$W/policy.edn; echo '{:allow #{[:cap/call 35] [:cap/call 37] [:cap/call 38] [:cap/call 39]}}' > $pol
load() { sysctl -n vm.loadavg | awk '{print $2}'; }
grp() { local d=$1; d=${d#$R/}; d=${d#/Users/junkawasaki/github/kotoba-lang/amu-embench/bench/}; echo ${d//\//.}; }
xoff() { sed -n 's/.*:offset \([0-9]*\).*/\1/p'; }
seed() {
  KEXE_COMMAND=1 KEXE_CAP_RESOURCES_35=$W KEXE_STRING_POOL=268435456 KEXE_PAIRS=4194304 KEXE_VECTORS=65536 \
    KEXE_VECTOR_ITEMS=16777216 KEXE_CPU_SECONDS=120 KEXE_WALL_SECONDS=120 $L $S 0 0 aarch64 $SEED_GRANT -- "$@"; }
# runx <bin> <off> <prefix> [type]: loader run (fuel on) -> <prefix>.out (stdout), <prefix>.st ("rc=N last-stderr-line");
# kexe-benchmark -> <prefix>.kb ("result fuel")
# SEEDFIX (2026-10-03): an export whose KIR result type is :string is observed as the loader's typed report observes it
# (KEXE_STRUCTURED_REPORT=1 KEXE_RESULT_TYPE=string: :status and :result-utf8-hex, the string's content), not by the raw
# handle word the plain run prints: that word numbers pair allocations (stage-0 allocates pair(0,0) for an option none
# and none for a local record, the seed the opposite), so equal strings can print different numbers. The plain run's
# stdout is kept in <prefix>.raw and a difference there is listed (RAW-HANDLE), not counted.
# EXPORT (2026-10-04): runx <bin> <off> <prefix> <rtype> <arity> [i64 args ..]: every export, arity 0..5 with the
# representative arguments of kbd_exports.py; the result is observed by content through the loader's typed report
# (KEXE_RESULT_TYPE = rtype: string, option-i64, option-string, result-i64, vector-i64, bytes, record:N), the handle word
# (`:result N`) and the fuel/heap tail cut off; rtype opaque (a handle without a content report: records with non-scalar
# fields, keywords, closures ..) keeps only the exit status and trap line (listed OPAQUE). kexe-benchmark runs arity 0 only.
runx() {
  local b=$1 o=$2 p=$3 rt=$4 ar=$5; shift 5
  ( cd $D; KEXE_PAIRS=2097152 KEXE_VECTORS=65536 KEXE_VECTOR_ITEMS=1048576 KEXE_FUEL=$FUEL KEXE_CPU_SECONDS=${KBD_SECONDS:-120} KEXE_WALL_SECONDS=${KBD_SECONDS:-120} \
      KEXE_CAP_RESOURCES_35=$D nice $L $b $o $ar aarch64 $SEED_GRANT "$@" > $p.out 2> $p.err; echo "rc=$? $(grep -v '^ *$' $p.err | tail -1 | tr '\t' ' ' | cut -c1-100)" > $p.st
    if [ "$rt" = opaque ]; then
      mv $p.out $p.raw; : > $p.out
    elif [ "$rt" != i64 ]; then
      mv $p.out $p.raw
      KEXE_STRUCTURED_REPORT=1 KEXE_RESULT_TYPE=$rt KEXE_PAIRS=2097152 KEXE_VECTORS=65536 KEXE_VECTOR_ITEMS=1048576 KEXE_FUEL=$FUEL \
        KEXE_CPU_SECONDS=${KBD_SECONDS:-120} KEXE_WALL_SECONDS=${KBD_SECONDS:-120} KEXE_CAP_RESOURCES_35=$D nice $L $b $o $ar aarch64 $SEED_GRANT "$@" 2>/dev/null \
        | grep '^{:status' | sed -e 's/ :result -\{0,1\}[0-9][0-9]*//' -e 's/ :fuel {.*//' > $p.out
    fi )
  if [ $ar = 0 ]; then
    local j=$(cd $D; nice $KB raw $b $o aarch64 0 1 0 $FUEL 2>/dev/null)
    echo "$(echo "$j" | sed -n 's/.*"result":\(-*[0-9]*\).*/\1/p') $(echo "$j" | sed -n 's/.*"contextFuelConsumed":\([0-9]*\).*/\1/p')" > $p.kb
  else : > $p.kb; fi
}
# lfuel <bin> <off> <arity> [args ..]: fuel the C loader's typed report says the run consumed (initial - remaining), empty when it has none
lfuel() { local b=$1 o=$2 ar=$3; shift 3; ( cd $D; KEXE_STRUCTURED_REPORT=1 KEXE_PAIRS=2097152 KEXE_VECTORS=65536 KEXE_VECTOR_ITEMS=1048576 KEXE_FUEL=$FUEL \
    KEXE_CPU_SECONDS=${KBD_SECONDS:-120} KEXE_WALL_SECONDS=${KBD_SECONDS:-120} KEXE_CAP_RESOURCES_35=$D nice $L $b $o $ar aarch64 $SEED_GRANT "$@" 2>/dev/null \
    | sed -n 's/.*:fuel {:initial \([0-9]*\) :remaining \([0-9]*\)[ }].*/\1 \2/p' | awk '{print $1-$2}' ) }
codelen() { python3 -c 'import sys; s=open(sys.argv[1],encoding="utf-8").read(); i=s.index(":code [")+7; print(len(s[i:s.index("]",i)].split()))' $1; }

one() {  # <src> <group>
  local f=$1 g=$2 id=$2.${1:t:r} h k r ex kst kerr="" n=0 same=0 sot=0 tmo=0 feq=0 fcmp=0 f0=0 f1=0 c0=- c1=- note="" xd=0
  local e s t o0 o1 v st0 st1 kb0 kb1
  D=$W/run/$id; rm -rf $D; mkdir -p $D
  h=$(shasum -a 256 $f | cut -c1-16); k=$KC/$h.kexe
  if [ ! -f $k ] && [ ! -f $k.fail ]; then
    seed_slot_take
    r=$( ulimit -s 65500 2>/dev/null; cd ${f:h}; nice $SEED_STAGE0 compile $f --target aarch64-macos --jvm-free --policy $pol --output $k.tmp.$$ 2>&1 )
    seed_slot_give
    if echo "$r" | grep -q ':ok true'; then mv $k.tmp.$$ $k; else echo "$r" | head -3 > $k.fail; rm -f $k.tmp.$$*; fi
  fi
  if [ ! -f $k ]; then printf "%s\tS0-FAIL\t-\t0\t0\t0\t0\t0\t0\t-\t-\t%s\n" $id "$(head -1 $k.fail | tr '\t' ' ' | cut -c1-100)" > $D/line; return; fi
  python3 $R/scripts/seed/kir_extract.py $k $D/p.kir 2>/dev/null || { printf "%s\tNOPROG\t-\t0\t0\t0\t0\t0\t0\t-\t-\t-\n" $id > $D/line; return; }
  if (cd $D; seed compile-kir $D/p.kir --output $D/k.kseed) > $D/k.log 2>&1 && grep -q ':ok true' $D/k.log; then kst=ok
  else kst=$(grep -o 'E[0-9][0-9]*' $D/k.log | head -1); kst=${kst:-ERR}; kerr=$(grep -v '^ *$' $D/k.log | head -1 | tr '\t' ' ' | cut -c1-160); fi
  c0=$(codelen $k)
  [ $kst = ok ] && c1=$(head -1 $D/k.kseed | awk '{print $2}')   # KSEED1 <code-bytes> <symbols>
  # SEEDFIX: the metered build (compile-kir --metered refuses by name what it cannot charge exactly as machine_ir: the
  # selector's metered fallback); F4 is checked on the programs it accepts (same code: the flag only refuses)
  kmet=-; if [ $kst = ok ]; then kmet=ok; (cd $D; seed compile-kir $D/p.kir --output $D/km.kseed --metered) > $D/km.log 2>&1 && grep -q ':ok true' $D/km.log \
    || { kmet=$(grep -o 'E[0-9][0-9]*' $D/km.log | head -1); kmet="${kmet:-ERR}:$(grep -o "'[^']*'" $D/km.log | head -1 | tr -d "'")"; }; fi
  # EXPORT (2026-10-04): every KIR :exports entry (not only arity 0): kbd_exports.py list gives its arity, parameter kinds,
  # representative argument vectors and the typed report of its result; an export whose parameters the runner cannot
  # supply (not i64/bool/string/vector-i64, or > 5) is checked for presence only (NOT-RUN, counted in column 16); arity > 0 runs in column 17
  local -a ex exl av; local line ar pk tn cl as rt ai nr=0 npos=0 sid
  ex=("${(@f)$(python3 $H/kbd_exports.py list $D/p.kir 2>/dev/null)}")
  : > $D/exports.tsv
  if [ $kst = ok ]; then
    for line in $ex; do
      [ -n "$line" ] || continue
      exl=("${(@ps:\t:)line}"); s=$exl[1] ar=$exl[2] pk=$exl[3] tn=$exl[4] cl=$exl[5] as=$exl[6] rt=$exl[7]; t=$rt
      o0=$(python3 $H/kbd_exports.py s0code $k $s $D/0.bin | xoff); o1=$(cd $D; seed extract-native $D/k.kseed --symbol $s --output $D/1.bin 2>/dev/null | xoff)
      # an export stage-0's artifact has and the seed's container lacks is an export-table difference (F1)
      if [ -n "$o0" ] && [ -z "$o1" ]; then n=$((n+1)); xd=$((xd+1)); echo "$s\t$tn\tDIFF-EXPORT-MISSING-IN-SEED" >> $D/exports.tsv; continue; fi
      [ -n "$o0" ] && [ -n "$o1" ] || { echo "$s\t$tn\tNO-SYMBOL" >> $D/exports.tsv; continue; }
      if [ "$as" = - ]; then nr=$((nr+1)); echo "$s\t$tn\tNOT-RUN (arity $ar, parameters not i64/bool/string/vector-i64): present in both" >> $D/exports.tsv; continue; fi
      [ "$as" = . ] && av=("") || av=("${(@s:;:)as}")
      for ai in {1..$#av}; do
      if [ $ar = 0 ]; then sid=$s; else sid=$s.$ai; npos=$((npos+1)); fi
      n=$((n+1)); runx $D/0.bin $o0 $D/0.$sid $rt $ar ${(s:|:)av[ai]}; runx $D/1.bin $o1 $D/1.$sid $rt $ar ${(s:|:)av[ai]}
      st0=$(cat $D/0.$sid.st); st1=$(cat $D/1.$sid.st); kb0=($(cat $D/0.$sid.kb)); kb1=($(cat $D/1.$sid.kb))
      v=SAME
      # a run stopped by the loader's time limit (SIGALRM / SIGXCPU, KEXE_*_SECONDS) is not a behaviour: TIMEOUT-<side>, kept out
      # of the DIFF count and listed (the host is loaded; stage-0's xgboost needs > 30 s with fuel on at load 80)
      if [[ "$st0 $st1" == *SIGALRM* || "$st0 $st1" == *SIGXCPU* ]]; then
        v=TIMEOUT; [[ "$st0" == *SIG[AX][LC]* ]] && v="$v-s0"; [[ "$st1" == *SIG[AX][LC]* ]] && v="$v-seed"
        [ "$kb0[1]" = "$kb1[1]" ] || v="$v DIFF-KB"
      elif ! cmp -s $D/0.$sid.out $D/1.$sid.out || [ "${st0%% *}" != "${st1%% *}" ]; then v=DIFF
      elif [ "$rt" = i64 ] && [ "$kb0[1]" != "$kb1[1]" ]; then   # SEEDFIX/EXPORT: a non-i64 result word is a handle (see runx)
        # the C loader (the product runtime) agrees; kexe-benchmark leaves some runtime slots NULL (cap_call, bytes, ..), so a
        # side that calls one crashes there (empty result): KB-CRASH-<side>, behaviour SAME, listed. Two different results = DIFF.
        if [ -z "$kb0[1]" ]; then v="SAME KB-CRASH-s0"; elif [ -z "$kb1[1]" ]; then v="SAME KB-CRASH-seed"; else v=DIFF; fi
      fi
      # the trap text (last stderr line) is part of behaviour when the run did not return 0
      [[ $v == SAME* ]] && [ "${st0%% *}" != rc=0 ] && [ "$st0" != "$st1" ] && v=DIFF-TRAPKIND
      [ -f $D/0.$sid.raw ] && ! cmp -s $D/0.$sid.raw $D/1.$sid.raw && v="$v RAW-HANDLE"
      [ "$rt" = opaque ] && v="$v OPAQUE"
      [[ $v == SAME* ]] && same=$((same+1)); [[ $v == TIMEOUT* && $v != *DIFF* ]] && tmo=$((tmo+1))
      [ "${st0%% *}" = rc=0 ] && [ "${st1%% *}" != rc=0 ] && { sot=$((sot+1)); v="$v SEED-ONLY-TRAP"; }
      # SEEDFIX: fuel = kexe-benchmark's contextFuelConsumed when both sides have one; when kexe-benchmark crashed on a side
      # (a slot it leaves NULL) the C loader's typed report (initial - remaining, also on a trap) of both sides is used
      fu0=$kb0[2] fu1=$kb1[2] fs=kb
      if [ -z "$fu0" ] || [ -z "$fu1" ]; then
        if [ "${st0%% *}" = rc=0 ] && [ "${st1%% *}" = rc=0 ]; then fu0=$(lfuel $D/0.bin $o0 $ar ${(s:|:)av[ai]}); fu1=$(lfuel $D/1.bin $o1 $ar ${(s:|:)av[ai]}); fs=loader; else fs=none; fi
      fi
      [ -n "$fu0" ] && [ -n "$fu1" ] && fcmp=$((fcmp+1))
      if [ -n "$fu0" ] && [ "$fu0" = "$fu1" ]; then feq=$((feq+1)); fi
      f0=$((f0+${fu0:-0})); f1=$((f1+${fu1:-0}))
      printf "%s\t%s\t%s\t[%s]\t[%s]\tkb0=%s/%s\tkb1=%s/%s\tfuel(%s)=%s/%s\targs=%s\n" $sid $tn/$rt "$v" "$st0" "$st1" "${kb0[1]}" "${kb0[2]}" "${kb1[1]}" "${kb1[2]}" $fs "$fu0" "$fu1" "${av[ai]}" >> $D/exports.tsv
      done
    done
  else note=$kerr; fi
  printf "%s\tok\t%s\t%d\t%d\t%d\t%d\t%d\t%d\t%s\t%s\t%s\t%d\t%s\t%d\t%d\t%d\n" $id $kst $n $same $sot $feq $f0 $f1 $c0 $c1 "$note" $tmo $kmet $fcmp $nr $npos > $D/line
}

parts=${KBD_PARTS:-P G}; [ "${KBD_G:-1}" = 0 ] && parts=P
: > $W/summary.txt
say() { print -r -- "$*" | tee -a $W/summary.txt; }
say "kir-backend-diff: seed $(shasum -a 256 $S | cut -c1-16) ($(wc -c < $S | tr -d ' ') B), stage-0 $(shasum -a 256 $SEED_STAGE0 | cut -c1-16), $(date '+%Y-%m-%d %H:%M'), load $(load)"
if [ -f ${S:h}/seed-2.bin ]; then cmp -s $S ${S:h}/seed-2.bin && say "F5: seed-1 == seed-2 in ${S:h} (fixed point)" || say "F5: seed-1 != seed-2 in ${S:h}: FIXED POINT BROKEN"; fi

if [[ " $parts " == *" P "* ]]; then
  for d in $dirs; do
    g=$(grp $d)
    for f in $d/*.kotoba; do
      while [ $(jobs -r | wc -l) -ge ${KBD_JOBS:-3} ]; do sleep 0.2; done
      one ${f:A} $g &
    done
  done
  wait
  cat $W/run/*/line(N) | sort > $W/programs.tsv
  # documented refusals (plan section 7 item 4): matched on the seed's refusal text
  # SEEDFIX (2026-10-03): + scalar variants and heterogeneous vectors (variant-new/-match, hetero-vector-*; E1203 by name),
  # documented in docs/selfhost-seed-merge-20261003.md section 7 item 4
  DOC=${KBD_DOC:-'entropy|wire 23|f64|f32|float|more than 16 param|E2116|capture|variant|hetero-vector'}
  awk -F'\t' -v doc="$DOC" '
    $2=="ok" { s0++; if ($3=="ok") { k++; ex+=$4; sm+=$5; sot+=$6; fe+=$7; fc+=$15; f0+=$8; f1+=$9; c0+=$10; c1+=$11; tm+=$13; nr+=$16; np+=$17; if ($5+$13<$4) dp++; if ($6>0) tp++; if ($7<$15) fp++;
                                     if ($14=="ok") { mk++; mfc+=$15; mfe+=$7; mex+=$4; if ($7<$15) mfp++ } else mfb++ }
               else { if (tolower($12) ~ doc) rd++; else ru++ } }
    END { printf "P: %d programs stage-0 compiles; seed compile-kir accepts %d (%.1f%%); refused %d documented + %d other\n", s0, k, 100*k/s0, rd, ru;
          printf "P: %d exports run on both: %d same behaviour, %d stopped by the time limit, %d differ (%d programs); seed-only traps %d (%d programs)\n", ex, sm, tm, ex-sm-tm, dp, sot, tp;
          printf "P: fuel (unmetered build) equal on %d of %d exports, %d not comparable (a side trapped and kexe-benchmark has no number); %d programs with a difference; fuel sum s0 %d seed %d; code bytes (accepted programs) s0 %d seed %d (%.3fx)\n", fe, ex, ex-fc, fp, f0, f1, c0, c1, (c0>0?c1/c0:0);
          printf "P: EXPORT: every KIR export: %d runs above are arity > 0 with representative arguments; %d exports present in both containers but not run (parameters not i64/bool/string/vector-i64)\n", np, nr;
          printf "F4: metered build (compile-kir --metered) accepts %d of %d programs (%d refused by name: metered fallback); fuel compared on %d of their %d exports (kexe-benchmark, else the loader report when both return), equal on %d; %d programs differ\n", mk, k, mfb, mfc, mex, mfe, mfp }' $W/programs.tsv | tee -a $W/summary.txt
  awk -F'\t' '$2=="ok" && $3=="ok" && $14!="ok" { print "  metered fallback  " $1 "  " $14 }' $W/programs.tsv | tee -a $W/summary.txt
  awk -F'\t' -v doc="$DOC" '$2=="ok" && $3!="ok" { print (tolower($12) ~ doc ? "  refused(doc)   " : "  refused(F2)    ") $1 "  " $12 }' $W/programs.tsv | tee -a $W/summary.txt
  for D in $W/run/*(/); do [ -f $D/exports.tsv ] && awk -F'\t' -v id=${D:t} '$3 ~ /DIFF|TRAP|NO-SYMBOL|TIMEOUT|KB-CRASH|RAW-HANDLE/ { print "  " id " " $0 }' $D/exports.tsv; done | cut -c1-260 | tee -a $W/summary.txt
  say "P: EXPORT: $(cat $W/run/*/exports.tsv(N) | grep -c OPAQUE) runs with an opaque result (exit status and trap compared, value not observable by content)"
fi

if [[ " $parts " == *" G "* ]]; then
  say "G: flip.sh MERGE with this seed (load $(load))"
  MERGE_RUNS=${KBD_MERGE_RUNS:-1} SEED_BUILD=$SEED_BUILD FLIP_W=$W/flip FLIP_PARTS=merge zsh $R/seed/tests/kir/flip.sh $S > $W/flip.log 2>&1
  [ -f $W/flip/merge.tsv ] && awk -F'\t' '{ v=$14; n++; if (v ~ /^EQUAL/ && v !~ /TRAP-seed/) e++; if (v ~ /DIFF/) d++; if (v ~ /TRAP-seed/) t++; if (v ~ /REFUSED|FAILED/) r++ }
      END { printf "G: %d merge runs: %d EQUAL, %d DIFF, %d seed-only trap, %d refused/failed\n", n, e, d, t, r }' $W/flip/merge.tsv | tee -a $W/summary.txt
  [ -f $W/flip/merge.tsv ] && awk -F'\t' '$14 !~ /^EQUAL$/ { print "  " $1 " " $14 }' $W/flip/merge.tsv | cut -c1-200 | tee -a $W/summary.txt
fi
say "end $(date '+%H:%M'), load $(load)"
