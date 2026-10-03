#!/bin/zsh
# seed/tests/kir/flip.sh [seed.bin] -- the merge flip test (agent KIR5; BOOTSTRAP-TOOL, zsh + python3; test harness only).
#
# Decides docs/selfhost-seed-merge-20261003.md's flip condition with one command. Three parts, all against STAGE-0
# (bootstrap-reference, build/native-image/amu-native) on the same KIR:
#   SCAN   slice.py scan of the 10 big guests (build/seed-kir/big/*.kir, every non-helper function's call closure compiled
#          by `seed compile-kir`): compile count per guest.
#   MERGE  merge.sh runs of the merge guests (seed/tests/kir/merge/*.cljk + the desugar pass image) at scale 1 and 8:
#          stage-0's native `main` and the seed's native `main` (from stage-0's KIR) on the same input, stdout compared
#          byte for byte and hashed (sha256/16 of each side).
#   EQUAL  slice.py equal: per function of the big guests, compiled (SCAN) and reached by an EQUAL merge run (the same
#          structural hash in that guest's `main` closure; static reachability, not execution coverage).
# Output: $W/scan/<g>.tsv, $W/merge.tsv (merge.sh lines), $W/equal/<g>.tsv, and the summary $W/flip.txt (also stdout).
# Env: SEED_BUILD (default build/seed), FLIP_W (work dir, default $SEED_BUILD/flip), FLIP_KEXE (stage-0 kexe cache, one
#      <guest>.kexe per guest; a missing one is compiled by stage-0 through merge.sh and stored), FLIP_FORMS (the desugar
#      corpus, one EDN form per line, default build/hc/forms.txt; its 8x is FLIP_FORMS8, default build/hc/forms8.txt),
#      FLIP_DS (the desugar pass guest source, default build/hc/ds_pass.main.cljk = scripts/selfhost-wall/ds-pass-build.sh),
#      FLIP_PARTS (default "scan merge equal"), FLIP_J (parallel scans, default 3), FLIP_SCALES (default "1 8").
emulate -L zsh
setopt pipefail
H=${0:A:h}; R=${H:h:h:h}
export SEED_BUILD=${SEED_BUILD:-$R/build/seed}
source $R/scripts/seed/lib.sh
S=${1:-$SEED_BUILD/seed-1.bin}; S=${S:A}
W=${FLIP_W:-$SEED_BUILD/flip}; mkdir -p $W/scan $W/equal $W/in $W/m; W=${W:A}
KC=${FLIP_KEXE:-$R/build/kir5/kexe}; mkdir -p $KC; KC=${KC:A}
FORMS=${FLIP_FORMS:-$R/build/hc/forms.txt}; FORMS8=${FLIP_FORMS8:-$R/build/hc/forms8.txt}
DS=${FLIP_DS:-$R/build/hc/ds_pass.main.cljk}
BIG=$R/build/seed-kir/big
GUESTS=(case ri codec oat cc oa di vx vc ds_guest_w)
parts=${FLIP_PARTS:-scan merge equal}
load() { sysctl -n vm.loadavg | awk '{print $2}'; }
say() { print -r -- "$*" | tee -a $W/flip.txt; }
: > $W/flip.txt
say "flip: seed $(shasum -a 256 $S | cut -c1-16) ($(wc -c < $S | tr -d ' ') B), stage-0 $SEED_STAGE0, $(date '+%Y-%m-%d %H:%M'), load $(load)"

# ---- SCAN -------------------------------------------------------------------------------------------------------------
if [[ " $parts " == *" scan "* ]]; then
  cc=$W/cc.sh
  cat > $cc <<EOF
