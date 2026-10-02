#!/bin/zsh
# scripts/seed/gr.sh <rung> [--stage0] [seed.bin [offset]] -- gate GR: the rung conformance programs seed/tests/<rung>/
# (R1: feat/ 49 feature programs, conf/ 8 typed adaptations of lang/conformance control/ records/ values/ programs,
# neg/ 40 negatives). BOOTSTRAP-TOOL (zsh), owner GATES.
#   positives (feat/ conf/): the seed compiles each program, the C loader runs its first export (arity 0); the result
#     must equal the STAGE-0 oracle <rung>.oracle (a value, or `trap` = loader exit status != 0). Where stage-0 refuses
#     (doseq on native code) the expectation is the hand-derived line of <rung>.spec, reported separately as `spec`.
#     A positive refused by the seed front end FAILS (the rung must accept it).
#   negatives (neg/): `seed check` and `seed compile` must refuse with one line "seed: E<code> ..." (same line for both,
#     no output file). `hard` negatives (stage-0 refuses too) and `subset` negatives (stage-0 accepts, the seed's subset
#     is narrower) both must be refused; a subset negative may be accepted only when listed in <rung>.accept (one label
#     per line), a deliberate decision of the rung owner recorded in git.
#     <rung>.optional lists positives whose acceptance is the rung owner's open decision (a front-end refusal is then
#     reported as `optional refused`, not a failure; once accepted they must be equal like all others).
#   --stage0: harness self-test: the compiler is stage-0 itself (bootstrap-reference): positives must equal the oracle
#     by construction, negatives must give the oracle's verdict (ACCEPTED ones compile). Proves the harness and the oracle.
# Exit 0 iff everything holds. The exact refusal TEXTS of the negatives are the golden of g3.sh --rung <rung>.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
rung=${1:?usage: gr.sh <rung> [--stage0] [seed.bin [offset]]}; shift
s0=0; [ "$1" = "--stage0" ] && { s0=1; shift; }
R=$SEED_REPO; D=$R/seed/tests/$rung; W=$SEED_BUILD/gr-$rung$([ $s0 = 1 ] && echo -s0); mkdir -p $W
[ -f $D/$rung.oracle ] || { echo "GR: no oracle $D/$rung.oracle (scripts/seed/oracle.sh $rung)" >&2; exit 2; }
if [ $s0 = 0 ]; then
  bin=${1:-$SEED_BUILD/seed-1.bin}; off=${2:-$(cat ${bin%.bin}.offset)}
  [ -s $bin ] || { echo "GR: no compiler $bin" >&2; exit 2; }
