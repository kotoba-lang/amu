#!/bin/zsh
# BOOTSTRAP-TOOL. Prove the product acceptance conditions, not seed readiness.
# Usage: prove-100.sh AMU GENERATION-DIR [OUT]
# GENERATION-DIR contains g1/g2/g3, front1/front2/front3, inputs.sha256,
# inputs/scan/{src,order.txt,o} and inputs/kotoba-lang/lang/compat.
# Every absent item is FAIL; supplementary dyld evidence does not replace rule 11.
emulate -L zsh
setopt pipefail nullglob
R=${0:A:h:h:h}
A=${1:?usage: prove-100.sh AMU GENERATION-DIR [OUT]}; A=${A:A}
D=${2:?generation dir}; D=${D:A}
W=${3:-$D/proof}; mkdir -p $W; W=${W:A}
[[ $W != $D && $W != $R ]] || { echo 'proof output must be a separate directory' >&2; exit 2; }
: > $W/results.tsv
failed=0
row() { printf '%s\t%s\t%s\n' "$1" "$2" "$3" | tee -a $W/results.tsv; [ "$2" = PASS ] || failed=1; }
sha() { shasum -a 256 "$1" | awk '{print $1}'; }
{
  echo "date $(date -u '+%FT%TZ')"
  echo "amu $A $(sha $A)"
  echo "source-head $(git -C $R rev-parse HEAD)"
  echo "load $(sysctl -n vm.loadavg 2>/dev/null)"
  echo 'No timing result is reported; references run only in differential harnesses.'
} > $W/provenance.txt

# Content, not only repository heads, identifies external working-tree inputs.
if [ -s $D/inputs.sha256 ] && (cd $R && shasum -a 256 -c $D/inputs.sha256 > $W/inputs.log 2>&1); then
  row INPUTS PASS "manifest $(sha $D/inputs.sha256)"
else row INPUTS FAIL "missing or changed input content; $W/inputs.log"; fi

fixed=1
for f in amu amu.bin amu.kseed; do
  for g in 1 2 3; do [ -s $D/g$g/$f ] || fixed=0; done
  cmp -s $D/g1/$f $D/g2/$f && cmp -s $D/g2/$f $D/g3/$f || fixed=0
done
# Compare names and contents, independent of the generation's output paths.
for g in 1 2 3; do
  (cd $D/g$g/o && for f in *.kso; do shasum -a 256 "$f"; done) > $W/objects$g.sha 2> $W/objects$g.err || fixed=0
done
cmp -s $W/objects1.sha $W/objects2.sha && cmp -s $W/objects2.sha $W/objects3.sha || fixed=0
cmp -s $A $D/g3/amu || fixed=0
for g in 2 3; do
  prev=$((g - 1))
  grep -Fq "builder $D/g$prev/amu $(sha $D/g$prev/amu)" $D/g$g/amu.info || fixed=0
  grep -Fq "builder $D/g$prev/amu" $D/front$g.out || fixed=0
done
[ $fixed = 1 ] && row G4 PASS 'three generations: object contents, container, code and command equal; builder receipts present' \
  || row G4 FAIL 'missing/different generations or builder receipts'

if file $R/bin/amu | grep -q 'Mach-O\|ELF' && cmp -s $R/bin/amu $A; then
  row PRODUCT PASS 'bin/amu is the qualified image'
else row PRODUCT FAIL 'bin/amu still uses the bootstrap launcher'; fi

entry=1
for ns in kotoba.compiler.nbb.check-cli kotoba.compiler.nbb.aarch64-cli; do
  [ -s $D/g3/o/$ns.kso ] || entry=0
done
[ $entry = 1 ] && row ENTRIES PASS 'both source-compiled product entry objects present' \
  || row ENTRIES FAIL 'check-cli and/or aarch64-cli missing from the image'

