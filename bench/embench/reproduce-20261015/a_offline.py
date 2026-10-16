#!/usr/bin/env python3
"""Level (a) OFFLINE: recompute every acceptance decision, every per-workload ratio and the full-19 geometric mean of the
selected round from its raw records, and check every hash. Pure Python 3, no Apple hardware.

  python3 bench/embench/reproduce-20261015/a_offline.py [--round rounds/<name>.json] [--upstream <embench-iot checkout at 09c2ed8c>]
Default round: rounds/sa-m104-20261015.json (the corrected same-algorithm round). The historical m93 round can be checked
explicitly with --round rounds/m93-20261015.json. Round records must use the same layout (records/round, official, fresh-C).

Checks (any failure exits 1):
  1. SHA256SUMS of this package; the collection custody of both arms (every collected file is either vendored here with the
     recorded hash, or listed in records/omitted-files.json with the same hash and a reason; timer images and the timing
     loader must equal images/ and harness/; with --upstream the omitted Embench files are checked too).
  2. Protocol records: protocol revision text, hashed pre-registration (m_w re-derived from its recorded I_w, R_w, fuel and the
     retime rule; P_w(m_w) >= 0.6 s), expected values at n_w = the trusted-reference file, exact timer invocations (n_w, caps).
  3. Every attempt of both arms: CPU qualification (pre-admission raw idle, post raw idle, background idle >= 70 %, recomputed
     from tick counters), exactness (Kotoba: result/fuel/17-counter arena line vs the expected values; C: EMBENCH_NS, empty
     stderr, exit 0), the 0.5 s floor, retry eligibility, first-qualified selection.
  4. Scores (Kotoba baseline/(ms)*8192*m_w, C baseline/(ms)*32768), both reports' geometric means, per-workload
     ratio_w = (4/m_w)*K_ns/C_ns and the full-19 GM, against the selected round's recorded result."""
import argparse, hashlib, json, math, re, statistics, subprocess, sys
from pathlib import Path
PKG = Path(__file__).resolve().parent
REC = PKG / 'records'                      # set from the round config in main()
PUBLISHED_GM = 0.821298642657085
IMAGES, PORTS, IMAGE_TABLE = PKG / 'images', PKG / 'ports', PKG / 'expected/measured-images.json'
CPU_ONLY = {'quiet-admission-timeout', 'raw-post-cpu', 'background-cpu'}
CANONICAL_WORKLOADS = frozenset({
    'aha-mont64', 'crc32', 'depthconv', 'edn', 'huffbench', 'matmult-int', 'md5sum',
    'nettle-aes', 'nettle-sha256', 'nsichneu', 'picojpeg', 'qrduino', 'sglib-combined',
    'slre', 'statemate', 'tarfind', 'ud', 'wikisort', 'xgboost',
})
fails = []


def sha_b(b): return hashlib.sha256(b).hexdigest()
def sha_f(p): return sha_b(Path(p).read_bytes())
def jload(p): return json.loads(Path(p).read_text())
def check(cond, msg):
    if not cond: fails.append(msg); print('FAIL', msg)
    return cond


def cpu(c):
    before, after = c.get('before', {}).get('ticks'), c.get('after', {}).get('ticks')
    valid = (isinstance(before, list) and isinstance(after, list) and len(before) == 4 and len(after) == 4 and
             all(type(v) is int and 0 <= v <= 0xffffffff for v in before + after))
    if not check(valid, 'cpu ticks are four uint32 counters'): return 0.0
    processors = c['before'].get('processors')
    check(type(processors) is int and processors > 0 and c['after'].get('processors') == processors,
          'CPU processor count is positive and stable')
    d = [(b - a) & 0xffffffff for a, b in zip(before, after)]
    if not check(d == c.get('deltaTicks') and sum(d) > 0, 'cpu ticks'): return 0.0
    idle = 100 * d[2] / sum(d); check(abs(idle - c['idlePercent']) < 1e-9, 'idle percent recomputation')
    ns = c['after']['monotonicNs'] - c['before']['monotonicNs']; check(ns == c['envelopeNs'] and ns > 0, 'cpu envelope')
    return idle


def package_sums():
    sums = (PKG / 'SHA256SUMS').read_text().splitlines(); n = 0
    for line in sums:
        h, rel = line.split('  ', 1); p = PKG / rel; n += 1
        check(p.is_file() and sha_f(p) == h, 'SHA256SUMS ' + rel)
    listed = {l.split('  ', 1)[1] for l in sums}
    present = {str(p.relative_to(PKG)) for p in PKG.rglob('*') if p.is_file() and p.name != 'SHA256SUMS' and '__pycache__' not in p.parts}
    check(listed == present, 'SHA256SUMS lists exactly the package files (extra=%s missing=%s)' % (sorted(present - listed)[:5], sorted(listed - present)[:5]))
    return n


