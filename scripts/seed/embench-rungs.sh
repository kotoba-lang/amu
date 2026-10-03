#!/bin/zsh
# scripts/seed/embench-rungs.sh [--rungs "r2 r3 r4"] [--out DIR] [--max-load 8] [--poll 600] [--hours 3] -- the Embench re-measure of the
# recorded rung seeds on a QUIET host. BOOTSTRAP-TOOL (zsh + python3 via embench.sh), owner HOUSE2.
#   1. waits until the 1-minute load average (sysctl vm.loadavg) is below --max-load (default 8), polling every --poll seconds (default 600)
#      for at most --hours (default 3); if the host never gets quiet it runs ONCE with SEED_ALLOW_LOADED=1 and labels the whole result LOADED
#      (the numbers are then not a measurement; only correctness and code size are)
#   2. the seeds come from `bootstrap.sh --no-head` ($SEED_BUILD/boot/<rung>/seed-1.bin, every recorded hash checked), one SEED_BUILD per rung
#      ($OUT/work-<rung>: seed-1 = seed-2 = the rung's fixed point, so the provenance says selfhost_built=true only when that holds)
#   3. for stage-0 (the bootstrap-reference, SEED_COMPILER, labelled so by embench.sh) and each rung seed, in this order, scripts/seed/embench.sh
#      -> $OUT/<name>/qualification.json + seed-provenance.json (runner unchanged: 19 ports, check/compile/run x5, fuel 16M, test-* = 1)
#   4. $OUT/table.tsv and $OUT/RESULT.txt: per port compile ms, execute ns (cold single call), raw code bytes for stage-0 and every rung seed,
#      the host load at the start/end of every run, and the verdict line QUIET or LOADED.
# Default OUT: $SEED_BUILD/embench-rungs.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
rungs=(r2 r3 r4); out=$SEED_BUILD/embench-rungs; maxload=8; poll=600; hours=3
while [ $# -gt 0 ]; do
  case $1 in --rungs) rungs=(${=2}); shift 2 ;; --out) out=$2; shift 2 ;; --max-load) maxload=$2; shift 2 ;; --poll) poll=$2; shift 2 ;; --hours) hours=$2; shift 2 ;;
    *) echo "usage: embench-rungs.sh [--rungs 'r2 r3 r4'] [--out DIR] [--max-load N] [--poll SEC] [--hours H]" >&2; exit 2 ;; esac
