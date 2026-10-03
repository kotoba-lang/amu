#!/bin/zsh
# scripts/seed/link-capacity.sh [--seed S.bin] [--objs DIR] [--copies K] [--work W] -- the seed's link capacity (agent LINK,
# rung r6h, 2026-10-04). BOOTSTRAP-TOOL (zsh + python3 for the object renaming and the report); after the loader is built only
# seeds run. Measures, with real seed-compiled module objects (default: the 54 OK objects of a selfbuild scan, build/selfbuild-run/r6/o):
#   DIFF   the seed links and extracts every recorded selfbuild probe image (build/selfbuild-run/link/img*) at the DEFAULT profile
#          and the DEFAULT loader budget (16 Mi vector items): container and code slice byte-identical to the recorded ones
#          (those were linked by the r6e large-M seed, one byte per word, through OUT)
#   SCALE  K renamed copies of the whole object set (namespace "<ns>__cK" on the N and R lines; the code is unchanged) plus one
#          probe entry requiring every module of every copy: a link with K x the modules, edges and interface entries of the
#          scan (K=3: 162 modules, ~7.4 MB, more require edges than the old 256 cap). Linked, extracted, packaged
#          (scripts/seed/package.sh) and run: main = 0. The image is also checked against an independent linker
#          (link_oracle.py, BOOTSTRAP-TOOL: post-order layout, L relocations, S stub patches, keyword-table patch).
#   MAX    copies of the largest object, all required by the probe, until the link refuses: the largest image that links, and the
#          refusal one module later must be `seed: E6020 linked image exceeds the link buffer` by name (exit 1, no trap).
# Output: <work>/report.txt (default build/link-capacity). Host load is printed; no time here is a result on a loaded host.
emulate -L zsh
setopt pipefail
R=$(cd "$(dirname "$0")/../.." && pwd)
seed=$R/build/link/b/seed-1.bin; O=$R/build/selfbuild-run/r6/o; K=3; W=$R/build/link-capacity
IMGS=${LINK_IMGS:-$R/build/selfbuild-run/link}   # the recorded selfbuild probe images (img*/o, image.kseed, code.bin) for DIFF
while [ $# -gt 0 ]; do
  case $1 in --seed) seed=$2; shift 2 ;; --objs) O=$2; shift 2 ;; --copies) K=$2; shift 2 ;; --work) W=$2; shift 2 ;;
    *) echo "usage: link-capacity.sh [--seed S.bin] [--objs DIR] [--copies K] [--work W]" >&2; exit 2 ;; esac
