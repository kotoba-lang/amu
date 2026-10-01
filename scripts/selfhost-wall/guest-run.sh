#!/bin/zsh
# guest-run.sh: run the KOTOBA side of a differential (a module's text->text entry) as COMPILED code.
#
#   guest-run.sh [--native|--native-only|--wasm|--wasm-only|--interp] [--resolve] [--rebuild] <guest.cljk> <entry>  < cases > results
#
# The guest is a project-route module whose exported ENTRY takes one :string (the cases, one per line, or a
# batch) and answers one :string. The default mode is NATIVE: the module is wrapped with a `main` that reads the
# whole standard input (:io/read, wire 41), calls ENTRY and writes the answer (:io/write, wire 37), compiled with
# the amu native backend for this host (aarch64-macos, a .kexe), and run by the repo's own loader
# (tools/kexe_loader.c, command mode). No node, nbb or JVM runs the Kotoba code.
#
# Selfhost status of the three modes (docs/selfhost-native-gaps-20261001.md):
#   native  PRODUCT PATH. Compiled by amu (the compile step itself still runs on nbb today = bootstrap) and executed by
#           the C loader. When the backend refuses the module, the exact refusal is recorded (cache/<key>.native.refusal)
#           and printed, and the next mode runs.
#   wasm    BOOTSTRAP REFERENCE. wasm32 artifact instantiated by node's WebAssembly through runtime/browser-host.mjs.
#   interp  BOOTSTRAP REFERENCE. KIR interpreter on nbb (interp-run.cljs): the reference semantics, ~5 ms per source byte.
#
# `--native-only` / `--wasm-only` fail instead of falling back; `--interp` skips the compilers; `--resolve` prints the
# mode that would run (native|wasm|interp), compiling if needed, and reads no input. The negative answers are cached
# too, so a refused module costs one compile attempt until a source under the classpath changes.
#
# Env: WALL_CP (classpath file, default /private/tmp/wall-cp-11.txt), WALL_K (kotoba-lang checkout), WALL_AMU_SRC,
#      WALL_NBB_DIR (checkout with node_modules), GUEST_CACHE, GUEST_POOL (native string pool bytes, default 256 MiB),
#      GUEST_PAIRS (native pair arena, default 32M), GUEST_VECTORS / GUEST_VECTOR_ITEMS (native vector table entries / element words, defaults 4M / 128M: a list of aggregate handles is a vector, every `typed-list-conj` allocates one),
#      GUEST_SECONDS (native cpu/wall limit, default 600), GUEST_FUEL (native fuel, default unmetered).
HERE="$(cd "$(dirname "$0")" && pwd)"
AMU=${WALL_AMU_ROOT:-$(cd "$HERE/../.." && pwd)}
K=${WALL_K:?set WALL_K}
CPFILE=${WALL_CP:?set WALL_CP}
CP=$(cat $CPFILE)
AMU_SRC=${WALL_AMU_SRC:-$AMU/src}
NBB_DIR=${WALL_NBB_DIR:-$AMU}
CACHE=${GUEST_CACHE:-/tmp/kotoba-guest-cache}
mkdir -p $CACHE

mode=native; only=0; resolve=0; rebuild=0
while [ $# -gt 0 ]; do
  case $1 in
    --native) mode=native;; --native-only) mode=native; only=1;;
    --wasm) mode=wasm;; --wasm-only) mode=wasm; only=1;;
    --interp) mode=interp;; --resolve) resolve=1;; --rebuild) rebuild=1;;
    --) shift; break;;
    -*) echo "guest-run: unknown option $1" >&2; exit 2;;
    *) break;;
  esac; shift
done
guest=$1; entry=$2
[ -f "$guest" ] && [ -n "$entry" ] || { echo "usage: guest-run.sh [mode] <guest.cljk> <entry> < input" >&2; exit 2; }
guest=$(cd "$(dirname "$guest")" && pwd)/$(basename "$guest")

SRCDIRS=(${(f)"$(echo "$CP" | tr ':' '\n' | grep '/src$')"} $AMU_SRC $K/lang/compat)
SP=(); for d in $SRCDIRS; do SP+=(--source-path $d); done
export KROOTS="${(j/:/)SRCDIRS}"
key=$(cat $guest <(echo $entry) | shasum -a 256 | cut -c1-16)-$(basename $guest .cljk)

# stale when any source under the classpath is newer than the product (cached refusals included)
fresh() {  # $1 = product file (GUEST_NOFRESH=1: any existing product counts, for a loop of batches)
  [ -n "$GUEST_NOFRESH" ] && [ -e "$1" ] && return 0
  [ $rebuild -eq 0 ] && [ -e "$1" ] && [ "$guest" -ot "$1" ] && [ "$HERE/guest-run.sh" -ot "$1" ] || return 1
  [ -z "$(find $SRCDIRS -newer "$1" \( -name '*.cljk' -o -name '*.kotoba' -o -name '*.cljc' \) -print -quit 2>/dev/null)" ]
}
refusal_of() { sed -n 's/.*:message "\([^"]*\)".*/\1/p' | head -1 | cut -c1-400; }

nbb() { ( cd $NBB_DIR; ulimit -s ${WALL_ULIMIT_S:-65520} 2>/dev/null; exec nice node --stack-size=${WALL_STACK_SIZE:-56000} node_modules/nbb/cli.js --classpath "$CP:$AMU_SRC" "$@" ); }

