#!/bin/zsh
# BOOTSTRAP-TOOL: compare frozen native compiler commands on one runner.
# W contains bench/embench/{ports,run_native_qualification.py}, images/{r6l,r6m,stage0},
# runner.c and an actual upstream Git checkout. No product-path code changes.
emulate -L zsh
setopt pipefail
W=${1:?usage: compare-embench.sh SNAPSHOT [MAX-WAIT-SECONDS]}; W=${W:A}
limit=${2:-900}
[[ $limit = <-> ]] || exit 2
load() { sysctl -n vm.loadavg | awk '{print $2}'; }
quiet() { awk -v l="$1" 'BEGIN {exit !(l != "" && l <= 4)}'; }
cc -O2 -std=c11 $W/runner.c -o $W/runner -ldl > $W/runner-build.log 2>&1 || exit 2
for image in r6l r6m stage0; do [ -x $W/images/$image ] || exit 2; done
[ "$(git -C $W/upstream rev-parse HEAD)" = 09c2ed8c3b7008c95d08b038de4a3f6dc103ed70 ] || exit 2
find $W/images $W/bench/embench/ports -type f -exec shasum -a 256 {} + > $W/inputs.sha256
shasum -a 256 $W/runner $W/runner.c $W/bench/embench/run_native_qualification.py >> $W/inputs.sha256
: > $W/wait-load.tsv
started=$SECONDS; stable=0
while true; do
  l=$(load) || exit 2
  printf '%s\t%s\n' "$(date -u '+%FT%TZ')" "$l" >> $W/wait-load.tsv
  if quiet "$l"; then stable=$((stable+1)); else stable=0; fi
  [ $stable -ge 3 ] && break
  if [ $((SECONDS-started)) -ge $limit ]; then
    echo "BLOCKED: host did not become quiet (load1=$l; threshold=4)" | tee $W/status.txt
    exit 3
  fi
  sleep 5
done
echo "START: stable quiet host load1=$l; common runner $(shasum -a 256 $W/runner | awk '{print $1}')"
: > $W/run-load.tsv
(while true; do printf '%s\t%s\n' "$(date -u '+%FT%TZ')" "$(load)" >> $W/run-load.tsv; sleep 2; done) &
sampler=$!
trap 'kill $sampler 2>/dev/null; wait $sampler 2>/dev/null' EXIT INT TERM
for image in r6l r6m stage0; do
  echo "RUN $image"
  python3 $W/bench/embench/run_native_qualification.py --compiler $W/images/$image --runner $W/runner \
    --output $W/results/$image --upstream $W/upstream --samples 5 > $W/$image.log 2>&1 \
    || { echo "FAIL $image (see $W/$image.log)" | tee $W/status.txt; exit 1; }
done
printf '%s\t%s\n' "$(date -u '+%FT%TZ')" "$(load)" >> $W/run-load.tsv
kill $sampler; wait $sampler 2>/dev/null; trap - EXIT INT TERM
shasum -a 256 -c $W/inputs.sha256 > $W/input-check.log || exit 1
if ! awk -F '\t' '$2 == "" || $2 > 4 {bad++} END {exit (NR == 0 || bad > 0)}' $W/run-load.tsv; then
  echo 'INVALID: host exceeded quiet threshold during measurement; do not publish speed ratios' | tee $W/status.txt
  exit 3
fi
echo 'PASS: all three compilers, 19/19 correctness, five samples, one runner, all sampled loads <= 4' | tee $W/status.txt