otool -L $A > $W/libraries.txt 2>&1
deps=$(tail -n +2 $W/libraries.txt | awk '{print $1}')
allow=$(sed -n 's/^allow \([^ ]*\).*/\1/p' $D/g3/amu.info)
if [ -n "$deps" ] && ! echo "$deps" | grep -vq '^/usr/lib/' && [ -n "$allow" ] && [[ ",$allow," != *",20,"* ]]; then
  row STATIC PASS "libraries $deps; wires $allow"
else row STATIC FAIL "unverified dependencies/capabilities; $W/libraries.txt"; fi

# These gates run on THIS image. Historical seed/rungs records never substitute.
AM_SEED=$R/build/seed-boot/r6m/seed-1.bin zsh $R/scripts/seed/launcher/test.sh $A $W/launcher > $W/launcher.log 2>&1
if grep -q '^PASS L2 ' $W/launcher.log && ! grep -q '^FAIL L2 ' $W/launcher.log; then
  row G1 PASS "19 Embench correctness programs; $W/launcher.log"
else row G1 FAIL "$W/launcher.log"; fi
if grep -q '^PASS L3 ' $W/launcher.log; then
  row INTERPOSER PASS "supplementary process interposer only; $W/launcher.log"
else row INTERPOSER FAIL "$W/launcher.log"; fi

corpus_ok=1
for p in none corpus-policy corpus-policy-all; do
  args=(); [ $p = none ] || args=($R/seed/tests/checkfull/fx/$p.edn)
  zsh $R/seed/tests/checkfull/corpus.sh $A $W/corpus-$p $args > $W/corpus-$p.log 2>&1 || corpus_ok=0
  awk -F '\t' '($6 != "SAME-OK" && $6 != "SAME-REFUSE") {bad++} END {exit (NR != 391 || bad > 0)}' \
    $W/corpus-$p/check.tsv || corpus_ok=0
done
[ $corpus_ok = 1 ] && row G2 PASS '391/391 check verdict, message and exit in three policy modes' \
  || row G2 FAIL 'corpus difference, missing case or crash'
AM_SEED=$R/build/seed-boot/r6m/seed-1.bin zsh $R/seed/amu-main/parity.sh $W/compile-corpus \
  --compile $A > $W/compile-corpus.log 2>&1
compile_rc=$?
if [ $compile_rc = 0 ] && awk -F '\t' \
     '($4 != "BEHAVIOUR-SAME" && $4 != "BOTH-REFUSE") {bad++} END {exit (NR != 391 || bad > 0)}' \
     $W/compile-corpus/compile.tsv; then
  row COMPILE_FULL PASS '391 corpus programs: compile refusal and exported behaviour agree with reference'
else row COMPILE_FULL FAIL "compile/behaviour difference or missing export; $W/compile-corpus/summary.txt"; fi
zsh $R/seed/tests/checkfull/diff.sh $A $W/negative > $W/negative.log 2>&1
if [ $? = 0 ] && [ -s $W/negative/result.tsv ] && ! grep -q '^DIFF' $W/negative/result.tsv; then
  row G3 PASS 'argument and refusal differential; declared gaps evaluated separately'
else row G3 FAIL "$W/negative.log"; fi
if grep -q '^STUB\|^DECLARED' $W/negative/result.tsv; then
  row CHECK_FULL FAIL 'declared or stub check paths remain'
else row CHECK_FULL PASS 'no declared/stub case in check differential'; fi

# Full rule 11 needs an exec trace. An interposer is supplementary and is never
# silently promoted to strace/dtruss evidence. sudo -n prevents an unattended prompt.
SUDO='sudo -n' bash $R/scripts/selfhost-wall/no-host-processes.sh --list -- $A --help > $W/trace-preflight.log 2>&1
trace_rc=$?
if [ $trace_rc != 0 ]; then
  row G5 FAIL "exec tracer unavailable/unverified (exit $trace_rc); $W/trace-preflight.log"
