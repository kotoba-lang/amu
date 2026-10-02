#!/bin/zsh
# scripts/seed/embench.sh [OUTDIR] -- first Embench measurement on the packaged seed (design 3.4). BOOTSTRAP-TOOL (zsh + python3 for the
# unchanged qualification runner, which is a BOOTSTRAP-TOOL and never part of the compiler's process tree).
#
#   Runs  python3 bench/embench/run_native_qualification.py --compiler build/seed/seed --runner build/seed/kexe-benchmark
#         --upstream $EMBENCH_UPSTREAM --output OUTDIR
#   UNCHANGED, with the seed packaged by scripts/seed/package.sh as the --compiler command. The runner calls
#   `seed check <f> --jvm-free`, `seed compile <f> --target aarch64-macos --jvm-free --output X`, and
#   `seed extract-native X --symbol S --output R` (stdout must contain `:offset N`), in an environment holding only an empty
#   PATH, HOME and TMPDIR=/tmp, then runs every test-* export under kexe-benchmark with fuel 16777216 and requires the result 1.
#   Afterwards it writes OUTDIR/seed-provenance.json: the claim "selfhost-built" is only made when build/seed/seed-1.bin and
#   seed-2.bin are byte-identical (the fixed point, gate G4); the label says "seed R0 (selfhost-built subset compiler)",
#   not "amu" (design 3.3). The runner's own qualification.json is left byte for byte as the runner wrote it.
#
# Env: EMBENCH_UPSTREAM (required: a git checkout of embench-iot, commit 09c2ed8c3b7008c95d08b038de4a3f6dc103ed70 in the
#      2026-09-29 run), SEED_BUILD (default build/seed), SEED_STAGE (which seed-N to package, default 1).
#      Run it on a quiet host (rule 4): the script refuses to start when the 1-minute load average is above SEED_MAX_LOAD
#      (default 4) unless SEED_ALLOW_LOADED=1, and records the load average in the provenance.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
B=$SEED_BUILD; R=$SEED_REPO
stage=${SEED_STAGE:-1}
out=${1:-$B/embench-seed-r0}
case $out in /*) ;; *) out=$PWD/$out ;; esac
[ -n "$EMBENCH_UPSTREAM" ] && [ -d "$EMBENCH_UPSTREAM/.git" ] || { echo "embench: set EMBENCH_UPSTREAM to a git checkout of embench-iot" >&2; exit 2; }
load=$(sysctl -n vm.loadavg | awk '{print $2}')
if [ -z "$SEED_ALLOW_LOADED" ] && awk "BEGIN{exit !($load > ${SEED_MAX_LOAD:-4})}"; then
  echo "embench: load average $load is above ${SEED_MAX_LOAD:-4}; rerun on a quiet host or set SEED_ALLOW_LOADED=1 (the result is then not a measurement)" >&2; exit 3
fi
# the compiler under test: seed-N packaged, with the out directory inside the baked scope.
# SEED_COMPILER=<path> bypasses packaging (harness dry runs, e.g. with stage-0; the provenance then says so).
if [ -n "$SEED_COMPILER" ]; then
  [ -x "$SEED_COMPILER" ] || { echo "embench: SEED_COMPILER is not executable" >&2; exit 2; }
  comp=$SEED_COMPILER; label="harness dry run with SEED_COMPILER (not the seed)"
else
  $R/scripts/seed/package.sh $stage --scope "$R:$B:$out:/private/tmp:/tmp" --out $B/seed || exit $?
  comp=$B/seed; label="seed R0 (selfhost-built subset compiler)"
fi
# the runner, built from the repo's source (C, system cc)
if [ ! -x $B/kexe-benchmark ] || [ $R/bench/runtime-comparison/kexe-benchmark.c -nt $B/kexe-benchmark ]; then
  cc -O2 -std=c11 $R/bench/runtime-comparison/kexe-benchmark.c -o $B/kexe-benchmark.tmp.$$ -ldl && mv $B/kexe-benchmark.tmp.$$ $B/kexe-benchmark || { echo "embench: cannot build kexe-benchmark" >&2; exit 2; }
fi
mkdir -p $out
python3 $R/bench/embench/run_native_qualification.py --compiler $comp --runner $B/kexe-benchmark \
  --upstream $EMBENCH_UPSTREAM --output $out || { echo "embench: the qualification runner failed (a port did not return 1, or a seed command failed)" >&2; exit 1; }
# provenance
sha() { shasum -a 256 $1 | cut -c1-64; }
fp=false; [ -z "$SEED_COMPILER" ] && [ -s $B/seed-1.bin ] && [ -s $B/seed-2.bin ] && cmp -s $B/seed-1.bin $B/seed-2.bin && fp=true
{
  echo '{'
  echo '  "format": "amu.seed-provenance/v1",'
  echo "  \"label\": \"$label\","
  echo "  \"selfhost_built\": $fp,"
  echo "  \"fixed_point_seed1_equals_seed2\": $fp,"
  echo "  \"seed_stage_packaged\": $stage,"
  for k in 1 2; do [ -s $B/seed-$k.bin ] && echo "  \"seed_${k}_bin_sha256\": \"$(sha $B/seed-$k.bin)\","; done
  [ -s $B/seed-unity.kotoba ] && echo "  \"unity_source_sha256\": \"$(sha $B/seed-unity.kotoba)\","
  [ -s $B/seed-0.info ] && echo "  \"stage0_bootstrap_sha256\": \"$(sed -n 's/^stage0-sha256 //p' $B/seed-0.info)\","
  echo "  \"compiler_sha256\": \"$(sha $comp)\","
  echo "  \"loader_source_sha256\": \"$(sha $R/tools/kexe_loader.c)\","
  echo "  \"runner_sha256\": \"$(sha $B/kexe-benchmark)\","
  echo "  \"load_average_1m_at_start\": $load,"
  echo "  \"qualification_json_sha256\": \"$(sha $out/qualification.json)\","
  echo "  \"repo_head\": \"$(git -C $R rev-parse HEAD)\""
  echo '}'
} > $out/seed-provenance.json
[ -z "$SEED_COMPILER" ] && cp $B/seed-package.info $out/seed-package.info
echo "embench: $out/qualification.json (selfhost_built=$fp)"