done
seed=${seed:A}; O=${O:A}; mkdir -p $W; W=${W:A}
# inputs are copied under the work dir (inside the repo: the loader's wire-35 scope), so they may come from another worktree
rm -rf $W/in; mkdir -p $W/in/o; cp $O/*.kso $W/in/o/; O=$W/in/o
for D in $IMGS/img*(N/); do mkdir -p $W/in/${D:t}; cp -R $D/o $D/image.kseed $D/code.bin $W/in/${D:t}/ 2>/dev/null; done
source $R/scripts/seed/lib.sh
export SEED_BUILD=$W SEED_RESOURCES_35=$R
sha() { shasum -a 256 $1 | cut -c1-16; }
now() { perl -MTime::HiRes=time -e 'printf "%.2f", time'; }
off=$(cat ${seed%.bin}.offset 2>/dev/null || echo 0)
rep=$W/report.txt
{ echo "link-capacity $(date '+%F %T') seed $(sha $seed) ($(wc -c < $seed | tr -d ' ') B) load $(sysctl -n vm.loadavg | awk '{print $2}')"
  echo "objects $O ($(ls $O/*.kso | wc -l | tr -d ' ') files)"; } > $rep
fail=0

# ---- DIFF ----
for D in $W/in/img*(N/); do
  [ -f $D/image.kseed ] && [ -f $D/o/selfbuild.probe.kso ] || continue
  rm -f $W/d.kseed $W/d.bin
  seed_run $seed $off link $D/o/selfbuild.probe.kso --object-dir $D/o --output $W/d.kseed > $W/d.log 2>&1
  seed_run $seed $off extract-native $W/d.kseed --symbol main --output $W/d.bin >> $W/d.log 2>&1
  if cmp -s $W/d.kseed $D/image.kseed && cmp -s $W/d.bin $D/code.bin; then
    echo "DIFF ${D:t} PASS container $(wc -c < $W/d.kseed | tr -d ' ') B and code slice identical to the recorded r6e large-M link (default profile, default budget)" >> $rep
  else echo "DIFF ${D:t} FAIL ($(tail -1 $W/d.log))" >> $rep; fail=1; fi
done

# ---- SCALE ----
S=$W/scale; rm -rf $S; mkdir -p $S/o
python3 - $O $S $K > $S/tops.txt <<'EOF'
import sys, os, glob
O, S, K = sys.argv[1], sys.argv[2], int(sys.argv[3])
objs = {}
for f in glob.glob(os.path.join(O, '*.kso')):
    t = open(f, encoding='latin-1').read()
    objs[t.split('\n')[1][2:]] = t
req = set()
for t in objs.values():
    for l in t.split('\n'):
        if l.startswith('R '): req.add(l[2:])
tops = sorted(n for n in objs if n not in req)
for k in range(1, K + 1):
    for n, t in objs.items():
        out = []
        for l in t.split('\n'):
            if l.startswith('N ') or (l.startswith('R ') and l[2:] in objs): l = l + '__c%d' % k
            out.append(l)
        open(os.path.join(S, 'o', '%s__c%d.kso' % (n, k)), 'w', encoding='latin-1').write('\n'.join(out))
    for n in sorted(objs): print('%s__c%d' % (n, k))   # the probe requires every module (more edges than the old 256 cap)
EOF
i=0; req=""; for n in $(cat $S/tops.txt); do req="$req [$n :as m$i]"; i=$((i+1)); done
printf '(ns selfbuild.probe\n  {:kotoba/export [main]}\n  (:require%s))\n\n(defn main [] :i64 0)\n' "$req" > $S/probe.kotoba
nmod=$(( $(ls $S/o/*.kso | wc -l) + 1 ))
t0=$(now)
seed_run $seed $off compile $S/probe.kotoba --emit-module --entry --object-dir $S/o --output $S/o/selfbuild.probe.kso > $S/emit.log 2>&1
t1=$(now)
SEED_VECTOR_ITEMS=${LC_ITEMS:-16777216} seed_run $seed $off link $S/o/selfbuild.probe.kso --object-dir $S/o --output $S/image.kseed > $S/link.log 2>&1; st=$?
t2=$(now)
if [ $st -eq 0 ] && [ -s $S/image.kseed ]; then
  SEED_VECTOR_ITEMS=${LC_ITEMS:-16777216} seed_run $seed $off extract-native $S/image.kseed --symbol main --output $S/code.bin > $S/extract.log 2>&1
  python3 $R/scripts/seed/link_oracle.py $S/o selfbuild.probe $S/oracle.kseed > $S/oracle.log 2>&1
  orc=FAIL; cmp -s $S/oracle.kseed $S/image.kseed && orc=PASS
  mkdir -p $S/pkg; cp $S/code.bin $S/pkg/seed-1.bin; sed -n 's/.*:offset \([0-9]*\).*/\1/p' $S/extract.log > $S/pkg/seed-1.offset
  SEED_BUILD=$S/pkg zsh $R/scripts/seed/package.sh 1 --out $S/pkg/image --allow 3,35,37,38,39 > $S/package.log 2>&1
  $S/pkg/image > $S/run.out 2>&1; rst=$?
  edges=$(grep -h -c '^R ' $S/o/*.kso | awk '{s+=$1} END {print s}'); ifs=$(grep -h -c '^E ' $S/o/*.kso | awk '{s+=$1} END {print s}')
  echo "SCALE K=$K $( [ $orc = PASS ] && [ $rst -eq 0 ] && echo PASS || echo FAIL ) modules $nmod, require edges $edges, interface entries $ifs, image $(wc -c < $S/code.bin | tr -d ' ') B, container $(wc -c < $S/image.kseed | tr -d ' ') B; oracle $orc; packaged run exit $rst; emit $(printf %.1f $(( t1 - t0 ))) s, link $(printf %.1f $(( t2 - t1 ))) s (loader vector items ${LC_ITEMS:-16777216})" >> $rep
  [ $orc = PASS ] && [ $rst -eq 0 ] || fail=1
else echo "SCALE K=$K FAIL link exit $st: $(tail -1 $S/link.log)" >> $rep; fail=1; fi

# ---- MAX ----
X=$W/max; rm -rf $X; mkdir -p $X/o
big=$(ls -S $O/*.kso | head -1); bn=$(sed -n 2p $big | cut -c3-)
# N renamed copies of the largest object (each keeps the original's requires, copied unrenamed from the object directory); the
# probe requires copies 1..N without an alias (no stubs), so the link holds N x the largest blob
cp $O/*.kso $X/o/
lo=1; hi=${LC_MAXN:-200}; last_ok=0; last_ok_bytes=0
python3 - $big $X/o $hi <<'EOF2'
import sys, os
big, D, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
t = open(big, encoding='latin-1').read().split('\n')
name = t[1][2:]
for k in range(1, n + 1):
    out = ['N %s__x%d' % (name, k) if l.startswith('N ') else l for l in t]
    open(os.path.join(D, '%s__x%d.kso' % (name, k)), 'w', encoding='latin-1').write('\n'.join(out))
EOF2
tryn() { # link a probe requiring copies 1..N: 0 = linked
  local j req=""; for j in $(seq 1 $1); do req="$req [$bn""__x$j]"; done
  printf '(ns selfbuild.probe\n  {:kotoba/export [main]}\n  (:require%s))\n\n(defn main [] :i64 0)\n' "$req" > $X/probe.kotoba
  seed_run $seed $off compile $X/probe.kotoba --emit-module --entry --object-dir $X/o --output $X/o/selfbuild.probe.kso > $X/emit.log 2>&1 || return 2
  rm -f $X/image.kseed
  SEED_VECTOR_ITEMS=${LC_ITEMS:-16777216} seed_run $seed $off link $X/o/selfbuild.probe.kso --object-dir $X/o --output $X/image.kseed > $X/link.$1.log 2>&1
}
# binary search for the largest N that links (a link either succeeds or refuses by name; anything else is a FAIL)
while [ $lo -le $hi ]; do
  mid=$(( (lo + hi) / 2 )); tryn $mid; st=$?
  if [ $st -eq 0 ] && [ -s $X/image.kseed ]; then last_ok=$mid; last_ok_bytes=$(head -1 $X/image.kseed | awk '{print $2}'); lo=$((mid+1))
  else refusal="$mid: exit $st $(tail -1 $X/link.$mid.log)"; hi=$((mid-1)); fi
done
nx=$((last_ok+1)); tryn $nx; st=$?; msg=$(tail -1 $X/link.$nx.log)
if [ $st -eq 1 ] && [[ $msg == *E6020* ]] && ! grep -q KEXE_TRAP $X/link.$nx.log; then v=PASS; else v=FAIL; fail=1; fi
echo "MAX $v largest linked image $last_ok_bytes B ($last_ok copies of $bn + its requires); one more copy: exit $st, '$msg'" >> $rep
echo "load at end $(sysctl -n vm.loadavg | awk '{print $2}')" >> $rep
cat $rep
exit $fail