done
case $out in /*) ;; *) out=$PWD/$out ;; esac
mkdir -p $out
R=$SEED_REPO
load1() { sysctl -n vm.loadavg | awk '{print $2}'; }
quiet=0; waited=0; limit=$((hours*3600))
while :; do
  l=$(load1); echo "embench-rungs: load $l at $(date '+%H:%M:%S') (wait $waited s of $limit)" | tee -a $out/poll.log
  if awk "BEGIN{exit !($l < $maxload)}"; then quiet=1; break; fi
  [ $waited -ge $limit ] && break
  sleep $poll; waited=$((waited+poll))
done
verdict=QUIET; extra=""
[ $quiet -eq 1 ] || { verdict=LOADED; extra="SEED_ALLOW_LOADED=1"; echo "embench-rungs: the host never got below load $maxload in $hours h: one LOADED run (not a measurement)" | tee -a $out/poll.log; }
# the rung seeds (verified by bootstrap.sh --no-head)
BOOT=$out/boot
if ! [ -s $BOOT/$rungs[-1]/seed-1.bin ]; then
  SEED_BOOT=$BOOT zsh $R/scripts/seed/bootstrap.sh --no-head > $out/bootstrap.log 2>&1 || { echo "embench-rungs: bootstrap.sh --no-head failed"; tail -3 $out/bootstrap.log; exit 1; }
fi
runone() {   # runone <name> [stage0]
  local n=$1 w=$out/work-$1 rc
  mkdir -p $w
  if [ "$2" = stage0 ]; then
    env SEED_BUILD=$w SEED_COMPILER=$SEED_STAGE0 SEED_MAX_LOAD=$maxload ${=extra} zsh $R/scripts/seed/embench.sh $out/$n > $out/$n.log 2>&1; rc=$?
  else
    local d=$BOOT/$n
    cp $d/seed-1.bin $w/seed-1.bin; cp $d/seed-1.bin $w/seed-2.bin; cp $d/seed-1.offset $w/seed-1.offset; cp $d/seed-1.offset $w/seed-2.offset
    env SEED_BUILD=$w SEED_STAGE=1 SEED_MAX_LOAD=$maxload ${=extra} zsh $R/scripts/seed/embench.sh $out/$n > $out/$n.log 2>&1; rc=$?
  fi
  echo "embench-rungs: $n rc=$rc load_end $(load1)"; tail -1 $out/$n.log
}
runone stage0 stage0
for r in $rungs; do runone $r; done
python3 - $out $verdict ${rungs} <<'PY'
import csv, json, os, sys
out, verdict, rungs = sys.argv[1], sys.argv[2], sys.argv[3:]
names = ['stage0'] + rungs
data = {}
for n in names:
    p = os.path.join(out, n, 'summary.csv')
    if os.path.exists(p):
        data[n] = {r['workload']: r for r in csv.DictReader(open(p))}
ports = sorted(set().union(*[set(d) for d in data.values()])) if data else []
def f(n, p, k):
    try: return float(data[n][p][k])
    except Exception: return None
lines = []
hdr = ['port'] + [f'{k}:{n}' for k in ('compile_ms', 'exec_ns', 'code_B') for n in names]
lines.append('\t'.join(hdr))
import math
geo = {k: {n: [] for n in names} for k in ('compile_median_ms', 'execute_median_ns')}
for p in ports:
    row = [p]
    for k in ('compile_median_ms', 'execute_median_ns', 'raw_code_bytes'):
        for n in names:
            v = f(n, p, k); row.append('-' if v is None else (f'{v:.1f}' if k == 'compile_median_ms' else f'{v:.0f}'))
            if v and k in geo: geo[k][n].append((p, v))
    lines.append('\t'.join(row))
res = []
res.append(f'verdict {verdict} (load average 1 min < 8 required for QUIET)')
for n in names:
    pj = os.path.join(out, n, 'seed-provenance.json')
    if os.path.exists(pj):
        j = json.load(open(pj)); res.append(f"{n}: load start {j.get('load_average_1m_at_start')} end {j.get('load_average_1m_at_end')} host_loaded {j.get('host_loaded')} selfhost_built {j.get('selfhost_built')} compiler_sha256 {j.get('compiler_sha256','')[:16]}")
    qp = os.path.join(out, n, 'qualification.json')
    if os.path.exists(qp):
        q = json.load(open(qp)); w = q.get('workloads', [])
        res.append(f"{n}: {sum(1 for x in w if x.get('correct'))}/{len(w)} workloads correct")
def gm(vs): return math.exp(sum(math.log(v) for v in vs) / len(vs)) if vs else float('nan')
s0 = dict(geo['execute_median_ns']['stage0']) if 'stage0' in geo['execute_median_ns'] else {}
for n in names[1:]:
    both = [(p, v / s0[p]) for p, v in geo['execute_median_ns'][n] if p in s0 and s0[p] > 0]
    if both:
        res.append(f"{n}: execute geomean ratio to stage-0 {gm([r for _, r in both]):.3f}, max {max(both, key=lambda x: x[1])[1]:.2f} ({max(both, key=lambda x: x[1])[0]})")
    c0 = dict(geo['compile_median_ms']['stage0']); cc = dict(geo['compile_median_ms'][n])
    if c0 and cc: res.append(f"{n}: compile ms sum {sum(cc.values()):.0f} (stage-0 {sum(c0.values()):.0f})")
open(os.path.join(out, 'table.tsv'), 'w').write('\n'.join(lines) + '\n')
open(os.path.join(out, 'RESULT.txt'), 'w').write('\n'.join(res) + '\n')
print('\n'.join(res))
PY