else
  trace_ok=1; mkdir -p $W/objects
  for f in $D/inputs/scan/src/**/*.(kotoba|cljk|cljc) $D/g3/tree/seed/split/**/*.kotoba \
           $D/g3/roots/amu/*.kotoba $D/inputs/kotoba-lang/lang/compat/**/*.kotoba; do
    tag=$(echo $f | shasum -a 256 | cut -c1-16)
    SUDO='sudo -n' bash $R/scripts/selfhost-wall/no-host-processes.sh --list -- $A check $f \
      --source-path $D/inputs/scan/src --source-path $D/g3/tree/seed/split --source-path $D/g3/roots \
      --source-path $D/inputs/kotoba-lang/lang/compat --policy $R/seed/tests/checkfull/fx/corpus-policy-all.edn \
      > $W/check-$tag.trace 2>&1 || trace_ok=0
    SUDO='sudo -n' bash $R/scripts/selfhost-wall/no-host-processes.sh --list -- $A refactor plan all $f \
      > $W/refactor-$tag.trace 2>&1 || trace_ok=0
    SUDO='sudo -n' bash $R/scripts/selfhost-wall/no-host-processes.sh --list -- $A compile $f \
      --target aarch64-macos --emit-module --object-dir $D/g3/o --output $W/objects/$tag.kso \
      > $W/compile-$tag.trace 2>&1 || trace_ok=0
  done
  # Compile the compiler itself, then compare its code to the rung input.
  zsh $R/scripts/seed/build.sh unity > $W/unity.log 2>&1 || trace_ok=0
  SUDO='sudo -n' bash $R/scripts/selfhost-wall/no-host-processes.sh --list -- $A compile $R/build/seed/seed-unity.kotoba \
    --target aarch64-macos --output $W/self.kexe > $W/compile.trace 2>&1 || trace_ok=0
  [ $trace_ok = 1 ] && row G5 PASS 'own-source check/refactor plan/module compilation and compiler compile traced' \
    || row G5 FAIL 'own-source command or trace failed'
fi
$A refactor verify --runner $A --classpath $D/inputs/scan/src > $W/verify.log 2>&1
[ $? = 0 ] && row REFACTOR_VERIFY PASS "$W/verify.log" || row REFACTOR_VERIFY FAIL "$W/verify.log"

# Under load, correctness is evidence; benchmark timing is not.
load=$(sysctl -n vm.loadavg 2>/dev/null | awk '{print $2}')
if [ -n "$load" ] && awk -v l=$load 'BEGIN {exit !(l <= 4)}'; then
  # Qualification compiles through the actual command, never a seed substitute.
  # Sample throughout, so a quiet start alone cannot qualify the timing.
  : > $W/bench-load.txt
  (while true; do sysctl -n vm.loadavg | awk '{print $2}' >> $W/bench-load.txt; sleep 1; done) &
  sampler=$!
  SEED_BUILD=$W/bench-tools SEED_COMPILER=$A SEED_MAX_LOAD=4 \
    zsh $R/scripts/seed/embench.sh $W/quiet-bench > $W/quiet-bench.log 2>&1
  bench_rc=$?; kill $sampler; wait $sampler 2>/dev/null
  if [ $bench_rc = 0 ] && [ -s $W/quiet-bench/qualification.json ] \
       && awk '{if ($1 > 4) bad++} END {exit (NR == 0 || bad > 0)}' $W/bench-load.txt; then
    row QUIET_BENCH PASS "qualified command $(sha $A); all sampled loads <= 4; $W/quiet-bench"
  else row QUIET_BENCH FAIL "qualification failed or host became loaded; $W/quiet-bench.log"; fi
else row QUIET_BENCH FAIL "no quiet benchmark receipt (load1 ${load:-unknown})"; fi
if [ $failed = 0 ]; then echo '100% PASS'; exit 0; fi
echo "100% FAIL; evidence $W/results.tsv"
exit 1
