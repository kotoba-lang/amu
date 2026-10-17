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


def owned_path(name):
    path = (ROOT / name).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        raise SystemExit('input must be a repository-owned file: ' + str(name))
    return path


def inputs(receipt_path):
    receipt_path = owned_path(receipt_path)
    receipt = json.loads(receipt_path.read_text())
    for row in receipt['sourceFiles']:
        path = owned_path(row['path'])
        if path.stat().st_size != row['bytes'] or digest(path) != row['sha256']:
            raise SystemExit('source pin mismatch: ' + row['path'])
    paths = [line.strip() for line in owned_path(receipt.get('manifestPath', 'seed/MANIFEST')).read_text().splitlines()
             if line.strip() and not line.startswith('#')]
    module_count = receipt.get('moduleCount', len(paths))
    if len(paths) != module_count:
        raise SystemExit(f'expected {module_count} modules from the receipt, found {len(paths)}')
    unity = b''.join(owned_path(path).read_bytes() + b'\n' for path in paths)
    if hashlib.sha256(unity).hexdigest() != receipt['sourceUnitySHA256']:
        raise SystemExit('unity pin mismatch')
    producer = owned_path(receipt.get('bootstrapPath', 'seed/bootstrap/adopted-20261012.bin'))
    loader_source = owned_path(receipt.get('loaderPath', 'seed/bootstrap/adopted-loader-20261012.c'))
    expected_producer_sha256 = receipt.get('bootstrapSHA256', receipt['nativeImageSHA256'])
    if digest(producer) != expected_producer_sha256:
        raise SystemExit('native producer pin mismatch')
    if digest(loader_source) != receipt['loaderSourceSHA256']:
        raise SystemExit('trusted C loader source pin mismatch')
    return receipt, unity, producer, loader_source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--receipt', type=Path, default=ROOT / 'seed/adoption-20261018.json')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--generations', type=int, choices=[1, 2, 3], default=3)
    args = parser.parse_args()
    receipt, unity, producer, loader_source = inputs(args.receipt.resolve())
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
    host = out / 'host'
    artifacts = out / 'artifacts'
    host.mkdir()
    artifacts.mkdir()
    source = artifacts / 'seed-unity.kotoba'
    source.write_bytes(unity)
    calls = []
    def run(argv, name, env):
        row = {'name': name, 'argv': [str(x) for x in argv]}
        loader_before = digest(loader) if loader.exists() else None
        producer_before = digest(producer)
        source_before = digest(source)
        with (host / (name + '.stdout')).open('wb') as stdout, \
             (host / (name + '.stderr')).open('wb') as stderr:
            result = subprocess.run(row['argv'], cwd=artifacts, env=env,
                                    stdout=stdout, stderr=stderr, timeout=1800)
        if digest(producer) != producer_before or digest(source) != source_before:
            raise SystemExit('compiler input changed during native invocation')
        if loader_before is not None and digest(loader) != loader_before:
            raise SystemExit('host loader changed during native invocation')
        row['exit'] = result.returncode
        calls.append(row)
        (host / 'calls.json').write_text(json.dumps(calls, indent=2) + '\n')
        if result.returncode != 0:
            raise SystemExit('failed ' + name + '; raw logs preserved')
    env = dict(os.environ)
    env.update(KEXE_COMMAND='1', KEXE_CAP_RESOURCES_35=str(artifacts),
               KEXE_FUEL='off', KEXE_VECTORS='4194304',
               KEXE_VECTOR_ITEMS='134217728', KEXE_STRING_POOL='268435456',
               KEXE_PAIRS='16777216', KEXE_CPU_SECONDS='1800',
               KEXE_WALL_SECONDS='1800', TMPDIR=str(artifacts))
    loader = host / 'kexe-loader'
    run(['clang', '-std=c11', '-O2', loader_source, '-o', loader], 'loader-build', env)
    images = []
    for generation in range(1, args.generations + 1):
        prefix = [loader, producer, '0', '0', 'aarch64', '35,37,38,39', '--']
        container = artifacts / ('G'+str(generation)+'.kseed')
        native = artifacts / ('G'+str(generation)+'.bin')
        run(prefix + ['compile', source, '--target', 'aarch64-macos', '--output', container],
            'G'+str(generation)+'-compile', env)
        run(prefix + ['extract-native', container, '--symbol', 'main', '--output', native],
            'G'+str(generation)+'-extract', env)
        images.append({'generation': generation, 'bytes': native.stat().st_size,
                       'sha256': digest(native), 'containerSHA256': digest(container)})
        producer = native
    fixed_point = (len(images) >= 2
                   and images[-1]['sha256'] == images[-2]['sha256']
                   and images[-1]['containerSHA256'] == images[-2]['containerSHA256'])
    receipt_match = bool(images and images[-1]['sha256'] == receipt['nativeImageSHA256'])
    report = {'status': 'PASS_ADOPTED_NATIVE_SELF_BUILD' if fixed_point and receipt_match
              else 'FAIL_ADOPTED_NATIVE_SELF_BUILD', 'generations': images,
              'sourceUnitySHA256': receipt['sourceUnitySHA256'],
              'fixedPoint': fixed_point,
              'receiptNativeImageSHA256': receipt['nativeImageSHA256'],
              'finalImageMatchesReceipt': receipt_match,
              'CTrustedLoaderBuilt': True, 'JVMNodeOrGraalFallback': False,
              'performanceMeasurement': False,
              'performanceGoalStatus': receipt.get('performanceGoalStatus', 'unspecified')}
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    if not fixed_point:
        raise SystemExit('native self-build did not reach an image and container fixed point')
    if not receipt_match:
        raise SystemExit('final self-build image differs from the adopted fixed-point image')


if __name__ == '__main__':
    main()
