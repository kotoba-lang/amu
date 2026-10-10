#!/bin/zsh
# seed/tests/compile-cli/run.sh <front-objects> [work-dir] [list] -- the product entry nbb.aarch64-cli built FROM SOURCE
# on the seed route (no spike): its Kotoba `main` dispatches to nbb.cli's Kotoba `run!`, whose `compile` is the host's
# `compile-uncached!` over kotoba.compiler.native-artifact. Build: seed r6m compiles cli-support, native-admission,
# native-artifact, nbb.cli and nbb.aarch64-cli (entry) of this tree against a copy of FRONT-OBJECTS, links the entry and
# extracts `main`. Then each program of LIST (default: the parity corpus dirs of seed/amu-main/parity.sh that exist
# here) is compiled by `bin/amu compile --target aarch64-macos` (BOOTSTRAP-REFERENCE, KOTOBA_VERDICT_CACHE=off: the
# guest has no verdict cache and answers :disabled) and by the guest with the same command line, and compared:
#   - exit status (the host's exit-code class of the refusal's phase on both sides);
#   - both accept: compare_artifact.py on the .kexe and .provenance.edn (seal first, then key by key), and
#     compare_cli.py on the stdout answer maps (as data, output dirs normalised) and the .publication.edn markers.
# Classes (result.tsv column 1): BOTH-ACCEPT, BOTH-REFUSE (same exit code), BOTH-REFUSE-CLASS-DIFF, GUEST-ONLY,
# HOST-ONLY (the guest's refusal phase and message are in the row).
# FRONT-OBJECTS must carry the frontend, kotoba.native.aarch64, kotoba.verifier, the project twins and a
# kotoba.kir.target / kotoba.kir.interp the seed reads (osaho 464cb04 or later), e.g. the seed17 objects with those two
# modules and their dependents rebuilt (docs/selfhost-compile-twin-spike-20261008.md, compile-cli addendum).
# Guests run with the native image's budgets and the 1 Mi kgraph (ADR 0369). CC_JOBS (default 6) programs at a time.
# Seed: CS_SEED (default build/seed-boot/r6m/seed-1.bin, checked against seed/rungs/r6m.record).
# --image AMU (2026-10-10): instead of building the entry, drive a packaged native amu image's `compile` (the image's
# product entry) with the same command line; the rest (host run, classes, artifact and answer comparison) is unchanged.
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h:h}
if [ "$1" = --job ]; then
  # --job <work-dir> <file>: one program, one row in <work-dir>/rows/
  W=$2; f=${3:A}; k=${${f#$R/}//\//.}; L=$(cat $W/loader 2>/dev/null); off=$(cat $W/offset 2>/dev/null)
  pol=$W/policy.edn; mkdir -p $W/h/$k $W/g/$k; rm -f $W/h/$k/*(N) $W/g/$k/*(N)
  (cd $R && KOTOBA_VERDICT_CACHE=off bin/amu compile $f --target aarch64-macos --policy $pol --output $W/h/$k/out.kexe \
     > $W/h/$k/stdout 2> $W/h/$k/stderr); hs=$?
  if [ -s $W/image ]; then
    # --image: the packaged amu image's own `compile` (its baked budgets and wires; scope = the repository + W)
    KEXE_CAP_RESOURCES_35=$R:$W $(cat $W/image) compile $f --target aarch64-macos --policy $pol \
      --output $W/g/$k/out.kexe > $W/g/$k/stdout 2> $W/g/$k/stderr; gs=$?
  else
  KEXE_COMMAND=1 KEXE_CAP_RESOURCES_35=$R:$W KEXE_STRING_POOL=1073741824 KEXE_PAIRS=67108864 KEXE_VECTORS=67108864 \
    KEXE_VECTOR_ITEMS=134217728 KEXE_HASHCONS=16 KEXE_KGRAPH=1048576 KEXE_CPU_SECONDS=600 KEXE_WALL_SECONDS=900 \
    $L $W/a64cli.bin $off 0 aarch64 3,35,37,38,39 -- compile $f --target aarch64-macos --policy $pol \
    --output $W/g/$k/out.kexe > $W/g/$k/stdout 2> $W/g/$k/stderr; gs=$?
  fi
  he=$(sed -n 's/.*:error \(:[a-z0-9-]*\).*/\1/p' $W/h/$k/stderr | head -1)
  ge=$(sed -n 's/.*:error \(:[a-z0-9-]*\).*/\1/p' $W/g/$k/stderr | head -1)
  gm=$(sed -n 's/.*:message "\(.*\)"}$/\1/p' $W/g/$k/stderr | head -1); [ -n "$gm" ] || gm=$(head -c 160 $W/g/$k/stderr | tr '\n\t' '  ')
  art=(- - - -); cli=(- - -)
  if [ $hs -eq 0 ] && [ $gs -eq 0 ]; then
    cls=BOTH-ACCEPT
    art=($(python3 $R/seed/tests/compile-twin/compare_artifact.py $W/h/$k/out.kexe $W/g/$k/out.kexe))
    cli=($(python3 $H/compare_cli.py $W/h/$k/stdout $W/g/$k/stdout $W/h/$k $W/g/$k $W/h/$k/out.kexe $W/g/$k/out.kexe))
  elif [ $hs -ne 0 ] && [ $gs -ne 0 ]; then
    if [ $hs -eq $gs ]; then cls=BOTH-REFUSE; else cls=BOTH-REFUSE-CLASS-DIFF; fi
  elif [ $gs -eq 0 ]; then cls=GUEST-ONLY
  else cls=HOST-ONLY; fi
  # class host-status guest-status host-phase guest-phase seal keys prov prov-keys stdout stdout-keys publication file guest-message
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' $cls $hs $gs "${he:--}" "${ge:--}" $art $cli \
    ${f#$R/} "$gm" > $W/rows/$k.tsv
  exit 0
fi
if [ "$1" = --image ]; then
  # --image AMU [work-dir] [list] (2026-10-10): no entry is built; the guest is the packaged native amu image's PRODUCT
  # `compile` (seed/amu-main l/amu/compile = nbb.aarch64-cli's Kotoba run), driven with the same command line.
  IMG=${2:A}; [ -x "$IMG" ] || { echo "usage: run.sh --image AMU [work-dir] [list]" >&2; exit 2; }
  W=${3:-$R/build/compile-cli-image}; mkdir -p $W; W=${W:A}; shift 1   # $3 = the list, as below
  echo $IMG > $W/image; echo "image $IMG $(shasum -a 256 $IMG | cut -c1-16)"
else
[ -d "$1" ] || { echo "usage: run.sh <front-objects> [work-dir] [list] | run.sh --image AMU [work-dir] [list]" >&2; exit 2; }
FRONT=${1:A}; W=${2:-$R/build/compile-cli}; mkdir -p $W; W=${W:A}; rm -f $W/image
SB=${CS_SEED:-$R/build/seed-boot/r6m/seed-1.bin}
sha() { shasum -a 256 $1 | cut -c1-64; }
[ -n "$CS_SEED" ] || [ "$(sha $SB)" = "$(sed -n 's/^seed1_sha256 //p' $R/seed/rungs/r6m.record)" ] || { echo "compile-cli: $SB is not rung r6m's seed" >&2; exit 1; }
export SEED_REPO=$R SEED_BUILD=$W/sb SEED_PAIRS=${SEED_PAIRS:-16777216}; mkdir -p $SEED_BUILD; source $R/scripts/seed/lib.sh
run() { SEED_RESOURCES_35=$R:$W SEED_VECTOR_ITEMS=134217728 SEED_SECONDS=1800 seed_run "$@"; }
O=$W/o; rm -rf $O; mkdir -p $O; cp $FRONT/*.kso $O/
comp() { run $SB 0 compile $1 --emit-module "${@:3}" --object-dir $O --output $O/$2.kso > $W/emit-$2.log 2>&1 \
           || { echo "compile-cli: $2 refused: $(grep -m1 '^seed: E' $W/emit-$2.log || tail -1 $W/emit-$2.log)" >&2; exit 1; }
         echo "$2 $(wc -c < $O/$2.kso | tr -d ' ') bytes"; }
comp $R/src/kotoba/compiler/bounded_edn.cljk kotoba.compiler.bounded-edn
comp $R/src/kotoba/compiler/nbb/cli_support.cljk kotoba.compiler.nbb.cli-support
[ -f $O/kotoba.compiler.effect-classification.kso ] || comp $R/src/kotoba/compiler/effect_classification.cljk kotoba.compiler.effect-classification
[ -f $O/kotoba.compiler.effect-row.kso ] || comp $R/src/kotoba/compiler/effect_row.cljk kotoba.compiler.effect-row
comp $R/src/kotoba/compiler/nbb/project_source.cljk kotoba.compiler.nbb.project-source
comp $R/src/kotoba/compiler/native_admission.kotoba kotoba.compiler.native-admission
comp $R/src/kotoba/compiler/native_artifact.kotoba kotoba.compiler.native-artifact
comp $R/src/kotoba/compiler/nbb/cli.cljk kotoba.compiler.nbb.cli
comp $R/src/kotoba/compiler/nbb/aarch64_cli.cljk kotoba.compiler.nbb.aarch64-cli --entry
run $SB 0 link $O/kotoba.compiler.nbb.aarch64-cli.kso --object-dir $O --output $W/a64cli.kseed > $W/link.log 2>&1 || { tail -3 $W/link.log; exit 1; }
# the seed's extract-native reads the image as one bytes value: at most 8 MiB (KEXE_BYTES_VALUE_LIMIT, ADR 0362)
echo "linked $(wc -c < $W/a64cli.kseed | tr -d ' ') bytes (extract-native limit 8388608)"
run $SB 0 extract-native $W/a64cli.kseed --symbol main --output $W/a64cli.bin > $W/extract.log 2>&1 || { cat $W/extract.log; exit 1; }
sed -n 's/.*:offset \([0-9]*\).*/\1/p' $W/extract.log > $W/offset; [ -s $W/offset ] || { echo "compile-cli: extract-native failed" >&2; exit 1; }
seed_loader > $W/loader || exit 2
[ -n "$CC_BUILD_ONLY" ] && exit 0
fi
cd $R
if [ -n "$3" ]; then files=(${(f)"$(cat $3)"})
else
  files=(); for d in seed/tests/r1/feat seed/tests/r1/conf seed/tests/corpus resources/kotoba/lang-conformance/{values,control,native} \
                    $R/seed/tests/conformance/*(/N) examples test/dual-backend test/nbb/fixtures test/nbb/fixtures/state bench/runtime-comparison; do
    files+=(${${d:A}/#$PWD/$R}/*.kotoba(N)); done
fi
echo '{:allow #{[:cap/call 35] [:cap/call 37] [:cap/call 38] [:cap/call 39]}}' > $W/policy.edn
rm -rf $W/rows $W/h $W/g; mkdir -p $W/rows
print -l ${files:A} | xargs -P ${CC_JOBS:-6} -I{} zsh $H/run.sh --job $W {}
cat $W/rows/*.tsv | sort -t$'\t' -k13 > $W/result.tsv
echo "programs $(wc -l < $W/result.tsv | tr -d ' ')"
cut -f1,6-8,10,12 $W/result.tsv | sort | uniq -c
