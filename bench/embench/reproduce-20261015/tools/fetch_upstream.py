#!/usr/bin/env python3
"""Fetch Embench IoT upstream at the exact commit the round used and verify it.

  python3 bench/embench/reproduce-20261015/tools/fetch_upstream.py --dest <new-dir> [--url <git url>]

Default URL: https://github.com/embench/embench-iot.git ; commit 09c2ed8c3b7008c95d08b038de4a3f6dc103ed70.
Verifies the 40 C source/support/baseline files of the C arm's source custody and the 6 driver files (benchmark_speed.py and
pylib/*) that both arms ran. Embench IoT is GPL-3.0-or-later (sources carry their own notices); it is fetched, not vendored."""
import argparse, json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import repro_lib as R

COMMIT = '09c2ed8c3b7008c95d08b038de4a3f6dc103ed70'
DRIVER = {'benchmark_speed.py': 'decab87cc8eb4a714ceb1387fe4d4ce8c38464d61a8572f1d3298af75a87a828',
          'pylib/embench_core.py': '7675a4368f1c38eaffc163a4c9e00fc0373f0c3c447c639366e844b7c1793b30',
          'pylib/run_gdbserver_sim.py': 'f298cf88f5feda7e869d3de5f7fa6ea56e4f64e4ed633ff0afbb180f6aab2c9d',
          'pylib/run_native.py': '639c0db4ee8a9778c1551edc292457a816d1d3019989e1ffef50c2c4009abdbe',
          'pylib/run_stm32f4-discovery.py': '92b3f895412193f5f5bfb530cc69fe8191d74f16b5257f9ae8bba9e4e7de87c2',
          'pylib/run_wally.py': 'cf1e66674c9cdb1ac7b187f4a0ff2ae2bb6cc1c3e791fceb0a9b151077a40bcd'}


def verify(dest):
    dest = Path(dest); bad = []
    head = subprocess.run(['git', '-C', str(dest), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    if head != COMMIT: bad.append('HEAD %s != %s' % (head, COMMIT))
    src = R.load('records/fresh-C/source-custody.json')['sourceHashes']
    for rel, h in list(src.items()) + list(DRIVER.items()):
        p = dest / rel
        if not p.is_file() or R.sha_file(p) != h: bad.append(rel)
    return dict(commit=head, sourceFiles=len(src), driverFiles=len(DRIVER), mismatches=bad)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dest', required=True, type=Path); ap.add_argument('--url', default='https://github.com/embench/embench-iot.git')
    ap.add_argument('--verify-only', action='store_true')
    a = ap.parse_args()
    if not a.verify_only:
        if a.dest.exists(): raise SystemExit('destination exists: ' + str(a.dest))
        subprocess.run(['git', 'clone', '--quiet', a.url, str(a.dest)], check=True)
        subprocess.run(['git', '-C', str(a.dest), 'checkout', '--quiet', '--detach', COMMIT], check=True)
    r = verify(a.dest); print(json.dumps(r))
    print('UPSTREAM', 'PASS' if not r['mismatches'] else 'FAIL')
    sys.exit(0 if not r['mismatches'] else 1)


if __name__ == '__main__':
    main()
