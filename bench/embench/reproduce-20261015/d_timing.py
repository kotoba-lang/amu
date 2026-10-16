#!/usr/bin/env python3
"""Level (d) TIMING: a same-host Kotoba + C campaign under the round's protocol, producing the full-19 geometric mean of
ratio_w = (4/m_w) * K_ns / C_ns on YOUR machine.

  python3 bench/embench/reproduce-20261015/tools/fetch_upstream.py --dest <upstream-dir>
  python3 bench/embench/reproduce-20261015/d_timing.py --upstream <upstream-dir> --out <new-dir> [--round rounds/<name>.json]
                                                       [--images <dir>] [--workloads w1,w2]

Protocol (the official harness files, unchanged): the upstream Embench driver benchmark_speed.py with the target module
harness/kotoba/run_trigger.py (Kotoba, GSF 8192, n_w = LSF*8192*m_w) and harness/c/run_trigger.py (C, GSF 32768); warm-up 1,
sample 1; CPU admission: raw host idle >= 70 % before, raw idle and estimated background idle >= 70 % over the run; at most
3 attempts, retries only for CPU reasons; the first qualified attempt is selected (never the fastest); 0.5 s floor;
Kotoba exactness against the expected values at n_w. Kotoba campaign first, then C, in one session. No subset GM: a GM is
printed only when all 38 runs are accepted.

C binaries are built here from upstream with c/build_c.py (your clang), or pass --c-binaries <dir>. Kotoba images default to
images/ (or pass --images <b_build out>/step4-images).
EXPECTED SPREAD: the published 0.79988 is one cycle on one Apple M4 host under its load. Other hosts, clang versions,
background load and thermal state change both arms; expect a different GM, and per-workload ratios can move by 10 % or more."""
import argparse, json, math, os, shutil, statistics, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'tools'))
import repro_lib as R


def other_benchmark_processes(root):
    q = subprocess.run(['/bin/ps', '-axo', 'pid=,command='], capture_output=True, text=True, check=True)
    me = os.getpid()
    return [l.strip() for l in q.stdout.splitlines() if str(root) + '/' in l and ('/timer' in l or 'benchmark_speed.py' in l or '/results/measured/src/' in l)
            and not l.strip().startswith(str(me) + ' ')]


def setup_root(root, upstream, trigger):
    root.mkdir()
    shutil.copytree(upstream, root / 'upstream', ignore=shutil.ignore_patterns('.git'))
    shutil.copyfile(trigger, root / 'run_trigger.py'); shutil.copyfile(R.PKG / 'harness/darwin_cpu_idle.py', root / 'darwin_cpu_idle.py')
    (root / 'results/measured/src').mkdir(parents=True)


def drive(root, gsf):
    up = root / 'upstream'
    cmd = [sys.executable, str(up / 'benchmark_speed.py'), '--builddir', str(root / 'results/measured'), '--logdir', str(root / 'results/official-logs'),
           '--target-module', 'run_trigger', '--gsf', str(gsf), '--json-output', '--samples', '1']
    q = subprocess.run(cmd, env=dict(os.environ, PYTHONPATH=str(root)), cwd=up, capture_output=True, text=True, timeout=7200)
    (root / 'results/official.stdout').write_text(q.stdout); (root / 'results/official.stderr').write_text(q.stderr)
    return dict(driverExit=q.returncode, driverCommand=[str(c).replace(str(root), '<root>') for c in cmd])


