#!/bin/zsh
# scripts/seed/r6-scan.sh [seed.bin] -- the first R6 measurement (agent R6A, 2026-10-03). BOOTSTRAP-TOOL (zsh + python helper).
# How many of the 126 modules of the minimal reach set (docs/selfhost-minimal-reach-20261002.md, /private/tmp/reach-minimal.txt)
# the SEED compiles, module by module, with the seed as the checker (not stage-0):
#   1. r6_scan.py farm: the 126 files copied into one source root $W/src at their namespace paths; a dependency-first order
#      (the Kotoba reading of each ns form, the selection rule of 10-lex).
#   2. per module in that order: `seed compile <file> --emit-module --object-dir $W/o` (separate mode: the module is checked,
#      lowered and compiled against the interfaces of its requires' objects). Status per module:
#        OK        the object was written (the module compiles; its interface is available to its importers)
#        REFUSED   the seed refused it: the first refusal (code + text) is the histogram's key
#        BLOCKED   a required module has no object (it, or one of its requires, was refused): not attempted
#        TRAP      the seed did not answer (loader trap / budget / timeout): exit status and the loader's last line
#   3. link: `seed link` of every OK module whose closure is all OK (a container per root that links) -- only when asked
#      (--link), the libraries have no entry exports.
# Output: $W/r6-scan.tsv (ns, status, lines, code, text, ms), $W/hist.txt (the histogram), the load average at start and end.
# Env: SEED_BUILD (default build/seed-r6a), R6_LIST (default /private/tmp/reach-minimal.txt).
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
# FOLD (r6k, FRONTSRC request): kotoba.compiler.frontend.desugar needs a 16 Mi pair arena (4 Mi = lib.sh default traps :pairs)
export SEED_PAIRS=${SEED_PAIRS:-16777216}
R=$SEED_REPO; B=${SEED_BUILD:A}; W=$B/r6
bin=${1:-$B/seed-1.bin}; [ "$1" = --link ] && bin=$B/seed-1.bin
off=$(cat ${bin%.bin}.offset 2>/dev/null || echo 0)
list=${R6_LIST:-/private/tmp/reach-minimal.txt}
mkdir -p $W; rm -rf $W/o $W/log; mkdir -p $W/o $W/log
python3 $R/scripts/seed/r6_scan.py farm $list $W > $W/order.txt 2> $W/external.txt || { echo "r6-scan: farm failed" >&2; exit 2; }
export SEED_RESOURCES_35=$R:$W
load0=$(uptime | sed 's/.*averages: //')
print -r -- "# r6-scan $(date '+%F %T') compiler $(shasum -a 256 $bin | cut -c1-16) load $load0" > $W/r6-scan.tsv
typeset -A ok
while read -r ns fp deps; do
  lines=$(wc -l < $fp | tr -d ' ')
  miss=""
  if [ "$deps" != "-" ]; then for d in ${=deps}; do [ -n "${ok[$d]}" ] || { miss=$d; break; }; done; fi
  if [ -n "$miss" ]; then
    printf '%s\tBLOCKED\t%s\t-\trequires %s\t0\n' $ns $lines $miss >> $W/r6-scan.tsv; continue
  fi
  t0=$(perl -MTime::HiRes=time -e 'printf "%d", time*1000')
  seed_run $bin $off compile $fp --emit-module --object-dir $W/o --output $W/o/$ns.kso > $W/log/$ns.log 2>&1; st=$?
  t1=$(perl -MTime::HiRes=time -e 'printf "%d", time*1000')
  ms=$((t1 - t0))
  if [ $st -eq 0 ] && [ -s $W/o/$ns.kso ]; then
    ok[$ns]=1; printf '%s\tOK\t%s\t-\t%s\t%s\n' $ns $lines "$(wc -c < $W/o/$ns.kso | tr -d ' ') object bytes" $ms >> $W/r6-scan.tsv
  else
    l=$(grep -m1 '^seed: E' $W/log/$ns.log)
    if [ -n "$l" ]; then
      code=$(print -r -- "$l" | sed -n 's/^seed: \(E[0-9]*\).*/\1/p')
      txt=$(print -r -- "$l" | sed 's/^seed: E[0-9]* *//; s/^[^ ]*:[0-9]*:[0-9]*: *//' | tr '\t' ' ' | cut -c1-200)
      printf '%s\tREFUSED\t%s\t%s\t%s\t%s\n' $ns $lines $code "$txt" $ms >> $W/r6-scan.tsv
    else
      printf '%s\tTRAP\t%s\tTRAP\texit %s: %s\t%s\n' $ns $lines $st "$(tail -1 $W/log/$ns.log | tr '\t' ' ' | cut -c1-160)" $ms >> $W/r6-scan.tsv
    fi
  fi
done < $W/order.txt
print -r -- "# load at end $(uptime | sed 's/.*averages: //')" >> $W/r6-scan.tsv
python3 $R/scripts/seed/r6_scan.py hist $W/r6-scan.tsv $W/order.txt | tee $W/hist.txt
