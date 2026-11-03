#!/usr/bin/env python3
"""Record native `into` alias observations; this is not a conformance gate.

The same source runs on native macOS ARM64 or Linux x86-64/ARM64. No expected
value is asserted: semantics across mutation and aliases are not settled here.
"""
import argparse
import hashlib
import json
import platform
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'seed/tests/kototama-into-alias-observation.kotoba'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--compiler', type=Path, required=True)
    p.add_argument('--compiler-sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    system, machine = platform.system(), platform.machine()
    if (system, machine) not in (('Darwin', 'arm64'), ('Linux', 'x86_64'), ('Linux', 'aarch64')):
        raise ValueError('native macOS ARM64 or native Linux x86-64/ARM64 required')
    compiler = a.compiler.resolve(strict=True)
    if sha(compiler) != a.compiler_sha256:
        raise ValueError('compiler digest mismatch')
    out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    binary = out / ('probe' if system == 'Darwin' else 'probe.elf')
    source = out / 'probe.kotoba'
    source.write_bytes(SOURCE.read_bytes())
    env = {'PATH': '/nonexistent', 'LANG': 'C', 'KEXE_CAP_RESOURCES_35': str(out),
           'KEXE_STACK_BYTES': '8388608'}
    cmd = [str(compiler), 'compile', str(source)]
    if system == 'Darwin':
        cmd += ['-o', str(binary)]
    else:
        cmd += ['--target', 'x86_64-linux' if machine == 'x86_64' else 'aarch64-linux',
                '--output', str(binary), '--format', 'static']
    built = subprocess.run(cmd, cwd=out, env=env, capture_output=True, timeout=300)
    (out / 'compile.stdout').write_bytes(built.stdout); (out / 'compile.stderr').write_bytes(built.stderr)
    if built.returncode or built.stderr or not binary.is_file():
        raise RuntimeError('native compile failed: ' + built.stderr.decode(errors='replace')[-500:])
    binary.chmod(0o700)
    runenv = dict(env, KEXE_ALLOW='-', KEXE_FUEL='off', KEXE_STRUCTURED_REPORT='1')
    result = subprocess.run([str(binary)], cwd=out, env=runenv, capture_output=True, timeout=30)
    (out / 'run.stdout').write_bytes(result.stdout); (out / 'run.stderr').write_bytes(result.stderr)
    if result.returncode or result.stderr:
        raise RuntimeError('native observation failed: ' + result.stderr.decode(errors='replace')[-500:])
    pattern = rb'^(-?[0-9]+)\s*$' if system == 'Darwin' else rb':status :ok\s+:result (-?[0-9]+)\b'
    match = re.search(pattern, result.stdout)
    if not match:
        raise ValueError('unrecognized native result')
    number = int(match[1])
    if sha(source) != sha(SOURCE):
        raise ValueError('source changed during observation')
    record = {'schema': 'amu.into-alias-observation.v1', 'system': system, 'machine': machine,
              'sourceSha256': sha(SOURCE), 'compilerSha256': sha(compiler), 'binarySha256': sha(binary),
              'encodedResult': number, 'semanticDecision': 'unsettled', 'conformanceQualified': False}
    (out / 'observation.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