def custody(arm, upstream):
    D = REC / arm; rec = jload(D / 'collection-custody.json'); om = {r['path']: r for r in jload(REC / 'omitted-files.json')[arm]}
    images = {p.stem: sha_f(p) for p in IMAGES.glob('*.bin')}; vend = present = 0
    for row in rec['files']:
        rel = row['path'][len('results/'):] if row['path'].startswith('results/') else row['path']; p = D / rel
        if p.is_file():
            vend += check(sha_f(p) == row['sha256'] and p.stat().st_size == row['bytes'], 'custody %s %s' % (arm, rel)); continue
        o = om.get(rel); check(o is not None and o['sha256'] == row['sha256'], 'omitted file recorded %s %s' % (arm, rel))
        if rel.endswith('/image.bin'): check(images.get(rel.split('/')[1]) == row['sha256'], 'timer image == images/ ' + rel)
        if rel.endswith('/separated-loader.c'): check(sha_f(PKG / 'harness/separated-loader.c') == row['sha256'], 'timer loader == harness ' + rel)
        if upstream and rel.startswith('upstream/'):
            upstream_rel = rel[len('upstream/'):]
            tracked = subprocess.run(['git', '-C', str(upstream), 'ls-files', '--error-unmatch', '--', upstream_rel],
                                     capture_output=True, text=True)
            if tracked.returncode == 0:
                present += check(sha_f(Path(upstream) / upstream_rel) == row['sha256'], 'upstream file ' + rel)
            else:
                generated_cache = '__pycache__' in Path(upstream_rel).parts and upstream_rel.endswith('.pyc')
                check(tracked.returncode == 1 and generated_cache and o is not None and
                      o.get('reason') == 'Generated Python bytecode in the captured upstream checkout; not tracked Embench source',
                      'untracked upstream artifact classification ' + rel)
    return dict(files=len(rec['files']), vendoredVerified=vend, upstreamVerified=present)


CEILING = {'heap': 64 * 1024 * 1024, 'string-pool': 1024 * 1024 * 1024, 'vectors': 64 * 1024 * 1024, 'vector-items': 128 * 1024 * 1024}
ENV = {'heap': 'KEXE_PAIRS', 'string-pool': 'KEXE_STRING_POOL', 'vectors': 'KEXE_VECTORS', 'vector-items': 'KEXE_VECTOR_ITEMS'}


def caps_plan(caps1, m):
    """The pre-registration cap rule with the trusted loader's ceilings (None if m is infeasible)."""
    plan = {}
    for res, env in ENV.items():
        need = caps1[res]['used'] * m
        if need > CEILING[res]: return None
        if need > caps1[res]['capacity']: plan[env] = str(min(caps1[res]['capacity'] * m, CEILING[res]))
    return plan