fi
L=$(seed_loader) || exit 2
export SEED_RESOURCES_35=$R:$W
echo '{:allow #{}}' > $W/pol.edn
opt=""; [ -f $D/$rung.optional ] && opt=$(grep -v '^[;#]' $D/$rung.optional)
pos_opt=0; pos_ok=0; pos_spec=0; pos_bad=0; pos_front=0; neg_ok=0; neg_bad=0; neg_acc=0; n=0
compile() {   # compile <src> <stem> -> rc; writes $W/<stem>.kseed (seed) or .kexe (stage-0); stderr first line in $W/cc.err
  local src=$1 stem=$2
  rm -f $W/$stem.kseed $W/$stem.kexe
  if [ $s0 = 1 ]; then
    seed_slot_take; ( ulimit -s 65500; nice $SEED_STAGE0 compile $src --target aarch64-macos --jvm-free --policy $W/pol.edn --output $W/$stem.kexe > $W/cc.out 2>&1 ); local rc=$?
    seed_slot_give; grep -q ':ok true' $W/cc.out && return 0
    head -c 300 $W/cc.out | tr '\n' ' ' > $W/cc.err; return 1
  else
    seed_run $bin $off compile $src $W/$stem.kseed > $W/cc.out 2> $W/cc.err; return $?
  fi
}
extract_run() {   # extract_run <stem> <sym> -> prints value|trap
  local stem=$1 sym=$2 o x v rc
  if [ $s0 = 1 ]; then
    seed_slot_take; x=$( nice $SEED_STAGE0 extract-native $W/$stem.kexe --symbol $sym --output $W/$stem.bin 2>&1 ); seed_slot_give
    o=$(echo "$x" | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  else
    x=$(zsh $R/scripts/seed/seed-cc.sh extract $W/$stem.kseed $sym $W/$stem.bin) || { echo "extract-fail"; return; }
    o=$(echo "$x" | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  fi
  v=$(cd $W; KEXE_CPU_SECONDS=20 KEXE_WALL_SECONDS=20 $L $W/$stem.bin $o 0 aarch64 - 2>$W/run.err | tail -1); rc=${pipestatus[1]}
  if [ $rc -eq 0 ] && [ -n "$v" ]; then echo $v; else echo trap; fi
}
# ---- positives
while IFS=$'\t' read -r lab want msg; do
  [ -n "$lab" ] || continue; n=$((n+1)); f=$D/$lab.kotoba; stem=${lab//\//-}
  src=spec; if [ "$want" = refused ]; then
    want=$(grep "^$lab " $D/$rung.spec | cut -d' ' -f2)
    [ -n "$want" ] || { echo "GR: no expectation for $lab (stage-0 refused, no spec line)"; pos_bad=$((pos_bad+1)); continue; }
    [ $s0 = 1 ] && { pos_spec=$((pos_spec+1)); continue; }   # stage-0 refuses it by definition
  else src=stage-0; fi
  if ! compile $f $stem; then
    if [[ $'\n'$opt$'\n' == *$'\n'$lab$'\n'* ]]; then pos_opt=$((pos_opt+1)); echo "OPTIONAL $lab: refused: $(head -1 $W/cc.err | cut -c1-90)"; continue; fi
    pos_front=$((pos_front+1)); echo "FRONT $lab: refused: $(head -1 $W/cc.err | cut -c1-110)"; continue; fi
  sym=$(sed -n 's/.*(:export \[\([^] ]*\).*/\1/p' $f | head -1)
  got=$(extract_run $stem $sym)
  if [ "$got" = "$want" ]; then if [ $src = spec ]; then pos_spec=$((pos_spec+1)); else pos_ok=$((pos_ok+1)); fi
  else pos_bad=$((pos_bad+1)); echo "BAD   $lab: $src=$want got=$got"; fi
done < $D/$rung.oracle
# ---- negatives
accept_ok=""; [ -f $D/$rung.accept ] && accept_ok=$(grep -v '^[;#]' $D/$rung.accept)
while IFS=$'\t' read -r lab verdict msg; do
  [ -n "$lab" ] || continue; n=$((n+1)); f=$D/$lab.kotoba; stem=${lab//\//-}
  if [ $s0 = 1 ]; then
    if compile $f $stem; then got=ACCEPTED; else got=refused; fi
    if [ "$got" = "$verdict" ]; then neg_ok=$((neg_ok+1)); else neg_bad=$((neg_bad+1)); echo "BADNEG $lab: stage-0 now $got, oracle $verdict"; fi
    continue
  fi
  seed_run $bin $off check $f > $W/chk.out 2> $W/chk.err; crc=$?
  compile $f $stem; mrc=$?
  cl=$(head -1 $W/chk.err); ml=$(head -1 $W/cc.err)
  if [ $crc -eq 1 ] && [ $mrc -eq 1 ] && [ "$cl" = "$ml" ] && [[ $cl =~ '^seed: E[0-9]+ ' ]] && [ ! -e $W/$stem.kseed ]; then neg_ok=$((neg_ok+1))
  elif [ $crc -eq 0 ] && [ $mrc -eq 0 ] && [[ $'\n'$accept_ok$'\n' == *$'\n'$lab$'\n'* ]] && [ "$verdict" = ACCEPTED ]; then neg_acc=$((neg_acc+1))
  else neg_bad=$((neg_bad+1)); echo "BADNEG $lab ($verdict in stage-0): check rc=$crc [$cl] compile rc=$mrc [$ml]"; fi
done < $D/$rung-neg.oracle
tag=""; [ $s0 = 1 ] && tag=" stage-0 self-test (spec lines not run)"
echo "GR [$rung]$tag: positives: $pos_ok equal to stage-0, $pos_spec equal to spec, $pos_opt optional refused, $pos_front refused by the front end, $pos_bad different; negatives: $neg_ok refused, $neg_acc accepted by decision, $neg_bad wrong ($n programs)"
[ $pos_front -eq 0 ] && [ $pos_bad -eq 0 ] && [ $neg_bad -eq 0 ]