#!/bin/zsh
source $R/scripts/seed/lib.sh
o=\$(mktemp $W/scan/o.XXXXXX)
SEED_RESOURCES_35=$W SEED_BUILD=$SEED_BUILD seed_run $S 0 compile-kir \${1:A} --output \$o 2>&1 | head -3; rc=\$?
rm -f \$o; exit \$rc
EOF
  l0=$(load)
  for g in $GUESTS; do
    while (( $(jobs | wc -l) >= ${FLIP_J:-3} )); do sleep 1; done
    ( nice python3 $H/slice.py scan $BIG/$g.kir $W/scan/$g.tsv "zsh $cc" ) &
  done
  wait
  say "SCAN (load $l0 -> $(load)): guest functions compile"
  for g in $GUESTS; do say "  $g $(wc -l < $W/scan/$g.tsv | tr -d ' ') $(awk -F'\t' '$5=="ok"' $W/scan/$g.tsv | wc -l | tr -d ' ')"; done
  cat $W/scan/*.tsv | awk -F'\t' '{n++; o+=($5=="ok")} END{printf "  total %d %d (%.2f%%)\n", n, o, 100*o/n}' | tee -a $W/flip.txt
  awk -F'\t' '$5!="ok"{print "  refused " FILENAME ": " $1 " " $6}' $W/scan/*.tsv | sed "s|$W/scan/||" | cut -c1-200 | tee -a $W/flip.txt
fi

# ---- MERGE ------------------------------------------------------------------------------------------------------------
# label guest input [stdin]: the inputs are made here, deterministically
mk_inputs() {
  local d=$W/in
  for sc in ${=FLIP_SCALES:-1 8}; do
    mkdir -p $d/$sc
    python3 $H/merge/gen-inputs.py $d/$sc $sc
    local f=$FORMS; [ $sc = 1 ] || f=$FORMS8
    for p in read desugar all; do { print "!$p"; cat $f; } > $d/$sc/ds-$p.in; done
    cp $f $d/$sc/forms.in
    head -c $(( 4096 * sc )) $f > $d/$sc/sha2.in
    python3 $H/merge/gen-docops.py $d/$sc/docops.in $(( 4000 * sc )) 2 > /dev/null
    python3 $H/merge/gen-ri-doc.py $d/$sc/ri.in $(( 2000 * sc )) 5 --unknown > /dev/null
    python3 $H/merge/gen-float.py $d/$sc/float.in $sc
    python3 - $f $d/$sc/kw.in <<'PY'
import re, sys
# every keyword text of the corpus (keywords the guest never spells), first occurrence order
seen, out = set(), []
for k in re.findall(r'(?<![\w:/.*+!?<>=-]):([A-Za-z*+!?<>=_.-][\w*+!?<>=./-]*)', open(sys.argv[1], encoding='utf-8').read()):
    if k not in seen and k not in ('nil', 'true', 'false'):  # ':nil' etc.: the guest's document-edn-read traps on both sides
        seen.add(k); out.append(k)
open(sys.argv[2], 'w').write(''.join(k + '\n' for k in out))
PY
  done
}
# one merge.sh run; stage-0's kexe of the guest comes from (or goes into) the cache
mrun() {  # label guest input stdin?
  local lab=$1 g=$2 inp=$3 si=${4:-0} key=${2:t:r}
  local env=(SEED_BUILD=$SEED_BUILD MERGE_W=$W/m MERGE_RUNS=${MERGE_RUNS:-3} MERGE_SEED_BIN=$S MERGE_STDIN=$si)
  [ -f $KC/$key.kexe ] && env+=(MERGE_KEXE=$KC/$key.kexe)
  [[ $key == ri_doc || $key == ds_pass.main ]] && env+=(MERGE_CAPS="3 33 34 41")
  [[ $key == ds_pass.main ]] && env+=(MERGE_GRANT=35,37,38,39,3,41)
  env $env zsh $H/merge.sh $g $inp $lab | tee -a $W/merge.tsv
  [ -f $KC/$key.kexe ] || { [ -f $W/m/$lab.kexe ] && cp $W/m/$lab.kexe $KC/$key.kexe; }
  return 0
}
if [[ " $parts " == *" merge "* ]]; then
  mk_inputs
  : > $W/merge.tsv
  l0=$(load)
  M=$H/merge
  for sc in ${=FLIP_SCALES:-1 8}; do
    I=$W/in/$sc
    for p in read desugar all; do mrun ds-$p-$sc $DS $I/ds-$p.in 1; done
    # validate-expr's cases are the desugar pass's answers (stage-0's run above)
    python3 $M/gen-vx.py $W/m/ds-desugar-$sc.s0.out $I/vx.in
    # the guest never frees: one run of every case exhausts the loader's vector table on BOTH sides (measured: 320 of 516
    # cases at scale 1), so the cases go in parts of 96 (each part a run of its own, the header line repeated)
    rm -f $I/vx-p*.in
    awk -v d=$I 'NR==1{h=$0; next} {k=int((NR-2)/96); f=sprintf("%s/vx-p%03d.in", d, k); if (!(f in seen)) {print h > f; seen[f]=1} print >> f}' $I/vx.in
    for p in $I/vx-p*.in; do MERGE_RUNS=1 mrun vx-$sc-${${p:t:r}#vx-} $M/vx.cljk $p; done
    mrun fc-$sc $M/form_count.cljk $I/forms.in
    mrun edn-$sc $M/edn.cljk $I/forms.in
    mrun kw-$sc $M/kw.cljk $I/kw.in
    mrun float-$sc $M/float.cljk $I/float.in
    mrun kstring-$sc $M/kstring.cljk $I/kstring.in
    mrun posix-$sc $M/posix_path.cljk $I/posix.in
    mrun case-$sc $M/case.cljk $I/case.in
    mrun sha2-$sc $M/sha2.cljk $I/sha2.in
    mrun docops-$sc $M/docops.cljk $I/docops.in
    mrun ri-$sc $M/ri_doc.cljk $I/ri.in
  done
  say "MERGE (load $l0 -> $(load)): label verdict out-bytes s0-sha seed-sha run-ms s0/seed"
  awk -F'\t' '{printf "  %s %s %s %s %s %s/%s\n", $1, $14, $13, $18, $19, $9, $10}' $W/merge.tsv | tee -a $W/flip.txt
fi

# ---- EQUAL ------------------------------------------------------------------------------------------------------------
if [[ " $parts " == *" equal "* ]]; then
  # a guest's runs count as EQUAL when every scale's output is byte-identical and no side trapped alone
  typeset -A V
  while IFS=$'\t' read -r lab rest; do
    v=$(print -r -- "$rest" | awk -F'\t' '{print $13}')
    if [[ $v == EQUAL || $v == "EQUAL TRAP-both"* ]]; then V[$lab]=EQUAL; else V[$lab]=NOTEQUAL; fi
  done < $W/merge.tsv
  args=()
  for lab in ${(k)V}; do [ -f $W/m/$lab.kir ] && args+=($W/m/$lab.kir=$V[$lab]); done
  say "EQUAL (per function: compiled AND reached by an EQUAL merge run; reached by a non-EQUAL run counted apart)"
  say "  guest functions compile compile+EQUAL reached-by-NOTEQUAL"
  for g in $GUESTS; do
    python3 $H/slice.py equal $BIG/$g.kir $W/scan/$g.tsv $args > $W/equal/$g.tsv
    say "  $g $(tail -1 $W/equal/$g.tsv | cut -f2- | tr '\t' ' ')"
  done
  cat $W/equal/*.tsv | awk -F'\t' '$1=="#"{n+=$2; o+=$3; e+=$4; x+=$5} END{printf "  total %d %d (%.2f%%) %d (%.2f%%) %d\n", n, o, 100*o/n, e, 100*e/n, x}' | tee -a $W/flip.txt
fi
say "end $(date '+%H:%M') load $(load)"