def preregistration(screen_at_max=None):
    """Re-derive every m_w from the recorded I_w, R_w, fuel, m=1 capacities and prior attempts: feasibility = fuel bound and
    loader ceilings; m_w = smallest feasible m with P_w(m) >= target (else the largest feasible); retime rule = next feasible m
    whose (image, n) was not executed on Joseph, or (Amendment 3) keep m when none exists; screen P_w(m_w) >= rule.screen."""
    pre = REC / 'round/preregistration.json'; h = sha_f(pre)
    check((REC / 'round/preregistration.sha256').read_text().split()[0] == h, 'preregistration.sha256')
    reg = jload(pre); FUEL_LIMIT = int(0.9 * 2 ** 35); out = {}; rule = reg['rule']; target = rule.get('target', 1.0); screen = rule['screen']
    timed = {(a['imageSHA256'], a['n']) for a in reg.get('priorJosephAttempts', []) if 'n' in a}
    for x in reg['workloads']:
        P = lambda m: x['I'] * m / x['R']
        feas = [m for m in (1, 2, 4, 8, 16) if m * x['fuelM1'] <= FUEL_LIMIT and caps_plan(x['capacitiesM1'], m) is not None]
        if 'feasibleMultipliers' in x: check(feas == x['feasibleMultipliers'], 'feasible multipliers ' + x['workload'])
        mT = next((m for m in feas if P(m) >= target), None); m0 = mT if mT is not None else max(feas)
        if x.get('retimeRuleApplied'):
            nxt = [f for f in feas if f > m0 and (x['candidateNativeSHA256'], x['n1'] * f) not in timed]; m = nxt[0] if nxt else None
        else: m = m0
        if x.get('retimeForcedAmendment3'): check(m == m0 and not [f for f in feas if f > m0 and (x['candidateNativeSHA256'], x['n1'] * f) not in timed], 'Amendment 3 only where m is forced ' + x['workload'])
        check(m0 == x['multiplierBeforeRetimeRule'] and m == x['multiplier'] and x['n'] == x['n1'] * m, 'pre-registered m_w ' + x['workload'])
        check(caps_plan(x['capacitiesM1'], m) == x['extraCapsPlanned'], 'pre-registered caps ' + x['workload'])
        thr = screen_at_max if (screen_at_max is not None and m == max(feas)) else screen   # Amendment 4: at the maximum feasible m
        check(P(m) >= thr and abs(P(m) - x['projectedJosephSeconds']) < 1e-9, 'screen P_w(m_w) >= %.2f s %s' % (thr, x['workload']))
        out[x['workload']] = x
    return h, reg, out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--upstream', type=Path, help='optional Embench checkout at 09c2ed8c to verify the omitted upstream files')
    ap.add_argument('--round', help='round config (default rounds/sa-m104-20261015.json)')
    a = ap.parse_args()
    global REC, PUBLISHED_GM, IMAGES, PORTS, IMAGE_TABLE
    rnd = json.loads(((PKG / a.round) if a.round and not Path(a.round).is_absolute() and not Path(a.round).exists() else Path(a.round or PKG / 'rounds/sa-m104-20261015.json')).read_text())
    REC, PUBLISHED_GM = PKG / rnd['records'], rnd['publishedGM']
    IMAGES, PORTS, IMAGE_TABLE = PKG / rnd['images'], PKG / rnd['ports'], PKG / rnd['pins']['imageTable']
    nsums = package_sums()
    cust = {arm: custody(arm, a.upstream) for arm in ['official', 'fresh-C']}
    pre_sha, reg, REG = preregistration(rnd.get('screenAtMaximumFeasible'))
    # the harness used by levels (c)/(d) is exactly what the round ran
    same_table = [(rnd['workloads'], 'official/workloads.json')] if not rnd.get('multipliers') else []  # override rounds: checked via the pre-registration
    for h, r in same_table + [('harness/kotoba/run_trigger.py', 'official/run_trigger.py'),
                 ('harness/c/run_trigger.py', 'fresh-C/run_trigger.py'), ('harness/darwin_cpu_idle.py', 'official/darwin_cpu_idle.py'),
                 ('harness/darwin_cpu_idle.py', 'fresh-C/darwin_cpu_idle.py')]:
        check((PKG / h).read_bytes() == (REC / r).read_bytes(), 'harness file == round file: ' + h)
    for t in sorted((REC / 'official/timers').iterdir()):
        for f in ['timing-extension.h', 'timing-frontend.h']: check((PKG / 'harness' / f).read_bytes() == (t / f).read_bytes(), 'timing header == round file: %s/%s' % (t.name, f))
    official_workloads = {e['workload'] for e in jload(REC / 'official/workloads.json')}
    image_workloads = set(jload(IMAGE_TABLE))
    configured_raw = jload(PKG / rnd['workloads'])
    configured_workloads = set(configured_raw) if isinstance(configured_raw, dict) else {e['workload'] for e in configured_raw}
    check(official_workloads == CANONICAL_WORKLOADS, 'official workload table is the canonical 19')
    check(image_workloads == CANONICAL_WORKLOADS, 'image table is the canonical 19')
    check(configured_workloads == CANONICAL_WORKLOADS, 'round workload table is the canonical 19')
    check(image_workloads == official_workloads, 'image table covers all official workloads')
    for w, e in jload(IMAGE_TABLE).items():
        check(sha_f(IMAGES / (w + '.bin')) == e['native']['sha256'] and sha_f(IMAGES / (w + '.kseed')) == e['kseed']['sha256'], 'images/ == measured image ' + w)
        check(sha_f(PORTS / ('official-' + w + '.kotoba')) == e['sourceSHA256'], 'ports/ == measured source ' + w)
    proto = (REC / 'round/protocol-revision.txt').read_text()
    N = jload(REC / 'official/report.json'); C = jload(REC / 'fresh-C/report.json')
    check(N['status'] == 'COMPLETE_EXPLORATORY_TRANSLATED_PORT_DRIVER_FORMULA' and N.get('full19') is True, 'Kotoba report complete')
    check(C['status'] == 'COMPLETE_EXPLORATORY_ORIGINAL_C19_SPEED_DRIVER' and C.get('full19') is True, 'C report complete')
    check(N['protocolRevision'] == proto and N['preregistrationSHA256'] == pre_sha and proto.startswith(reg['protocolRevision']), 'protocol revision (pre-registered text + later amendments) + pre-registration hash in the campaign report')
    check(N['multipliers'] == {w: x['multiplier'] for w, x in REG.items()}, 'report multipliers == pre-registration')
    check(N['GSF'] == 8192 and C['globalScaleFactor'] == 32768 and N['fuel'] == 2 ** 35, 'GSF / fuel')
    for r in (N, C):
        check(r['samplesPerWorkload'] == 1 and r['maxActualAttemptsPerWorkload'] == 3 and r['cpuOnlyRetries'] and r['selectionPolicy'] == 'FIRST_CPU_QUALIFIED_NOT_FASTEST', 'protocol fields')
    E = {e['workload']: e for e in jload(REC / 'official/expected-original-accounting.json')}
    ref = jload(REC / 'round/reference-accounting-receipt.json')
    check(sha_f(REC / 'round/expected-accounting-mw.json') == ref['expectedAccounting']['sha256'] and ref['candidateUsed'] is False, 'expected values = trusted-reference file')
    check((REC / 'official/expected-original-accounting.json').read_bytes() == (REC / 'round/expected-accounting-mw.json').read_bytes(), 'campaign expected file == reference file')
    W = {e['workload']: e for e in jload(REC / 'official/workloads.json')}
    root = jload(REC / 'round/official-root-packet-pin.json')['root']
    for w, e in W.items():
        m = e['multiplier']; check(m == REG[w]['multiplier'] and e['n'] == e['LSF'] * 8192 * m == E[w]['n'] and e['extraCaps'] == REG[w]['extraCapsPlanned'], 'workload table ' + w)
        caps = dict(KEXE_FUEL='34359738368', KEXE_STRUCTURED_REPORT='1', KEXE_ARENA_USE='1', KEXE_CPU_SECONDS='1800', KEXE_WALL_SECONDS='1800')
        if w == 'aha-mont64': caps.update(KEXE_VECTORS='67108864', KEXE_VECTOR_ITEMS='134217728')
        if w == 'qrduino': caps.update(KEXE_PAIRS='65536')
        if w == 'slre': caps.update(KEXE_PAIRS='8388608')
        caps.update(e['extraCaps'])
        import shlex
        inv = (REC / 'official/measured/src' / w / w).read_text()
        check(inv == '#!/bin/sh\nexec env ' + ' '.join(shlex.quote(k + '=' + v) for k, v in caps.items()) + ' ' + shlex.quote(root + '/timers/' + w + '/timer') + ' ' + str(e['n']) + '\n', 'timer invocation (n_w, caps) ' + w)
    baseline = jload(REC / 'official/upstream/baseline-data/speed.json')
    check((REC / 'official/upstream/baseline-data/speed.json').read_bytes() == (REC / 'fresh-C/upstream/baseline-data/speed.json').read_bytes(), 'same Embench baseline in both arms')
    rows = {}
    for arm, gsf, report in [('official', 8192, N), ('fresh-C', 32768, C)]:
        raw_dir = REC / arm / 'measured/raw'; rows[arm] = {}
        for w in sorted(W):
            raw = jload(raw_dir / (w + '.json')); samples = raw['samples']
            check(1 <= len(samples) <= 3 and raw['maxAttempts'] == 3 and raw['selectionPolicy'] == 'FIRST_CPU_QUALIFIED_NOT_FASTEST', 'raw header %s %s' % (arm, w))
            recs = []
            for i, s in enumerate(samples):
                quiet = jload(raw_dir / ('%s-quiet-%d.json' % (w, i))); probes = quiet['probes']; pre = cpu(probes[-1]['cpuActivity']) if probes else None
                if s.get('executed', True) is False:
                    check(not quiet['ready'] and s['reasons'] == ['quiet-admission-timeout'] and s['retryEligible'], 'unexecuted attempt'); recs.append(dict(accepted=False, reasons=s['reasons'])); continue
                check(quiet['ready'] and probes[-1]['quiet'] and pre >= 70, 'pre-admission idle >= 70 %s %s' % (arm, w))
                post = cpu(s['cpuActivity']); c = s['cpuActivity']
                processors = c['before'].get('processors', 0)
                check(c.get('logicalCpuCount') == processors and processors > 0, 'logical CPU count == raw processor count')
                bg = min(100, post + 100 * c['childCpuNs'] / (c['envelopeNs'] * processors)) if processors > 0 else 0
                check(abs(bg - c['estimatedBackgroundIdlePercent']) < 1e-9, 'background idle')
                ns = s['elapsedNs']; reasons = []
                if arm == 'official':
                    try: sample = json.loads(s['stdout'].splitlines()[-1])
                    except (ValueError, IndexError): sample = None
                    f = re.search(r':status :ok :result 1 .*:fuel \{:initial (\d+) :remaining (\d+)\}', s['stdout'])
                    ok = (s['returncode'] == 0 and sample and {k: v for k, v in sample.items() if k != 'elapsedNs'} == E[w]['expectedSample'] and s['stderr'] == E[w]['expectedStderr']
                          and f and int(f[1]) == 2 ** 35 and int(f[1]) - int(f[2]) == sample['benchmarkFuel'] + sample['verifyFuel'] and sample['elapsedNs'] == ns)
                else:
                    mm = re.fullmatch(r'EMBENCH_NS=(\d+)\n', s['stdout']); ok = not s['returncode'] and not s['stderr'] and mm is not None and int(mm[1]) == ns
                if not ok: reasons.append('execution-or-verification')
                if not isinstance(ns, int) or ns < 500000000: reasons.append('short-interval')
                if post < 70: reasons.append('raw-post-cpu')
                if bg < 70: reasons.append('background-cpu')
                check(s['accepted'] == (not reasons) and s['reasons'] == reasons and s['retryEligible'] == (bool(reasons) and set(reasons) <= CPU_ONLY), 'acceptance %s %s attempt %d' % (arm, w, i))
                recs.append(dict(accepted=not reasons, reasons=reasons, elapsedNs=ns, exact=ok, pre=pre, post=post, bg=bg))
            acc = [i for i, r in enumerate(recs) if r['accepted']]
            check(len(acc) == 1 and acc[0] == len(recs) - 1 and raw['selectedAttempt'] == acc[0] and all(set(r['reasons']) <= CPU_ONLY for r in recs[:-1]), 'first-qualified selection %s %s' % (arm, w))
            sel = recs[acc[0]] if acc else None
            mult = W[w]['multiplier'] if arm == 'official' else 1
            score = baseline[w] / (sel['elapsedNs'] / 1e6) * gsf * mult if sel else None
            if sel: check(abs(score - report['relativeSpeeds'][w]) < 1e-8 * score, 'relative speed %s %s' % (arm, w))
            rows[arm][w] = dict(selected=sel, attempts=len(recs), score=score)
        gm = math.exp(statistics.mean(math.log(r['score']) for r in rows[arm].values()))
        check(abs(gm - report['speedGeometricMean']) < 1e-8 * gm, 'speed GM %s' % arm); rows[arm]['_gm'] = gm
    ratios = {w: (4 / W[w]['multiplier']) * rows['official'][w]['selected']['elapsedNs'] / rows['fresh-C'][w]['selected']['elapsedNs'] for w in W}
    gm = math.exp(statistics.mean(math.log(v) for v in ratios.values()))
    check(abs(gm - rows['fresh-C']['_gm'] / rows['official']['_gm']) < 1e-12, 'GM of ratios == C GM / Kotoba GM')
    check(abs(gm - PUBLISHED_GM) < 1e-12, 'published GM %r' % PUBLISHED_GM)
    fs = jload(REC / 'round/final-summary.json'); check(abs(fs['KotobaElapsedDividedByC'] - gm) < 1e-12, 'final-summary GM')
    for p in fs['perWorkload']: check(abs(p['KotobaElapsedDividedByC'] - ratios[p['workload']]) < 1e-12, 'final-summary ratio ' + p['workload'])
    print('%-15s %3s %10s %10s %8s %5s' % ('workload', 'm_w', 'K_ns', 'C_ns', 'ratio', 'tries'))
    for w in sorted(W):
        print('%-15s %3d %10d %10d %8.4f %2d/%d' % (w, W[w]['multiplier'], rows['official'][w]['selected']['elapsedNs'], rows['fresh-C'][w]['selected']['elapsedNs'], ratios[w], rows['official'][w]['attempts'], rows['fresh-C'][w]['attempts']))
    out = dict(level='a-offline', packageFilesVerified=nsums, custody=cust, preregistrationSHA256=pre_sha, kotobaGM=rows['official']['_gm'], cGM=rows['fresh-C']['_gm'],
               ratioGM=gm, ratios=ratios, failures=fails, status='PASS' if not fails else 'FAIL')
    print(json.dumps({k: v for k, v in out.items() if k != 'ratios'}, indent=1))
    print('LEVEL_A', out['status'], 'GM %.16g' % gm)
    sys.exit(0 if not fails else 1)


if __name__ == '__main__':
    main()
