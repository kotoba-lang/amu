#!/bin/zsh
# scripts/seed/rung-report.sh [--record rN [--tag NAME] [--allow-incomplete]] -- the rung ladder report. BOOTSTRAP-TOOL (zsh +
# python3 for the table text), owner GATES.
#
#   --record rN   measure the CURRENT build as rung rN and write seed/rungs/rN.record (committed evidence):
#                   - the gate statuses of build/seed/gates/rN/summary.tsv (scripts/seed/gates.sh --rung rN; every row must
#                     be PASS or SKIP, else refused unless --allow-incomplete, which marks the record `incomplete`),
#                   - git HEAD, optional tag, host load average, unity source lines (seed/MANIFEST files) and sha256,
#                     seed-1.bin / seed-2.bin sizes and sha256 (the fixed point), stage-0 sha256,
#                   - compile ms of the 19 Embench ports: median of 3 runs of the PACKAGED seed (build/seed/seed, KEXE_EMBEDDED
#                     loader + seed-1; `compile <port> --target aarch64-macos --output X`, wall time including process start)
#                     and of stage-0 (build/native-image/amu-native, same command), and the code bytes of the port's export.
#   (no option)   regenerate docs/selfhost-seed-rungs-20261002.md from the design ladder (section 1.4) and every
#                 seed/rungs/*.record: rung, features, gates passed, fixed-point sha, lines, compile ms for the 19 ports.
# Rungs without a record are listed as `not started / not recorded`.
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
R=$SEED_REPO; B=$SEED_BUILD; S=$R/scripts/seed
sha() { shasum -a 256 $1 | cut -c1-64; }
now() { perl -MTime::HiRes=time -e 'printf "%.1f", time*1000'; }
if [ "$1" = --record ]; then
  rung=${2:?rung}; shift 2; tag=""; incomplete=0
  while [ $# -gt 0 ]; do case $1 in --tag) tag=$2; shift 2 ;; --allow-incomplete) incomplete=1; shift ;; *) echo "unknown $1" >&2; exit 2 ;; esac; done
  G=$B/gates/$rung/summary.tsv
  [ -s $G ] || { echo "rung-report: no gate summary $G (run scripts/seed/gates.sh --rung $rung)" >&2; exit 2; }
  if awk -F'\t' '$2=="FAIL"' $G | grep -q .; then
    [ $incomplete -eq 1 ] || { echo "rung-report: gates failed for $rung:"; awk -F'\t' '$2=="FAIL"' $G; exit 1; }
  fi
  for k in seed-1.bin seed-2.bin seed-unity.kotoba; do [ -s $B/$k ] || { echo "rung-report: no $B/$k" >&2; exit 2; }; done
  [ -x $B/seed ] || { echo "rung-report: no packaged seed $B/seed (scripts/seed/package.sh 1; gates.sh runs it with G5)" >&2; exit 2; }
  O=$R/seed/rungs/$rung.record; W=$B/rung-$rung; mkdir -p $W
  P=${SEED_PORTS:-$R/bench/embench/ports}
  fp=no; cmp -s $B/seed-1.bin $B/seed-2.bin && fp=yes
  {
    echo "rung $rung"
    echo "date $(date +%Y-%m-%d)"
    echo "head $(git -C $R rev-parse HEAD)"
    echo "tag ${tag:-none}"
    echo "status $([ $incomplete -eq 1 ] && echo incomplete || echo complete)"
    echo "load1 $(sysctl -n vm.loadavg | awk '{print $2}')"
    echo "unity_lines $(wc -l < $B/seed-unity.kotoba | tr -d ' ')"
    echo "build $(awk -F'\t' '$1=="BUILD" && $4 ~ /^reused/ {print "reused"}' $G | head -1)"
    echo "unity_sha256 $(sha $B/seed-unity.kotoba)"
    echo "fixed_point $fp"
    echo "seed1_bytes $(wc -c < $B/seed-1.bin | tr -d ' ')"
    echo "seed1_sha256 $(sha $B/seed-1.bin)"
    echo "seed2_sha256 $(sha $B/seed-2.bin)"
    echo "packaged_seed_sha256 $(sha $B/seed)"
    echo "stage0_sha256 $(sha $SEED_STAGE0)"
    awk -F'\t' '{printf "gate %s %s %s\n", $1, $2, $3}' $G
  } > $O.tmp
  echo '{:allow #{}}' > $W/pol.edn
  for f in $P/*.kotoba; do
    n=${f:t:r}; sym=$(sed -n '1s/.*:export \[[^]]*\(test-[a-z0-9-]*\).*/\1/p' $f)
    ts=(); t0s=()
    for i in 1 2 3; do
      a=$(now); env -i PATH=/nonexistent HOME=$HOME TMPDIR=/tmp $B/seed compile $f --target aarch64-macos --jvm-free --output $W/$n.kseed > $W/$n.log 2>&1 || { echo "rung-report: seed failed on $n: $(head -2 $W/$n.log)" >&2; exit 1; }; b=$(now)
      ts+=($((b-a)))
    done
    for i in 1 2 3; do
      seed_slot_take; a=$(now); ( ulimit -s 65500; nice $SEED_STAGE0 compile $f --target aarch64-macos --jvm-free --policy $W/pol.edn --output $W/$n.s0.kexe > $W/$n.s0.log 2>&1 ); b=$(now); seed_slot_give
      t0s+=($((b-a)))
    done
    x=$(env -i PATH=/nonexistent HOME=$HOME TMPDIR=/tmp $B/seed extract-native $W/$n.kseed --symbol $sym --output $W/$n.bin 2>&1)
    med() { printf '%s\n' $@ | sort -n | sed -n 2p; }
    printf 'port %s %.1f %.1f %d\n' $n $(med $ts) $(med $t0s) $(wc -c < $W/$n.bin) >> $O.tmp
  done
  mv $O.tmp $O
  echo "rung-report: wrote $O ($(grep -c '^port ' $O) ports, fixed_point=$fp)"
  exit 0
fi

# ---- generate the document
python3 - $R <<'PY'
import glob, os, statistics, sys
R = sys.argv[1]
ladder = [
 ('r0', 'Seed-0: 41 heads, 4 types (i64, bool, string, vector-i64), 3 capability wires; stack IR (SIR), depth-indexed temporaries, C runtime calls for vector and string ops', 'G1 19 ports, G2 corpus, G3 refusal texts, G4 fixed point, G5 no host processes'),
 ('r1', 'sugar and enums: do, when, cond, case on i64/keywords, ->/->>, dotimes/doseq, keywords as interned i64, flat records', 'R0 gates + GR (seed/tests/r1: 49 feature programs, 8 typed conformance adaptations, 40 negatives) + G3 golden for r1'),
 ('r2', 'performance, no new language: inline vector/pair access, linear-scan allocation, constant folding, counted-loop fuel prepay', 'R0-R1 gates + Embench medians within 1.5x of the 2026-09-29 reference, code bytes within 1.5x'),
 ('r3', 'values: options/results, try/throw/abort, typed lists, maps and sets, full strings', 'conformance abort/ collections/ stdlib/'),
 ('r4', 'functions: fn, closures, multi-arity, invoke, map/filter/reduce', 'conformance functions/'),
 ('r5', 'modules and effects: ns :require, qualified names, perform/handle, atom/swap!, capability policy', 'conformance namespace_priority/ entry_extensions/ state/ local-state/ reader_target/'),
 ('r6', 'Forms, :document ops, #?(:kotoba ..); the seed compiles the big compiler module by module (convergence point)', 'per-module differentials against the stage-0-built guest'),
 ('r7', '(optional) the seed frontend and backend are amu: full checker rules, CIDs, check/refactor/compile driver', 'rule 11 on the seed lineage'),
]
recs = {}
for p in sorted(glob.glob(os.path.join(R, 'seed/rungs/*.record'))):
    d = {'gates': [], 'ports': []}
    for l in open(p):
        k, _, v = l.rstrip('\n').partition(' ')
        if k == 'gate': d['gates'].append(v.split(' ', 2))
        elif k == 'port':
            n, a, b, c = v.split(' '); d['ports'].append((n, float(a), float(b), int(c)))
        else: d[k] = v
    recs[d['rung']] = d
out = []
w = out.append
w('# Seed rung ladder, measured (generated by scripts/seed/rung-report.sh)\n')
w('Generated from the design ladder (docs/selfhost-seed-design-20261002.md section 1.4) and the committed records `seed/rungs/<rung>.record`, which `scripts/seed/rung-report.sh --record <rung>` writes only after `scripts/seed/gates.sh --rung <rung>` has run (a failing gate refuses the record). Every number below is read from a record; a rung without a record is `not recorded`. Stage-0 is the BOOTSTRAP-REFERENCE (JVM-built native image); seed-N is selfhost-built. Compile ms are the median of 3 wall-clock runs per port, process start included, on the host and load recorded for the rung (the Mac is shared: read the ratios, not the absolute ms).\n')
w('## Ladder\n')
w('| rung | features | gates (required) | status | gates passed | fixed point seed-1 == seed-2 (sha256) | lines (unity source) | compile ms, 19 ports (seed / stage-0 / ratio) |')
w('|---|---|---|---|---|---|---|---|')
for r, feat, gate in ladder:
    d = recs.get(r)
    if not d:
        w('| %s | %s | %s | not recorded | | | | |' % (r.upper(), feat, gate)); continue
    gp = ', '.join('%s %s (%ss)' % (g[0], g[1], g[2]) for g in d['gates'] if g[1] != 'SKIP')
    sk = ', '.join(g[0] for g in d['gates'] if g[1] == 'SKIP')
    ts = sum(p[1] for p in d['ports']); t0 = sum(p[2] for p in d['ports'])
    w('| %s | %s | %s | %s%s | %s%s | %s `%s` | %s | %.0f / %.0f / %.1fx |' % (
        r.upper(), feat, gate, d.get('status', '?'), (', tag `%s`' % d['tag']) if d.get('tag', 'none') != 'none' else '',
        gp, (' ; skipped: ' + sk) if sk else '', 'yes' if d.get('fixed_point') == 'yes' else '**NO**',
        d['seed1_sha256'][:16] + '...', d['unity_lines'], ts, t0, t0 / ts if ts else 0))
w('')
w('## Per-port compile ms and code bytes\n')
rs = [r for r, _, _ in ladder if r in recs]
if rs:
    ports = [p[0] for p in recs[rs[0]]['ports']]
    hdr = '| port | ' + ' | '.join('%s seed ms | %s stage-0 ms | %s code B' % (r.upper(), r.upper(), r.upper()) for r in rs) + ' |'
    w(hdr); w('|---|' + '---|' * (3 * len(rs)))
    for i, n in enumerate(ports):
        cells = []
        for r in rs:
            m = {p[0]: p for p in recs[r]['ports']}.get(n)
            cells += ['%.1f' % m[1], '%.1f' % m[2], str(m[3])] if m else ['', '', '']
        w('| %s | %s |' % (n, ' | '.join(cells)))
    w('')
    for r in rs:
        d = recs[r]
        ps = recs[r]['ports']
        w('- **%s**: seed %.1f-%.1f ms per port, stage-0 %.1f-%.1f ms, ratio %.1f-%.1fx (wall, process start included)%s; head `%s`, %s, load average %s at record time, unity sha256 `%s`, seed-1 sha256 `%s`, seed-2 sha256 `%s`, stage-0 sha256 `%s`, seed-1 %s bytes.' % (
          r.upper(), min(q[1] for q in ps), max(q[1] for q in ps), min(q[2] for q in ps), max(q[2] for q in ps), min(q[2]/q[1] for q in ps), max(q[2]/q[1] for q in ps), ('; the BUILD gate reused build artifacts whose unity sha256 matches the head' if d.get('build') == 'reused' else ''), d['head'][:12], d['date'], d['load1'], d['unity_sha256'][:16] + '...', d['seed1_sha256'], d['seed2_sha256'], d['stage0_sha256'][:16] + '...', d['seed1_bytes']))
else:
    w('No rung is recorded yet (`scripts/seed/gates.sh --rung r0 && scripts/seed/rung-report.sh --record r0`).')
w('')
w('## Gates\n')
w('G1: 19 Embench ports, test-* = 1 under the C loader and kexe-benchmark (fuel 16M), seed-0 and seed-1. G2: seed/tests/corpus equal to stage-0. G3: refusal texts, scripts/seed/g3.sh, golden seed/tests/golden/refusal-<rung>.txt. G4: seed-1.bin == seed-2.bin and seed-0/seed-1 containers byte-identical. G5: no program started by the packaged seed (dyld interpose). GR: rung conformance (scripts/seed/gr.sh), r1 and later. Run all with `scripts/seed/gates.sh --rung rN`; fuel accounting: `scripts/seed/fuel.sh` (docs/selfhost-seed-fuel-20261002.md).')
open(os.path.join(R, 'docs/selfhost-seed-rungs-20261002.md'), 'w').write('\n'.join(out) + '\n')
print('rung-report: wrote docs/selfhost-seed-rungs-20261002.md (%d recorded rungs)' % len(recs))
PY
