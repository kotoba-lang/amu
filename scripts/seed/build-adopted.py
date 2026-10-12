#!/usr/bin/env python3
"""Bootstrap orchestration only: pinned native selfhost, no JVM/Node fallback."""
import argparse
import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs():
    receipt = json.loads((ROOT / 'seed/adoption-20261012.json').read_text())
    for row in receipt['sourceFiles']:
        path = ROOT / row['path']
        if path.stat().st_size != row['bytes'] or digest(path) != row['sha256']:
            raise SystemExit('source pin mismatch: ' + row['path'])
    paths = [line.strip() for line in (ROOT / 'seed/MANIFEST').read_text().splitlines()
             if line.strip() and not line.startswith('#')]
    if len(paths) != 16:
        raise SystemExit('expected the reviewed 16-module source closure')
    unity = b''.join((ROOT / path).read_bytes() + b'\n' for path in paths)
    if hashlib.sha256(unity).hexdigest() != receipt['sourceUnitySHA256']:
        raise SystemExit('unity pin mismatch')
    producer = ROOT / 'seed/bootstrap/adopted-20261012.bin'
    loader_source = ROOT / 'seed/bootstrap/adopted-loader-20261012.c'
    if digest(producer) != receipt['nativeImageSHA256']:
        raise SystemExit('native producer pin mismatch')
    if digest(loader_source) != receipt['loaderSourceSHA256']:
        raise SystemExit('trusted C loader source pin mismatch')
    return receipt, unity, producer, loader_source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--generations', type=int, choices=[1, 2, 3], default=3)
    args = parser.parse_args()
    receipt, unity, producer, loader_source = inputs()
    if args.verify_only:
        print(json.dumps({'status': 'PASS_ADOPTED_SOURCE_AND_BOOTSTRAP_PINS',
                          'sourceUnitySHA256': receipt['sourceUnitySHA256']}))
        return
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise SystemExit('this pinned native bootstrap requires macOS arm64')
    if args.output is None:
        raise SystemExit('--output is required; use a new dedicated workspace')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = out / 'seed-unity.kotoba'
    source.write_bytes(unity)
    calls = []
    def run(argv, name, env):
        row = {'name': name, 'argv': [str(x) for x in argv]}
        with (out / (name + '.stdout')).open('wb') as stdout, \
             (out / (name + '.stderr')).open('wb') as stderr:
            result = subprocess.run(row['argv'], cwd=out, env=env,
                                    stdout=stdout, stderr=stderr, timeout=1800)
        row['exit'] = result.returncode
        calls.append(row)
        (out / 'calls.json').write_text(json.dumps(calls, indent=2) + '\n')
        if result.returncode != 0:
            raise SystemExit('failed ' + name + '; raw logs preserved')
    env = dict(os.environ)
    env.update(KEXE_COMMAND='1', KEXE_CAP_RESOURCES_35=str(ROOT)+':'+str(out),
               KEXE_FUEL='off', KEXE_VECTORS='4194304',
               KEXE_VECTOR_ITEMS='134217728', KEXE_STRING_POOL='268435456',
               KEXE_PAIRS='16777216', KEXE_CPU_SECONDS='1800',
               KEXE_WALL_SECONDS='1800', TMPDIR=str(out))
    loader = out / 'kexe-loader'
    run(['clang', '-std=c11', '-O2', loader_source, '-o', loader], 'loader-build', env)
    images = []
    for generation in range(1, args.generations + 1):
        prefix = [loader, producer, '0', '0', 'aarch64', '35,37,38,39', '--']
        container = out / ('G'+str(generation)+'.kseed')
        native = out / ('G'+str(generation)+'.bin')
        run(prefix + ['compile', source, '--target', 'aarch64-macos', '--output', container],
            'G'+str(generation)+'-compile', env)
        run(prefix + ['extract-native', container, '--symbol', 'main', '--output', native],
            'G'+str(generation)+'-extract', env)
        if digest(native) != receipt['nativeImageSHA256']:
            raise SystemExit('self-build differs from the adopted fixed-point image')
        images.append({'generation': generation, 'bytes': native.stat().st_size,
                       'sha256': digest(native), 'containerSHA256': digest(container)})
        producer = native
    report = {'status': 'PASS_ADOPTED_NATIVE_SELF_BUILD', 'generations': images,
              'sourceUnitySHA256': receipt['sourceUnitySHA256'],
              'CTrustedLoaderBuilt': True, 'JVMNodeOrGraalFallback': False,
              'performanceMeasurement': False, 'performanceGoalStatus': 'paused'}
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