def collect(root, names, gsf, mult, baseline):
    rows = {}
    for w in names:
        f = root / 'results/measured/raw' / (w + '.json')
        if not f.exists(): rows[w] = dict(accepted=False, reasons=['not-run (driver stopped)']); continue
        raw = json.loads(f.read_text()); sel = raw['selectedAttempt']
        s = raw['samples'][sel] if sel is not None else None
        rows[w] = dict(accepted=sel is not None, attempts=len(raw['samples']), reasons=[x['reasons'] for x in raw['samples']],
                       elapsedNs=s['elapsedNs'] if s else None, score=baseline[w] / (s['elapsedNs'] / 1e6) * gsf * mult.get(w, 1) if s else None)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--upstream', required=True, type=Path); ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--images', type=Path); ap.add_argument('--c-binaries', type=Path); ap.add_argument('--workloads')
    ap.add_argument('--round', help='round config (default rounds/m93-20261015.json)')
    a = ap.parse_args(); R.require_macos_arm64()
    subprocess.run([sys.executable, str(R.PKG / 'tools/fetch_upstream.py'), '--dest', str(a.upstream), '--verify-only'], check=True)
    out = R.fresh_dir(a.out); up = a.upstream.resolve()
    rnd = R.load_round(a.round); W = R.round_workloads(rnd); names = a.workloads.split(',') if a.workloads else sorted(W)
    images = a.images or R.PKG / rnd['images']; exp_p = R.round_path(rnd, 'expectedAccounting')
    if not exp_p: raise SystemExit('this round has no expected values yet: derive them with c_reference.py --round ... --write <file>')
    image_table_p = R.round_path(rnd, 'imageTable')
    if not image_table_p: raise SystemExit('this round has no pinned image table')
    image_table = json.loads(image_table_p.read_text())
    if len(names) != len(set(names)) or set(names) - set(W): raise SystemExit('workloads must be unique names in the selected round')
    image_inputs = {}
    for w in names:
        if w not in image_table: raise SystemExit('no pinned image for workload: ' + w)
        candidates = [Path(images) / (w + '.kseed'), Path(images) / ('official-' + w + '.kseed')]
        kseed = next((p for p in candidates if p.is_file()), None)
        if kseed is None: raise SystemExit('missing Kotoba image for workload: ' + w)
        kseed_bytes = kseed.read_bytes()
        try: exports, image = R.kseed_parts(kseed_bytes)
        except (UnicodeDecodeError, ValueError) as exc: raise SystemExit('invalid kseed for %s: %s' % (w, exc))
        pin = image_table[w]
        if (R.sha(kseed_bytes) != pin['kseed']['sha256'] or R.sha(image) != pin['native']['sha256']
                or exports != pin['exports']):
            raise SystemExit('Kotoba image does not match the selected round pins: ' + w)
        image_inputs[w] = (kseed, image, exports)
    baseline = json.loads((up / 'baseline-data/speed.json').read_text()); mult = {w: W[w]['multiplier'] for w in W}
    report = dict(level='d-timing', round=rnd['round'], started=time.time(), workloads=names, full19=len(names) == 19, protocol='round 2026-10-15 m93 (see README)')
    def save(): (out / 'report.json').write_text(json.dumps(report, indent=1) + '\n')
    # C binaries
    cdir = a.c_binaries
    if cdir is None:
        subprocess.run([sys.executable, str(R.PKG / 'c/build_c.py'), '--upstream', str(up), '--out', str(out / 'c-build')], check=True); cdir = out / 'c-build'
    # ---- Kotoba arm
    K = out / 'kotoba'; setup_root(K, up, R.PKG / 'harness/kotoba/run_trigger.py')
    shutil.copyfile(exp_p, K / 'expected-original-accounting.json')
    for w in names:
        e = W[w]; _, image, exports = image_inputs[w]
        timer = R.build_timer(K / 'timers' / w, R.PKG / 'harness', image, exports, e)
        caps = R.caps_for(w, e['extraCaps']); d = K / 'results/measured/src' / w; d.mkdir()
        import shlex
        (d / w).write_text('#!/bin/sh\nexec env ' + ' '.join(shlex.quote(k + '=' + v) for k, v in caps.items()) + ' ' + shlex.quote(str(timer)) + ' ' + str(e['n']) + '\n'); (d / w).chmod(0o755)
    assert not other_benchmark_processes(out), 'other benchmark processes are running under this output root'
    report['kotoba'] = drive(K, 8192); report['kotoba']['rows'] = collect(K, names, 8192, mult, baseline); save()
    # ---- C arm (same session, after Kotoba)
    Cr = out / 'c'; setup_root(Cr, up, R.PKG / 'harness/c/run_trigger.py')
    for w in names:
        d = Cr / 'results/measured/src' / w; d.mkdir(); shutil.copyfile(Path(cdir) / w / w, d / w); (d / w).chmod(0o755)
    report['c'] = drive(Cr, 32768); report['c']['rows'] = collect(Cr, names, 32768, {}, baseline); save()
    kr, cr = report['kotoba']['rows'], report['c']['rows']
    ratios = {w: (4 / mult[w]) * kr[w]['elapsedNs'] / cr[w]['elapsedNs'] for w in names if kr[w]['accepted'] and cr[w]['accepted']}
    all38 = report['full19'] and len(ratios) == 19
    report.update(ratios=ratios, acceptedKotoba=sum(r['accepted'] for r in kr.values()), acceptedC=sum(r['accepted'] for r in cr.values()),
                  geometricMean=math.exp(statistics.mean(math.log(v) for v in ratios.values())) if all38 else None,
                  note=None if all38 else 'NOT A FULL-19 RESULT: no geometric mean (no subset GM by protocol)', ended=time.time())
    save()
    for w in names:
        print('%-15s m_w %2d  Kotoba %s  C %s  ratio %s' % (w, mult[w], kr[w].get('elapsedNs') or kr[w]['reasons'], cr[w].get('elapsedNs') or cr[w]['reasons'],
              ('%.4f' % ratios[w]) if w in ratios else '-'))
    print('LEVEL_D', 'GM %.4f' % report['geometricMean'] if all38 else report['note'], 'accepted Kotoba %d/%d C %d/%d' % (report['acceptedKotoba'], len(names), report['acceptedC'], len(names)))


if __name__ == '__main__':
    main()
