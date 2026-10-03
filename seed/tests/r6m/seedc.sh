#!/bin/zsh
# seed/tests/r6m/seedc.sh compile <src> [--target T] [--output O] [...] -- an `amu compile`-shaped front for a seed binary
# (agent SEEDLANG, 2026-10-04), so seed/amu-main/parity.sh --compile (AM_KSEED=1) can measure the seed's LANGUAGE directly,
# without a launcher image. Env: SEEDC_BIN (seed binary, default $SEED_BUILD/seed-1.bin), SEEDC_OFF (default 0).
# BOOTSTRAP-TOOL (zsh); only the C loader and the seed run.
emulate -L zsh
source ${0:A:h}/../../../scripts/seed/lib.sh
bin=${SEEDC_BIN:-$SEED_BUILD/seed-1.bin}; off=${SEEDC_OFF:-0}
[ "$1" = compile ] || { echo "seedc: compile only" >&2; exit 64; }
shift; src=${1:A}; shift
out=""; rest=()
while [ $# -gt 0 ]; do case $1 in --output) out=${2:A}; shift 2 ;; --target) shift 2 ;; --policy) shift 2 ;; *) rest+=$1; shift ;; esac; done
[ -n "$out" ] || out=${src%.kotoba}.kseed
r=$(SEED_RESOURCES_35=$SEED_REPO:${src:h}:${out:h} seed_run $bin $off compile $src --target aarch64-macos --output $out $rest 2>&1); c=$?
print -r -- "$r" | grep -v '^seed: ' 
print -r -- "$r" | grep '^seed: ' >&2
[ $c = 0 ] && exit 0 || exit 65
