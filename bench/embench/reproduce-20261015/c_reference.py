#!/usr/bin/env python3
"""Level (c), part 2: RE-DERIVE the expected exactness values at every n_w from the TRUSTED reference images, never from the
candidate, and compare them with records/round/expected-accounting-mw.json.

  python3 bench/embench/reproduce-20261015/c_reference.py --out <new-dir> [--round rounds/<name>.json] [--write <file>]
                                                         [--jobs 3] [--only w1,w2]
For a new round (its own multiplier table) --write produces the round's expected-values file (same schema as
records/round/expected-accounting-mw.json); for a round that has one, the derived values are compared with it.

References (reference/, with their export tables in reference/reference-images.json):
  round51  : the original translated ports compiled by the qualified WM G4 fixed point. Their round51 raw records are where
             expected-original-accounting.json (the m=1 values, reference/expected-original-accounting-m1.json) came from.
  round114 : the round114 adopted images (an independent compiler), as a cross-check.
Both run in the same timer harness as the measurement. Per workload, round51 runs at m in {1, 2, m_w/2, m_w} (plus 3 when
m_w = 2) and round114 at {1, m_w}. Required: both references reproduce the m=1 values byte for byte, agree with each other at
n_w, and the round51 values at n_w equal the published expected values. The report also shows that fuel and the 17 arena
counters are exactly affine in n (only tarfind's benchmarkFuel deviates, by a few thousand units out of 7.8e9, from its
data-dependent warm-seeded work; its value at n_w is measured, not extrapolated). Takes ~10-30 minutes."""
import argparse, json, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, str(Path(__file__).resolve().parent / 'tools'))
import repro_lib as R


def points(m): return sorted({1} if m == 1 else ({1, 2, m // 2, m} | ({3} if m == 2 else set())))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True, type=Path); ap.add_argument('--jobs', type=int, default=3); ap.add_argument('--only')
    ap.add_argument('--round', help='round config (default rounds/sa-m104-20261015.json)'); ap.add_argument('--write', type=Path)
    a = ap.parse_args(); R.require_macos_arm64(); out = R.fresh_dir(a.out)
    rnd = R.load_round(a.round); W = R.round_workloads(rnd); exp_p = R.round_path(rnd, 'expectedAccounting')
    E = {e['workload']: e for e in json.loads(exp_p.read_text())} if exp_p else None
    E1 = {e['workload']: e for e in R.load('reference/expected-original-accounting-m1.json')}; ref = R.load('reference/reference-images.json')
    names = a.only.split(',') if a.only else sorted(W); jobs = []
    for w in names:
        for which in ['round51', 'round114']:
            meta = ref[which][w]; img = (R.PKG / 'reference' / which / (w + '.bin')).read_bytes(); assert R.sha(img) == meta['native']['sha256'], (which, w)
            t = R.build_timer(out / which / w, R.PKG / 'harness', img, meta['exports'], meta)
            for m in (points(W[w]['multiplier']) if which == 'round51' else sorted({1, W[w]['multiplier']})):
                jobs.append((w, which, m, t, R.caps_for(w, W[w]['extraCaps']), E1[w]['n'] * m))
    def go(j):
        w, which, m, t, caps, n = j; r = R.run_timer(t, n, caps)
        print('%-15s %-8s m=%-2d ok=%s' % (w, which, m, r['returncode'] == 0 and r['fuelConsistent']), flush=True)
        return (w, which, m), r
    with ThreadPoolExecutor(a.jobs) as ex: res = dict(ex.map(go, jobs))
    strip = lambda s: {k: v for k, v in s.items() if k != 'elapsedNs'}
    table = []; fails = []; derived = []
    for w in names:
        m = W[w]['multiplier']
        for (ww, which, mm), r in res.items():
            if ww == w and mm == 1 and not R.exact(r, E1[w]): fails.append('%s %s does not reproduce the m=1 values' % (which, w))
            if ww == w and not (r['returncode'] == 0 and r['fuelConsistent']): fails.append('%s %s m=%d failed: %s' % (which, w, mm, r['stderr'].strip()[-200:]))
        a51, a114 = res[(w, 'round51', m)], res[(w, 'round114', m)]
        if not all(res[(w, wh, mm)]['sample'] for (ww, wh, mm) in res if ww == w):
            table.append(dict(workload=w, multiplier=m, failed=True)); print('%-15s m_w %2d reference run failed (see report)' % (w, m), flush=True); continue
        agree = strip(a51['sample']) == strip(a114['sample']) and a51['stderr'] == a114['stderr']
        matches = (strip(a51['sample']) == E[w]['expectedSample'] and a51['stderr'] == E[w]['expectedStderr'] and E[w]['n'] == W[w]['n']) if E else None
        if not agree: fails.append('references disagree at n_w: ' + w)
        if matches is False: fails.append('derived values differ from the published expected values: ' + w)
        derived.append(dict(workload=w, n=W[w]['n'], LSF=W[w]['LSF'], multiplier=m, expectedSample=strip(a51['sample']), expectedStderr=a51['stderr'],
                            derivation='round51 WM-G4 original image at n=LSF*8192*m_w (c_reference.py); round114 image agrees; both reproduce the m=1 values'))
        series = {mm: dict({k: res[(w, 'round51', mm)]['sample'][k] for k in ['benchmarkFuel', 'verifyFuel', 'result']},
                           **{k: int(v) for k, v in __import__('re').findall(r':([a-z-]+) (\d+)', res[(w, 'round51', mm)]['stderr'])}) for mm in points(m)}
        lin = {}
        pts = points(m)
        if len(pts) >= 2:
            for k in series[pts[0]]:
                d = series[pts[1]][k] - series[pts[0]][k]; slope = d // (pts[1] - pts[0]) if d % (pts[1] - pts[0]) == 0 else None
                lin[k] = slope is not None and all(series[x][k] == series[pts[0]][k] + (x - pts[0]) * slope for x in pts)
        table.append(dict(workload=w, multiplier=m, points=pts, referencesAgreeAtNw=agree, equalsPublishedExpected=matches,
                          nonAffineFields=[k for k, v in lin.items() if not v], fuelAtNw=a51['sample']['benchmarkFuel'] + a51['sample']['verifyFuel']))
        unexpected_non_affine = sorted(set(table[-1]['nonAffineFields']) - ({'benchmarkFuel'} if w == 'tarfind' else set()))
        if unexpected_non_affine:
            fails.append('%s has unexpected non-affine accounting fields: %s' % (w, ', '.join(unexpected_non_affine)))
        print('%-15s m_w %2d points %-14s agree=%s published=%s nonAffine=%s' % (w, m, pts, agree, matches, table[-1]['nonAffineFields']), flush=True)
    status = 'PASS' if not fails else 'FAIL'
    if a.write and not fails:
        a.write.parent.mkdir(parents=True, exist_ok=True); a.write.write_text(json.dumps(derived, indent=1) + '\n'); print('wrote', a.write)
    (out / 'report.json').write_text(json.dumps(dict(level='c-reference', round=rnd['round'], table=table, failures=fails, status=status), indent=1) + '\n')
    print('LEVEL_C_REFERENCE', status, fails[:5])
    sys.exit(0 if status == 'PASS' else 1)


if __name__ == '__main__':
    main()
