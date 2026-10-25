#!/usr/bin/env python3
"""Build fresh original Embench C binaries from the pinned upstream source for the selected host's timing campaign.

  python3 bench/embench/reproduce-20261015/c/build_c.py --upstream <embench-iot at 09c2ed8c> --out <new-dir> [--cc /usr/bin/clang]

Per workload w (sources = sorted upstream/src/w/*.c), use:
  clang -O2 -std=gnu11 -DWARMUP_HEAT=1 -DGLOBAL_SCALE_FACTOR=32768 -I upstream/support -I upstream/src/w <sources>
        upstream/support/main.c upstream/support/beebsc.c c/boardsupport.c -lm -o <out>/w
c/boardsupport.c (sha256 0e58ae7a...) times start_trigger..stop_trigger with CLOCK_MONOTONIC_RAW and prints EMBENCH_NS=<ns>.
The compiler version, command lines and output hashes are recorded in build-c.json. The historical M93 binary hashes are
also included as a diagnostic comparison; a different clang produces different (equally valid) fresh binaries."""
import argparse, json, re, shutil, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import repro_lib as R
GSF = 32768
UPSTREAM_COMMIT = '09c2ed8c3b7008c95d08b038de4a3f6dc103ed70'
FLAGS = ['-O2', '-std=gnu11', '-DWARMUP_HEAT=1', '-DGLOBAL_SCALE_FACTOR=%d' % GSF]
BOARDSUPPORT_SHA256 = '0e58ae7ab3c9f813e4fd7b2738bb60a39c2f3d8da57168b00163c9b7f7cd02c0'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--upstream', required=True, type=Path); ap.add_argument('--out', required=True, type=Path); ap.add_argument('--cc', default='/usr/bin/clang')
    a = ap.parse_args(); R.require_macos_arm64()
    up = a.upstream.resolve(); bs = R.PKG / 'c/boardsupport.c'; assert R.sha_file(bs) == BOARDSUPPORT_SHA256, 'boardsupport.c pin'
    upstream_commit = subprocess.run(['git', '-C', str(up), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    assert upstream_commit == UPSTREAM_COMMIT, 'upstream must be the pinned Embench source commit'
    changed = subprocess.run(['git', '-C', str(up), 'diff', '--quiet', 'HEAD', '--', 'src', 'support'])
    untracked = subprocess.run(['git', '-C', str(up), 'ls-files', '--others', '--exclude-standard', '--', 'src', 'support'],
                               capture_output=True, text=True, check=True).stdout.splitlines()
    assert changed.returncode == 0 and not [p for p in untracked if Path(p).suffix in {'.c', '.h'}], \
        'pinned C source checkout is modified or has untracked C/header inputs'
    frozen = R.load('records/fresh-C/source-custody.json')['binaries']; baseline = json.loads((up / 'baseline-data/speed.json').read_text())
    names = sorted(baseline); assert len(names) == 19
    max_lsf = max(int(m[1]) for n in names for p in (up / 'src' / n).glob('*.c') for m in re.finditer(r'#define\s+LOCAL_SCALE_FACTOR\s+(\d+)', p.read_text()))
    assert max_lsf * GSF < 2147483647, 'scaled loop signed overflow'
    out = R.fresh_dir(a.out); rows = []
    found_compiler = shutil.which(a.cc)
    if found_compiler is None: raise SystemExit('C compiler not found: ' + a.cc)
    compiler_path = str(Path(found_compiler).resolve())
    version = subprocess.run([compiler_path, '--version'], capture_output=True, text=True, check=True).stdout
    for n in names:
        d = out / n; d.mkdir()
        src = sorted((up / 'src' / n).glob('*.c'))
        common = [up / 'support/main.c', up / 'support/beebsc.c']
        cmd = [compiler_path, *FLAGS, '-I', up / 'support', '-I', up / 'src' / n,
               *src, *common, bs, '-lm', '-o', d / n]
        q = subprocess.run(list(map(str, cmd)), capture_output=True, text=True)
        if q.returncode: raise SystemExit('C build failed for %s: %s' % (n, q.stderr[-1000:]))
        h = R.sha_file(d / n)
        compile_sources = [*src, *common]
        source_paths = sorted(set([*compile_sources, *sorted((up / 'src' / n).glob('*.h')),
                                   *sorted((up / 'support').glob('*.h'))]),
                              key=lambda x: x.relative_to(up).as_posix())
        argv_template = ['<compiler>', *FLAGS, '-I', '<upstream>/support', '-I', '<upstream>/src/' + n,
                         *['<upstream>/' + x.relative_to(up).as_posix() for x in compile_sources],
                         '<package>/c/boardsupport.c', '-lm', '-o', '<out>/' + n + '/' + n]
        rows.append(dict(workload=n, sha256=h, bytes=(d / n).stat().st_size, frozenSHA256=frozen[n]['sha256'],
                         identicalToFrozen=h == frozen[n]['sha256'],
                         sourceHashes={x.relative_to(up).as_posix(): R.sha_file(x) for x in source_paths},
                         argvTemplate=argv_template,
                         argv=[str(x).replace(str(up), '<upstream>').replace(str(R.PKG), '<package>').replace(str(out), '<out>') for x in cmd]))
        print('%-15s %s %s' % (n, h[:16], 'identical to the frozen official binary' if rows[-1]['identicalToFrozen'] else 'differs from the frozen binary (compiler version)'), flush=True)
    (out / 'build-c.json').write_text(json.dumps(dict(schemaVersion=2, upstreamCommit=upstream_commit, globalScaleFactor=GSF,
                                                       boardsupportSHA256=R.sha_file(bs),
                                                       compiler=dict(path=compiler_path, version=version), rows=rows), indent=1) + '\n')
    print('C_BUILD done: %d binaries, %d identical to the frozen official ones' % (len(rows), sum(r['identicalToFrozen'] for r in rows)))


if __name__ == '__main__':
    main()
