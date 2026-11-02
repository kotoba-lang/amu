#!/usr/bin/env python3
"""Run a bounded native safety-fixture probe on macOS ARM; not a full security gate.

Python stages pinned inputs, invokes the supplied native compiler and packager,
compares exit diagnostics and writes a receipt. No hosted compiler or runtime is
used. The positive program itself checks its computed results. This does not
qualify exported 6–8 argument calls, verifier/fuzz coverage, or other targets.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / 'test/fixtures/selfhost/safety-boundaries'
REFUSALS = {'internal-17': 'E2178', 'exported-9': 'E2108',
            'runtime-require-quoted': 'E1005', 'runtime-require-string': 'E2101',
            'unknown-op': 'E2101', 'unbound': 'E2102',
            'duplicate-ns': 'E2004', 'namespace-extra': 'E6021',
            'fs-empty-capabilities': 'E2176', 'fs-wrong-capability': 'E2176',
            'fs-transitive-empty': 'E2176'}
POSITIVES = {'arity-positive': (b') 136)', b') 135)'),
             'metadata-positive': (b'(sequence) 2)', b'(sequence) 3)'),
             'fs-positive': (b') 3)', b') 4)'),
             'fs-transitive-positive': (b'(helper) 3)', b'(helper) 4)')}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('compiler', 'packager', 'output'):
        ap.add_argument('--' + name, type=Path, required=True)
    a = ap.parse_args()
    if (platform.system(), platform.machine()) != ('Darwin', 'arm64'):
        raise ValueError('requires macOS ARM64')
    compiler, packager = (p.resolve(strict=True) for p in (a.compiler, a.packager))
    for p in (compiler, packager):
        subprocess.run(['/usr/bin/codesign', '--verify', '--strict', str(p)], check=True, capture_output=True, timeout=30)
    fixtures = [FIXTURES / (n + '.kotoba') for n in POSITIVES] + [FIXTURES / 'refusals' / (n + '.kotoba') for n in REFUSALS]
    inputs = [compiler, packager, Path(__file__).resolve(), *fixtures]
    pins = {str(p): sha(p) for p in inputs}
    out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    (out / 'data').write_bytes(b'abc')  # Explicit test-only FD3 file grant.
    for p in fixtures: shutil.copyfile(p, out / p.name)
    for name, (old, new) in POSITIVES.items():
        source = (out / (name + '.kotoba')).read_bytes()
        if source.count(old) != 1: raise ValueError('positive negative-control anchor changed: ' + name)
        (out / (name + '-negative-control.kotoba')).write_bytes(source.replace(old, new, 1))
    fd = os.open(out, os.O_RDONLY | os.O_DIRECTORY)
    saved = None
    try:
        if fd != 3:
            try: saved = os.dup(3)
            except OSError: pass
            os.dup2(fd, 3)
        def run(args):
            return subprocess.run(list(map(str, args)), cwd=out, env={'PATH': '/nonexistent', 'LANG': 'C'},
                                  pass_fds=(3,), capture_output=True, timeout=180)
        observations = []
        for name, expected in [(name + suffix, expected) for name in POSITIVES for suffix, expected in (('', 42), ('-negative-control', 7))]:
            image, payload, raw = out / (name + '.macho'), out / (name + '.kseed'), out / (name + '.raw')
            r = run([compiler, 'compile', '/' + name + '.kotoba', '--target', 'aarch64-macos', '--output', payload.name])
            if r.returncode or r.stderr or not payload.is_file(): raise ValueError((name, 'compile', r.returncode, r.stderr[-300:]))
            r = run([compiler, 'extract-native', payload.name, '--symbol', 'main', '--output', raw.name])
            m = re.search(rb':offset (\d+), :length (\d+), :arity 0}', r.stdout)
            if r.returncode or r.stderr or not m or int(m[2]) != raw.stat().st_size: raise ValueError((name, 'extract'))
            r = run([packager, image.name, raw.name, 'fs2-cli-stdio-general', m[1].decode()])
            if r.returncode or r.stderr: raise ValueError((name, 'package'))
            image.chmod(0o700)
            subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', str(image)], check=True, capture_output=True, timeout=30)
            r = run([image])
            if r.returncode != expected or r.stderr: raise ValueError((name, 'execute', r.returncode, r.stderr[-300:]))
            observations.append({'case': name, 'exit': r.returncode, 'sourceSha256': sha(out / (name + '.kotoba')),
                                 'payloadSha256': sha(payload), 'imageSha256': sha(image)})
        for name, diagnostic in REFUSALS.items():
            image = out / (name + '.kseed')
            r = run([compiler, 'compile', '/' + name + '.kotoba', '--target', 'aarch64-macos', '--output', image.name])
            if r.returncode == 0 or diagnostic.encode() not in r.stderr or image.exists():
                raise ValueError((name, 'refusal', r.returncode, r.stderr[-300:], image.exists()))
            observations.append({'case': name, 'exit': r.returncode, 'diagnostic': diagnostic, 'artifact': False})
    finally:
        if fd != 3:
            if saved is None: os.close(3)
            else: os.dup2(saved, 3); os.close(saved)
        os.close(fd)
    if any(sha(p) != pins[str(p)] for p in inputs): raise ValueError('input changed during probe')
    receipt = {'status': 'PASS_NATIVE_SAFETY_BOUNDARY_SLICE', 'inputs': pins, 'observations': observations,
               'target': 'aarch64-macos', 'fullSafetyQualification': False, 'nativeControllerGate': False}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(receipt['status'])


if __name__ == '__main__':
    main()
