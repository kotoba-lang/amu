#!/usr/bin/env python3
"""Observe two native reader/admission refusals on Linux x86-64.

Python stages source-locked inputs and observes a pinned native compiler; it is
not a CI gate and does not qualify general dynamic loading or backend parity.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / 'test/fixtures/selfhost/safety-boundaries'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--compiler', type=Path, required=True)
    ap.add_argument('--compiler-sha256', required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    if (platform.system(), platform.machine()) != ('Linux', 'x86_64'):
        raise ValueError('requires Linux x86-64')
    compiler = a.compiler.resolve(strict=True)
    if sha(compiler) != a.compiler_sha256:
        raise ValueError('compiler digest mismatch')
    cases = [('positive', FIXTURES / 'determinism.kotoba', None),
             ('quoted', FIXTURES / 'refusals/runtime-require-quoted.kotoba', 'E1005'),
             ('string', FIXTURES / 'refusals/runtime-require-string.kotoba', 'E2101')]
    inputs = [compiler, Path(__file__).resolve(), *[p for _, p, _ in cases]]
    pins = {str(p): sha(p) for p in inputs}
    out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    env = {'PATH': '/nonexistent', 'LANG': 'C', 'KEXE_CAP_RESOURCES_35': str(out), 'KEXE_STACK_BYTES': '8388608'}
    observations = []
    for name, source, diagnostic in cases:
        root = out / name; root.mkdir(); entry = root / 'main.kotoba'; shutil.copyfile(source, entry)
        lock = root / 'source.ksl'
        lock.write_text('KSL1\nentry ' + str(entry) + '\nroot ' + str(root) + '\nfile ' + sha(entry) + ' ' + str(entry) + '\n')
        artifact = root / 'output.kx64'
        r = subprocess.run([str(compiler), 'compile', str(entry), '--target', 'x86_64-linux', '--output', str(artifact),
                            '--format', 'kx64-v1', '--source-path', str(root), '--source-lock', str(lock),
                            '--source-lock-sha256', sha(lock)], cwd=out, env=env, capture_output=True, timeout=180)
        if diagnostic is None:
            if r.returncode or r.stderr or not artifact.is_file(): raise ValueError((name, r.returncode, r.stderr[-400:]))
        elif r.returncode == 0 or diagnostic.encode() not in r.stderr or artifact.exists():
            raise ValueError((name, r.returncode, r.stderr[-400:], artifact.exists()))
        observations.append({'case': name, 'exit': r.returncode, 'diagnostic': diagnostic, 'artifact': artifact.exists(),
                             'sourceSha256': sha(entry), 'sourceLockSha256': sha(lock)})
    if any(sha(Path(p)) != h for p, h in pins.items()): raise ValueError('input changed')
    receipt = {'status': 'PASS_NATIVE_REQUIRE_REFUSALS_LINUX', 'inputs': pins, 'observations': observations,
               'positiveCompileOnly': True, 'generalDynamicLoadingQualified': False, 'backendParityQualified': False}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n'); print(receipt['status'])


if __name__ == '__main__':
    main()
