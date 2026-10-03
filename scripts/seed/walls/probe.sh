#!/bin/zsh
# probe.sh <file> [objdir]: seed r6f compiles one module in separate mode against objdir (default build/walls/o, a live
# copy of the last scan's objects); on success the object replaces <objdir>/<ns>.kso, so dependents can be probed next.
# BOOTSTRAP-TOOL (agent WALLS, 2026-10-04). WALLS_SEED: the seed (default build/walls/r6f/seed-1.bin, rung r6f da6d0a98).
f=${1:A}; cd ${0:A:h}/../../..
export SEED_BUILD=$PWD/build/walls SEED_SECONDS=300
source scripts/seed/lib.sh
O=${2:-$PWD/build/walls/o}
case $f in $PWD/*) ;; *) mkdir -p build/walls/p/src; cp $f build/walls/p/src/${f:t}; f=$PWD/build/walls/p/src/${f:t} ;; esac
ns=$(grep -m1 -o '(ns [^ )]*' $f | cut -c5-)
seed_run ${WALLS_SEED:-build/walls/r6f/seed-1.bin} 0 compile $f --emit-module --object-dir $O --output $PWD/build/walls/p/out.kso 2>&1; st=$?
[ $st -eq 0 ] && cp $PWD/build/walls/p/out.kso $O/$ns.kso
echo "exit $st ($ns)"
