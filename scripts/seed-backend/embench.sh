#!/bin/zsh
# scripts/seed-backend/embench.sh [OUTDIR] -- BOOTSTRAP-TOOL (ADR 0365): the 19 Embench ports through the FULL amu pipeline
# (nbb frontend -> sealed KIR -> `--backend seed` -> artifact + provenance -> compile-time verifier re-emitting with the seed)
# under the UNCHANGED qualification runner, then the output-set verifier on every result.
#
#   1. scripts/seed-backend/build-wrapper.sh OUTDIR/tool    (classpath, packaged seed, Mach-O wrapper)
#   2. python3 bench/embench/run_native_qualification.py --compiler OUTDIR/tool/amu-seed --runner <kexe-benchmark>
#        --samples $SB_SAMPLES (default 1) --output OUTDIR/q     (correct = every test-* export returns 1)
#   3. per port: which backend emitted the artifact (the compile report's :backend), and
#      `verify-output-set <kexe> --seed OUTDIR/tool/seed` (the verifier re-emits with the recorded seed and compares bytes)
#      and the same WITHOUT --seed (must be refused by name: the recorded emitter is not available)
#   4. OUTDIR/seed-backend-labels.json: the labels the runner's report cannot carry (node + nbb ARE in the process tree;
#      timings are not results on a loaded host; load average at start and end).
# Env: EMBENCH_UPSTREAM (embench-iot checkout; else the declared-commit shim scripts/seed/embench_declared_upstream.py),
#      SB_SAMPLES, SB_PORTS_ROOT (default the amu-embench checkout holding bench/embench/ports and the runner).
emulate -L zsh
setopt pipefail
R=${0:A:h:h:h}
O=${1:-$R/build/seed-backend/embench}; mkdir -p $O; O=${O:A}
E=${SB_PORTS_ROOT:-/Users/junkawasaki/github/kotoba-lang/amu-embench}
load() { sysctl -n vm.loadavg | awk '{print $2}'; }
l0=$(load)
zsh $R/scripts/seed-backend/build-wrapper.sh $O/tool || exit 2
KB=$O/tool/kexe-benchmark
cc -O2 -std=c11 $R/bench/runtime-comparison/kexe-benchmark.c -o $KB -ldl || exit 2
rm -rf $O/q
if [ -n "$EMBENCH_UPSTREAM" ]; then
  python3 $E/bench/embench/run_native_qualification.py --compiler $O/tool/amu-seed --runner $KB --upstream $EMBENCH_UPSTREAM \
    --samples ${SB_SAMPLES:-1} --output $O/q > $O/runner.log 2>&1
else
  python3 $R/scripts/seed/embench_declared_upstream.py $E/bench/embench/run_native_qualification.py --compiler $O/tool/amu-seed \
    --runner $KB --upstream $R --samples ${SB_SAMPLES:-1} --output $O/q > $O/runner.log 2>&1
fi
rc=$?
echo "runner exit $rc (0 = every port compiled, extracted and returned 1)"
CP=$(cat $O/tool/classpath.txt)
vos() { (cd $R && nice node --stack-size=4096 node_modules/nbb/cli.js --classpath "$CP" src/kotoba/compiler/nbb/output_set_cli.cljk verify-output-set "$@" 2>&1 | tail -1) }
: > $O/ports.tsv
for d in $O/q/*(/); do
  n=${d:t}; [ $n = isolated-empty-path ] && continue
  k=$d/$n.kexe
  [ -f $k ] || { printf "%s\tNO-KEXE\t-\t-\t-\n" $n >> $O/ports.tsv; continue; }
  last=$(ls $d/compile-*.stdout | sort | tail -1)
  em=$(grep -o ':emitted :[a-z-]*' $last | head -1 | awk '{print $2}')
  fb=$(grep -o ':fallback {[^}]*}' $last | head -1 | tr '\t' ' ')
  rec=$(grep -c ':emitter {:name :kotoba-seed' $k)
  v1=$(vos $k --seed $O/tool/seed); v2=$(vos $k)
  a1=$(echo "$v1" | grep -q ':committed true' && echo ACCEPT || echo "REFUSED:$(echo $v1 | grep -o ':message "[^"]*' | cut -c11-)")
  a2=$(echo "$v2" | grep -q ':committed true' && echo ACCEPT || echo "REFUSED:$(echo $v2 | grep -o ':message "[^"]*' | cut -c11-)")
  printf "%s\t%s\t%s\t%s\t%s\t%s\n" $n "${em:-?}" "artifact-records-seed=$rec" "verify(--seed)=$a1" "verify(no seed)=$a2" "${fb:--}" >> $O/ports.tsv
done
l1=$(load)
total=$(wc -l < $O/ports.tsv | tr -d ' ')
seed=$(awk -F'\t' '$2==":kotoba-seed"' $O/ports.tsv | wc -l | tr -d ' ')
acc=$(grep -c 'verify(--seed)=ACCEPT' $O/ports.tsv)
ref=$(grep -c 'verify(no seed)=REFUSED:recorded emitter is not available' $O/ports.tsv)
correct=$(python3 -c "import json,sys; r=json.load(open('$O/q/qualification.json')); print(sum(1 for w in r['workloads'] if w['correct']))" 2>/dev/null || echo 0)
cat > $O/seed-backend-labels.json <<J
{
  "format": "amu.seed-backend-qualification-labels/v1",
  "label": "BOOTSTRAP: amu nbb route (node + nbb in the process tree) with --backend seed; NOT a selfhost compiler and NOT an official Embench score",
  "runner_report_fields_not_true_of_this_run": ["javascript_node_dependency", "jvm_dependency (no JVM is used, but the field only reflects otool of the wrapper)"],
  "wrapper_info": "$O/tool/wrapper.info",
  "ports": $total,
  "correct_ports_runner": $correct,
  "emitted_by_seed": $seed,
  "output_set_verifier_accepts_with_seed": $acc,
  "output_set_verifier_refuses_without_seed": $ref,
  "runner_exit": $rc,
  "load_average_1m_at_start": $l0,
  "load_average_1m_at_end": $l1,
  "timings_are_results": false
}
J
cat $O/ports.tsv
echo "ports $total; runner correct $correct; emitted by seed $seed; verify-output-set --seed ACCEPT $acc; without seed refused by name $ref; load $l0 -> $l1"
# The compile-time verifier (re-emitting with the seed) passed for every port whose compile succeeded, and so did
# extract-native's (runner exit 0). verify-output-set additionally decodes the artifact with kotoba.lang.edn, which refuses
# integers beyond 2^53-1 (:native-decode, output_admission.cljk) on 6 ports on BOTH backends (measured 2026-10-03); those are
# not counted against the seed. A refusal that names the emitter, the instruction stream or the export table is.
bad=$(grep -c 'verify(--seed)=REFUSED:\(recorded emitter\|native instruction\|native export\|runtime KIR\)' $O/ports.tsv)
echo "seed-related refusals with --seed: $bad"
[ $rc = 0 ] && [ $correct = 19 ] && [ $seed = 19 ] && [ $bad = 0 ] && [ $acc = $ref ]