build_loader() {
  loader=$CACHE/kexe-loader
  [ -x $loader ] && [ $loader -nt $AMU/tools/kexe_loader.c ] || cc $AMU/tools/kexe_loader.c -std=c11 -O2 -o $loader || return 1
}

native_ready() {  # sets nbin noffset; returns 0 when a native product exists, 1 (and a refusal file) otherwise
  nbin=$CACHE/$key.native.bin; noff=$CACHE/$key.native.offset; nref=$CACHE/$key.native.refusal
  fresh $nbin && return 0
  fresh $nref && return 1
  rm -f $nbin $noff $nref
  local wrapped=$CACHE/$key.main.cljk kexe=$CACHE/$key.kexe pol=$CACHE/policy.edn out
  # plain text: the export list becomes [main], and a main that reads stdin, calls ENTRY and writes the answer is appended
  awk '!d && sub(/:kotoba\/export \[[^]]*\]/, ":kotoba/export [main]") {d=1} {print}' $guest > $wrapped
  printf '\n(defn main [] :i64\n  (let [text (typed-cap-call :io/read :string :string "")\n        out (%s text)\n        n (typed-cap-call :io/write :string :string out)]\n    0))\n' $entry >> $wrapped
  echo '{:allow #{[:cap/call 3] [:cap/call 37] [:cap/call 41]}}' > $pol
  out=$(nbb $AMU_SRC/kotoba/compiler/nbb/aarch64_cli.cljk compile $wrapped --target aarch64-macos --jvm-free --policy $pol --output $kexe $SP 2>&1)
  if ! echo "$out" | grep -q ':ok true'; then
    echo "$out" | refusal_of > $nref; [ -s $nref ] || echo "$out" | tail -3 | cut -c1-400 > $nref; return 1
  fi
  out=$(nbb $AMU_SRC/kotoba/compiler/nbb/x86_64_cli.cljk extract-native $kexe --symbol main --output $nbin 2>&1)
  echo "$out" | grep -q ':ok true' || { echo "extract-native: $out" | cut -c1-400 > $nref; return 1; }
  echo "$out" | sed -n 's/.*:offset \([0-9]*\).*/\1/p' > $noff
  return 0
}

wasm_ready() {
  wbin=$CACHE/$key.wasm; wref=$CACHE/$key.wasm.refusal
  fresh $wbin && return 0
  fresh $wref && return 1
  rm -f $wbin $wref
  # the browser host wants a `main` export beside the entry
  local wrapped=$CACHE/$key.wasm.cljk
  awk '!d && match($0, /:kotoba\/export \[[^]]*/) {$0 = substr($0, 1, RSTART+RLENGTH-1) " main" substr($0, RSTART+RLENGTH); d=1} {print}' $guest > $wrapped
  printf '\n(defn main [] :i64 0)\n' >> $wrapped
  out=$(nbb $AMU_SRC/kotoba/compiler/nbb/wasm_cli.cljk compile $wrapped --target wasm32-browser --fuel ${GUEST_WASM_FUEL:-4000000000000} --output $wbin $SP 2>&1)
  if ! echo "$out" | grep -q ':ok true'; then
    echo "$out" | refusal_of > $wref; [ -s $wref ] || echo "$out" | tail -3 | cut -c1-400 > $wref; return 1
  fi
  return 0
}

run_native() {
  build_loader || { echo "guest-run: cannot build the kexe loader" >&2; return 2; }
  KEXE_COMMAND=1 KEXE_STRING_POOL=${GUEST_POOL:-268435456} KEXE_PAIRS=${GUEST_PAIRS:-33554432} \
    KEXE_VECTORS=${GUEST_VECTORS:-4194304} KEXE_VECTOR_ITEMS=${GUEST_VECTOR_ITEMS:-134217728} \
    KEXE_CPU_SECONDS=${GUEST_SECONDS:-600} KEXE_WALL_SECONDS=${GUEST_SECONDS:-600} ${GUEST_FUEL:+KEXE_FUEL=$GUEST_FUEL} \
    $loader $nbin $(cat $noff) 0 aarch64 3,37,41
}

if [ $mode = native ]; then
  if native_ready; then
    [ $resolve -eq 1 ] && { echo native; exit 0; }
    run_native; exit $?
  fi
  echo "guest-run: native refused $(basename $guest): $(cat $nref)" >&2
  [ $only -eq 1 ] && exit 3
  mode=wasm
fi
if [ $mode = wasm ]; then
  if wasm_ready; then
    [ $resolve -eq 1 ] && { echo wasm; exit 0; }
    echo "guest-run: mode=wasm (BOOTSTRAP: node WebAssembly)" >&2
    ulimit -s ${WALL_ULIMIT_S:-65520} 2>/dev/null
    exec node --stack-size=${WALL_STACK_SIZE:-56000} $HERE/wasm-run.mjs $wbin $entry
  fi
  echo "guest-run: wasm refused $(basename $guest): $(cat $wref)" >&2
  [ $only -eq 1 ] && exit 3
fi
[ $resolve -eq 1 ] && { echo interp; exit 0; }
echo "guest-run: mode=interp (BOOTSTRAP: KIR interpreter on nbb)" >&2
GUEST=$guest ENTRY=$entry nbb $HERE/interp-run.cljs
