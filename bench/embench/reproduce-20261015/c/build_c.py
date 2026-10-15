#!/usr/bin/env python3
"""Build the 19 original Embench C benchmarks exactly as the C arm's binaries were built (round65, frozen and reused).

  python3 bench/embench/reproduce-20261015/c/build_c.py --upstream <embench-iot at 09c2ed8c> --out <new-dir> [--cc /usr/bin/clang]

Per workload w (sources = sorted upstream/src/w/*.c):
  clang -O2 -std=gnu11 -DWARMUP_HEAT=1 -DGLOBAL_SCALE_FACTOR=32768 -I upstream/support -I upstream/src/w <sources>
        upstream/support/main.c upstream/support/beebsc.c c/boardsupport.c -lm -o <out>/w
c/boardsupport.c (sha256 0e58ae7a...) times start_trigger..stop_trigger with CLOCK_MONOTONIC_RAW and prints EMBENCH_NS=<ns>.
The official binaries were built with Apple clang 17.0.0 (clang-1700.6.4.2) on macOS 26.2 arm64; their hashes are listed in
records/fresh-C/source-custody.json. A different clang produces different (equally valid) binaries; this is reported, not an error."""
import argparse, json, re, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import repro_lib as R
GSF = 32768
BOARDSUPPORT_SHA256 = '0e58ae7ab3c9f813e4fd7b2738bb60a39c2f3d8da57168b00163c9b7f7cd02c0'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--upstream', required=True, type=Path); ap.add_argument('--out', required=True, type=Path); ap.add_argument('--cc', default='/usr/bin/clang')
    a = ap.parse_args(); R.require_macos_arm64()
    up = a.upstream.resolve(); bs = R.PKG / 'c/boardsupport.c'; assert R.sha_file(bs) == BOARDSUPPORT_SHA256, 'boardsupport.c pin'
    frozen = R.load('records/fresh-C/source-custody.json')['binaries']; baseline = json.loads((up / 'baseline-data/speed.json').read_text())
    names = sorted(baseline); assert len(names) == 19
    max_lsf = max(int(m[1]) for n in names for p in (up / 'src' / n).glob('*.c') for m in re.finditer(r'#define\s+LOCAL_SCALE_FACTOR\s+(\d+)', p.read_text()))
    assert max_lsf * GSF < 2147483647, 'scaled loop signed overflow'
    out = R.fresh_dir(a.out); rows = []
    version = subprocess.run([a.cc, '--version'], capture_output=True, text=True).stdout
    for n in names:
        d = out / n; d.mkdir()
        cmd = [a.cc, '-O2', '-std=gnu11', '-DWARMUP_HEAT=1', '-DGLOBAL_SCALE_FACTOR=%d' % GSF, '-I', up / 'support', '-I', up / 'src' / n,
               *sorted((up / 'src' / n).glob('*.c')), up / 'support/main.c', up / 'support/beebsc.c', bs, '-lm', '-o', d / n]
        q = subprocess.run(list(map(str, cmd)), capture_output=True, text=True)
        if q.returncode: raise SystemExit('C build failed for %s: %s' % (n, q.stderr[-1000:]))
        h = R.sha_file(d / n); rows.append(dict(workload=n, sha256=h, frozenSHA256=frozen[n]['sha256'], identicalToFrozen=h == frozen[n]['sha256'],
                                                 argv=[str(x).replace(str(up), '<upstream>').replace(str(R.PKG), '<package>').replace(str(out), '<out>') for x in cmd]))
        print('%-15s %s %s' % (n, h[:16], 'identical to the frozen official binary' if rows[-1]['identicalToFrozen'] else 'differs from the frozen binary (compiler version)'), flush=True)
    (out / 'build-c.json').write_text(json.dumps(dict(compiler=version, gsf=GSF, rows=rows), indent=1) + '\n')
    print('C_BUILD done: %d binaries, %d identical to the frozen official ones' % (len(rows), sum(r['identicalToFrozen'] for r in rows)))


if __name__ == '__main__':
    main()
