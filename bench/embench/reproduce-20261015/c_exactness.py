#!/usr/bin/env python3
"""Level (c) EXACTNESS: run each of the 19 measured images at its pre-registered n_w = LSF*8192*m_w with the official caps and
check result, fuel and the 17-counter arena line against the expected values (records/round/expected-accounting-mw.json,
re-derivable from the trusted reference images with c_reference.py). Elapsed times are printed but are NOT results.

  python3 bench/embench/reproduce-20261015/c_exactness.py --out <new-dir> [--images <dir>] [--only w1,w2] [--count-instructions]

--images: default images/ of this package (the measured images); pass <b_build out>/step4-images to test the images you
          rebuilt yourself with G* (files official-<w>.kseed).
--count-instructions: also re-count the candidate's timed-interval instructions at m=1 (the I_w of the pre-registration;
          proc_pid_rusage ri_instructions around the timed call, the instrumentation of tools/mktimer.py) and compare with
          the pre-registered values (typically within 0.1-0.8 %, more under heavy load; the check allows 2 %).
The timer is harness/separated-loader.c (= seed/bootstrap/adopted-loader-20261012.c + harness/separated-loader.diff, checked
here) with harness/timing-extension.h, harness/timing-frontend.h and a generated timing-packet-generated.h."""
import argparse, json, shutil, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'tools'))
import repro_lib as R

DIAG_PATCHES = [  # identical to the instruction-counting instrumentation of tools/mktimer.py (validate.py instr=)
    ('#include <dlfcn.h>', '#include <dlfcn.h>\n#include <libproc.h>\nstatic void diag_ic(uint64_t*i,uint64_t*c){struct rusage_info_v4 r;if(proc_pid_rusage(getpid(),RUSAGE_INFO_V4,(rusage_info_t*)&r)){*i=*c=0;return;}*i=r.ri_instructions;*c=r.ri_cycles;}'),
    ('uint64_t initial=s->context.fuel,begin=timing_now();', 'uint64_t di0,dc0,di1,dc1;diag_ic(&di0,&dc0);uint64_t initial=s->context.fuel,begin=timing_now();'),
    ('uint64_t end=timing_now(),benchmark_fuel=initial-s->context.fuel;', 'uint64_t end=timing_now(),benchmark_fuel=initial-s->context.fuel;diag_ic(&di1,&dc1);fprintf(stderr,"DIAG_IC instructions=%llu cycles=%llu\\n",(unsigned long long)(di1-di0),(unsigned long long)(dc1-dc0));')]


def check_timer_loader():
    with tempfile.TemporaryDirectory() as t:
        x = Path(t) / 'loader.c'; shutil.copyfile(R.REPO / 'seed/bootstrap/adopted-loader-20261012.c', x)
        q = subprocess.run(['patch', '-s', str(x)], stdin=open(R.PKG / 'harness/separated-loader.diff'), capture_output=True, text=True)
        ok = q.returncode == 0 and x.read_bytes() == (R.PKG / 'harness/separated-loader.c').read_bytes()
    if not ok: raise SystemExit('harness/separated-loader.c is not adopted-loader-20261012.c + harness/separated-loader.diff')
    return R.sha_file(R.PKG / 'harness/separated-loader.c')


def find_image(d, w):
    for name in [w + '.kseed', 'official-' + w + '.kseed']:
        if (Path(d) / name).is_file(): return Path(d) / name
    raise SystemExit('no kseed for %s in %s' % (w, d))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True, type=Path); ap.add_argument('--images', type=Path, default=R.PKG / 'images')
    ap.add_argument('--only'); ap.add_argument('--count-instructions', action='store_true')
    a = ap.parse_args(); R.require_macos_arm64()
    loader_sha = check_timer_loader()
    out = R.fresh_dir(a.out); W = {e['workload']: e for e in R.load('harness/workloads.json')}
    E = {e['workload']: e for e in R.load('records/round/expected-accounting-mw.json')}
    measured = R.load('expected/measured-images.json'); pre = {x['workload']: x for x in R.load('records/round/preregistration.json')['workloads']}
    E1 = {e['workload']: e for e in R.load('reference/expected-original-accounting-m1.json')}
    rows = []; names = a.only.split(',') if a.only else sorted(W)
    for w in names:
        e = W[w]; exports, image = R.kseed_parts(find_image(a.images, w).read_bytes())
        same = R.sha(image) == measured[w]['native']['sha256'] and exports == measured[w]['exports']
        timer = R.build_timer(out / w, R.PKG / 'harness', image, exports, e)
        run = R.run_timer(timer, e['n'], R.caps_for(w, e['extraCaps'])); ok = R.exact(run, E[w])
        row = dict(workload=w, multiplier=e['multiplier'], n=e['n'], imageSHA256=R.sha(image), imageIdenticalToMeasured=same, exact=ok,
                   benchmarkFuel=(run['sample'] or {}).get('benchmarkFuel'), localElapsedNsNotAResult=run['elapsedNs'], stderr=run['stderr'])
        if a.count_instructions:
            ct = R.build_timer(out / (w + '-count'), R.PKG / 'harness', image, exports, e, DIAG_PATCHES); counts = []
            for _ in range(3):
                r = R.run_timer(ct, E1[w]['n'], R.caps_for(w))
                line = [l for l in r['stderr'].splitlines() if l.startswith('DIAG_IC ')][0]; counts.append(int(line.split()[1].split('=')[1]))
                r['stderr'] = '\n'.join(l for l in r['stderr'].splitlines() if not l.startswith('DIAG_IC ')) + '\n'
                if not R.exact(r, E1[w]): raise SystemExit('instruction-count run not exact at m=1: ' + w)
            row.update(instructions=counts, preregisteredI=pre[w]['I'], relativeToPreregistered=min(counts) / pre[w]['I'])
        rows.append(row)
        print('%-15s m_w %2d n %9d exact=%s imageAsMeasured=%s%s' % (w, e['multiplier'], e['n'], ok, same,
              ('  I %.4g vs pre-registered %.4g (x%.4f)' % (min(row['instructions']), pre[w]['I'], row['relativeToPreregistered'])) if a.count_instructions else ''), flush=True)
    status = 'PASS' if all(r['exact'] for r in rows) and len(rows) == (len(names)) else 'FAIL'
    if a.count_instructions and any(abs(r['relativeToPreregistered'] - 1) > 0.02 for r in rows): status = 'FAIL'
    (out / 'report.json').write_text(json.dumps(dict(level='c-exactness', timerLoaderSHA256=loader_sha, workloads=len(rows), rows=rows, status=status), indent=1) + '\n')
    print('LEVEL_C', status, '%d/%d exact' % (sum(r['exact'] for r in rows), len(rows)))
    sys.exit(0 if status == 'PASS' else 1)


if __name__ == '__main__':
    main()
