#!/bin/zsh
# scripts/seed/lib.sh -- shared helpers of the seed scripts (sourced, not run). BOOTSTRAP-TOOL.
#
# STAGE-0 is the BOOTSTRAP-REFERENCE compiler: build/native-image/amu-native (JVM-built, GraalVM native image).
# It is used only to build seed-0 and unit-test binaries; it is never in the seed's runtime process tree.
#
# Env: SEED_STAGE0 (default <repo>/build/native-image/amu-native; never the -next build that may be in progress),
#      SEED_MANIFEST (default <repo>/seed/MANIFEST; a reduced list for smoke tests),
#      SEED_BUILD (default <repo>/build/seed), SEED_STAGE0_SLOTS (default 2: at most this many concurrent
#      stage-0 compiles machine-wide, enforced with mkdir locks in /tmp/seed-stage0.lock.<k>),
#      SEED_EXTRACT (auto|py|native, default auto: extract-native, falling back to kexe_code.py on 'too many nodes').

SEED_REPO=${SEED_REPO:-$(cd "$(dirname "${(%):-%x}")/../.." && pwd)}
SEED_STAGE0=${SEED_STAGE0:-$SEED_REPO/build/native-image/amu-native}
SEED_BUILD=${SEED_BUILD:-$SEED_REPO/build/seed}
SEED_GRANT=${SEED_GRANT:-35,37,38,39}
mkdir -p $SEED_BUILD

# manifest paths in order (comments and blank lines dropped)
seed_manifest() { grep -v '^[[:space:]]*#' ${SEED_MANIFEST:-$SEED_REPO/seed/MANIFEST} | grep -v '^[[:space:]]*$' | sed 's/[[:space:]].*//'; }

# the C loader, rebuilt when tools/kexe_loader.c is newer
seed_loader() {
  local l=$SEED_BUILD/kexe-loader
  if [ ! -x $l ] || [ $SEED_REPO/tools/kexe_loader.c -nt $l ]; then
    cc $SEED_REPO/tools/kexe_loader.c -std=c11 -O2 -o $l.tmp.$$ 2>$SEED_BUILD/kexe-loader.cc.log && mv $l.tmp.$$ $l || { echo "seed: cannot build the loader (see $SEED_BUILD/kexe-loader.cc.log)" >&2; return 2; }
  fi
  echo $l
}

# take one of SEED_STAGE0_SLOTS machine-wide slots (stale locks of dead pids are reclaimed)
_seed_lock=""
seed_slot_take() {
  local n=${SEED_STAGE0_SLOTS:-2} k
  while :; do
    for k in $(seq 1 $n); do
      local d=/tmp/seed-stage0.lock.$k
      if mkdir $d 2>/dev/null; then echo $$ > $d/pid; _seed_lock=$d; return 0; fi
      local p=$(cat $d/pid 2>/dev/null)
      if [ -n "$p" ] && ! kill -0 $p 2>/dev/null; then rm -rf $d; fi
    done
    sleep 1
  done
}
seed_slot_give() { [ -n "$_seed_lock" ] && rm -rf $_seed_lock; _seed_lock=""; }

# seed_stage0_build <src.kotoba> <out-prefix> : compile with stage-0 and extract `main`.
# Writes <out-prefix>.kexe, <out-prefix>.bin, <out-prefix>.offset, <out-prefix>.log. Returns 0 on success.
seed_stage0_build() {
  local src=$1 out=$2 pol=$SEED_BUILD/stage0-policy.edn caps="" c r
  [ -x $SEED_STAGE0 ] || { echo "seed: no stage-0 at $SEED_STAGE0" >&2; return 2; }
  for c in ${(s:,:)SEED_GRANT}; do caps="$caps [:cap/call $c]"; done
  echo "{:allow #{$caps}}" > $pol
  seed_slot_take
  trap 'seed_slot_give' EXIT INT TERM
  r=$( ulimit -s 65500 2>/dev/null; nice $SEED_STAGE0 compile $src --target aarch64-macos --jvm-free --policy $pol --output $out.kexe 2>&1 )
  echo "$r" > $out.log
  if ! echo "$r" | grep -q ':ok true'; then seed_slot_give; return 1; fi
  if [ "${SEED_EXTRACT:-auto}" = py ]; then
    r=$( python3 $SEED_REPO/scripts/seed/kexe_code.py $out.kexe main $out.bin 2>&1 )
  else
    r=$( ulimit -s 65500 2>/dev/null; nice $SEED_STAGE0 extract-native $out.kexe --symbol main --output $out.bin 2>&1 )
  fi
  echo "$r" >> $out.log
  seed_slot_give
  if ! echo "$r" | grep -q ':ok true'; then
    # stage-0's extract-native refuses a kexe above 200,000 EDN nodes (bounded_edn max-nodes; the :code vector has one node
    # per code byte), i.e. a seed unity above about 5.5k lines. Fallback (BOOTSTRAP-TOOL, measured byte-identical to
    # extract-native on R0's seed-0): scripts/seed/kexe_code.py reads :code and the symbol offset directly.
    # SEED_EXTRACT=py forces it, SEED_EXTRACT=native forbids it.
    if [ "${SEED_EXTRACT:-auto}" != native ] && echo "$r" | grep -q 'too many nodes'; then
      echo "seed: extract-native refused (too many nodes); falling back to scripts/seed/kexe_code.py" >&2
      r=$( python3 $SEED_REPO/scripts/seed/kexe_code.py $out.kexe main $out.bin 2>&1 )
      echo "$r" >> $out.log
    fi
    echo "$r" | grep -q ':ok true' || return 1
  fi
  echo "$r" | sed -n 's/.*:offset \([0-9]*\).*/\1/p' > $out.offset
  return 0
}

# seed_run <bin> <offset> [guest args...] : run an arity-0 `main` in loader command mode.
seed_run() {
  local bin=$1 off=$2; shift 2
  local l; l=$(seed_loader) || return 2
  KEXE_COMMAND=1 KEXE_CAP_RESOURCES_35=${SEED_RESOURCES_35:-$SEED_REPO} \
    KEXE_STRING_POOL=${SEED_POOL:-268435456} KEXE_PAIRS=${SEED_PAIRS:-4194304} \
    KEXE_VECTORS=${SEED_VECTORS:-65536} KEXE_VECTOR_ITEMS=${SEED_VECTOR_ITEMS:-16777216} \
    KEXE_CPU_SECONDS=${SEED_SECONDS:-120} KEXE_WALL_SECONDS=${SEED_SECONDS:-120} \
    $l $bin $off 0 aarch64 $SEED_GRANT -- "$@"
}
