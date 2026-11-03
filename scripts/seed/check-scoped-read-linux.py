#!/usr/bin/env python3
"""Exercise KFR1 in an isolated Linux container using an Amu compiler.

Python stages and observes; the compiler, packaged runner and guest are
Amu-built native artifacts. This does not qualify the Darwin runtime.
"""
import argparse
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--compiler', type=Path, required=True)
ap.add_argument('--output', type=Path, required=True)
ap.add_argument('--arch', choices=['arm64', 'amd64'], default='arm64')
args = ap.parse_args()
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=False)
spec = importlib.util.spec_from_file_location('mac', ROOT / 'scripts/seed/check-aiueos-user-macos-native.py')
mac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mac)
compiler = args.compiler.resolve(strict=True)
source = ROOT / 'seed/tests/scoped-read/probe.kotoba'
(out / 'probe.kotoba').write_bytes(source.read_bytes())
(out / 'binary.kotoba').write_bytes((ROOT / 'seed/tests/scoped-read/binary.kotoba').read_bytes())
(out / 'runner.kotoba').write_bytes((ROOT / 'seed/x86_64-kx64-runner.kotoba').read_bytes())
if args.arch == 'arm64':
    mac.native_run(compiler, out, 'compile', 'probe.kotoba', '--target', 'aarch64-macos', '--output', 'probe.kseed')
    mac.native_run(compiler, out, 'compile', 'runner.kotoba', '--target', 'aarch64-linux', '--output', 'probe.elf',
                   '--format', 'packed', '--payload', 'probe.kseed')
else:
    mac.native_run(compiler, out, 'compile', 'probe.kotoba', '--target', 'x86_64-linux', '--output', 'probe.elf',
                   '--format', 'static')
(out / 'probe.elf').chmod(0o755)
if args.arch == 'arm64':
    mac.native_run(compiler, out, 'compile', 'binary.kotoba', '--target', 'aarch64-macos', '--output', 'binary.kseed')
    mac.native_run(compiler, out, 'compile', 'runner.kotoba', '--target', 'aarch64-linux', '--output', 'binary.elf',
                   '--format', 'packed', '--payload', 'binary.kseed')
else:
    mac.native_run(compiler, out, 'compile', 'binary.kotoba', '--target', 'x86_64-linux', '--output', 'binary.elf',
                   '--format', 'static')
(out / 'binary.elf').chmod(0o755)
image = 'docker.io/library/python:3.12-alpine' if args.arch == 'arm64' else 'localhost/jun555-linux:amd64'
info = subprocess.run(['podman', 'image', 'inspect', image, '--format', '{{.Id}} {{.Architecture}}'],
                      check=True, capture_output=True, text=True, timeout=30).stdout.strip()
if not info.endswith(' ' + args.arch):
    raise ValueError('local architecture-matched test image required')
observer = ROOT / 'scripts/seed/observe-scoped-read-linux.py'
run = subprocess.run(['podman', 'run', '--rm', '--pull', 'never', '--network', 'none', '--platform', 'linux/' + args.arch,
                      '-v', str(out) + ':/work:rw', '-v', str(observer) + ':/observer.py:ro', image,
                      'python3', '/observer.py'], capture_output=True, text=True, timeout=180)
if run.returncode:
    raise ValueError((run.returncode, run.stdout, run.stderr))
receipt = json.loads((out / 'scoped-read-result.json').read_text())
if args.arch == 'arm64':
    fault = out / 'fault'
    fault.mkdir()
    (fault / 'probe.elf').write_bytes((out / 'probe.elf').read_bytes())
    (fault / 'probe.elf').chmod(0o755)
    profile = out / 'pread-eio.json'
    profile.write_text(json.dumps({'defaultAction': 'SCMP_ACT_ALLOW', 'architectures': ['SCMP_ARCH_AARCH64'],
        'syscalls': [{'names': ['pread64'], 'action': 'SCMP_ACT_ERRNO', 'errnoRet': 5,
                      'args': [{'index': 2, 'value': 6, 'op': 'SCMP_CMP_EQ'}]}]}))
    failed = subprocess.run(['podman', 'run', '--rm', '--pull', 'never', '--network', 'none',
        '--platform', 'linux/arm64', '--security-opt', 'seccomp=' + str(profile),
        '-v', str(fault) + ':/work:rw', '-v', str(observer) + ':/observer.py:ro', image,
        'python3', '/observer.py', 'pread-fault'], capture_output=True, text=True, timeout=180)
    if failed.returncode:
        raise ValueError(('fault', failed.returncode, failed.stdout, failed.stderr))
    receipt['preadFault'] = json.loads((fault / 'fault-result.json').read_text())
receipt.update(compilerSha256=hashlib.sha256(compiler.read_bytes()).hexdigest(), image=info,
               sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest(),
               elfSha256=hashlib.sha256((out / 'probe.elf').read_bytes()).hexdigest(),
               scope='Linux ' + args.arch + ', isolated synthetic data; seccomp if available; fleet integration unqualified')
(out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print('PASS_SCOPED_READ_LINUX_' + args.arch.upper(), flush=True)
